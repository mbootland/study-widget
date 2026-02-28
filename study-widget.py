import tkinter as tk
import itertools
import json
import os
from PIL import Image, ImageTk, ImageSequence

# CONFIG
BG_COLOR = "#000000"       # Black
FG_COLOR = "#FFA500"       # Orange
CORRECT_COLOR = "#00E676"  # Strong Green
WRONG_COLOR = "#616161"    # Grey 700
TIMER_COLOR = "#FF5252"    # Red Accent 200
PAUSE_COLOR = "#B0BEC5"    # Blue Grey 200

FONT_Q = ("Consolas", 18)
FONT_A = ("Consolas", 15)
FONT_TIMER = ("Consolas", 13)
FONT_EXPL = ("Consolas", 14, "italic")

READ_TIME_SEC = 30
REVEAL_TIME_SEC = 10

class StudyWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("GCP Quiz Overlay")
        self.root.configure(bg=BG_COLOR)
        
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)

        self.base_width = 500
        self.base_height = 200
        self.width = self.base_width
        self.height = self.base_height
        
        screen_width = self.root.winfo_screenwidth()
        x_pos = screen_width - self.width - 40
        y_pos = 40
        self.root.geometry(f"{self.width}x{self.height}+{x_pos}+{y_pos}")

        self.timer_job = None
        self.anim_job = None
        self.remaining_sec = 0
        self.reveal_remaining_sec = 0
        self.is_paused = False
        self.has_moved = False

        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        self.root.bind("<ButtonRelease-1>", self.check_click_pause)
        self.root.bind("<Button-3>", self.skip_step)
        self.root.bind("<Button-2>", lambda e: root.quit())

        # Load GIF using Pillow for resizing
        self.frames = []
        self.frame_idx = 0
        self.pil_frames = [] # Keep original PIL images for resizing
        
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            gif_path = os.path.join(script_dir, "fireplace.gif")
            
            # Open the GIF
            gif_img = Image.open(gif_path)
            
            # Extract all frames
            for frame in ImageSequence.Iterator(gif_img):
                # Convert to RGBA
                frame = frame.convert("RGBA")
                
                # Create a darkened version for better text readability
                # Create a semi-transparent black overlay
                overlay = Image.new("RGBA", frame.size, (0, 0, 0, 150)) # 150/255 opacity
                
                # Composite overlay on top of frame
                darkened_frame = Image.alpha_composite(frame, overlay)
                
                self.pil_frames.append(darkened_frame)
            
            print(f"Loaded {len(self.pil_frames)} frames from fireplace.gif")
            
            # Initial resize of frames
            self.resize_frames(self.width, self.height)
            
        except Exception as e:
            print(f"Could not load GIF with Pillow: {e}")

        # Create Background Canvas for GIF
        self.canvas = tk.Canvas(root, bg=BG_COLOR, highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.canvas.bind("<Button-1>", self.start_move)
        self.canvas.bind("<B1-Motion>", self.do_move)

        self.load_questions()
        self.quiz_cycle = itertools.cycle(self.questions)
        self.current_q = next(self.quiz_cycle)

        # Start GIF loop if frames loaded
        if self.frames:
            self.animate_gif()
        
        # Initial Render
        self.render_ui()
        self.update_timer()

    def resize_frames(self, width, height):
        self.frames = [] # Clear old PhotoImages
        for pil_frame in self.pil_frames:
            # Resize using LANCZOS for quality
            resized = pil_frame.resize((width, height), Image.Resampling.LANCZOS)
            self.frames.append( ImageTk.PhotoImage(resized) )
            
    def animate_gif(self):
        if not self.frames:
            return
        
        # If window size changed significantly, we might want to resize frames here?
        # But resizing every frame every loop is too slow.
        # We only resize when window geometry changes in resize_window
        
        frame = self.frames[self.frame_idx]
        self.frame_idx = (self.frame_idx + 1) % len(self.frames)
        
        # Center coordinates
        cx = self.width // 2
        cy = self.height // 2
        
        self.canvas.delete("bg_img")
        self.canvas.create_image(cx, cy, image=frame, tags="bg_img")
        self.canvas.tag_lower("bg_img")
        
        self.anim_job = self.root.after(100, self.animate_gif)

    def render_ui(self):
        self.canvas.delete("ui_text")
        
        wrap_w = self.width - 40
        
        # Question Text
        q_text = f"Q{self.current_q['id']}: {self.current_q['question']}"
        self.draw_outlined_text(20, 20, q_text, FONT_Q, FG_COLOR, wrap_w)
        
        bbox = self.canvas.bbox("ui_text")
        y_cursor = bbox[3] + 20 if bbox else 60
        
        letters = 'ABCD'
        correct_idx = self.current_q['correct_idx']
        
        for i, opt in enumerate(self.current_q['options'][:4]):
            color = FG_COLOR
            text = f"{letters[i]}) {opt}"
            
            if self.remaining_sec <= 0 and self.reveal_remaining_sec > 0:
                if i == correct_idx:
                    color = CORRECT_COLOR
                    text += "  ✔"
                else:
                    color = WRONG_COLOR
            
            self.draw_outlined_text(40, y_cursor, text, FONT_A, color, wrap_w - 20)
            bbox = self.canvas.bbox("ui_text")
            y_cursor = bbox[3] + 5

        if self.remaining_sec <= 0 and self.reveal_remaining_sec > 0:
            expl = self.current_q.get('explanation', "No explanation.")
            y_cursor += 10
            self.draw_outlined_text(20, y_cursor, f"WHY: {expl}", FONT_EXPL, FG_COLOR, wrap_w)
            bbox = self.canvas.bbox("ui_text")
            y_cursor = bbox[3] + 10

        y_cursor += 15
        if self.is_paused:
            timer_text = "PAUSED (Click to resume)"
            timer_col = PAUSE_COLOR
        elif self.remaining_sec > 0:
            bars = "▓" * int(self.remaining_sec * 10 / READ_TIME_SEC)
            timer_text = f"Reveal in {self.remaining_sec}s  {bars}"
            timer_col = TIMER_COLOR
        else:
            bars = "▓" * int(self.reveal_remaining_sec * 10 / REVEAL_TIME_SEC)
            timer_text = f"Next in {self.reveal_remaining_sec}s  {bars}"
            timer_col = TIMER_COLOR
            
        self.draw_outlined_text(20, y_cursor, timer_text, FONT_TIMER, timer_col, wrap_w)
        
        bbox = self.canvas.bbox("all")
        if bbox:
            req_h = bbox[3] + 20
            # Only resize if height changes significantly to avoid jitter
            # And also resize GIF frames if dimensions change
            if req_h != self.height:
                self.height = max(req_h, self.base_height)
                self.root.geometry(f"{self.width}x{self.height}")
                # We need to re-scale the background frames to match new height!
                if self.pil_frames:
                     self.resize_frames(self.width, self.height)

    def draw_outlined_text(self, x, y, text, font, color, width):
        for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1), (0,1), (0,-1), (1,0), (-1,0)]:
            self.canvas.create_text(x+dx, y+dy, text=text, font=font, fill="black", width=width, anchor="nw", tags="ui_text")
        self.canvas.create_text(x, y, text=text, font=font, fill=color, width=width, anchor="nw", tags="ui_text")

    def load_questions(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, "questions.json")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.questions = data[::-1]
            print(f"Loaded {len(self.questions)} questions (reversed, cycle).")
        except Exception as e:
            print(f"Error: {e}")
            self.questions = [{"id": 0, "question": str(e), "options": ["Fix"], "correct_idx": 0, "explanation": "JSON?"}]

    def show_next_question(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
        self.current_q = next(self.quiz_cycle)
        self.remaining_sec = READ_TIME_SEC
        self.is_paused = False
        self.render_ui()
        self.update_timer()

    def update_timer(self):
        if self.is_paused:
            self.render_ui() 
            self.timer_job = self.root.after(200, self.update_timer)
            return

        if self.remaining_sec > 0:
            self.remaining_sec -= 1
            self.render_ui()
            self.timer_job = self.root.after(1000, self.update_timer)
        else:
            self.reveal_answer()

    def reveal_answer(self):
        self.remaining_sec = 0
        self.reveal_remaining_sec = REVEAL_TIME_SEC
        self.is_paused = False
        self.render_ui()
        self.update_reveal_timer()

    def update_reveal_timer(self):
        if self.is_paused:
            self.render_ui()
            self.timer_job = self.root.after(200, self.update_reveal_timer)
            return

        if self.reveal_remaining_sec > 0:
            self.reveal_remaining_sec -= 1
            self.render_ui()
            self.timer_job = self.root.after(1000, self.update_reveal_timer)
        else:
            self.show_next_question()

    def start_move(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self.has_moved = False

    def do_move(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_start_x)
        y = self.root.winfo_y() + (event.y - self._drag_start_y)
        self.root.geometry(f"+{x}+{y}")
        self.has_moved = True

    def check_click_pause(self, event):
        if not self.has_moved:
            self.is_paused = not self.is_paused
            self.render_ui() 

    def skip_step(self, event):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
        if self.remaining_sec > 0:
            self.remaining_sec = 0
            self.reveal_answer()
        else:
            self.reveal_remaining_sec = 0
            self.show_next_question()

if __name__ == "__main__":
    root = tk.Tk()
    app = StudyWidget(root)
    root.mainloop()

import tkinter as tk
import itertools
import json
import os
from PIL import Image, ImageTk, ImageSequence

# CONFIG
BG_COLOR = "#F5E6C4"       # Parchment / Scroll Beige
FG_COLOR = "#000000"       # Black Ink
CORRECT_COLOR = "#006400"  # Dark Green
WRONG_COLOR = "#555555"    # Dark Grey
TIMER_COLOR = "#8B0000"    # Dark Red
PAUSE_COLOR = "#607D8B"    # Blue Grey

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

        # Load & Resize GIF to Small Icon (64x64)
        self.frames = []
        self.frame_idx = 0
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            gif_path = os.path.join(script_dir, "fireplace.gif")
            
            gif_img = Image.open(gif_path)
            
            # Resize to small icon size
            icon_size = (64, 64)
            
            for frame in ImageSequence.Iterator(gif_img):
                frame = frame.convert("RGBA")
                # Resize
                resized = frame.resize(icon_size, Image.Resampling.LANCZOS)
                # Create PhotoImage
                self.frames.append( ImageTk.PhotoImage(resized) )
            
            print(f"Loaded {len(self.frames)} frames (64x64) for icon.")
            
        except Exception as e:
            print(f"Could not load GIF icon: {e}")

        # Main Layout Frame
        # We use a Canvas to draw the GIF, but regular labels for text?
        # Actually, let's stick to Canvas for everything so we can layer the GIF easily.
        # Or simpler: Use a Label for the GIF in the corner.
        
        # Strategy: 
        # 1. Main UI constructed with pack() for text (auto-resize height).
        # 2. GIF placed absolutely in top-right using place().
        
        # Container for text content
        # We need padding at the BOTTOM-LEFT for the fire
        self.content_frame = tk.Frame(root, bg=BG_COLOR)
        # Use pack but with padding to avoid the icon space?
        # Better: use place() for icon and standard pack for text, but add bottom padding to text container.
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=(10, 80)) # Bottom padding for icon
        
        # Forward drags from frame
        self.content_frame.bind("<Button-1>", self.start_move)
        self.content_frame.bind("<B1-Motion>", self.do_move)

        self.load_questions()

        # Question Label (Top)
        self.q_label = tk.Label(self.content_frame, text="", font=FONT_Q, bg=BG_COLOR, fg=FG_COLOR, justify="left", wraplength=self.width-40) 
        self.q_label.pack(pady=(0, 10), anchor="w")
        
        # Options Labels
        self.opt_labels = []
        for i in range(4):
            lbl = tk.Label(self.content_frame, text="", font=FONT_A, bg=BG_COLOR, fg=FG_COLOR, anchor="w", justify="left", wraplength=self.width-40)
            lbl.pack(fill="x", pady=2)
            self.opt_labels.append(lbl)

        # Explanation Label
        self.expl_label = tk.Label(self.content_frame, text="", font=FONT_EXPL, bg=BG_COLOR, fg=FG_COLOR, justify="left", wraplength=self.width-40)
        self.expl_label.pack(pady=(10, 5), anchor="w")

        # Timer Label - Move slightly up or right to avoid icon?
        # Since icon is bottom-left, timer can stay bottom-right in the content frame
        self.timer_label = tk.Label(self.content_frame, text="", font=FONT_TIMER, bg=BG_COLOR, fg=TIMER_COLOR, anchor="e")
        self.timer_label.pack(side="bottom", fill="x", pady=5)

        # GIF Label (Placed in BOTTOM-LEFT corner of ROOT)
        self.gif_label = tk.Label(root, bg=BG_COLOR, borderwidth=0)
        self.gif_label.place(relx=0.0, rely=1.0, x=10, y=-10, anchor="sw") # Bottom Left padding
        
        # Bind events to all widgets recursively
        self.bind_recursive(self.root)

        self.quiz_cycle = itertools.cycle(self.questions)
        self.show_next_question()

        if self.frames:
            self.animate_gif()

    def bind_recursive(self, widget):
        widget.bind("<Button-1>", self.start_move)
        widget.bind("<B1-Motion>", self.do_move)
        widget.bind("<ButtonRelease-1>", self.check_click_pause)
        if isinstance(widget, tk.Label): # Only labels might block, frames pass through usually
             pass 
        
        # Actually simpler: just bind to known elements
        for lbl in [self.q_label, self.expl_label, self.timer_label, self.gif_label] + self.opt_labels:
            lbl.bind("<Button-1>", self.start_move)
            lbl.bind("<B1-Motion>", self.do_move)

    def animate_gif(self):
        if not self.frames:
            return
        
        frame = self.frames[self.frame_idx]
        self.frame_idx = (self.frame_idx + 1) % len(self.frames)
        
        self.gif_label.configure(image=frame)
        
        self.anim_job = self.root.after(100, self.animate_gif)

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

    def resize_window(self):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Width logic (Question text width = full width - padding)
        # Icon is bottom-left, so it doesn't restrict question width at top
        wrap_w = self.width - 40
        
        self.q_label.config(wraplength=wrap_w)
        for lbl in self.opt_labels:
            lbl.config(wraplength=wrap_w - 20)
        self.expl_label.config(wraplength=wrap_w)
        
        self.root.update_idletasks()
        
        # Measure content height via the container frame
        req_h = self.content_frame.winfo_reqheight() + 20 # Padding

        # Enforce max
        new_h = min(req_h, int(screen_height * 0.8))
        
        if req_h > new_h:
             new_w = min(int(screen_width * 0.6), 800)
             self.width = new_w
             # Recalculate wrap
             wrap_w = self.width - 40
             self.q_label.config(wraplength=wrap_w)
             for lbl in self.opt_labels:
                 lbl.config(wraplength=wrap_w - 20)
             self.expl_label.config(wraplength=wrap_w)
             
             self.root.update_idletasks()
             req_h = self.content_frame.winfo_reqheight() + 20
             new_h = min(req_h, int(screen_height * 0.8))
        
        # Stability check
        if abs(self.height - new_h) > 5:
            self.height = new_h
            self.root.geometry(f"{self.width}x{self.height}")

    def show_next_question(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
        self.current_q = next(self.quiz_cycle)
        self.expl_label.config(text="")
        
        for lbl in self.opt_labels:
            lbl.config(fg=FG_COLOR)
        
        self.q_label.config(text=f"Q{self.current_q['id']}: {self.current_q['question']}")
        letters = 'ABCD'
        for i, opt in enumerate(self.current_q['options'][:4]):
            self.opt_labels[i].config(text=f"{letters[i]}) {opt}")
            
        self.resize_window()
        self.remaining_sec = READ_TIME_SEC
        self.is_paused = False
        self.update_timer()

    def update_timer(self):
        if self.is_paused:
            self.timer_label.config(text="PAUSED (Click to resume)", fg=PAUSE_COLOR)
            self.timer_job = self.root.after(200, self.update_timer)
            return

        if self.remaining_sec > 0:
            bars = "▓" * int(self.remaining_sec * 10 / READ_TIME_SEC)
            self.timer_label.config(text=f"Reveal in {self.remaining_sec}s  {bars}", fg=TIMER_COLOR)
            self.remaining_sec -= 1
            self.timer_job = self.root.after(1000, self.update_timer)
        else:
            self.reveal_answer()

    def reveal_answer(self):
        correct_idx = self.current_q['correct_idx']
        explanation = self.current_q.get('explanation', "No explanation.")
        for i, lbl in enumerate(self.opt_labels):
            if i != correct_idx:
                lbl.config(fg=WRONG_COLOR)
            else:
                lbl.config(fg=CORRECT_COLOR, text=lbl.cget("text") + "  ✔")
        self.expl_label.config(text=f"WHY: {explanation}")
        
        self.resize_window()
        self.remaining_sec = 0
        self.reveal_remaining_sec = REVEAL_TIME_SEC
        self.is_paused = False
        self.update_reveal_timer()

    def update_reveal_timer(self):
        if self.is_paused:
            self.timer_label.config(text="PAUSED (Click to resume)", fg=PAUSE_COLOR)
            self.timer_job = self.root.after(200, self.update_reveal_timer)
            return

        if self.reveal_remaining_sec > 0:
            bars = "▓" * int(self.reveal_remaining_sec * 10 / REVEAL_TIME_SEC)
            self.timer_label.config(text=f"Next in {self.reveal_remaining_sec}s  {bars}", fg=TIMER_COLOR)
            self.reveal_remaining_sec -= 1
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
            self.update_timer_display()

    def update_timer_display(self):
        # Helper to force update label text immediately on pause
        if self.is_paused:
             self.timer_label.config(text="PAUSED (Click to resume)", fg=PAUSE_COLOR)

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

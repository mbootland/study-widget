import tkinter as tk
import itertools
import json
import os

# CONFIG
TRANSPARENT_COLOR = "#FF00FF" # Magenta - will be made transparent
OUTLINE_COLOR = "#FFFFFF"     # White outline
Q_COLOR = "#000000"           # Black text
OPT_COLOR = "#000000"
CORRECT_COLOR = "#008000"     # Green
WRONG_COLOR = "#404040"       # Dark Grey
TIMER_COLOR = "#000000"
EXPLAIN_COLOR = "#000000"
PAUSE_COLOR = "#808080"

FONT_Q = ("Consolas", 14, "bold")
FONT_A = ("Consolas", 12, "bold")
FONT_TIMER = ("Consolas", 11, "bold")
FONT_EXPL = ("Consolas", 11, "italic")

READ_TIME_SEC = 30
REVEAL_TIME_SEC = 10

class StudyWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("GCP Quiz Overlay")
        self.root.configure(bg=TRANSPARENT_COLOR)
        
        # Make the window background transparent
        self.root.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)

        self.base_width = 500
        self.base_height = 250
        self.width = self.base_width
        self.height = self.base_height
        
        screen_width = self.root.winfo_screenwidth()
        x_pos = screen_width - self.width - 40
        y_pos = 40
        self.root.geometry(f"{self.width}x{self.height}+{x_pos}+{y_pos}")

        self.timer_job = None
        self.remaining_sec = 0
        self.reveal_remaining_sec = 0
        self.is_paused = False
        self.has_moved = False

        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        self.root.bind("<ButtonRelease-1>", self.check_click_pause)
        self.root.bind("<Button-3>", self.skip_step)
        self.root.bind("<Button-2>", lambda e: root.quit())

        # Main Canvas
        self.canvas = tk.Canvas(root, bg=TRANSPARENT_COLOR, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.load_questions()
        self.quiz_cycle = itertools.cycle(self.questions)
        self.show_next_question()

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

    def draw_text_outline(self, x, y, text, font, color, anchor="nw", width=None):
        # Draw outline (4 directions)
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            self.canvas.create_text(x + dx, y + dy, text=text, font=font, fill=OUTLINE_COLOR, anchor=anchor, width=width)
        # Draw main text
        self.canvas.create_text(x, y, text=text, font=font, fill=color, anchor=anchor, width=width)

    def render_scene(self):
        self.canvas.delete("all")
        
        # Calculate max width for text wrapping
        max_text_width = self.width - 20

        y_cursor = 10
        
        # Question
        q_text = f"Q{self.current_q['id']}: {self.current_q['question']}"
        self.draw_text_outline(10, y_cursor, q_text, FONT_Q, Q_COLOR, width=max_text_width)
        
        # Calculate height of question to move cursor
        # (This is a bit tricky in canvas, we approximate or query bbox)
        # For simplicity, we query the last item created
        bbox = self.canvas.bbox("all")
        if bbox:
            y_cursor = bbox[3] + 10
        else:
            y_cursor += 30

        # Options
        letters = 'ABCD'
        correct_idx = self.current_q['correct_idx']
        
        for i, opt in enumerate(self.current_q['options'][:4]):
            color = OPT_COLOR
            text = f"{letters[i]}) {opt}"
            
            # If revealing
            if self.remaining_sec <= 0 and self.reveal_remaining_sec > 0:
                if i == correct_idx:
                    color = CORRECT_COLOR
                    text += "  ✔"
                else:
                    color = WRONG_COLOR
            
            self.draw_text_outline(20, y_cursor, text, FONT_A, color, width=max_text_width-20)
            
            bbox = self.canvas.bbox("all")
            y_cursor = bbox[3] + 5

        # Explanation (if revealing)
        if self.remaining_sec <= 0 and self.reveal_remaining_sec > 0:
            expl = self.current_q.get('explanation', "No explanation.")
            y_cursor += 5
            self.draw_text_outline(10, y_cursor, f"WHY: {expl}", FONT_EXPL, EXPLAIN_COLOR, width=max_text_width)
            
            bbox = self.canvas.bbox("all")
            y_cursor = bbox[3] + 10

        # Timer
        y_cursor += 10
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

        # Draw timer at bottom right effectively, or just below everything
        self.draw_text_outline(10, y_cursor, timer_text, FONT_TIMER, timer_col, width=max_text_width)

        # Update window height if needed
        bbox = self.canvas.bbox("all")
        if bbox:
            required_h = bbox[3] + 20
            if required_h != self.height:
                self.height = required_h
                self.root.geometry(f"{self.width}x{self.height}")

    def show_next_question(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
        self.current_q = next(self.quiz_cycle)
        self.remaining_sec = READ_TIME_SEC
        self.is_paused = False
        self.render_scene()
        self.update_timer()

    def update_timer(self):
        if self.is_paused:
            self.render_scene()
            self.timer_job = self.root.after(200, self.update_timer)
            return

        if self.remaining_sec > 0:
            self.remaining_sec -= 1
            self.render_scene()
            self.timer_job = self.root.after(1000, self.update_timer)
        else:
            self.reveal_answer()

    def reveal_answer(self):
        self.remaining_sec = 0 
        self.reveal_remaining_sec = REVEAL_TIME_SEC
        self.is_paused = False
        self.render_scene()
        self.update_reveal_timer()

    def update_reveal_timer(self):
        if self.is_paused:
            self.render_scene()
            self.timer_job = self.root.after(200, self.update_reveal_timer)
            return

        if self.reveal_remaining_sec > 0:
            self.reveal_remaining_sec -= 1
            self.render_scene()
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
            self.render_scene()

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

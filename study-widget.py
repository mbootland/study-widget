import tkinter as tk
import itertools
import json
import os

# CONFIG
BG_COLOR = "#000000"       # Black
FG_COLOR = "#FFD700"       # Gold (Default)
CORRECT_COLOR = "#00E676"  # Strong Green
WRONG_COLOR = "#616161"    # Grey 700
TIMER_COLOR = "#FF5252"    # Red Accent 200
PAUSE_COLOR = "#B0BEC5"    # Blue Grey 200

# Christmas Tree Colors (Cycle through these)
RAINBOW_COLORS = [
    "#FF0000", # Red
    "#00FF00", # Green
    "#0000FF", # Blue
    "#FFFF00", # Yellow
    "#00FFFF", # Cyan
    "#FF00FF", # Magenta
    "#FFA500", # Orange
]

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
        self.remaining_sec = 0
        self.reveal_remaining_sec = 0
        self.is_paused = False
        self.has_moved = False

        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        self.root.bind("<ButtonRelease-1>", self.check_click_pause)
        self.root.bind("<Button-3>", self.skip_step)
        self.root.bind("<Button-2>", lambda e: root.quit())

        self.load_questions()

        # REPLACE Label with Text widget for the Question to support multi-color
        self.q_text = tk.Text(root, font=FONT_Q, bg=BG_COLOR, fg=FG_COLOR, 
                              bd=0, highlightthickness=0, wrap="word", height=4)
        self.q_text.pack(pady=(10, 5), padx=10, fill="x")
        # Disable editing
        self.q_text.bind("<Key>", lambda e: "break")
        # Forward drag events
        self.q_text.bind("<Button-1>", self.start_move)
        self.q_text.bind("<B1-Motion>", self.do_move)
        self.q_text.bind("<ButtonRelease-1>", self.check_click_pause)
        self.q_text.bind("<Button-3>", self.skip_step)

        # Setup tags for colors
        for i, color in enumerate(RAINBOW_COLORS):
            self.q_text.tag_configure(f"c{i}", foreground=color)

        self.opt_labels = []
        for i in range(4):
            lbl = tk.Label(root, text="", font=FONT_A, bg=BG_COLOR, fg=FG_COLOR, anchor="w", justify="left")
            lbl.pack(fill="x", padx=20, pady=2)
            lbl.bind("<Button-1>", self.start_move)
            lbl.bind("<B1-Motion>", self.do_move)
            self.opt_labels.append(lbl)

        self.expl_label = tk.Label(root, text="", font=FONT_EXPL, bg=BG_COLOR, fg=FG_COLOR, justify="left")
        self.expl_label.pack(pady=(5, 5), padx=10, anchor="w")

        self.timer_label = tk.Label(root, text="", font=FONT_TIMER, bg=BG_COLOR, fg=TIMER_COLOR, anchor="e")
        self.timer_label.pack(side="bottom", fill="x", padx=10, pady=5)

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

    def set_rainbow_text(self, text_widget, content):
        text_widget.config(state="normal")
        text_widget.delete("1.0", "end")
        
        # Insert character by character with cycling color tags
        for i, char in enumerate(content):
            tag = f"c{i % len(RAINBOW_COLORS)}"
            text_widget.insert("end", char, tag)
            
        text_widget.config(state="disabled")

    def resize_window(self):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        wrap_w = self.width - 40
        # For Text widget, wrapping is handled by width in CHARACTERS not pixels usually,
        # but place/pack fill handles width. We just need to ensure height is enough.
        
        for lbl in self.opt_labels:
            lbl.config(wraplength=wrap_w - 20)
        self.expl_label.config(wraplength=wrap_w)
        
        self.root.update_idletasks()
        
        # Calculate height needed for Text widget based on content
        # This is tricky with Text widgets. simpler to just let it fill what it needs or fixed height?
        # Let's try to estimate lines.
        # num_lines = int(self.q_text.index('end-1c').split('.')[0])
        # q_height = num_lines * 30 # Approx px per line
        
        # Better: use dlineinfo to measure
        # But for now, let's just stick to a slightly flexible approach
        
        content_h = (100 + # Approx for Question Text (fixed height=4 lines approx)
                     sum(l.winfo_reqheight() for l in self.opt_labels) + 
                     self.expl_label.winfo_reqheight() + 
                     self.timer_label.winfo_reqheight() * 2 + 
                     60)

        new_h = min(content_h, int(screen_height * 0.8))
        if content_h > new_h:
             new_w = min(int(screen_width * 0.6), 800)
             self.width = new_w
             wrap_w = self.width - 40
             # Resize text width? It fills X automatically.
             for lbl in self.opt_labels:
                 lbl.config(wraplength=wrap_w - 20)
             self.expl_label.config(wraplength=wrap_w)
             self.root.update_idletasks()
             content_h = (100 + 
                          sum(l.winfo_reqheight() for l in self.opt_labels) + 
                          self.expl_label.winfo_reqheight() + 
                          self.timer_label.winfo_reqheight() * 2 + 
                          60)
             new_h = min(content_h, int(screen_height * 0.8))
        
        self.height = new_h
        self.root.geometry(f"{self.width}x{self.height}")

    def show_next_question(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
        self.current_q = next(self.quiz_cycle)
        self.expl_label.config(text="")
        
        for lbl in self.opt_labels:
            lbl.config(fg=FG_COLOR)
        
        q_str = f"Q{self.current_q['id']}: {self.current_q['question']}"
        self.set_rainbow_text(self.q_text, q_str)
        
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
            if self.timer_job:
                self.root.after_cancel(self.timer_job)
                if self.remaining_sec > 0:
                    self.update_timer()
                elif self.reveal_remaining_sec > 0:
                    self.update_reveal_timer()

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

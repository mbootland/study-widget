import tkinter as tk
import itertools
import json
import os

# CONFIG
BG_COLOR = "#000000"
Q_COLOR = "#FFD700"
OPT_COLOR = "#4FC3F7"
CORRECT_COLOR = "#00E676"
WRONG_COLOR = "#424242"
TIMER_COLOR = "#FF5252"
EXPLAIN_COLOR = "#FFD700"

FONT_Q = ("Consolas", 24, "bold")
FONT_A = ("Consolas", 20, "bold")
FONT_TIMER = ("Consolas", 16, "bold")
FONT_EXPL = ("Consolas", 16, "bold italic")

READ_TIME_SEC = 30
REVEAL_TIME_SEC = 10

class StudyWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("GCP Quiz Overlay")
        self.root.configure(bg=BG_COLOR)

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.width = int(screen_width * 0.95)
        self.height = int(screen_height * 0.6)
        x_pos = (screen_width - self.width) // 2
        y_pos = 40
        self.root.geometry(f"{self.width}x{self.height}+{x_pos}+{y_pos}")

        self.timer_job = None
        self.remaining_sec = 0
        self.reveal_remaining_sec = 0

        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        self.root.bind("<Button-3>", lambda e: root.quit())

        self.load_questions()

        self.q_label = tk.Label(root, text="", font=FONT_Q, bg=BG_COLOR, fg=Q_COLOR, justify="left")
        self.q_label.pack(pady=(15, 10), padx=15, anchor="w")

        self.opt_labels = []
        for i in range(4):
            lbl = tk.Label(root, text="", font=FONT_A, bg=BG_COLOR, fg=OPT_COLOR, anchor="w", justify="left")
            lbl.pack(fill="x", padx=25, pady=2)
            self.opt_labels.append(lbl)

        self.expl_label = tk.Label(root, text="", font=FONT_EXPL, bg=BG_COLOR, fg=EXPLAIN_COLOR, justify="left")
        self.expl_label.pack(pady=(10, 5), padx=15, anchor="w")

        self.timer_label = tk.Label(root, text="", font=FONT_TIMER, bg=BG_COLOR, fg=TIMER_COLOR, anchor="e")
        self.timer_label.pack(side="bottom", fill="x", padx=10, pady=5)

        self.quiz_cycle = itertools.cycle(self.questions)
        self.show_next_question()
        self.apply_overlay_settings()

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
        wrap_w = self.width - 60
        self.q_label.config(wraplength=wrap_w)
        for lbl in self.opt_labels:
            lbl.config(wraplength=wrap_w - 20)
        self.expl_label.config(wraplength=wrap_w)
        self.root.update_idletasks()
        screen_height = self.root.winfo_screenheight()
        content_h = self.q_label.winfo_reqheight() + sum(l.winfo_reqheight() for l in self.opt_labels) + self.expl_label.winfo_reqheight() + self.timer_label.winfo_reqheight() * 2 + 120
        new_h = max(500, min(int(screen_height * 0.85), content_h))
        self.root.geometry(f"{self.width}x{new_h}+{self.root.winfo_x()}+{self.root.winfo_y()}")

    def show_next_question(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
        self.current_q = next(self.quiz_cycle)
        self.expl_label.config(text="")
        for lbl in self.opt_labels:
            lbl.config(fg=OPT_COLOR)
        self.resize_window()
        self.q_label.config(text=f"Q{self.current_q['id']}: {self.current_q['question']}")
        letters = 'ABCD'
        for i, opt in enumerate(self.current_q['options'][:4]):
            clean_opt = opt.lstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ. )')
            self.opt_labels[i].config(text=f"{letters[i]}) {clean_opt}")
        self.resize_window()
        self.remaining_sec = READ_TIME_SEC
        self.update_timer()

    def update_timer(self):
        if self.remaining_sec > 0:
            bars = "▓" * int(self.remaining_sec * 10 / READ_TIME_SEC)
            self.timer_label.config(text=f"Reveal in {self.remaining_sec}s  {bars}")
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
        self.reveal_remaining_sec = REVEAL_TIME_SEC
        self.update_reveal_timer()

    def update_reveal_timer(self):
        if self.reveal_remaining_sec > 0:
            bars = "▓" * int(self.reveal_remaining_sec * 10 / REVEAL_TIME_SEC)
            self.timer_label.config(text=f"Next in {self.reveal_remaining_sec}s  {bars}")
            self.reveal_remaining_sec -= 1
            self.timer_job = self.root.after(1000, self.update_reveal_timer)
        else:
            self.show_next_question()

    def start_move(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def do_move(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_start_x)
        y = self.root.winfo_y() + (event.y - self._drag_start_y)
        self.root.geometry(f"+{x}+{y}")

    def apply_overlay_settings(self):
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.lift()
        self.root.attributes('-alpha', 0.95)
        self.root.after(2000, self.apply_overlay_settings)

if __name__ == "__main__":
    root = tk.Tk()
    app = StudyWidget(root)
    root.mainloop()
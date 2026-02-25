import tkinter as tk
import random
import time
import itertools
import json
import os
import sys

# --- CONFIGURATION ---
BG_COLOR = "#000000"       # Solid Black
Q_COLOR  = "#ffffff"       # White
OPT_COLOR = "#cccccc"      # Light Grey
CORRECT_COLOR = "#00ff00"  # Bright Green
WRONG_COLOR = "#555555"    # Dim Grey
TIMER_COLOR = "#ff9900"    # Orange
EXPLAIN_COLOR = "#ffff00"  # Bright Yellow

# --- FONTS (Larger & Bold) ---
FONT_Q = ("Consolas", 16, "bold")
FONT_A = ("Consolas", 13, "bold")
FONT_TIMER = ("Consolas", 11, "bold")
FONT_EXPL = ("Consolas", 12, "bold italic")

# --- TIMING ---
READ_TIME_SEC = 30    # 30s to read question
REVEAL_TIME_MS = 30000 # 30s to read answer/explanation

class StudyWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("GCP Quiz Overlay")
        self.root.configure(bg=BG_COLOR)

        # Window Setup (Wide & Tall for readability)
        screen_width = self.root.winfo_screenwidth()
        self.width = 700
        self.height = 500 
        x_pos = screen_width - self.width - 40
        y_pos = 40
        self.root.geometry(f"{self.width}x{self.height}+{x_pos}+{y_pos}")

        # Drag Logic
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        self.root.bind("<Button-3>", lambda e: root.quit())

        # Load Questions
        self.load_questions()

        # --- Layout ---
        self.q_label = tk.Label(root, text="", font=FONT_Q, bg=BG_COLOR, fg=Q_COLOR, wraplength=self.width-20, justify="left")
        self.q_label.pack(pady=(20, 15), padx=15, anchor="w")

        self.opt_labels = []
        for i in range(4):
            lbl = tk.Label(root, text="", font=FONT_A, bg=BG_COLOR, fg=OPT_COLOR, anchor="w", wraplength=self.width-30, justify="left")
            lbl.pack(fill="x", padx=25, pady=4)
            self.opt_labels.append(lbl)

        # Explanation Label (Hidden initially)
        self.expl_label = tk.Label(root, text="", font=FONT_EXPL, bg=BG_COLOR, fg=EXPLAIN_COLOR, wraplength=self.width-20, justify="left")
        self.expl_label.pack(pady=(20, 5), padx=15, anchor="w")

        # Countdown Timer Bar
        self.timer_label = tk.Label(root, text="", font=FONT_TIMER, bg=BG_COLOR, fg=TIMER_COLOR, anchor="e")
        self.timer_label.pack(side="bottom", fill="x", padx=10, pady=5)

        # Start Quiz Loop
        self.quiz_cycle = itertools.cycle(self.questions)
        self.current_q = None
        self.timer_job = None
        self.show_next_question()

        # Always on Top Loop
        self.apply_overlay_settings()

    def load_questions(self):
        # Look for questions.json in the same directory as the script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, "questions.json")
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                self.questions = json.load(f)
            random.shuffle(self.questions)
            print(f"Loaded {len(self.questions)} questions.")
        except Exception as e:
            print(f"Error loading questions.json: {e}")
            # Fallback question if file missing
            self.questions = [{
                "id": 0,
                "question": f"Error loading questions.json: {e}",
                "options": ["Check file path", "Check JSON format", "Check permissions", "Panic"],
                "correct_idx": 0,
                "explanation": "Ensure questions.json is in the same folder as this script."
            }]

    def show_next_question(self):
        self.current_q = next(self.quiz_cycle)
        
        # Reset UI
        self.expl_label.config(text="") # Hide explanation
        for lbl in self.opt_labels:
            lbl.config(fg=OPT_COLOR)

        # Update Text with ID
        self.q_label.config(text=f"Q{self.current_q['id']}: {self.current_q['question']}")
        letters = ['A', 'B', 'C', 'D']
        for i, opt in enumerate(self.current_q['options']):
            if i < 4: # Safety check
                self.opt_labels[i].config(text=f"{letters[i]}. {opt}")

        # Start Countdown
        self.remaining_sec = READ_TIME_SEC
        self.update_timer()

    def update_timer(self):
        if self.remaining_sec > 0:
            # Update bar visualization
            bars = "▓" * int(self.remaining_sec * (10/READ_TIME_SEC)) 
            self.timer_label.config(text=f"Reveal in {self.remaining_sec}s  {bars}")
            
            self.remaining_sec -= 1
            self.timer_job = self.root.after(1000, self.update_timer)
        else:
            self.timer_label.config(text="REVEALED - Next in 30s")
            self.reveal_answer()

    def reveal_answer(self):
        correct_idx = self.current_q['correct_idx']
        explanation = self.current_q.get('explanation', "No explanation provided.")
        
        # Dim incorrect answers
        for i, lbl in enumerate(self.opt_labels):
            if i != correct_idx:
                lbl.config(fg=WRONG_COLOR)
            else:
                lbl.config(fg=CORRECT_COLOR, text=lbl.cget("text") + "  ✔")
        
        # Show Explanation
        self.expl_label.config(text=f"WHY: {explanation}")
        
        # Schedule Next Question
        self.root.after(REVEAL_TIME_MS, self.show_next_question)

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
        self.root.attributes('-alpha', 0.95) # High opacity for black bg
        self.root.after(2000, self.apply_overlay_settings)

if __name__ == "__main__":
    root = tk.Tk()
    app = StudyWidget(root)
    root.mainloop()

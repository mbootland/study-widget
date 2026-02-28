import tkinter as tk
import itertools
import json
import os

# CONFIG
TEXT_BG_KEY = "#000001"    # Almost black, used as transparent key for text window
BG_TINT_COLOR = "#000000"  # Pure black for the background tint window
FG_COLOR = "#FFFFFF"       # White text
CORRECT_COLOR = "#00E676"  # Bright Green
WRONG_COLOR = "#757575"    # Grey
TIMER_COLOR = "#FF5252"    # Red

FONT_Q = ("Consolas", 14, "bold")
FONT_A = ("Consolas", 12, "bold")
FONT_TIMER = ("Consolas", 11, "bold")
FONT_EXPL = ("Consolas", 11, "italic")

READ_TIME_SEC = 30
REVEAL_TIME_SEC = 10
BG_OPACITY = 0.2  # 20% visible background (Very faint tint)

class StudyWidget:
    def __init__(self, root):
        self.root = root
        
        # --- WINDOW 1: The Background Tint (Ghostly) ---
        self.bg_window = tk.Toplevel(root)
        self.bg_window.title("GCP Background")
        self.bg_window.configure(bg=BG_TINT_COLOR)
        self.bg_window.overrideredirect(True)
        self.bg_window.attributes('-alpha', BG_OPACITY) # Faint!
        self.bg_window.attributes('-topmost', True)

        # --- WINDOW 2: The Text Layer (Solid) ---
        # Root is the text layer
        self.root.title("GCP Quiz Text")
        self.root.configure(bg=TEXT_BG_KEY)
        self.root.wm_attributes("-transparentcolor", TEXT_BG_KEY) # Make background 100% invisible
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        self.root.attributes('-alpha', 1.0) # Text is 100% solid!

        self.base_width = 500
        self.base_height = 200
        self.width = self.base_width
        self.height = self.base_height
        
        screen_width = self.root.winfo_screenwidth()
        x_pos = screen_width - self.width - 40
        y_pos = 40
        
        # Position both windows
        self.root.geometry(f"{self.width}x{self.height}+{x_pos}+{y_pos}")
        self.bg_window.geometry(f"{self.width}x{self.height}+{x_pos}+{y_pos}")

        self.timer_job = None
        self.remaining_sec = 0
        self.reveal_remaining_sec = 0
        self.is_paused = False
        self.has_moved = False

        # Bind dragging to the TEXT window (since user clicks text)
        # We need to move BOTH windows
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        self.root.bind("<ButtonRelease-1>", self.check_click_pause)
        self.root.bind("<Button-3>", self.skip_step)
        self.root.bind("<Button-2>", lambda e: self.quit_all())

        self.load_questions()

        # UI Elements (on Root/Text Window)
        self.q_label = tk.Label(root, text="", font=FONT_Q, bg=TEXT_BG_KEY, fg=FG_COLOR, justify="left")
        self.q_label.pack(pady=(10, 5), padx=10, anchor="w")
        self.bind_drag(self.q_label)

        self.opt_labels = []
        for i in range(4):
            lbl = tk.Label(root, text="", font=FONT_A, bg=TEXT_BG_KEY, fg=FG_COLOR, anchor="w", justify="left")
            lbl.pack(fill="x", padx=20, pady=2)
            self.bind_drag(lbl)
            self.opt_labels.append(lbl)

        self.expl_label = tk.Label(root, text="", font=FONT_EXPL, bg=TEXT_BG_KEY, fg=FG_COLOR, justify="left")
        self.expl_label.pack(pady=(5, 5), padx=10, anchor="w")
        self.bind_drag(self.expl_label)

        self.timer_label = tk.Label(root, text="", font=FONT_TIMER, bg=TEXT_BG_KEY, fg=TIMER_COLOR, anchor="e")
        self.timer_label.pack(side="bottom", fill="x", padx=10, pady=5)
        self.bind_drag(self.timer_label)

        self.quiz_cycle = itertools.cycle(self.questions)
        self.show_next_question()
        
        # Keep background behind text
        self.lift_windows()

    def bind_drag(self, widget):
        widget.bind("<Button-1>", self.start_move)
        widget.bind("<B1-Motion>", self.do_move)

    def quit_all(self):
        self.root.quit()

    def lift_windows(self):
        self.bg_window.lift()
        self.root.lift()
        self.root.after(2000, self.lift_windows)

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
        
        wrap_w = self.width - 40
        self.q_label.config(wraplength=wrap_w)
        for lbl in self.opt_labels:
            lbl.config(wraplength=wrap_w - 20)
        self.expl_label.config(wraplength=wrap_w)
        
        self.root.update_idletasks()
        
        content_h = (self.q_label.winfo_reqheight() + 
                     sum(l.winfo_reqheight() for l in self.opt_labels) + 
                     self.expl_label.winfo_reqheight() + 
                     self.timer_label.winfo_reqheight() * 2 + 
                     60)

        new_h = min(content_h, int(screen_height * 0.8))
        if content_h > new_h:
             new_w = min(int(screen_width * 0.6), 800)
             self.width = new_w
             wrap_w = self.width - 40
             self.q_label.config(wraplength=wrap_w)
             for lbl in self.opt_labels:
                 lbl.config(wraplength=wrap_w - 20)
             self.expl_label.config(wraplength=wrap_w)
             self.root.update_idletasks()
             content_h = (self.q_label.winfo_reqheight() + 
                          sum(l.winfo_reqheight() for l in self.opt_labels) + 
                          self.expl_label.winfo_reqheight() + 
                          self.timer_label.winfo_reqheight() * 2 + 
                          60)
             new_h = min(content_h, int(screen_height * 0.8))
        
        self.height = new_h
        # Resize BOTH windows
        geo = f"{self.width}x{self.height}"
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f"{geo}+{x}+{y}")
        self.bg_window.geometry(f"{geo}+{x}+{y}")

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
            self.timer_label.config(text="PAUSED (Click to resume)", fg="#B0BEC5")
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
            self.timer_label.config(text="PAUSED (Click to resume)", fg="#B0BEC5")
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
        # Calculate new position
        x = self.root.winfo_x() + (event.x - self._drag_start_x)
        y = self.root.winfo_y() + (event.y - self._drag_start_y)
        
        # Move BOTH windows together
        self.root.geometry(f"+{x}+{y}")
        self.bg_window.geometry(f"+{x}+{y}")
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

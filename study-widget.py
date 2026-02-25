import tkinter as tk
import itertools
import time

# --- GCP ACE/PRO QUIZ DATA (Harder Scenarios) ---
# Format: (Question, [Option A, Option B, Option C, Option D], Correct Index 0-3)
QUIZ_DATA = [
    (
        "You need to grant an external auditor read access to a specific Cloud Storage bucket, but they don't have a Google account.",
        ["Create a Service Account and share the key.", "Use a Signed URL with a limited expiration.", "Add their email to Cloud Identity.", "Make the bucket public for 1 hour."],
        1 # Signed URL is best for temp external access without accounts
    ),
    (
        "Which load balancer type preserves the client IP address by default for TCP traffic?",
        ["External HTTP(S) Load Balancer", "Internal HTTP(S) Load Balancer", "External TCP/UDP Network Load Balancer", "SSL Proxy Load Balancer"],
        2 # Network LB (Passthrough) preserves IP. Proxies (HTTP/SSL) replace it with LB IP.
    ),
    (
        "You ran 'gcloud config set project my-proj'. You now want to run a command against 'other-proj' without changing the config.",
        ["You must run 'gcloud config set project other-proj' first.", "Use the --project flag with the command.", "Use 'gcloud use other-proj'.", "Set the CLOUD_PROJECT env var."],
        1 # --project flag overrides config
    ),
    (
        "App Engine Standard is scaling too slowly. Which setting in app.yaml should you adjust?",
        ["max_instances", "min_idle_instances", "target_cpu_utilization", "max_concurrent_requests"],
        1 # min_idle_instances keeps instances warm for spikes
    ),
    (
        "You need to transfer 50TB of on-prem data to Cloud Storage. Bandwidth is 100Mbps. Fastest method?",
        ["gsutil -m cp", "Storage Transfer Service", "Transfer Appliance", "Cloud VPN"],
        2 # 50TB on 100Mbps takes ~46 days. Appliance is faster.
    ),
    (
        "Which command creates a custom role using a YAML definition file?",
        ["gcloud iam roles create --file=role.yaml", "gcloud projects add-iam-policy-binding", "gcloud iam service-accounts create", "gcloud iam roles update --file=role.yaml"],
        0 # roles create
    ),
    (
        "GKE: You need to ensure a specific pod runs on a node with SSDs. What do you use?",
        ["Taints and Tolerations", "Node Selector / Affinity", "Pod Disruption Budget", "Horizontal Pod Autoscaler"],
        1 # Node Affinity/Selector targets hardware properties
    ),
    (
        "Cloud Run service fails to connect to Cloud SQL with 'Connection refused'. The VPC Connector is set up.",
        ["Enable the Cloud SQL Admin API.", "Ensure the Service Account has Cloud SQL Client role.", "Configure Private Service Access for the VPC.", "Allow port 3306 in Firewall."],
        2 # Private IP Cloud SQL requires Private Service Access peering
    ),
    (
        "You need to prevent developers from creating External IP addresses for VM instances in a specific folder.",
        ["VPC Service Controls", "Organization Policy (constraints/compute.vmExternalIpAccess)", "IAM Deny Policy", "Firewall Rules"],
        1 # Org Policy is for restriction/compliance
    ),
    (
        "BigQuery: You want to reduce costs for queries that are run frequently with the exact same parameters.",
        ["Use Flex Slots.", "Enable Cached Query Results.", "Use Clustered Tables.", "Materialized Views."],
        1 # Caching is free and automatic if enabled
    ),
]

# --- MONOKAI THEME ---
BG_COLOR = "#272822"       # Monokai Background (Dark Grey)
Q_COLOR  = "#66d9ef"       # Monokai Blue (Cyan)
OPT_COLOR = "#f8f8f2"      # Monokai White/Off-white
CORRECT_COLOR = "#a6e22e"  # Monokai Green
WRONG_COLOR = "#75715e"    # Monokai Grey (for dimmed options)
TIMER_COLOR = "#fd971f"    # Monokai Orange

# --- FONTS ---
FONT_Q = ("Consolas", 14, "bold")
FONT_A = ("Consolas", 12)
FONT_TIMER = ("Consolas", 10, "bold")

# --- TIMING ---
READ_TIME_SEC = 30    # Time to read question
REVEAL_TIME_MS = 5000 # Time to show answer

class StudyWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("GCP Quiz Overlay")
        self.root.configure(bg=BG_COLOR)

        # Window Setup
        screen_width = self.root.winfo_screenwidth()
        self.width = 550
        self.height = 300
        x_pos = screen_width - self.width - 40
        y_pos = 40
        self.root.geometry(f"{self.width}x{self.height}+{x_pos}+{y_pos}")

        # Drag Logic
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        self.root.bind("<Button-3>", lambda e: root.quit())

        # --- Layout ---
        self.q_label = tk.Label(root, text="", font=FONT_Q, bg=BG_COLOR, fg=Q_COLOR, wraplength=self.width-20, justify="left")
        self.q_label.pack(pady=(15, 10), padx=10, anchor="w")

        self.opt_labels = []
        for i in range(4):
            lbl = tk.Label(root, text="", font=FONT_A, bg=BG_COLOR, fg=OPT_COLOR, anchor="w", wraplength=self.width-30, justify="left")
            lbl.pack(fill="x", padx=20, pady=2)
            self.opt_labels.append(lbl)

        # Countdown Timer Bar
        self.timer_label = tk.Label(root, text="", font=FONT_TIMER, bg=BG_COLOR, fg=TIMER_COLOR, anchor="e")
        self.timer_label.pack(side="bottom", fill="x", padx=10, pady=5)

        # Start Quiz Loop
        self.quiz_cycle = itertools.cycle(QUIZ_DATA)
        self.current_q = None
        self.timer_job = None
        self.show_next_question()

        # Always on Top Loop
        self.apply_overlay_settings()

    def show_next_question(self):
        self.current_q = next(self.quiz_cycle)
        question, options, _ = self.current_q
        
        # Reset colors
        for lbl in self.opt_labels:
            lbl.config(fg=OPT_COLOR)

        # Update Text
        self.q_label.config(text=f"Q: {question}")
        letters = ['A', 'B', 'C', 'D']
        for i, opt in enumerate(options):
            self.opt_labels[i].config(text=f"{letters[i]}. {opt}")

        # Start Countdown
        self.remaining_sec = READ_TIME_SEC
        self.update_timer()

    def update_timer(self):
        if self.remaining_sec > 0:
            # Update bar visualization
            bars = "▓" * self.remaining_sec
            spaces = "░" * (READ_TIME_SEC - self.remaining_sec)
            self.timer_label.config(text=f"Reveal in {self.remaining_sec}s  {bars}{spaces}")
            
            self.remaining_sec -= 1
            self.timer_job = self.root.after(1000, self.update_timer)
        else:
            self.timer_label.config(text="REVEALED")
            self.reveal_answer()

    def reveal_answer(self):
        _, _, correct_idx = self.current_q
        
        # Dim incorrect answers
        for i, lbl in enumerate(self.opt_labels):
            if i != correct_idx:
                lbl.config(fg=WRONG_COLOR)
            else:
                lbl.config(fg=CORRECT_COLOR, text=lbl.cget("text") + "  ✔")
        
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
        self.root.attributes('-alpha', 0.90)
        self.root.after(2000, self.apply_overlay_settings)

if __name__ == "__main__":
    root = tk.Tk()
    app = StudyWidget(root)
    root.mainloop()

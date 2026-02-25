import tkinter as tk
import random
import time
import itertools

# --- GCP ACE EXAM DATA (Randomized & Numbered) ---
# Format: (ID, Question, [Option A, Option B, Option C, Option D], Correct Index 0-3, Explanation)
QUIZ_DATA = [
    (1,
     "Your App Engine application needs to connect to a Cloud SQL instance in the same project. You want to ensure the traffic stays within Google's network and does not use public IPs.",
     ["Configure the Cloud SQL instance to use Private Service Access.", "Use the Cloud SQL Proxy with the instance's public IP.", "Allow the App Engine region in the Cloud SQL authorized networks.", "Create a VPC Peering connection between App Engine and Cloud SQL."],
     0,
     "App Engine Standard connects to Cloud SQL via the Auth Proxy automatically, but to enforce private IPs (RFC 1918), you must configure Private Service Access (allocated IP range + VPC peering) for the Cloud SQL instance."
    ),
    (2,
     "You need to create a custom IAM role for a specific project. This role should allow users to view the configuration of Compute Engine instances but not list them.",
     ["compute.instances.get", "compute.instances.list", "compute.instances.osLogin", "compute.instances.setMetadata"],
     0,
     "'get' permissions typically allow viewing a single resource's details (configuration). 'list' allows seeing all resources in a collection. The requirement specifically excludes listing."
    ),
    (3,
     "You have a GKE cluster. You need to ensure that a specific deployment of pods is ALWAYS scheduled on nodes with the label 'disktype: ssd'.",
     ["Use Node Affinity with 'requiredDuringSchedulingIgnoredDuringExecution'.", "Use Node Affinity with 'preferredDuringSchedulingIgnoredDuringExecution'.", "Use Taints on the SSD nodes and Tolerations on the pods.", "Use a PodDisruptionBudget."],
     0,
     "'required...' ensures a hard constraint: the pod will NOT be scheduled unless the node matches. 'preferred' is a soft constraint. Taints repel pods, they don't attract them (unless combined with affinity, but affinity is the primary mechanism for selection)."
    ),
    (4,
     "You are storing data in Cloud Storage that must be kept for exactly 5 years for compliance, after which it must be deleted. No one, not even admins, should be able to delete it before then.",
     ["Use a Retention Policy with a 'Locked' Bucket Lock.", "Use Object Versioning with a Lifecycle Rule.", "Use Signed URLs with a 5-year duration.", "Grant 'Storage Object Admin' only to a service account."],
     0,
     "A Locked Retention Policy enforces WORM (Write Once, Read Many) compliance. Once locked, it cannot be reduced or removed until the retention period expires."
    ),
    (5,
     "You have a critical production application in a single region. You want to ensure high availability if a single zone fails.",
     ["Deploy a Global HTTP(S) Load Balancer.", "Create a Managed Instance Group (MIG) distributing instances across multiple zones.", "Use a Regional Persistent Disk.", "Enable Autohealing for the instance."],
     1,
     "A Regional MIG distributes VM instances across multiple zones (e.g., us-central1-a, b, c). If one zone goes down, the application survives in the others. A Regional PD provides storage HA, but the MIG provides compute HA."
    ),
    (6,
     "You want to view the costs of your project broken down by label (e.g., 'env: production'). You have already applied the labels to your resources.",
     ["Enable Billing Export to BigQuery and query the table.", "Go to the Billing Reports page in the Console and group by 'Label'.", "Use the Pricing Calculator.", "Create a Budget and set an alert."],
     1,
     "The Billing Reports page in the Cloud Console allows you to visualize and group costs by Label immediately. BigQuery is valid for complex analysis, but Console is the standard answer for 'viewing' breakdowns."
    ),
    (7,
     "You need to provide temporary access to a BigQuery dataset for a user who does not have a Google Account.",
     ["Create a Service Account and share the JSON key.", "Add the user to a Google Group and grant access to the group.", "This is not possible; BigQuery requires Google authentication.", "Create a Signed URL for the dataset."],
     2,
     "Unlike Cloud Storage, BigQuery does not support Signed URLs for direct access. Access to BigQuery resources requires an authenticated identity (Google Account, Service Account, or Cloud Identity)."
    ),
    (8,
     "You are deploying a Cloud Run service. You need to store sensitive API keys securely and expose them as environment variables.",
     ["Store keys in Cloud Storage and download them at startup.", "Use Cloud Key Management Service (KMS) to encrypt the keys.", "Use Secret Manager and map the secret to an environment variable.", "Embed the keys in the container image."],
     2,
     "Secret Manager is the managed service for storing sensitive data. Cloud Run has native integration to mount secrets as environment variables or volumes."
    ),
    (9,
     "Your organization requires that all new Cloud Storage buckets must not have public access prevention disabled.",
     ["Use an Organization Policy with the constraint 'storage.publicAccessPrevention'.", "Use VPC Service Controls to block public traffic.", "Use IAM to revoke 'Storage Object Viewer' from 'allUsers'.", "Set a default ACL on all buckets."],
     0,
     "Organization Policies are the tool for preventative compliance (guardrails) across the hierarchy. Enforcing 'public access prevention' at the Org/Folder level stops users from making buckets public."
    ),
    (10,
     "You need to connect your on-premises network to your VPC with the highest possible reliability (SLA) and consistent performance.",
     ["Cloud VPN with HA (High Availability).", "Dedicated Interconnect.", "Partner Interconnect.", "Carrier Peering."],
     1,
     "Dedicated Interconnect offers the highest SLA (99.99% with proper configuration) and dedicated bandwidth (consistent performance) compared to VPN (public internet) or Carrier Peering."
    ),
]

# --- MONOKAI THEME ---
BG_COLOR = "#272822"       # Monokai Background (Dark Grey)
Q_COLOR  = "#66d9ef"       # Monokai Blue (Cyan)
OPT_COLOR = "#f8f8f2"      # Monokai White/Off-white
CORRECT_COLOR = "#a6e22e"  # Monokai Green
WRONG_COLOR = "#75715e"    # Monokai Grey (dimmed)
TIMER_COLOR = "#fd971f"    # Monokai Orange
EXPLAIN_COLOR = "#e6db74"  # Monokai Yellow

# --- FONTS ---
FONT_Q = ("Consolas", 14, "bold")
FONT_A = ("Consolas", 12)
FONT_TIMER = ("Consolas", 10, "bold")
FONT_EXPL = ("Consolas", 11, "italic")

# --- TIMING ---
READ_TIME_SEC = 30    # 30s to read question
REVEAL_TIME_MS = 30000 # 30s to read answer/explanation (Total cycle ~60s)

class StudyWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("GCP Quiz Overlay")
        self.root.configure(bg=BG_COLOR)

        # Window Setup (Taller for explanation)
        screen_width = self.root.winfo_screenwidth()
        self.width = 650
        self.height = 420 
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

        # Explanation Label (Hidden initially)
        self.expl_label = tk.Label(root, text="", font=FONT_EXPL, bg=BG_COLOR, fg=EXPLAIN_COLOR, wraplength=self.width-20, justify="left")
        self.expl_label.pack(pady=(15, 5), padx=10, anchor="w")

        # Countdown Timer Bar
        self.timer_label = tk.Label(root, text="", font=FONT_TIMER, bg=BG_COLOR, fg=TIMER_COLOR, anchor="e")
        self.timer_label.pack(side="bottom", fill="x", padx=10, pady=5)

        # Start Quiz Loop
        self.quiz_data = list(QUIZ_DATA) # Copy data
        random.shuffle(self.quiz_data)   # Randomize order
        self.quiz_cycle = itertools.cycle(self.quiz_data)
        
        self.current_q = None
        self.timer_job = None
        self.show_next_question()

        # Always on Top Loop
        self.apply_overlay_settings()

    def show_next_question(self):
        self.current_q = next(self.quiz_cycle)
        q_id, question, options, _, _ = self.current_q
        
        # Reset UI
        self.expl_label.config(text="") # Hide explanation
        for lbl in self.opt_labels:
            lbl.config(fg=OPT_COLOR)

        # Update Text with ID
        self.q_label.config(text=f"Q{q_id}: {question}")
        letters = ['A', 'B', 'C', 'D']
        for i, opt in enumerate(options):
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
        _, _, _, correct_idx, explanation = self.current_q
        
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
        self.root.attributes('-alpha', 0.92)
        self.root.after(2000, self.apply_overlay_settings)

if __name__ == "__main__":
    root = tk.Tk()
    app = StudyWidget(root)
    root.mainloop()

import os
import sys
import tkinter as tk
from tkinter import messagebox
from datetime import date, timedelta
try:
    import winsound
except ImportError:
    winsound = None

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from storage import Storage

BG_ROOT = "#090d16"
BG_CARD = "#131b2e"
ACCENT_EMERALD = "#10b981"
ACCENT_CYAN = "#38bdf8"
ACCENT_AMBER = "#fbbf24"
ACCENT_ROSE = "#ef4444"
TEXT_WHITE = "#f8fafc"
TEXT_MUTED = "#94a3b8"

class AccountabilityPopup(tk.Tk):
    def __init__(self, target_date=None, target_label=None):
        super().__init__()
        self.storage = Storage()
        
        # Determine target date
        if target_date:
            self.target_date = target_date
            self.target_label = target_label or target_date.isoformat()
        else:
            # Check if yesterday is unrecorded first
            yest = date.today() - timedelta(days=1)
            yest_str = yest.isoformat()
            today_str = date.today().isoformat()
            
            if not self.storage.is_day_locked(yest_str):
                self.target_date = yest
                self.target_label = f"Yesterday ({yest.strftime('%a, %b %d')})"
            else:
                self.target_date = date.today()
                self.target_label = f"Today ({date.today().strftime('%a, %b %d')})"

        self.title("🔒 Irreversible Accountability Check-in")
        self.geometry("440x330")
        self.resizable(False, False)
        self.configure(bg=BG_ROOT)

        # Force always on top
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._on_close_attempt)

        # Center on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        cx = max(0, (sw - 440) // 2)
        cy = max(0, (sh - 330) // 2)
        self.geometry(f"+{cx}+{cy}")

        self._play_chime()
        self._build_ui()

    def _play_chime(self):
        if winsound:
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

    def _build_ui(self):
        # Header banner
        header = tk.Frame(self, bg="#1e1b4b", padx=16, pady=10)
        header.pack(fill="x")

        tk.Label(
            header,
            text="🔒 DAILY ACCOUNTABILITY CHECK-IN",
            font=("Segoe UI", 11, "bold"),
            fg=ACCENT_CYAN,
            bg="#1e1b4b"
        ).pack()

        tk.Label(
            header,
            text=f"Recording for: {self.target_label}",
            font=("Segoe UI", 9, "bold"),
            fg=ACCENT_AMBER,
            bg="#1e1b4b"
        ).pack(pady=(2, 0))

        # Main Question Card
        card = tk.Frame(self, bg=BG_CARD, padx=16, pady=12, highlightbackground="#23304a", highlightthickness=1)
        card.pack(fill="both", expand=True, padx=14, pady=10)

        tk.Label(
            card,
            text="Did you complete this day clean?",
            font=("Segoe UI", 11, "bold"),
            fg=TEXT_WHITE,
            bg=BG_CARD
        ).pack()

        tk.Label(
            card,
            text="(Did you sleep / haven't done anything or did you slip?)",
            font=("Segoe UI", 9),
            fg=TEXT_MUTED,
            bg=BG_CARD
        ).pack(pady=(2, 8))

        # Irreversible Warning
        warn_frame = tk.Frame(card, bg="#1a1c2e", padx=8, pady=4, highlightbackground="#312e81", highlightthickness=1)
        warn_frame.pack(fill="x", pady=(0, 10))
        tk.Label(
            warn_frame,
            text="⚠️ PERMANENT & ENCRYPTED: Once submitted, this answer is final.\nIt CANNOT be edited, reset, or changed from the database.",
            font=("Segoe UI", 7, "bold"),
            fg="#cbd5e1",
            bg="#1a1c2e",
            justify="center"
        ).pack()

        # Big Action Buttons
        btn_clean = tk.Button(
            card,
            text="🛡️ I HAVEN'T DONE ANYTHING (CLEAN)",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg=ACCENT_EMERALD,
            activebackground="#059669",
            activeforeground="#ffffff",
            bd=0,
            pady=8,
            cursor="hand2",
            command=self._submit_clean
        )
        btn_clean.pack(fill="x", pady=(0, 6))

        btn_slip = tk.Button(
            card,
            text="🔴 I SLIPPED",
            font=("Segoe UI", 9, "bold"),
            fg="#ffffff",
            bg="#b91c1c",
            activebackground=ACCENT_ROSE,
            activeforeground="#ffffff",
            bd=0,
            pady=6,
            cursor="hand2",
            command=self._submit_slip
        )
        btn_slip.pack(fill="x")

        # Footer Notice
        tk.Label(
            self,
            text="Dismissing will re-open this window every 10 minutes until answered.",
            font=("Segoe UI", 7, "italic"),
            fg=TEXT_MUTED,
            bg=BG_ROOT
        ).pack(side="bottom", pady=(0, 6))

    def _submit_clean(self):
        d_str = self.target_date.isoformat()
        ok = self.storage.register_day(d_str, "clean")
        if ok:
            streak_info = self.storage.get_streak_stats()
            cur = streak_info["current_streak"]
            s_suf = "s" if cur != 1 else ""
            messagebox.showinfo(
                "Locked & Encrypted 🛡️",
                f"{self.target_label} is permanently locked as CLEAN.\n\nCurrent Streak: {cur} Day{s_suf}. Freedom is your standard.",
                parent=self
            )
            self.destroy()
            sys.exit(0)
        else:
            messagebox.showerror("Error", "This day is already permanently locked!", parent=self)
            self.destroy()
            sys.exit(0)

    def _submit_slip(self):
        d_str = self.target_date.isoformat()
        ok = self.storage.register_day(d_str, "slip")
        if ok:
            messagebox.showinfo(
                "Logged With Honesty 🛡️",
                f"{self.target_label} is permanently locked as SLIP.\n\nHonesty is the foundation of true discipline. Rise and conquer tomorrow.",
                parent=self
            )
            self.destroy()
            sys.exit(0)
        else:
            messagebox.showerror("Error", "This day is already permanently locked!", parent=self)
            self.destroy()
            sys.exit(0)

    def _on_close_attempt(self):
        messagebox.showwarning(
            "Accountability Notice",
            "This day is still unrecorded!\n\nThis check-in window will re-open every 10 minutes until you register your status.",
            parent=self
        )
        self.destroy()
        sys.exit(1)

if __name__ == "__main__":
    app = AccountabilityPopup()
    app.mainloop()

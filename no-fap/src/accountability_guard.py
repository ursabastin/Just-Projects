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

from storage import Storage, ImmutableRecordError

BG_ROOT = "#090d16"
BG_CARD = "#131b2e"
ACCENT_EMERALD = "#10b981"
ACCENT_CYAN = "#38bdf8"
ACCENT_AMBER = "#fbbf24"
ACCENT_ROSE = "#ef4444"
TEXT_WHITE = "#f8fafc"
TEXT_MUTED = "#94a3b8"

class AccountabilityGuard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.storage = Storage()
        
        yesterday = date.today() - timedelta(days=1)
        self.yest_str = yesterday.isoformat()
        self.yest_formatted = yesterday.strftime("%A, %B %d, %Y")

        # If yesterday is ALREADY recorded, exit immediately
        if self.storage.is_yesterday_recorded():
            self.destroy()
            sys.exit(0)

        self.title("Morning Accountability Guard • Yesterday's Record")
        self.geometry("450x340")
        self.resizable(False, False)
        self.configure(bg=BG_ROOT)

        # Force on top of all windows
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._on_close_attempt)

        # Anti-minimize: If user tries to minimize, restore immediately
        self.bind("<Unmap>", self._on_unmap)

        # Center on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        cx = max(0, (sw - 450) // 2)
        cy = max(0, (sh - 340) // 2)
        self.geometry(f"+{cx}+{cy}")

        self._play_chime()
        self._build_ui()
        self._keep_topmost()

    def _play_chime(self):
        if winsound:
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

    def _keep_topmost(self):
        try:
            self.attributes("-topmost", True)
            self.lift()
        except Exception:
            pass
        self.after(1000, self._keep_topmost)

    def _on_unmap(self, event=None):
        if self.state() == "iconic":
            self.after(50, self._restore_focus)

    def _restore_focus(self):
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()

    def _build_ui(self):
        # Header banner
        header = tk.Frame(self, bg="#1e1b4b", padx=16, pady=10)
        header.pack(fill="x")

        tk.Label(
            header,
            text="☀️  MORNING ACCOUNTABILITY GUARD",
            font=("Segoe UI", 11, "bold"),
            fg=ACCENT_CYAN,
            bg="#1e1b4b"
        ).pack()

        tk.Label(
            header,
            text=f"Evaluating Yesterday: {self.yest_formatted}",
            font=("Segoe UI", 9, "bold"),
            fg=ACCENT_AMBER,
            bg="#1e1b4b"
        ).pack(pady=(2, 0))

        # Main Question Card
        card = tk.Frame(self, bg=BG_CARD, padx=16, pady=12, highlightbackground="#23304a", highlightthickness=1)
        card.pack(fill="both", expand=True, padx=14, pady=10)

        tk.Label(
            card,
            text="Did you complete yesterday clean?",
            font=("Segoe UI", 11, "bold"),
            fg=TEXT_WHITE,
            bg=BG_CARD
        ).pack()

        tk.Label(
            card,
            text="(Did you sleep / haven't done anything, or did you do it?)",
            font=("Segoe UI", 8),
            fg=TEXT_MUTED,
            bg=BG_CARD
        ).pack(pady=(2, 8))

        # Hard Lock Notice
        warn_frame = tk.Frame(card, bg="#1a1c2e", padx=8, pady=4, highlightbackground="#312e81", highlightthickness=1)
        warn_frame.pack(fill="x", pady=(0, 10))
        tk.Label(
            warn_frame,
            text="🔒 CANNOT BE AVOIDED OR DISMISSED\nThis window re-appears every 3 seconds until registered.\nOnce submitted, your answer is sealed forever in the ledger.",
            font=("Segoe UI", 7, "bold"),
            fg="#cbd5e1",
            bg="#1a1c2e",
            justify="center"
        ).pack()

        # Two Exclusive Action Buttons
        btn_clean = tk.Button(
            card,
            text="🛡️  I HAVEN'T DONE ANYTHING (CLEAN)",
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
            text="🔴  I DID IT (SLIP)",
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

    def _submit_clean(self):
        try:
            self.storage.record_yesterday("clean")
            streak_info = self.storage.get_streak_stats()
            cur = streak_info["current_streak"]
            s_suf = "s" if cur != 1 else ""
            messagebox.showinfo(
                "Yesterday Sealed 🛡️",
                f"Yesterday ({self.yest_formatted}) is permanently sealed as CLEAN.\n\nCurrent Streak: {cur} Day{s_suf}.\n\nRegistration complete. Rest easy today!",
                parent=self
            )
            self.destroy()
            sys.exit(0)
        except ImmutableRecordError:
            self.destroy()
            sys.exit(0)

    def _submit_slip(self):
        try:
            self.storage.record_yesterday("slip")
            messagebox.showinfo(
                "Yesterday Sealed 🔴",
                f"Yesterday ({self.yest_formatted}) is permanently sealed as SLIP.\n\nHonesty is freedom. Build your streak today.",
                parent=self
            )
            self.destroy()
            sys.exit(0)
        except ImmutableRecordError:
            self.destroy()
            sys.exit(0)

    def _on_close_attempt(self):
        # Exits with code 1 so the guardian daemon re-opens it in 3 seconds!
        self.destroy()
        sys.exit(1)

if __name__ == "__main__":
    app = AccountabilityGuard()
    app.mainloop()

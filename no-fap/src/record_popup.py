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

class RecordYesterdayPopup(tk.Tk):
    def __init__(self, on_done_cb=None):
        super().__init__()
        self.storage = Storage()
        self.on_done_cb = on_done_cb

        yesterday = date.today() - timedelta(days=1)
        self.yest_str = yesterday.isoformat()
        self.yest_formatted = yesterday.strftime("%A, %B %d, %Y")

        self.title("Record Yesterday • Tamper-Proof Ledger")
        self.geometry("450x340")
        self.resizable(False, False)
        self.configure(bg=BG_ROOT)
        self.attributes("-topmost", True)

        # Center on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        cx = max(0, (sw - 450) // 2)
        cy = max(0, (sh - 340) // 2)
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
            text="☀️  RECORD YESTERDAY'S ACCOUNTABILITY",
            font=("Segoe UI", 11, "bold"),
            fg=ACCENT_CYAN,
            bg="#1e1b4b"
        ).pack()

        tk.Label(
            header,
            text=f"Evaluating: {self.yest_formatted}",
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

        # Immutable Warning Frame
        warn_frame = tk.Frame(card, bg="#1a1c2e", padx=8, pady=4, highlightbackground="#312e81", highlightthickness=1)
        warn_frame.pack(fill="x", pady=(0, 10))
        tk.Label(
            warn_frame,
            text="🔒 CRYPTOGRAPHIC HARD LOCK\nOnce submitted, this block is permanently hashed & sealed.\nNeither you, the IDE, nor anyone can alter or reset it.",
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
            messagebox.showinfo(
                "Permanently Sealed 🛡️",
                f"Yesterday ({self.yest_formatted}) has been cryptographically sealed as CLEAN.\n\nRecord is permanently locked into the ledger.",
                parent=self
            )
            if self.on_done_cb:
                self.on_done_cb()
            self.destroy()
        except ImmutableRecordError:
            messagebox.showerror("Locked", "Yesterday has already been recorded and locked!", parent=self)
            self.destroy()

    def _submit_slip(self):
        try:
            self.storage.record_yesterday("slip")
            messagebox.showinfo(
                "Permanently Sealed 🔴",
                f"Yesterday ({self.yest_formatted}) has been cryptographically sealed as SLIP.\n\nHonesty is self-respect. Rise and conquer today.",
                parent=self
            )
            if self.on_done_cb:
                self.on_done_cb()
            self.destroy()
        except ImmutableRecordError:
            messagebox.showerror("Locked", "Yesterday has already been recorded and locked!", parent=self)
            self.destroy()

if __name__ == "__main__":
    app = RecordYesterdayPopup()
    app.mainloop()

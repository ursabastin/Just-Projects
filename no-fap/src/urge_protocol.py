import tkinter as tk
from tkinter import ttk, messagebox
import math
import random

REALISTIC_URGE_CHALLENGES = [
    ("Close your browser tabs immediately and stand up from your chair for 60 seconds.", "🛑 STEP AWAY"),
    ("Walk to the kitchen, pour a tall glass of cold water, and drink it slowly.", "💧 HYDRATE"),
    ("Wash your hands and splash cool water on your eyes and face at the sink.", "🚰 COOL SPLASH"),
    ("Leave this room right now. Walk to another room or step outside for 3 minutes.", "🚪 CHANGE ROOM"),
    ("Put your phone face down across the room. Keep both hands visibly on the desk.", "📵 NO PHONE"),
    ("Ask yourself: What am I feeling right now? (Boredom? Stress? Loneliness? Procrastination?)", "🧠 NAME THE TRIGGER")
]

STOIC_REMINDERS = [
    "\"The craving is just an adrenaline and dopamine spike. It peaks in 10 minutes and subsides. You are in command.\"",
    "\"You are not your impulses. You are the consciousness that chooses which impulses to act on.\"",
    "\"Five seconds of cheap dopamine will steal hours of energy, clarity, and self-respect.\"",
    "\"Every single time you close the tab and step away, your prefrontal cortex physically rewires.\""
]

class UrgeProtocolModal(tk.Toplevel):
    def __init__(self, parent, storage, on_victory_cb=None):
        super().__init__(parent)
        self.storage = storage
        self.on_victory_cb = on_victory_cb
        
        self.title("⚡ Emergency Urge Redirection Protocol")
        self.geometry("420x580")
        self.resizable(False, False)
        self.configure(bg="#090d16")
        self.transient(parent)
        self.grab_set()

        # Center on screen
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 210
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 290
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

        self.breathing_active = True
        self.breath_phase = 0
        self.phase_timer = 0
        self.phase_duration = 4.0
        self.orb_scale = 0.3
        self.cycle_count = 0
        self.current_challenge_idx = random.randint(0, len(REALISTIC_URGE_CHALLENGES) - 1)
        self.current_quote = random.choice(STOIC_REMINDERS)

        self._build_ui()
        self._animate_breathing()

    def _build_ui(self):
        # Header banner
        header = tk.Frame(self, bg="#1e1b4b", padx=15, pady=10)
        header.pack(fill="x")
        
        lbl_title = tk.Label(
            header,
            text="⚡ EMERGENCY URGE KILLER",
            font=("Segoe UI", 13, "bold"),
            fg="#f43f5e",
            bg="#1e1b4b"
        )
        lbl_title.pack()
        
        lbl_sub = tk.Label(
            header,
            text="The urge wave lasts 10-15 minutes. Ride the wave, do NOT act on it.",
            font=("Segoe UI", 8),
            fg="#cbd5e1",
            bg="#1e1b4b"
        )
        lbl_sub.pack()

        # Breathing container
        breath_frame = tk.Frame(self, bg="#0f172a", pady=8)
        breath_frame.pack(fill="x", padx=12, pady=(10, 6))

        tk.Label(
            breath_frame,
            text="BOX BREATHING (4-4-4-4 CALM REGULATION)",
            font=("Segoe UI", 8, "bold"),
            fg="#38bdf8",
            bg="#0f172a"
        ).pack()

        self.canvas = tk.Canvas(breath_frame, width=280, height=120, bg="#0f172a", highlightthickness=0)
        self.canvas.pack()

        self.lbl_instruction = tk.Label(
            breath_frame,
            text="Inhale deeply...",
            font=("Segoe UI", 10, "bold"),
            fg="#38bdf8",
            bg="#0f172a"
        )
        self.lbl_instruction.pack()

        # Practical Desk Challenge Box
        chal_box = tk.Frame(self, bg="#1e293b", padx=12, pady=10, relief="solid", bd=1)
        chal_box.pack(fill="x", padx=12, pady=6)

        header_chal = tk.Frame(chal_box, bg="#1e293b")
        header_chal.pack(fill="x")

        self.lbl_chal_badge = tk.Label(
            header_chal,
            text=REALISTIC_URGE_CHALLENGES[self.current_challenge_idx][1],
            font=("Segoe UI", 8, "bold"),
            fg="#fbbf24",
            bg="#374151",
            padx=6,
            pady=2
        )
        self.lbl_chal_badge.pack(side="left")

        btn_shuffle = tk.Button(
            header_chal,
            text="🎲 Another Action",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#1e293b",
            activebackground="#334155",
            activeforeground="#f8fafc",
            bd=0,
            cursor="hand2",
            command=self._shuffle_challenge
        )
        btn_shuffle.pack(side="right")

        self.lbl_chal_text = tk.Label(
            chal_box,
            text=REALISTIC_URGE_CHALLENGES[self.current_challenge_idx][0],
            font=("Segoe UI", 9, "bold"),
            fg="#f8fafc",
            bg="#1e293b",
            wraplength=370,
            justify="left",
            pady=6
        )
        self.lbl_chal_text.pack(anchor="w")

        # Stoic Reminder
        quote_box = tk.Frame(self, bg="#090d16", padx=12, pady=4)
        quote_box.pack(fill="x", padx=12)

        self.lbl_quote = tk.Label(
            quote_box,
            text=self.current_quote,
            font=("Segoe UI", 8, "italic"),
            fg="#94a3b8",
            bg="#090d16",
            wraplength=380,
            justify="center"
        )
        self.lbl_quote.pack()

        # Bottom Action Bar
        actions_frame = tk.Frame(self, bg="#090d16", padx=12, pady=10)
        actions_frame.pack(fill="x", side="bottom")

        btn_victory = tk.Button(
            actions_frame,
            text="🏆 I DEFEATED THIS URGE (+75 XP)",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg="#059669",
            activebackground="#10b981",
            activeforeground="#ffffff",
            bd=0,
            pady=8,
            cursor="hand2",
            command=self._on_conquer
        )
        btn_victory.pack(fill="x", pady=(0, 6))

        btn_close = tk.Button(
            actions_frame,
            text="Close / Back to Dashboard",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#1e293b",
            activebackground="#334155",
            activeforeground="#f8fafc",
            bd=0,
            pady=4,
            cursor="hand2",
            command=self._close_modal
        )
        btn_close.pack(fill="x")

    def _shuffle_challenge(self):
        new_idx = random.randint(0, len(REALISTIC_URGE_CHALLENGES) - 1)
        while new_idx == self.current_challenge_idx and len(REALISTIC_URGE_CHALLENGES) > 1:
            new_idx = random.randint(0, len(REALISTIC_URGE_CHALLENGES) - 1)
        self.current_challenge_idx = new_idx
        text, badge = REALISTIC_URGE_CHALLENGES[self.current_challenge_idx]
        self.lbl_chal_badge.config(text=badge)
        self.lbl_chal_text.config(text=text)

    def _animate_breathing(self):
        if not self.breathing_active or not self.winfo_exists():
            return

        dt = 0.05
        self.phase_timer += dt

        if self.phase_timer >= self.phase_duration:
            self.phase_timer = 0
            self.breath_phase = (self.breath_phase + 1) % 4
            if self.breath_phase == 0:
                self.cycle_count += 1

        t = self.phase_timer / self.phase_duration

        if self.breath_phase == 0:
            self.orb_scale = 0.25 + 0.55 * (1.0 - math.cos(t * math.pi / 2))
            phase_name = f"🌬️ INHALE DEEPLY ({int(self.phase_duration - self.phase_timer + 1)}s)"
            color = "#38bdf8"
        elif self.breath_phase == 1:
            self.orb_scale = 0.8
            phase_name = f"⏸️ HOLD BREATH ({int(self.phase_duration - self.phase_timer + 1)}s)"
            color = "#818cf8"
        elif self.breath_phase == 2:
            self.orb_scale = 0.8 - 0.55 * (math.sin(t * math.pi / 2))
            phase_name = f"💨 EXHALE SLOWLY ({int(self.phase_duration - self.phase_timer + 1)}s)"
            color = "#34d399"
        else:
            self.orb_scale = 0.25
            phase_name = f"⏸️ HOLD EMPTY ({int(self.phase_duration - self.phase_timer + 1)}s)"
            color = "#f59e0b"

        self.lbl_instruction.config(text=phase_name, fg=color)

        self.canvas.delete("all")
        cx, cy = 140, 60
        r = 14 + int(self.orb_scale * 45)
        
        self.canvas.create_oval(cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8, fill="", outline="#1e293b", width=3)
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="#ffffff", width=2)
        self.canvas.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill="#ffffff", outline="")

        self.after(50, self._animate_breathing)

    def _on_conquer(self):
        new_count = self.storage.record_urge_defeated()
        messagebox.showinfo(
            "Urge Conquered! 🛡️ (+75 XP)",
            f"Tremendous mental strength! You conquered this urge wave.\n\nTotal Urges Defeated: {new_count}\nReward: +75 XP earned!\n\nYour willpower grows stronger every single time.",
            parent=self
        )
        if self.on_victory_cb:
            self.on_victory_cb()
        self._close_modal()

    def _close_modal(self):
        self.breathing_active = False
        self.destroy()

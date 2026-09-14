import tkinter as tk
from tkinter import ttk

BG_ROOT = "#090d16"
BG_CARD = "#131b2e"
BG_CARD_HOVER = "#1e293b"
BORDER_SUBTLE = "#23304a"
BORDER_ACTIVE = "#38bdf8"
ACCENT_EMERALD = "#10b981"
ACCENT_ROSE = "#f43f5e"
ACCENT_CYAN = "#38bdf8"
ACCENT_AMBER = "#fbbf24"
TEXT_WHITE = "#f8fafc"
TEXT_MUTED = "#94a3b8"
TEXT_DIM = "#64748b"

class ModernProgressBar(tk.Canvas):
    def __init__(self, parent, height=14, bg_bar="#1e293b", fill_color=ACCENT_EMERALD, **kwargs):
        super().__init__(parent, height=height, bg=BG_CARD, highlightthickness=0, **kwargs)
        self.height = height
        self.bg_bar = bg_bar
        self.fill_color = fill_color
        self.progress = 0.0
        self.bind("<Configure>", lambda e: self._draw())

    def set_progress(self, val):
        self.progress = max(0.0, min(1.0, float(val)))
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.height
        if w <= 1:
            return
        self.create_rectangle(0, 0, w, h, fill=self.bg_bar, outline="")
        pw = int(w * self.progress)
        if pw > 0:
            self.create_rectangle(0, 0, pw, h, fill=self.fill_color, outline="")

class HabitCheckRow(tk.Frame):
    def __init__(self, parent, habit, is_checked, on_toggle_cb, on_delete_cb=None):
        super().__init__(parent, bg=BG_CARD, padx=8, pady=6, highlightbackground=BORDER_SUBTLE, highlightthickness=1)
        self.habit = habit
        self.is_checked = is_checked
        self.on_toggle_cb = on_toggle_cb
        self.on_delete_cb = on_delete_cb

        self.bind("<Enter>", lambda e: self.configure(highlightbackground=BORDER_ACTIVE))
        self.bind("<Leave>", lambda e: self.configure(highlightbackground=BORDER_SUBTLE))

        self.chk_canvas = tk.Canvas(self, width=22, height=22, bg=BG_CARD, highlightthickness=0, cursor="hand2")
        self.chk_canvas.pack(side="left", padx=(0, 8))
        self.chk_canvas.bind("<Button-1>", lambda e: self._toggle())

        self.lbl_text = tk.Label(
            self,
            text=self.habit["name"],
            font=("Segoe UI", 9),
            fg=TEXT_MUTED if self.is_checked else TEXT_WHITE,
            bg=BG_CARD,
            cursor="hand2",
            anchor="w"
        )
        self.lbl_text.pack(side="left", fill="x", expand=True)
        self.lbl_text.bind("<Button-1>", lambda e: self._toggle())

        # Delete button for custom or all habits
        self.btn_del = tk.Label(
            self,
            text="✕",
            font=("Segoe UI", 8),
            fg=TEXT_DIM,
            bg=BG_CARD,
            cursor="hand2",
            padx=4
        )
        self.btn_del.pack(side="right")
        self.btn_del.bind("<Button-1>", lambda e: self._on_delete())
        self.btn_del.bind("<Enter>", lambda e: self.btn_del.configure(fg=ACCENT_ROSE))
        self.btn_del.bind("<Leave>", lambda e: self.btn_del.configure(fg=TEXT_DIM))

        self._draw_check()

    def _draw_check(self):
        self.chk_canvas.delete("all")
        if self.is_checked:
            self.chk_canvas.create_oval(2, 2, 20, 20, fill=ACCENT_EMERALD, outline=ACCENT_EMERALD)
            self.chk_canvas.create_line(6, 11, 10, 15, fill="#ffffff", width=2)
            self.chk_canvas.create_line(10, 15, 16, 7, fill="#ffffff", width=2)
            self.lbl_text.configure(fg=TEXT_DIM, font=("Segoe UI", 9, "overstrike"))
        else:
            self.chk_canvas.create_oval(2, 2, 20, 20, fill="#1e293b", outline="#475569", width=2)
            self.lbl_text.configure(fg=TEXT_WHITE, font=("Segoe UI", 9))

    def _toggle(self):
        self.is_checked = not self.is_checked
        self._draw_check()
        self.on_toggle_cb(self.habit["id"])

    def _on_delete(self):
        if self.on_delete_cb:
            self.on_delete_cb(self.habit["id"])

    def set_checked(self, checked):
        self.is_checked = checked
        self._draw_check()

class LevelGuideModal(tk.Toplevel):
    def __init__(self, parent, storage):
        super().__init__(parent)
        self.storage = storage
        self.title("📊 Level System & Neurochemical Roadmap")
        self.geometry("440x620")
        self.resizable(False, False)
        self.configure(bg="#090d16")
        self.transient(parent)
        self.grab_set()

        # Center
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 220
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 310
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

        self._build_ui()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg="#1e1b4b", padx=14, pady=10)
        hdr.pack(fill="x")

        tk.Label(
            hdr,
            text="📊 LEVEL SYSTEM & XP ROADMAP",
            font=("Segoe UI", 11, "bold"),
            fg=ACCENT_CYAN,
            bg="#1e1b4b"
        ).pack()

        total_xp = self.storage.get_total_xp()
        current_lvl = self.storage.get_level_info()

        tk.Label(
            hdr,
            text=f"Your Status: Level {current_lvl['level']} ({current_lvl['title']}) • Total XP: {total_xp:,}",
            font=("Segoe UI", 8, "bold"),
            fg=ACCENT_AMBER,
            bg="#1e1b4b"
        ).pack(pady=(2, 0))

        # XP Earning Rules Card
        rules_card = tk.Frame(self, bg="#131b2e", padx=10, pady=8, highlightbackground=BORDER_SUBTLE, highlightthickness=1)
        rules_card.pack(fill="x", padx=12, pady=(10, 6))

        tk.Label(
            rules_card,
            text="HOW YOU EARN EXPERIENCE (XP):",
            font=("Segoe UI", 8, "bold"),
            fg=ACCENT_EMERALD,
            bg="#131b2e"
        ).pack(anchor="w")

        rules_text = (
            "• Daily Habit Checkbox: +25 XP each\n"
            "• Flawless Day (100% habits done): +100 XP bonus\n"
            "• Emergency Urge Conquered: +75 XP each\n"
            "• Clean Streak Time: +5 XP per clean hour (+120 XP/day)"
        )
        tk.Label(
            rules_card,
            text=rules_text,
            font=("Segoe UI", 8),
            fg=TEXT_WHITE,
            bg="#131b2e",
            justify="left"
        ).pack(anchor="w", pady=(2, 0))

        # Levels List Container (Scrollable)
        container = tk.Frame(self, bg="#090d16")
        container.pack(fill="both", expand=True, padx=12, pady=4)

        canvas = tk.Canvas(container, bg="#090d16", highlightthickness=0)
        sb = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#090d16")

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        c_win = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)

        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(c_win, width=e.width))

        levels = self.storage.get_all_levels()
        for lvl in levels:
            is_active = (lvl["level"] == current_lvl["level"])
            is_reached = lvl["is_reached"]

            bg_box = "#1e293b" if is_active else ("#131b2e" if is_reached else "#0d1322")
            border_c = ACCENT_AMBER if is_active else (ACCENT_EMERALD if is_reached else BORDER_SUBTLE)

            card = tk.Frame(scroll_frame, bg=bg_box, padx=10, pady=8, highlightbackground=border_c, highlightthickness=1)
            card.pack(fill="x", pady=4)

            # Top line: Level title & XP range
            top_line = tk.Frame(card, bg=bg_box)
            top_line.pack(fill="x")

            title_txt = f"{lvl['badge']} Level {lvl['level']}: {lvl['title'].upper()}"
            if is_active:
                title_txt += " (CURRENT)"

            tk.Label(
                top_line,
                text=title_txt,
                font=("Segoe UI", 9, "bold"),
                fg=ACCENT_AMBER if is_active else (ACCENT_EMERALD if is_reached else TEXT_MUTED),
                bg=bg_box
            ).pack(side="left")

            range_txt = f"{lvl['min_xp']:,} - {lvl['max_xp']:,} XP" if lvl['max_xp'] else f"{lvl['min_xp']:,}+ XP"
            tk.Label(
                top_line,
                text=range_txt,
                font=("Segoe UI", 8, "bold"),
                fg=TEXT_WHITE if is_reached else TEXT_DIM,
                bg=bg_box
            ).pack(side="right")

            # Description
            tk.Label(
                card,
                text=lvl["desc"],
                font=("Segoe UI", 8),
                fg=TEXT_WHITE if is_reached else TEXT_MUTED,
                bg=bg_box,
                wraplength=380,
                justify="left"
            ).pack(anchor="w", pady=(2, 2))

            # Neurochemical Phase
            tk.Label(
                card,
                text="🧠 " + lvl["scientific_phase"],
                font=("Segoe UI", 7, "italic"),
                fg=ACCENT_CYAN if is_reached else TEXT_DIM,
                bg=bg_box,
                wraplength=380,
                justify="left"
            ).pack(anchor="w")

        # Close Button
        btn_close = tk.Button(
            self,
            text="Got It / Close",
            font=("Segoe UI", 9, "bold"),
            fg=TEXT_WHITE,
            bg="#1e293b",
            activebackground="#334155",
            activeforeground=TEXT_WHITE,
            bd=0,
            pady=6,
            cursor="hand2",
            command=self.destroy
        )
        btn_close.pack(fill="x", padx=12, pady=10)

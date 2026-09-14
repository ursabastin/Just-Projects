import os
import sys
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, date, timedelta
import calendar

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from storage import Storage
from record_popup import RecordYesterdayPopup

BG_ROOT = "#090d16"
BG_CARD = "#131b2e"
BG_CELL = "#1a2234"
BG_CELL_OTHER_MONTH = "#0d1322"
BG_CELL_CLEAN = "#059669"
BG_CELL_SLIP = "#dc2626"
BORDER_SUBTLE = "#23304a"
BORDER_TODAY = "#38bdf8"
BORDER_YESTERDAY_PENDING = "#fbbf24"
ACCENT_EMERALD = "#10b981"
ACCENT_CYAN = "#38bdf8"
ACCENT_AMBER = "#fbbf24"
ACCENT_ROSE = "#f43f5e"
TEXT_WHITE = "#f8fafc"
TEXT_MUTED = "#94a3b8"
TEXT_DIM = "#475569"

WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

class ModernProgressBar(tk.Canvas):
    def __init__(self, parent, height=8, bg_bar="#1e293b", fill_color=ACCENT_EMERALD, **kwargs):
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

class CalendarApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.storage = Storage()

        self.title("Discipline Calendar - Immutable Encrypted Ledger")
        self.geometry("450x640")
        self.resizable(False, False)
        self.configure(bg=BG_ROOT)

        # Center on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        cx = max(0, (sw - 450) // 2)
        cy = max(0, (sh - 640) // 2)
        self.geometry(f"+{cx}+{cy}")

        today = date.today()
        self.view_year = today.year
        self.view_month = today.month

        # Prevent root geometry shifts
        self.pack_propagate(False)

        self.cells = []
        self.cell_dates = []

        self._build_ui()
        self._init_calendar_cells()
        self._update_display()

    def _build_ui(self):
        # 1. Top Header Banner
        top_bar = tk.Frame(self, bg=BG_ROOT, padx=14, pady=8, height=42)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        tk.Label(
            top_bar,
            text="🔒 IMMUTABLE CALENDAR",
            font=("Segoe UI", 11, "bold"),
            fg=ACCENT_CYAN,
            bg=BG_ROOT
        ).pack(side="left")

        self.lbl_streak_badge = tk.Label(
            top_bar,
            text="🔥 0 Days",
            font=("Segoe UI", 9, "bold"),
            fg=ACCENT_AMBER,
            bg="#1e293b",
            padx=8,
            pady=3,
            width=10
        )
        self.lbl_streak_badge.pack(side="right")

        # 2. Stats Summary Card
        stats_card = tk.Frame(self, bg=BG_CARD, padx=12, pady=10, highlightbackground=BORDER_SUBTLE, highlightthickness=1, height=96)
        stats_card.pack(fill="x", padx=14, pady=(0, 6))
        stats_card.pack_propagate(False)

        metrics_row = tk.Frame(stats_card, bg=BG_CARD)
        metrics_row.pack(fill="x")

        # Col 1: Current streak
        col1 = tk.Frame(metrics_row, bg=BG_CARD)
        col1.pack(side="left", fill="x", expand=True)
        tk.Label(col1, text="CURRENT STREAK", font=("Segoe UI", 7, "bold"), fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w")
        self.lbl_current_streak = tk.Label(col1, text="0 Days", font=("Segoe UI", 11, "bold"), fg=ACCENT_AMBER, bg=BG_CARD)
        self.lbl_current_streak.pack(anchor="w")

        # Col 2: Best streak
        col2 = tk.Frame(metrics_row, bg=BG_CARD)
        col2.pack(side="left", fill="x", expand=True)
        tk.Label(col2, text="BEST STREAK", font=("Segoe UI", 7, "bold"), fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w")
        self.lbl_best_streak = tk.Label(col2, text="0 Days", font=("Segoe UI", 11, "bold"), fg=ACCENT_CYAN, bg=BG_CARD)
        self.lbl_best_streak.pack(anchor="w")

        # Col 3: Total clean
        col3 = tk.Frame(metrics_row, bg=BG_CARD)
        col3.pack(side="left", fill="x", expand=True)
        tk.Label(col3, text="TOTAL CLEAN", font=("Segoe UI", 7, "bold"), fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w")
        self.lbl_total_clean = tk.Label(col3, text="0 Days", font=("Segoe UI", 11, "bold"), fg=ACCENT_EMERALD, bg=BG_CARD)
        self.lbl_total_clean.pack(anchor="w")

        # Monthly progress label
        self.lbl_month_progress = tk.Label(
            stats_card,
            text="Month: 0 / 0 Clean Days (0%)",
            font=("Segoe UI", 8),
            fg=TEXT_WHITE,
            bg=BG_CARD
        )
        self.lbl_month_progress.pack(anchor="w", pady=(6, 2))

        self.bar_month = ModernProgressBar(stats_card, height=6, bg_bar="#1e293b", fill_color=ACCENT_EMERALD)
        self.bar_month.pack(fill="x")

        # 3. Month Navigator Bar
        nav_card = tk.Frame(self, bg=BG_ROOT, padx=14, height=32)
        nav_card.pack(fill="x", pady=(2, 4))
        nav_card.pack_propagate(False)

        btn_prev = tk.Button(
            nav_card,
            text="◀",
            font=("Segoe UI", 9, "bold"),
            fg=TEXT_WHITE,
            bg="#1e293b",
            activebackground="#334155",
            activeforeground=TEXT_WHITE,
            bd=0,
            padx=10,
            pady=1,
            cursor="hand2",
            command=self._prev_month
        )
        btn_prev.pack(side="left")

        self.lbl_month_title = tk.Label(
            nav_card,
            text="September 2026",
            font=("Segoe UI", 11, "bold"),
            fg=TEXT_WHITE,
            bg=BG_ROOT,
            width=18
        )
        self.lbl_month_title.pack(side="left", padx=6)

        btn_next = tk.Button(
            nav_card,
            text="▶",
            font=("Segoe UI", 9, "bold"),
            fg=TEXT_WHITE,
            bg="#1e293b",
            activebackground="#334155",
            activeforeground=TEXT_WHITE,
            bd=0,
            padx=10,
            pady=1,
            cursor="hand2",
            command=self._next_month
        )
        btn_next.pack(side="left")

        btn_today = tk.Button(
            nav_card,
            text="Today",
            font=("Segoe UI", 8, "bold"),
            fg=ACCENT_CYAN,
            bg="#1e293b",
            activebackground="#334155",
            activeforeground=TEXT_WHITE,
            bd=0,
            padx=8,
            pady=1,
            cursor="hand2",
            command=self._jump_today
        )
        btn_today.pack(side="right")

        # 4. Weekday Headers
        weekdays_frame = tk.Frame(self, bg=BG_ROOT, padx=14, height=22)
        weekdays_frame.pack(fill="x")
        weekdays_frame.pack_propagate(False)
        for i, wd in enumerate(WEEKDAYS):
            lbl_wd = tk.Label(
                weekdays_frame,
                text=wd,
                font=("Segoe UI", 8, "bold"),
                fg=TEXT_DIM if i >= 5 else TEXT_MUTED,
                bg=BG_ROOT
            )
            lbl_wd.grid(row=0, column=i, sticky="nsew", padx=2)
            weekdays_frame.grid_columnconfigure(i, weight=1, uniform="wday")

        # 5. Calendar Days Grid Container (Fixed static grid)
        self.grid_frame = tk.Frame(self, bg=BG_ROOT, padx=14, height=310)
        self.grid_frame.pack(fill="both", expand=True, pady=(2, 4))
        self.grid_frame.grid_propagate(False)
        for c in range(7):
            self.grid_frame.grid_columnconfigure(c, weight=1, uniform="daycol")
        for r in range(6):
            self.grid_frame.grid_rowconfigure(r, weight=1, uniform="dayrow")

        # 6. Action Button (For Yesterday Recording Only)
        action_box = tk.Frame(self, bg=BG_ROOT, padx=14, pady=2, height=46)
        action_box.pack(fill="x")
        action_box.pack_propagate(False)

        self.btn_action = tk.Button(
            action_box,
            text="🔒 ALL RECORDS ARE PERMANENT & ENCRYPTED",
            font=("Segoe UI", 9, "bold"),
            fg=TEXT_MUTED,
            bg="#1e293b",
            activebackground="#334155",
            activeforeground=TEXT_WHITE,
            bd=0,
            pady=6,
            cursor="arrow",
            command=self._on_action_click
        )
        self.btn_action.pack(fill="both", expand=True)

        # 7. Legend & Status Footer
        legend_frame = tk.Frame(self, bg="#0d1322", padx=14, pady=5, height=44)
        legend_frame.pack(fill="x", side="bottom")
        legend_frame.pack_propagate(False)

        tk.Label(
            legend_frame,
            text="🟢 Clean (Sealed)   🔴 Slipped (Sealed)   ⚡ Yesterday (Click to Record)   🔷 Today",
            font=("Segoe UI", 7, "bold"),
            fg=ACCENT_CYAN,
            bg="#0d1322"
        ).pack()
        tk.Label(
            legend_frame,
            text="Cryptographic ledger. Only yesterday can be recorded. Once set, it cannot be changed.",
            font=("Segoe UI", 7, "italic"),
            fg=TEXT_DIM,
            bg="#0d1322"
        ).pack()

    def _init_calendar_cells(self):
        self.cells = []
        for idx in range(42):
            r = idx // 7
            c = idx % 7

            cell = tk.Frame(
                self.grid_frame,
                bg=BG_CELL,
                highlightbackground=BORDER_SUBTLE,
                highlightthickness=2,
                padx=1,
                pady=1
            )
            cell.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
            cell.pack_propagate(False)

            lbl_num = tk.Label(
                cell,
                text="",
                font=("Segoe UI", 9, "bold"),
                fg=TEXT_WHITE,
                bg=BG_CELL
            )
            lbl_num.pack(anchor="center", pady=(1, 0))

            lbl_st = tk.Label(
                cell,
                text="",
                font=("Segoe UI", 6, "bold"),
                fg=TEXT_WHITE,
                bg=BG_CELL,
                height=1
            )
            lbl_st.pack(anchor="center")

            cell.bind("<Button-1>", lambda e, i=idx: self._on_cell_click(i))
            lbl_num.bind("<Button-1>", lambda e, i=idx: self._on_cell_click(i))
            lbl_st.bind("<Button-1>", lambda e, i=idx: self._on_cell_click(i))

            self.cells.append({
                "cell": cell,
                "lbl_num": lbl_num,
                "lbl_st": lbl_st
            })

    def _update_display(self):
        cal = calendar.Calendar(firstweekday=0)
        dates = list(cal.itermonthdates(self.view_year, self.view_month))
        today = date.today()
        yesterday = today - timedelta(days=1)

        month_name = calendar.month_name[self.view_month]
        self.lbl_month_title.configure(text=f"{month_name} {self.view_year}")

        self.cell_dates = []

        for idx, d in enumerate(dates[:42]):
            self.cell_dates.append(d)
            cell_data = self.cells[idx]
            cell = cell_data["cell"]
            lbl_num = cell_data["lbl_num"]
            lbl_st = cell_data["lbl_st"]

            is_current_month = (d.month == self.view_month)
            is_today = (d == today)
            is_yesterday = (d == yesterday)
            is_future = (d > today)
            d_str = d.isoformat()
            status = self.storage.get_day_status(d_str)

            # Pick colors
            if not is_current_month:
                bg_color = BG_CELL_OTHER_MONTH
                fg_num = TEXT_DIM
                st_text = ""
                border_color = BORDER_SUBTLE
                cursor = ""
            elif status == "clean":
                bg_color = BG_CELL_CLEAN
                fg_num = TEXT_WHITE
                st_text = "🔒 CLEAN"
                border_color = "#047857"
                cursor = "hand2"
            elif status == "slip":
                bg_color = BG_CELL_SLIP
                fg_num = TEXT_WHITE
                st_text = "🔒 SLIP"
                border_color = "#b91c1c"
                cursor = "hand2"
            elif is_future:
                bg_color = "#111827"
                fg_num = TEXT_DIM
                st_text = ""
                border_color = BORDER_SUBTLE
                cursor = ""
            elif is_yesterday and not status:
                # YESTERDAY IS UNLOCKED AND PENDING RECORDING!
                bg_color = "#2d2410"
                fg_num = ACCENT_AMBER
                st_text = "RECORD"
                border_color = BORDER_YESTERDAY_PENDING
                cursor = "hand2"
            else:
                # Past unrecorded
                bg_color = BG_CELL
                fg_num = TEXT_MUTED
                st_text = "UNLOGGED"
                border_color = BORDER_SUBTLE
                cursor = "hand2"

            if is_today:
                border_color = BORDER_TODAY
                st_text = "TODAY"

            cell.configure(bg=bg_color, highlightbackground=border_color, cursor=cursor)
            lbl_num.configure(text=str(d.day), fg=fg_num, bg=bg_color)
            lbl_st.configure(
                text=st_text,
                fg=ACCENT_AMBER if (is_yesterday and not status) else (ACCENT_CYAN if is_today else TEXT_WHITE),
                bg=bg_color
            )

        self._update_stats()
        self._update_action_button()

    def _update_action_button(self):
        today = date.today()
        yesterday = today - timedelta(days=1)
        yest_str = yesterday.isoformat()

        if not self.storage.is_yesterday_recorded():
            self.btn_action.configure(
                text=f"⚠️ RECORD YESTERDAY ({yesterday.strftime('%b %d')}) - CLICK HERE",
                fg="#ffffff",
                bg="#b45309",
                activebackground="#d97706",
                cursor="hand2"
            )
        else:
            yest_st = self.storage.get_day_status(yest_str).upper()
            self.btn_action.configure(
                text=f"🔒 YESTERDAY SEALED ({yest_st}) • TODAY IN PROGRESS",
                fg=ACCENT_EMERALD if yest_st == "CLEAN" else ACCENT_ROSE,
                bg="#1e293b",
                activebackground="#1e293b",
                cursor="arrow"
            )

    def _on_action_click(self):
        if not self.storage.is_yesterday_recorded():
            RecordYesterdayPopup(on_done_cb=self._on_popup_done)
        else:
            yest_str = self.storage.get_yesterday_date()
            st = self.storage.get_day_status(yest_str).upper()
            messagebox.showinfo(
                "Permanently Sealed 🔒",
                f"Yesterday is already cryptographically recorded as {st}.\n\nUnder strict rules, records are permanent and cannot be altered.",
                parent=self
            )

    def _on_popup_done(self):
        self.storage = Storage()
        self._update_display()

    def _on_cell_click(self, idx):
        if idx >= len(self.cell_dates):
            return
        d = self.cell_dates[idx]
        today = date.today()
        yesterday = today - timedelta(days=1)
        d_str = d.isoformat()

        if d > today:
            messagebox.showinfo("Future Date", "Future dates cannot be recorded in advance.", parent=self)
            return

        if d == today:
            messagebox.showinfo(
                "Today In Progress ⏳",
                "Today is still ongoing! Under strict discipline rules, a day can only be evaluated and recorded once it is finished (tomorrow as yesterday).",
                parent=self
            )
            return

        # Check if already locked
        status = self.storage.get_day_status(d_str)
        if status is not None:
            messagebox.showinfo(
                "Permanently Sealed 🔒",
                f"{d.strftime('%A, %B %d, %Y')}\n\nStatus: {status.upper()}\n\nThis record is cryptographically sealed with Windows DPAPI and a SHA-256 hash-chain.\nIt CANNOT be altered, deleted, or reset by anyone.",
                parent=self
            )
            return

        # Date is unrecorded
        if d == yesterday:
            # THIS IS THE ONLY DATE THAT CAN BE RECORDED!
            RecordYesterdayPopup(on_done_cb=self._on_popup_done)
        else:
            messagebox.showinfo(
                "Past Date Closed 🔒",
                f"{d.strftime('%A, %B %d, %Y')} is past and unrecorded.\n\nUnder strict accountability rules, only yesterday can be evaluated and recorded.",
                parent=self
            )

    def _prev_month(self):
        if self.view_month == 1:
            self.view_month = 12
            self.view_year -= 1
        else:
            self.view_month -= 1
        self._update_display()

    def _next_month(self):
        if self.view_month == 12:
            self.view_month = 1
            self.view_year += 1
        else:
            self.view_month += 1
        self._update_display()

    def _jump_today(self):
        today = date.today()
        self.view_year = today.year
        self.view_month = today.month
        self._update_display()

    def _update_stats(self):
        streak_info = self.storage.get_streak_stats()
        month_info = self.storage.get_month_stats(self.view_year, self.view_month)

        cur = streak_info["current_streak"]
        best = streak_info["longest_streak"]
        tot = streak_info["total_clean_days"]

        s_suf = "s" if cur != 1 else ""
        b_suf = "s" if best != 1 else ""
        t_suf = "s" if tot != 1 else ""

        self.lbl_streak_badge.configure(text=f"🔥 {cur} Day{s_suf}")
        self.lbl_current_streak.configure(text=f"{cur} Day{s_suf}")
        self.lbl_best_streak.configure(text=f"{best} Day{b_suf}")
        self.lbl_total_clean.configure(text=f"{tot} Day{t_suf}")

        m_name = calendar.month_name[self.view_month]
        clean_cnt = month_info["clean_count"]
        elapsed = month_info["elapsed_days"]
        pct = month_info["clean_percentage"]

        self.lbl_month_progress.configure(
            text=f"{m_name}: {clean_cnt} / {elapsed} Clean Days ({int(pct)}% Clean)"
        )
        self.bar_month.set_progress(pct / 100.0)

if __name__ == "__main__":
    app = CalendarApp()
    app.mainloop()

import tkinter as tk
from tkinter import font as tkfont

# Strict, refined dark-mode palette
BG_ROOT = "#090d16"
BG_CARD = "#131b2e"
BG_CARD_HOVER = "#18223a"
BG_INPUT = "#0c1322"
BORDER_SUBTLE = "#23304a"
BORDER_FOCUS = "#38bdf8"
ACCENT_CYAN = "#38bdf8"
ACCENT_EMERALD = "#10b981"
ACCENT_AMBER = "#fbbf24"
ACCENT_ROSE = "#f43f5e"
TEXT_WHITE = "#f8fafc"
TEXT_MUTED = "#94a3b8"
TEXT_DIM = "#64748b"

FONT_FAMILY = "Segoe UI"

class ModernProgressBar(tk.Canvas):
    """Clean, smooth canvas-rendered progress bar."""
    def __init__(self, parent, height=10, bg_bar="#1c263c", fill_color=ACCENT_CYAN, **kwargs):
        super().__init__(parent, height=height, bg=BG_CARD, highlightthickness=0, **kwargs)
        self.bar_height = height
        self.bg_bar = bg_bar
        self.fill_color = fill_color
        self.progress = 0.0
        self.bind("<Configure>", lambda e: self._draw())

    def set_progress(self, val: float):
        self.progress = max(0.0, min(1.0, float(val)))
        self._draw()

    def set_fill_color(self, color: str):
        self.fill_color = color
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.bar_height
        if w <= 1:
            return
        
        # Background track
        self.create_rectangle(0, 0, w, h, fill=self.bg_bar, outline="")
        
        # Fill bar
        pw = int(w * self.progress)
        if pw > 0:
            self.create_rectangle(0, 0, pw, h, fill=self.fill_color, outline="")

class StyledEntry(tk.Frame):
    """Sleek dark input bar with placeholder and focus border highlight."""
    def __init__(self, parent, placeholder="", **kwargs):
        super().__init__(parent, bg=BG_INPUT, highlightbackground=BORDER_SUBTLE, highlightthickness=1)
        self.placeholder = placeholder
        self.has_placeholder = False

        self.entry = tk.Entry(
            self,
            font=(FONT_FAMILY, 10),
            bg=BG_INPUT,
            fg=TEXT_WHITE,
            insertbackground=ACCENT_CYAN,
            relief="flat",
            highlightthickness=0,
            **kwargs
        )
        self.entry.pack(fill="both", expand=True, padx=10, pady=8)

        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)

        if placeholder:
            self._set_placeholder()

    def _set_placeholder(self):
        self.has_placeholder = True
        self.entry.delete(0, "end")
        self.entry.insert(0, self.placeholder)
        self.entry.configure(fg=TEXT_DIM)

    def _on_focus_in(self, e):
        self.configure(highlightbackground=BORDER_FOCUS)
        if self.has_placeholder:
            self.has_placeholder = False
            self.entry.delete(0, "end")
            self.entry.configure(fg=TEXT_WHITE)

    def _on_focus_out(self, e):
        self.configure(highlightbackground=BORDER_SUBTLE)
        if not self.entry.get().strip():
            self._set_placeholder()

    def get(self) -> str:
        if self.has_placeholder:
            return ""
        return self.entry.get().strip()

    def set_text(self, text: str):
        self.has_placeholder = False
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self.entry.configure(fg=TEXT_WHITE)

    def clear(self):
        if self.placeholder:
            self._set_placeholder()
        else:
            self.entry.delete(0, "end")

class StyledButton(tk.Label):
    """Polished button with clean hover transitions and rounded feel."""
    def __init__(self, parent, text, command, bg_color=ACCENT_CYAN, fg_color="#000000",
                 hover_bg=None, font_size=10, bold=True, pad_x=14, pad_y=8, **kwargs):
        self.command = command
        self.bg_color = bg_color
        self.hover_bg = hover_bg or self._lighten(bg_color)
        self.disabled_bg = "#23304a"
        self.is_disabled = False

        font_weight = "bold" if bold else "normal"
        super().__init__(
            parent,
            text=text,
            font=(FONT_FAMILY, font_size, font_weight),
            bg=self.bg_color,
            fg=fg_color,
            padx=pad_x,
            pady=pad_y,
            cursor="hand2",
            relief="flat",
            **kwargs
        )

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _on_enter(self, e):
        if not self.is_disabled:
            self.configure(bg=self.hover_bg)

    def _on_leave(self, e):
        if not self.is_disabled:
            self.configure(bg=self.bg_color)

    def _on_click(self, e):
        if not self.is_disabled and self.command:
            self.command()

    def set_disabled(self, disabled: bool):
        self.is_disabled = disabled
        if disabled:
            self.configure(bg=self.disabled_bg, fg=TEXT_DIM, cursor="arrow")
        else:
            self.configure(bg=self.bg_color, fg="#000000" if self.bg_color in [ACCENT_CYAN, ACCENT_EMERALD, ACCENT_AMBER] else TEXT_WHITE, cursor="hand2")

    @staticmethod
    def _lighten(hex_color: str) -> str:
        if hex_color == ACCENT_CYAN:
            return "#7dd3fc"
        elif hex_color == ACCENT_EMERALD:
            return "#34d399"
        elif hex_color == ACCENT_ROSE:
            return "#fb7185"
        elif hex_color == ACCENT_AMBER:
            return "#fde047"
        return hex_color

class StatBadge(tk.Label):
    """Subtle pill/badge for status, format, and counts."""
    def __init__(self, parent, text, fg_color=TEXT_MUTED, bg_color="#18223a", **kwargs):
        super().__init__(
            parent,
            text=text,
            font=(FONT_FAMILY, 8, "bold"),
            fg=fg_color,
            bg=bg_color,
            padx=8,
            pady=3,
            **kwargs
        )

class SectionCard(tk.Frame):
    """Card container with subtle border."""
    def __init__(self, parent, **kwargs):
        px = kwargs.pop("padx", 14)
        py = kwargs.pop("pady", 12)
        super().__init__(
            parent,
            bg=BG_CARD,
            highlightbackground=BORDER_SUBTLE,
            highlightthickness=1,
            padx=px,
            pady=py,
            **kwargs
        )

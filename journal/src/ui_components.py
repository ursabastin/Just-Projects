import tkinter as tk
from tkinter import font as tkfont
import math
from typing import Callable, Optional

from config import (
    BG_ROOT, BG_CARD, BG_CARD_HOVER, BG_INPUT, BORDER_SUBTLE, BORDER_FOCUS,
    ACCENT_CYAN, ACCENT_EMERALD, ACCENT_AMBER, ACCENT_ROSE, ACCENT_PURPLE,
    TEXT_WHITE, TEXT_MUTED, TEXT_DIM, FONT_FAMILY
)

class StyledButton(tk.Button):
    """Modern dark-themed button with hover elevation."""

    def __init__(
        self,
        parent,
        text: str,
        command: Optional[Callable] = None,
        bg_color: str = BG_CARD,
        hover_color: str = BG_CARD_HOVER,
        fg_color: str = TEXT_WHITE,
        border_color: str = BORDER_SUBTLE,
        height: int = 1,
        font_size: int = 10,
        bold: bool = True,
        padx: int = 14,
        pady: int = 6,
        **kwargs
    ):
        font_spec = (FONT_FAMILY, font_size, "bold" if bold else "normal")
        super().__init__(
            parent,
            text=text,
            command=command,
            bg=bg_color,
            fg=fg_color,
            activebackground=hover_color,
            activeforeground=fg_color,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=border_color,
            font=font_spec,
            cursor="hand2",
            padx=padx,
            pady=pady,
            **kwargs
        )
        self.default_bg = bg_color
        self.hover_bg = hover_color
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _):
        self.configure(bg=self.hover_bg)

    def _on_leave(self, _):
        self.configure(bg=self.default_bg)


class Badge(tk.Frame):
    """Pill badge for tags, statuses, or wikilink representations."""

    def __init__(
        self,
        parent,
        text: str,
        color: str = ACCENT_CYAN,
        bg_color: str = BG_CARD,
        font_size: int = 8,
        **kwargs
    ):
        super().__init__(
            parent,
            bg=bg_color,
            highlightbackground=color,
            highlightthickness=1,
            padx=6,
            pady=2,
            **kwargs
        )
        self.lbl = tk.Label(
            self,
            text=text,
            fg=color,
            bg=bg_color,
            font=(FONT_FAMILY, font_size, "bold")
        )
        self.lbl.pack()


class SectionCard(tk.Frame):
    """Standardized dark card container with subtle borders."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=BG_CARD,
            highlightbackground=BORDER_SUBTLE,
            highlightthickness=1,
            padx=16,
            pady=12,
            **kwargs
        )


class WaveformVisualizer(tk.Canvas):
    """Dynamic multi-bar audio waveform visualizer responding to microphone RMS levels."""

    def __init__(self, parent, bar_count: int = 28, height: int = 60, **kwargs):
        super().__init__(
            parent,
            height=height,
            bg=BG_INPUT,
            highlightbackground=BORDER_SUBTLE,
            highlightthickness=1,
            **kwargs
        )
        self.bar_count = bar_count
        self.bar_height = height
        self.levels = [0.05] * bar_count
        self.active = False
        self.bind("<Configure>", lambda _: self._draw())

    def update_level(self, rms: float):
        """Pushes current RMS level into the wave array."""
        self.active = True
        # Shift values to create animated sound wave
        self.levels.pop(0)
        # Apply slight random harmonic jitter for realistic aesthetic
        jitter = (hash(str(rms)) % 20 - 10) / 100.0
        val = max(0.04, min(1.0, rms + jitter * 0.2))
        self.levels.append(val)
        self._draw()

    def set_idle(self):
        """Resets waveform to calm idle pulse."""
        self.active = False
        self.levels = [0.05] * self.bar_count
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 10 or h <= 10:
            return

        bar_width = max(2, (w - (self.bar_count * 3)) / self.bar_count)
        center_y = h / 2.0

        for i, lvl in enumerate(self.levels):
            x0 = i * (bar_width + 3) + 4
            x1 = x0 + bar_width

            if self.active:
                # Active colors: Rose/Amber pulse
                color = ACCENT_ROSE if lvl > 0.4 else (ACCENT_AMBER if lvl > 0.15 else ACCENT_CYAN)
            else:
                color = TEXT_DIM

            bar_h = max(4.0, lvl * (h - 8))
            y0 = center_y - (bar_h / 2.0)
            y1 = center_y + (bar_h / 2.0)

            self.create_rectangle(x0, y0, x1, y1, fill=color, outline="")


class ModernProgressBar(tk.Canvas):
    """Smooth determinate progress bar."""

    def __init__(self, parent, height: int = 6, bg_bar: str = "#1c263c", fill_color: str = ACCENT_CYAN, **kwargs):
        super().__init__(parent, height=height, bg=BG_CARD, highlightthickness=0, **kwargs)
        self.bar_height = height
        self.bg_bar = bg_bar
        self.fill_color = fill_color
        self.progress = 0.0
        self.bind("<Configure>", lambda _: self._draw())

    def set_progress(self, val: float):
        self.progress = max(0.0, min(1.0, float(val)))
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.bar_height
        if w <= 1:
            return
        self.create_rectangle(0, 0, w, h, fill=self.bg_bar, outline="")
        pw = int(w * self.progress)
        if pw > 0:
            self.create_rectangle(0, 0, pw, h, fill=self.fill_color, outline="")

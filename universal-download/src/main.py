import os
import sys
import threading
import queue
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from typing import Optional

# Ensure local imports work reliably
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from config import APP_NAME, APP_VERSION, DOWNLOAD_DIR, find_ffmpeg
from ui_components import (
    BG_ROOT, BG_CARD, BG_CARD_HOVER, BG_INPUT, BORDER_SUBTLE, BORDER_FOCUS,
    ACCENT_CYAN, ACCENT_EMERALD, ACCENT_AMBER, ACCENT_ROSE,
    TEXT_WHITE, TEXT_MUTED, TEXT_DIM, FONT_FAMILY,
    ModernProgressBar, StyledEntry, StyledButton, StatBadge, SectionCard
)
from downloader import MediaInspector, DownloaderEngine

class UniversalDownloaderApp(tk.Tk):
    def __init__(self, initial_url: Optional[str] = None):
        super().__init__()
        
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("620x780")
        self.minsize(560, 680)
        self.configure(bg=BG_ROOT)

        # Center on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        cx = max(0, (sw - 620) // 2)
        cy = max(0, (sh - 780) // 2)
        self.geometry(f"+{cx}+{cy}")

        # State
        self.current_media_info: Optional[dict] = None
        self.download_mode = tk.StringVar(value="video") # "video" or "audio"
        self.playlist_mode = tk.StringVar(value="complete") # "partial" or "complete"
        self.is_downloading = False
        
        # Thread queue for UI updates
        self.msg_queue = queue.Queue()

        # Engine
        self.engine = DownloaderEngine(
            on_progress=self._queue_progress,
            on_log=self._queue_log,
            on_complete=self._queue_complete
        )

        # Build UI layout
        self._build_header()
        self._build_url_section()
        self._build_media_card()
        self._build_format_selector()
        self._build_progress_section()
        self._build_actions()
        self._build_log_section()

        # Check periodically for messages from background threads
        self.after(50, self._process_queue)

        # Check initial URL or clipboard
        if initial_url and initial_url.startswith("http"):
            self.entry_url.set_text(initial_url)
            self.after(300, self.start_inspect_link)

    def _build_header(self):
        header_frame = tk.Frame(self, bg=BG_ROOT, pady=12, padx=16)
        header_frame.pack(fill="x")

        # Top row: title & version badge
        title_row = tk.Frame(header_frame, bg=BG_ROOT)
        title_row.pack(fill="x")

        lbl_title = tk.Label(
            title_row,
            text=APP_NAME.upper(),
            font=(FONT_FAMILY, 15, "bold"),
            fg=TEXT_WHITE,
            bg=BG_ROOT
        )
        lbl_title.pack(side="left")

        badge_ver = StatBadge(title_row, f"v{APP_VERSION}", fg_color=ACCENT_CYAN, bg_color="#10233b")
        badge_ver.pack(side="left", padx=(8, 0))

        btn_folder = StyledButton(
            title_row,
            text="📂 Open Videos Folder",
            command=self.open_output_folder,
            bg_color="#1e293b",
            fg_color=TEXT_WHITE,
            hover_bg="#2a3a54",
            font_size=8,
            pad_x=10,
            pad_y=4
        )
        btn_folder.pack(side="right")

        # Destination path indicator
        path_text = f"Saving to: {DOWNLOAD_DIR}"
        if len(path_text) > 65:
            path_text = path_text[:62] + "..."
        lbl_path = tk.Label(
            header_frame,
            text=path_text,
            font=(FONT_FAMILY, 8),
            fg=TEXT_DIM,
            bg=BG_ROOT,
            anchor="w"
        )
        lbl_path.pack(fill="x", pady=(2, 0))

    def _build_url_section(self):
        container = tk.Frame(self, bg=BG_ROOT, padx=16)
        container.pack(fill="x", pady=(0, 10))

        lbl_input = tk.Label(
            container,
            text="ENTER MEDIA LINK",
            font=(FONT_FAMILY, 8, "bold"),
            fg=TEXT_MUTED,
            bg=BG_ROOT
        )
        lbl_input.pack(anchor="w", pady=(0, 4))

        input_row = tk.Frame(container, bg=BG_ROOT)
        input_row.pack(fill="x")

        self.entry_url = StyledEntry(
            input_row,
            placeholder="Paste YouTube, Instagram, Facebook, or any media URL..."
        )
        self.entry_url.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.entry_url.entry.bind("<Return>", lambda e: self.start_inspect_link())

        btn_paste = StyledButton(
            input_row,
            text="📋 Paste",
            command=self.paste_from_clipboard,
            bg_color="#1e293b",
            fg_color=TEXT_WHITE,
            hover_bg="#2a3a54",
            font_size=9,
            pad_x=12,
            pad_y=7
        )
        btn_paste.pack(side="left", padx=(0, 6))

        self.btn_inspect = StyledButton(
            input_row,
            text="🔍 Inspect",
            command=self.start_inspect_link,
            bg_color=ACCENT_CYAN,
            fg_color="#000000",
            font_size=9,
            pad_x=14,
            pad_y=7
        )
        self.btn_inspect.pack(side="left")

    def _build_media_card(self):
        self.card_container = tk.Frame(self, bg=BG_ROOT, padx=16)
        self.card_container.pack(fill="x", pady=(0, 10))

        self.card_frame = SectionCard(self.card_container)
        self.card_frame.pack(fill="x")

        # Initial placeholder state
        self.lbl_card_status = tk.Label(
            self.card_frame,
            text="Ready. Paste a link above to detect video or playlist.",
            font=(FONT_FAMILY, 9),
            fg=TEXT_MUTED,
            bg=BG_CARD
        )
        self.lbl_card_status.pack(pady=10)

        # Dynamic inner widgets (initially hidden)
        self.media_detail_frame = tk.Frame(self.card_frame, bg=BG_CARD)
        
        # Badges row
        self.row_badges = tk.Frame(self.media_detail_frame, bg=BG_CARD)
        self.row_badges.pack(fill="x", pady=(0, 6))

        self.badge_type = StatBadge(self.row_badges, "SINGLE VIDEO", fg_color=ACCENT_EMERALD, bg_color="#0f2922")
        self.badge_type.pack(side="left")

        self.badge_duration = StatBadge(self.row_badges, "⏱ --:--", fg_color=TEXT_MUTED, bg_color="#1e293b")
        self.badge_duration.pack(side="left", padx=(6, 0))

        self.badge_bracket_count = StatBadge(
            self.row_badges, 
            "(Found 0 videos)", 
            fg_color=ACCENT_AMBER, 
            bg_color="#292010"
        )

        # Media Title
        self.lbl_media_title = tk.Label(
            self.media_detail_frame,
            text="",
            font=(FONT_FAMILY, 11, "bold"),
            fg=TEXT_WHITE,
            bg=BG_CARD,
            wraplength=540,
            justify="left",
            anchor="w"
        )
        self.lbl_media_title.pack(fill="x", pady=(0, 2))

        # Media Author/Channel
        self.lbl_media_author = tk.Label(
            self.media_detail_frame,
            text="",
            font=(FONT_FAMILY, 8),
            fg=TEXT_MUTED,
            bg=BG_CARD,
            anchor="w"
        )
        self.lbl_media_author.pack(fill="x", pady=(0, 8))

        # Playlist Options Container
        self.playlist_options_frame = tk.Frame(self.media_detail_frame, bg="#0d1424", padx=10, pady=8, highlightbackground=BORDER_SUBTLE, highlightthickness=1)
        
        lbl_pl_prompt = tk.Label(
            self.playlist_options_frame,
            text="PLAYLIST DETECTED - SELECT DOWNLOAD SCOPE:",
            font=(FONT_FAMILY, 8, "bold"),
            fg=ACCENT_AMBER,
            bg="#0d1424"
        )
        lbl_pl_prompt.pack(anchor="w", pady=(0, 6))

        # Option 1: Partial / First N videos
        opt1_row = tk.Frame(self.playlist_options_frame, bg="#0d1424")
        opt1_row.pack(fill="x", pady=(0, 6))

        self.rb_partial = tk.Radiobutton(
            opt1_row,
            text="Download First N Videos:",
            variable=self.playlist_mode,
            value="partial",
            font=(FONT_FAMILY, 9),
            fg=TEXT_WHITE,
            bg="#0d1424",
            selectcolor=BG_ROOT,
            activebackground="#0d1424",
            activeforeground=TEXT_WHITE,
            cursor="hand2"
        )
        self.rb_partial.pack(side="left")

        self.entry_playlist_limit = StyledEntry(opt1_row, placeholder="e.g. 5")
        self.entry_playlist_limit.pack(side="left", padx=(8, 0))
        self.entry_playlist_limit.set_text("5")
        self.entry_playlist_limit.configure(width=6)

        # Option 2: Complete playlist
        opt2_row = tk.Frame(self.playlist_options_frame, bg="#0d1424")
        opt2_row.pack(fill="x")

        self.rb_complete = tk.Radiobutton(
            opt2_row,
            text="Download Complete Playlist (All Videos)",
            variable=self.playlist_mode,
            value="complete",
            font=(FONT_FAMILY, 9),
            fg=TEXT_WHITE,
            bg="#0d1424",
            selectcolor=BG_ROOT,
            activebackground="#0d1424",
            activeforeground=TEXT_WHITE,
            cursor="hand2"
        )
        self.rb_complete.pack(side="left")

    def _build_format_selector(self):
        container = tk.Frame(self, bg=BG_ROOT, padx=16)
        container.pack(fill="x", pady=(0, 10))

        lbl_format = tk.Label(
            container,
            text="OUTPUT QUALITY PRESET (NO COMPLICATED SPIRALS)",
            font=(FONT_FAMILY, 8, "bold"),
            fg=TEXT_MUTED,
            bg=BG_ROOT
        )
        lbl_format.pack(anchor="w", pady=(0, 6))

        toggle_frame = tk.Frame(container, bg=BG_ROOT)
        toggle_frame.pack(fill="x")

        self.btn_mode_video = StyledButton(
            toggle_frame,
            text="🎬 High Quality Video (MP4)",
            command=lambda: self.set_download_mode("video"),
            bg_color=ACCENT_CYAN,
            fg_color="#000000",
            font_size=9,
            pad_x=16,
            pad_y=8
        )
        self.btn_mode_video.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.btn_mode_audio = StyledButton(
            toggle_frame,
            text="🎵 High Quality Audio (MP3)",
            command=lambda: self.set_download_mode("audio"),
            bg_color="#1e293b",
            fg_color=TEXT_WHITE,
            hover_bg="#2a3a54",
            font_size=9,
            pad_x=16,
            pad_y=8
        )
        self.btn_mode_audio.pack(side="left", expand=True, fill="x")

    def set_download_mode(self, mode: str):
        self.download_mode.set(mode)
        if mode == "video":
            self.btn_mode_video.configure(bg=ACCENT_CYAN, fg="#000000")
            self.btn_mode_audio.configure(bg="#1e293b", fg=TEXT_WHITE)
        else:
            self.btn_mode_audio.configure(bg=ACCENT_EMERALD, fg="#000000")
            self.btn_mode_video.configure(bg="#1e293b", fg=TEXT_WHITE)

    def _build_progress_section(self):
        container = tk.Frame(self, bg=BG_ROOT, padx=16)
        container.pack(fill="x", pady=(0, 10))

        card = SectionCard(container)
        card.pack(fill="x")

        # Top progress row
        status_row = tk.Frame(card, bg=BG_CARD)
        status_row.pack(fill="x", pady=(0, 6))

        self.lbl_status_text = tk.Label(
            status_row,
            text="Idle",
            font=(FONT_FAMILY, 9, "bold"),
            fg=TEXT_WHITE,
            bg=BG_CARD,
            anchor="w"
        )
        self.lbl_status_text.pack(side="left")

        self.lbl_percent = tk.Label(
            status_row,
            text="0%",
            font=(FONT_FAMILY, 9, "bold"),
            fg=ACCENT_CYAN,
            bg=BG_CARD
        )
        self.lbl_percent.pack(side="right")

        # Progress bar
        self.progress_bar = ModernProgressBar(card, height=10)
        self.progress_bar.pack(fill="x", pady=(0, 6))

        # Bottom metrics row
        metrics_row = tk.Frame(card, bg=BG_CARD)
        metrics_row.pack(fill="x")

        self.lbl_speed_eta = tk.Label(
            metrics_row,
            text="Speed: -- | ETA: --",
            font=(FONT_FAMILY, 8),
            fg=TEXT_MUTED,
            bg=BG_CARD
        )
        self.lbl_speed_eta.pack(side="left")

        self.lbl_bytes = tk.Label(
            metrics_row,
            text="0 B / 0 B",
            font=(FONT_FAMILY, 8),
            fg=TEXT_MUTED,
            bg=BG_CARD
        )
        self.lbl_bytes.pack(side="right")

    def _build_actions(self):
        container = tk.Frame(self, bg=BG_ROOT, padx=16)
        container.pack(fill="x", pady=(0, 10))

        btn_row = tk.Frame(container, bg=BG_ROOT)
        btn_row.pack(fill="x")

        self.btn_download = StyledButton(
            btn_row,
            text="⬇ START DOWNLOAD",
            command=self.start_download,
            bg_color=ACCENT_EMERALD,
            fg_color="#000000",
            font_size=10,
            bold=True,
            pad_x=20,
            pad_y=10
        )
        self.btn_download.pack(side="left", expand=True, fill="x", padx=(0, 8))

        self.btn_cancel = StyledButton(
            btn_row,
            text="⏹ Cancel",
            command=self.cancel_download,
            bg_color="#1e293b",
            fg_color=TEXT_WHITE,
            hover_bg=ACCENT_ROSE,
            font_size=10,
            bold=True,
            pad_x=16,
            pad_y=10
        )
        self.btn_cancel.pack(side="left")
        self.btn_cancel.set_disabled(True)

    def _build_log_section(self):
        container = tk.Frame(self, bg=BG_ROOT, padx=16)
        container.pack(fill="both", expand=True, pady=(0, 12))

        lbl_log = tk.Label(
            container,
            text="ACTIVITY & DIAGNOSTICS LOG",
            font=(FONT_FAMILY, 8, "bold"),
            fg=TEXT_MUTED,
            bg=BG_ROOT
        )
        lbl_log.pack(anchor="w", pady=(0, 4))

        log_card = SectionCard(container, padx=8, pady=8)
        log_card.pack(fill="both", expand=True)

        self.text_log = tk.Text(
            log_card,
            bg="#080c14",
            fg=TEXT_MUTED,
            font=("Consolas", 8),
            relief="flat",
            wrap="word",
            insertbackground=ACCENT_CYAN,
            highlightthickness=0
        )
        self.text_log.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(log_card, command=self.text_log.yview, bg=BG_CARD)
        scrollbar.pack(side="right", fill="y")
        self.text_log.configure(yscrollcommand=scrollbar.set)

    # -----------------------------
    # User Actions & Event Handlers
    # -----------------------------

    def paste_from_clipboard(self):
        try:
            clip = self.clipboard_get().strip()
            if clip:
                self.entry_url.set_text(clip)
                self.start_inspect_link()
        except Exception:
            pass

    def open_output_folder(self):
        try:
            os.startfile(DOWNLOAD_DIR)
        except Exception as e:
            self.log_message(f"Could not open directory: {e}")

    def log_message(self, msg: str):
        self.text_log.insert("end", f"{msg}\n")
        self.text_log.see("end")

    def start_inspect_link(self):
        url = self.entry_url.get().strip()
        if not url:
            return

        self.btn_inspect.set_disabled(True)
        self.lbl_card_status.pack(pady=10)
        self.lbl_card_status.configure(text="🔍 Analyzing link & detecting media format...", fg=ACCENT_CYAN)
        self.media_detail_frame.pack_forget()

        threading.Thread(target=self._run_inspect, args=(url,), daemon=True).start()

    def _run_inspect(self, url: str):
        try:
            info = MediaInspector.inspect(url)
            self.msg_queue.put(("inspect_success", info))
        except Exception as e:
            self.msg_queue.put(("inspect_error", str(e)))

    def start_download(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("URL Missing", "Please enter or paste a media link first.")
            return

        is_playlist = self.current_media_info.get("is_playlist", False) if self.current_media_info else False
        mode = self.download_mode.get()
        
        limit = None
        if is_playlist:
            if self.playlist_mode.get() == "partial":
                val_str = self.entry_playlist_limit.get()
                try:
                    limit = int(val_str)
                    if limit <= 0:
                        raise ValueError()
                except ValueError:
                    messagebox.showerror("Invalid Count", "Please enter a valid positive number for playlist videos to download.")
                    return

        self.is_downloading = True
        self.btn_download.set_disabled(True)
        self.btn_inspect.set_disabled(True)
        self.btn_cancel.set_disabled(False)
        self.btn_cancel.configure(bg=ACCENT_ROSE)
        
        self.lbl_status_text.configure(text="Starting download...", fg=ACCENT_CYAN)
        self.progress_bar.set_progress(0.0)

        self.engine.start_download(
            url=url,
            is_playlist=is_playlist,
            mode=mode,
            playlist_limit=limit
        )

    def cancel_download(self):
        if self.is_downloading:
            self.engine.cancel()
            self.lbl_status_text.configure(text="Cancelling...", fg=ACCENT_ROSE)
            self.btn_cancel.set_disabled(True)

    # -----------------------------
    # Thread Safe Message Processing
    # -----------------------------

    def _queue_progress(self, data: dict):
        self.msg_queue.put(("progress", data))

    def _queue_log(self, msg: str):
        self.msg_queue.put(("log", msg))

    def _queue_complete(self, res: dict):
        self.msg_queue.put(("complete", res))

    def _process_queue(self):
        try:
            while not self.msg_queue.empty():
                kind, payload = self.msg_queue.get_nowait()
                if kind == "inspect_success":
                    self._on_inspect_success(payload)
                elif kind == "inspect_error":
                    self._on_inspect_error(payload)
                elif kind == "progress":
                    self._on_progress_update(payload)
                elif kind == "log":
                    self.log_message(payload)
                elif kind == "complete":
                    self._on_download_complete(payload)
        finally:
            self.after(50, self._process_queue)

    def _on_inspect_success(self, info: dict):
        self.current_media_info = info
        self.btn_inspect.set_disabled(False)
        self.lbl_card_status.pack_forget()
        self.media_detail_frame.pack(fill="x")

        # Set title and author
        self.lbl_media_title.configure(text=info.get("title", "Untitled"))
        self.lbl_media_author.configure(text=f"By: {info.get('uploader', 'Unknown')}")

        if info.get("is_playlist"):
            self.badge_type.configure(text="PLAYLIST", fg=ACCENT_AMBER, bg="#2d2210")
            count = info.get("count", 0)
            self.badge_bracket_count.configure(text=f"(Found {count} videos)")
            self.badge_bracket_count.pack(side="left", padx=(6, 0))
            self.badge_duration.pack_forget()
            
            # Show playlist options
            self.playlist_options_frame.pack(fill="x", pady=(6, 0))
            self.entry_playlist_limit.set_text(str(min(count, 5)) if count > 0 else "5")
        else:
            self.badge_type.configure(text="SINGLE MEDIA", fg=ACCENT_EMERALD, bg="#0f2922")
            self.badge_duration.configure(text=f"⏱ {info.get('duration_str', '--:--')}")
            self.badge_duration.pack(side="left", padx=(6, 0))
            self.badge_bracket_count.pack_forget()
            self.playlist_options_frame.pack_forget()

        self.log_message(f"Analyzed: {info.get('title')} [{'Playlist' if info.get('is_playlist') else 'Single'}]")

    def _on_inspect_error(self, err_msg: str):
        self.btn_inspect.set_disabled(False)
        self.lbl_card_status.pack(pady=10)
        self.lbl_card_status.configure(text=f"❌ Analysis failed: {err_msg}", fg=ACCENT_ROSE)
        self.log_message(f"Error inspecting link: {err_msg}")

    def _on_progress_update(self, data: dict):
        status = data.get("status")
        if status == "downloading":
            pct = data.get("percent", 0.0)
            self.progress_bar.set_progress(pct / 100.0)
            self.lbl_percent.configure(text=f"{pct:.1f}%")
            
            idx = data.get("playlist_index")
            cnt = data.get("playlist_count")
            if idx and cnt:
                self.lbl_status_text.configure(text=f"Downloading [{idx}/{cnt}]: {data.get('filename', '')}")
            else:
                self.lbl_status_text.configure(text=f"Downloading: {data.get('filename', '')}")
                
            self.lbl_speed_eta.configure(text=f"Speed: {data.get('speed_str', '--')} | ETA: {data.get('eta_str', '--')}")
            self.lbl_bytes.configure(text=f"{data.get('downloaded_str', '0 B')} / {data.get('total_str', '0 B')}")

        elif status == "processing":
            self.progress_bar.set_progress(1.0)
            self.lbl_percent.configure(text="100%")
            self.lbl_status_text.configure(text=data.get("message", "Processing..."), fg=ACCENT_EMERALD)

    def _on_download_complete(self, res: dict):
        self.is_downloading = False
        self.btn_download.set_disabled(False)
        self.btn_inspect.set_disabled(False)
        self.btn_cancel.set_disabled(True)
        self.btn_cancel.configure(bg="#1e293b")

        if res.get("success"):
            self.progress_bar.set_progress(1.0)
            self.progress_bar.set_fill_color(ACCENT_EMERALD)
            self.lbl_status_text.configure(text="✅ Download Finished! Saved to Videos folder.", fg=ACCENT_EMERALD)
            self.lbl_percent.configure(text="100%", fg=ACCENT_EMERALD)
        elif res.get("cancelled"):
            self.lbl_status_text.configure(text="🛑 Download Cancelled.", fg=ACCENT_AMBER)
        else:
            err = res.get("error") or {}
            self.lbl_status_text.configure(text=f"❌ Download Failed: {err.get('title', 'Error')}", fg=ACCENT_ROSE)

def main():
    # Detect terminal args: download ext, download <url>, etc.
    initial_url = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg.lower() not in ["ext", "gui"]:
            initial_url = arg

    app = UniversalDownloaderApp(initial_url=initial_url)
    app.mainloop()

if __name__ == "__main__":
    main()

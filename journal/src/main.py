import os
import sys
import time
import queue
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Ensure local module imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import tkinter as tk
from tkinter import messagebox, ttk

from config import (
    APP_NAME, APP_VERSION, WINDOW_WIDTH, WINDOW_HEIGHT,
    BG_ROOT, BG_CARD, BG_CARD_HOVER, BG_INPUT, BORDER_SUBTLE, BORDER_FOCUS,
    ACCENT_CYAN, ACCENT_EMERALD, ACCENT_AMBER, ACCENT_ROSE, ACCENT_PURPLE,
    TEXT_WHITE, TEXT_MUTED, TEXT_DIM, FONT_FAMILY,
    load_config, save_config, detect_obsidian_vault
)
from storage import StorageManager
from audio_recorder import AudioRecorder
from hotkey_listener import PushToTalkListener
from speech_engine import SpeechAndSynthesisEngine
from logic_gates import LogicGatesEngine
from obsidian_vault import ObsidianVaultManager
from ui_components import (
    StyledButton, Badge, SectionCard, WaveformVisualizer, ModernProgressBar
)

# Application States
STATE_IDLE = "IDLE"
STATE_RECORDING = "RECORDING"
STATE_PROCESSING = "PROCESSING"
STATE_COMPLETED = "COMPLETED"


class VoiceJournalApp(tk.Tk):
    """
    Fixed-ratio desktop Voice Journal with Alt+Shift push-to-talk,
    multimodal AI synthesis, and Obsidian knowledge vault integration.
    """

    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.maxsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.resizable(False, False)  # Strict fixed rectangular format
        self.configure(bg=BG_ROOT)

        # Center on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        cx = max(0, (sw - WINDOW_WIDTH) // 2)
        cy = max(0, (sh - WINDOW_HEIGHT) // 2)
        self.geometry(f"+{cx}+{cy}")

        # Core State & Services
        self.config_data = load_config()
        self.storage = StorageManager()
        self.recorder = AudioRecorder()
        self.speech_engine = SpeechAndSynthesisEngine()
        self.vault_mgr = ObsidianVaultManager(self.config_data.get("obsidian_vault_path", detect_obsidian_vault()))
        self.logic_engine = LogicGatesEngine(self.config_data.get("obsidian_vault_path", detect_obsidian_vault()))

        self.state = STATE_IDLE
        self.msg_queue = queue.Queue()
        self.current_entry_id: Optional[str] = None
        self.last_saved_note_path: Optional[Path] = None
        self.last_processed_result: Optional[Dict[str, Any]] = None

        # Build GUI
        self._build_header()
        self._build_status_card()
        self._build_content_area()
        self._build_action_bar()

        # Start Hotkey Listener
        self.hotkey_listener = PushToTalkListener(
            on_press=self._on_hotkey_down,
            on_release=self._on_hotkey_up
        )
        self.hotkey_listener.start()

        # Setup message pump
        self.after(25, self._process_queue)

        # Ensure clean exit on window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -------------------------------------------------------------
    # UI Layout Construction
    # -------------------------------------------------------------
    def _build_header(self):
        """Top bar with application branding, vault status, and settings button."""
        header_frame = tk.Frame(self, bg=BG_ROOT, pady=10, padx=20)
        header_frame.pack(fill="x")

        # Left: App title and icon
        title_box = tk.Frame(header_frame, bg=BG_ROOT)
        title_box.pack(side="left")

        lbl_icon = tk.Label(title_box, text="🎙️", font=(FONT_FAMILY, 16), bg=BG_ROOT, fg=ACCENT_CYAN)
        lbl_icon.pack(side="left", padx=(0, 8))

        lbl_title = tk.Label(
            title_box,
            text=APP_NAME,
            font=(FONT_FAMILY, 15, "bold"),
            bg=BG_ROOT,
            fg=TEXT_WHITE
        )
        lbl_title.pack(side="left")

        # Right: Settings & Vault Badge
        right_box = tk.Frame(header_frame, bg=BG_ROOT)
        right_box.pack(side="right")

        vault_name = Path(self.config_data.get("obsidian_vault_path", "Vault")).name
        self.badge_vault = Badge(right_box, text=f"📂 {vault_name}", color=ACCENT_CYAN)
        self.badge_vault.pack(side="left", padx=(0, 10))

        btn_settings = StyledButton(
            right_box,
            text="⚙ Settings",
            command=self._open_settings_dialog,
            font_size=9,
            padx=10,
            pady=3
        )
        btn_settings.pack(side="left")

    def _build_status_card(self):
        """Visualizer, state badge, duration timer, and instructions."""
        self.status_card = SectionCard(self)
        self.status_card.pack(fill="x", padx=20, pady=(0, 12))

        # Top row inside card: Status Indicator & Timer
        top_row = tk.Frame(self.status_card, bg=BG_CARD)
        top_row.pack(fill="x", pady=(0, 8))

        self.badge_state = Badge(top_row, text="● READY", color=ACCENT_EMERALD)
        self.badge_state.pack(side="left")

        self.lbl_timer = tk.Label(
            top_row,
            text="00:00",
            font=(FONT_FAMILY, 13, "bold"),
            bg=BG_CARD,
            fg=TEXT_MUTED
        )
        self.lbl_timer.pack(side="right")

        # Dynamic Audio Waveform
        self.visualizer = WaveformVisualizer(self.status_card, height=52)
        self.visualizer.pack(fill="x", pady=(0, 10))

        # Progress bar (for AI processing)
        self.prog_bar = ModernProgressBar(self.status_card, height=4)
        self.prog_bar.pack(fill="x", pady=(0, 8))

        # Instructions / Context banner
        self.lbl_instruction = tk.Label(
            self.status_card,
            text="Hold [ Alt + Shift ] to speak your thoughts...",
            font=(FONT_FAMILY, 10, "italic"),
            bg=BG_CARD,
            fg=TEXT_MUTED
        )
        self.lbl_instruction.pack()

    def _build_content_area(self):
        """Scrollable notebook/viewer displaying Raw Transcript, AI Synthesis, and Wikilinks."""
        self.content_card = SectionCard(self)
        self.content_card.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        # Header for the active entry
        self.meta_row = tk.Frame(self.content_card, bg=BG_CARD)
        self.meta_row.pack(fill="x", pady=(0, 6))

        self.lbl_entry_title = tk.Label(
            self.meta_row,
            text="No Recording Active",
            font=(FONT_FAMILY, 12, "bold"),
            bg=BG_CARD,
            fg=TEXT_WHITE
        )
        self.lbl_entry_title.pack(side="left")

        self.badge_category = Badge(self.meta_row, text="Thought", color=ACCENT_PURPLE)
        self.badge_category.pack(side="right", padx=(4, 0))

        self.badge_sentiment = Badge(self.meta_row, text="Focused", color=ACCENT_AMBER)
        self.badge_sentiment.pack(side="right")

        # Scrollable output box
        self.text_container = tk.Frame(self.content_card, bg=BG_INPUT, highlightbackground=BORDER_SUBTLE, highlightthickness=1)
        self.text_container.pack(fill="both", expand=True, pady=(4, 8))

        self.output_text = tk.Text(
            self.text_container,
            wrap="word",
            bg=BG_INPUT,
            fg=TEXT_WHITE,
            insertbackground=ACCENT_CYAN,
            font=(FONT_FAMILY, 10),
            relief="flat",
            bd=8,
            selectbackground=BORDER_SUBTLE,
            selectforeground=TEXT_WHITE
        )
        self.output_text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self.text_container, orient="vertical", command=self.output_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.output_text.configure(yscrollcommand=scrollbar.set)

        # Initial placeholder
        self._display_welcome_message()

        # Bottom row inside content card: Wikilinks row
        self.wikilinks_frame = tk.Frame(self.content_card, bg=BG_CARD)
        self.wikilinks_frame.pack(fill="x", pady=(4, 0))

        lbl_wiki_tag = tk.Label(
            self.wikilinks_frame,
            text="🔗 Obsidian Graph Links:",
            font=(FONT_FAMILY, 9, "bold"),
            bg=BG_CARD,
            fg=TEXT_MUTED
        )
        lbl_wiki_tag.pack(side="left", padx=(0, 8))

        self.tags_container = tk.Frame(self.wikilinks_frame, bg=BG_CARD)
        self.tags_container.pack(side="left", fill="x", expand=True)

    def _build_action_bar(self):
        """Bottom toolbar with Push-to-Talk button, Open in Obsidian, and New Entry."""
        action_bar = tk.Frame(self, bg=BG_ROOT)
        action_bar.pack(fill="x", padx=20, pady=(0, 16))

        # Left: Manual push-to-talk button
        self.btn_ptt = StyledButton(
            action_bar,
            text="🎙 Push & Hold to Talk",
            bg_color=BG_CARD,
            hover_color=BG_CARD_HOVER,
            border_color=ACCENT_CYAN,
            font_size=10
        )
        self.btn_ptt.pack(side="left")
        self.btn_ptt.bind("<ButtonPress-1>", lambda _: self._on_hotkey_down())
        self.btn_ptt.bind("<ButtonRelease-1>", lambda _: self._on_hotkey_up())

        # Right: Obsidian link & New Entry
        self.btn_open_obsidian = StyledButton(
            action_bar,
            text="↗ Open Note in Obsidian",
            command=self._open_in_obsidian,
            bg_color=BG_CARD,
            hover_color=BG_CARD_HOVER,
            font_size=9
        )
        self.btn_open_obsidian.pack(side="right", padx=(8, 0))

        self.btn_new = StyledButton(
            action_bar,
            text="✨ New Entry",
            command=self._reset_to_idle,
            bg_color=BG_CARD,
            hover_color=BG_CARD_HOVER,
            font_size=9
        )
        self.btn_new.pack(side="right")

    # -------------------------------------------------------------
    # State Transitions & Recording Flow
    # -------------------------------------------------------------
    def _on_hotkey_down(self):
        """Triggered when Alt+Shift is pressed down."""
        if self.state == STATE_RECORDING or self.state == STATE_PROCESSING:
            return

        self.msg_queue.put(("START_RECORDING", None))

    def _on_hotkey_up(self):
        """Triggered when Alt+Shift is released."""
        if self.state != STATE_RECORDING:
            return

        self.msg_queue.put(("STOP_RECORDING", None))

    def _process_queue(self):
        """Polls messages from background threads."""
        try:
            while not self.msg_queue.empty():
                msg_type, payload = self.msg_queue.get_nowait()

                if msg_type == "START_RECORDING":
                    self._start_recording()

                elif msg_type == "STOP_RECORDING":
                    self._stop_recording_and_process()

                elif msg_type == "RMS_UPDATE":
                    if self.state == STATE_RECORDING:
                        self.visualizer.update_level(payload)
                        dur = self.recorder.get_duration()
                        mins = int(dur) // 60
                        secs = int(dur) % 60
                        self.lbl_timer.config(text=f"{mins:02d}:{secs:02d}")

                elif msg_type == "SYNTHESIS_PROGRESS":
                    progress, text = payload
                    self.prog_bar.set_progress(progress)
                    self.lbl_instruction.config(text=text)

                elif msg_type == "ENTRY_PROCESSED":
                    self._on_entry_complete(payload)

                elif msg_type == "PROCESSING_ERROR":
                    self._on_error(payload)

        except Exception as e:
            print(f"[Main] Error in queue processing: {e}")

        self.after(25, self._process_queue)

    def _start_recording(self):
        """Initiates microphone capture and updates visual state."""
        self.state = STATE_RECORDING
        self.badge_state.lbl.config(text="● RECORDING", fg=ACCENT_ROSE)
        self.badge_state.config(highlightbackground=ACCENT_ROSE)
        self.lbl_instruction.config(
            text="Speaking... (Release [Alt+Shift] when finished)",
            fg=ACCENT_ROSE
        )
        self.btn_ptt.configure(bg=ACCENT_ROSE, activebackground=ACCENT_ROSE)
        self.prog_bar.set_progress(0.0)

        started = self.recorder.start(
            rms_callback=lambda rms: self.msg_queue.put(("RMS_UPDATE", rms))
        )
        if not started:
            self._reset_to_idle()
            messagebox.showerror("Microphone Error", "Could not open audio input stream. Check your default microphone.")

    def _stop_recording_and_process(self):
        """Stops microphone stream and launches background AI & Logic Gates thread."""
        self.state = STATE_PROCESSING
        self.badge_state.lbl.config(text="● SYNTHESIZING", fg=ACCENT_AMBER)
        self.badge_state.config(highlightbackground=ACCENT_AMBER)
        self.btn_ptt.configure(bg=BG_CARD, activebackground=BG_CARD_HOVER)
        self.visualizer.set_idle()
        self.lbl_instruction.config(text="Processing audio with AI & Logic Gates...", fg=ACCENT_AMBER)

        now = datetime.now()
        entry_id = now.strftime("%Y%m%d-%H%M%S")
        self.current_entry_id = entry_id

        # Target audio path inside Obsidian attachments
        audio_filename = f"voice_{now.strftime('%Y-%m-%d_%H%M%S')}.wav"
        attachments_dir = self.vault_mgr.get_attachments_dir(
            self.config_data.get("attachments_folder", "Attachments/VoiceLogs")
        )
        audio_save_path = attachments_dir / audio_filename

        # Stop recorder
        saved_path, duration, raw_bytes = self.recorder.stop(save_path=audio_save_path)

        if duration < 0.3 or not raw_bytes:
            self._reset_to_idle()
            self.lbl_instruction.config(text="Recording too brief (under 0.3s). Try again.", fg=TEXT_MUTED)
            return

        # Relative path for Obsidian wikilink
        rel_audio_path = f"{self.config_data.get('attachments_folder', 'Attachments/VoiceLogs')}/{audio_filename}"

        # Run synthesis in worker thread
        threading.Thread(
            target=self._synthesis_worker,
            args=(saved_path, entry_id, now, duration, rel_audio_path),
            daemon=True
        ).start()

    def _synthesis_worker(self, audio_path: Path, entry_id: str, now: datetime, duration: float, rel_audio_path: str):
        """Worker thread orchestrating SpeechEngine -> LogicGates -> SQLite & Obsidian Vault."""
        try:
            self.msg_queue.put(("SYNTHESIS_PROGRESS", (0.25, "Transcribing speech and extracting intent...")))
            ai_data = self.speech_engine.process_audio(audio_path)

            self.msg_queue.put(("SYNTHESIS_PROGRESS", (0.60, "Running Python Logic Gates & resolving Obsidian graph...")))
            # Refresh vault index before matching
            self.logic_engine.indexer.refresh_index()
            gate_result = self.logic_engine.process_entry(
                ai_data=ai_data,
                entry_id=entry_id,
                timestamp_dt=now,
                audio_rel_path=rel_audio_path
            )

            self.msg_queue.put(("SYNTHESIS_PROGRESS", (0.85, "Writing to Obsidian Vault & Local SQLite Database...")))
            # 1. Save Markdown Note to Vault
            note_path = self.vault_mgr.save_journal_note(
                timestamp_dt=now,
                markdown_content=gate_result["markdown_content"],
                subfolder=self.config_data.get("journal_folder", "Journal/Voice")
            )

            # 2. Interlock with Daily Notes
            if self.config_data.get("auto_link_vault", True):
                self.vault_mgr.update_daily_note(
                    timestamp_dt=now,
                    snippet=gate_result["daily_note_snippet"],
                    daily_folder=self.config_data.get("daily_notes_folder", "Daily Notes")
                )

            # 3. Save to Local SQLite Registry
            self.storage.insert_entry({
                "id": entry_id,
                "timestamp": now.isoformat(),
                "audio_path": str(audio_path),
                "audio_duration": duration,
                "raw_transcript": ai_data.get("raw_transcript", ""),
                "title": gate_result["title"],
                "summary": ai_data.get("summary", ""),
                "key_insights": ai_data.get("key_insights", []),
                "action_items": ai_data.get("action_items", []),
                "entities": gate_result["resolved_entities"],
                "vault_file_path": str(note_path)
            })

            self.msg_queue.put(("SYNTHESIS_PROGRESS", (1.0, "Saved to Obsidian Vault & Local Registry!")))
            self.msg_queue.put(("ENTRY_PROCESSED", {
                "ai_data": ai_data,
                "gate_result": gate_result,
                "note_path": note_path,
                "duration": duration,
                "timestamp": now
            }))

        except Exception as e:
            self.msg_queue.put(("PROCESSING_ERROR", str(e)))

    def _on_entry_complete(self, payload: Dict[str, Any]):
        """Renders the synthesized entry and graph links into the UI."""
        self.state = STATE_COMPLETED
        self.last_saved_note_path = payload["note_path"]
        self.last_processed_result = payload

        ai_data = payload["ai_data"]
        gate_result = payload["gate_result"]
        title = gate_result["title"]
        category = gate_result.get("category", "Thought")
        sentiment = gate_result.get("sentiment", "Focused")

        self.badge_state.lbl.config(text="✔ SAVED", fg=ACCENT_EMERALD)
        self.badge_state.config(highlightbackground=ACCENT_EMERALD)
        self.lbl_instruction.config(
            text=f"✔ Saved note in Obsidian Vault: {Path(self.last_saved_note_path).name}",
            fg=ACCENT_EMERALD
        )

        self.lbl_entry_title.config(text=title)
        self.badge_category.lbl.config(text=category)
        self.badge_sentiment.lbl.config(text=sentiment)

        # Populate output text
        self.output_text.delete("1.0", tk.END)

        formatted_display = f"""=== 🧠 AI SYNTHESIZED SUMMARY ===
{ai_data.get('summary', '')}

=== 💡 KEY INSIGHTS ===
"""
        for item in ai_data.get("key_insights", []):
            formatted_display += f"• {item}\n"

        if ai_data.get("action_items"):
            formatted_display += "\n=== 🎯 ACTION ITEMS ===\n"
            for item in ai_data.get("action_items", []):
                formatted_display += f"☐ {item}\n"

        formatted_display += f"""
=== 📝 RAW TRANSCRIPT ===
"{ai_data.get('raw_transcript', '')}"
"""
        self.output_text.insert(tk.END, formatted_display)

        # Populate Wikilink badges
        for child in self.tags_container.winfo_children():
            child.destroy()

        resolved = gate_result.get("resolved_entities", [])
        if resolved:
            for ent in resolved[:6]:
                badge_text = ent["wikilink"]
                color = ACCENT_EMERALD if ent["match_type"] == "exact" else ACCENT_CYAN
                b = Badge(self.tags_container, text=badge_text, color=color, font_size=8)
                b.pack(side="left", padx=(0, 4))
        else:
            lbl_none = tk.Label(self.tags_container, text="No links", font=(FONT_FAMILY, 8), fg=TEXT_DIM, bg=BG_CARD)
            lbl_none.pack(side="left")

    def _on_error(self, err_msg: str):
        """Displays error details and restores idle state."""
        self.state = STATE_IDLE
        self.badge_state.lbl.config(text="● ERROR", fg=ACCENT_ROSE)
        self.badge_state.config(highlightbackground=ACCENT_ROSE)
        self.lbl_instruction.config(text=f"Error: {err_msg}", fg=ACCENT_ROSE)
        self.prog_bar.set_progress(0.0)

    def _reset_to_idle(self):
        """Resets UI back to ready state."""
        self.state = STATE_IDLE
        self.badge_state.lbl.config(text="● READY", fg=ACCENT_EMERALD)
        self.badge_state.config(highlightbackground=ACCENT_EMERALD)
        self.lbl_timer.config(text="00:00")
        self.prog_bar.set_progress(0.0)
        self.lbl_instruction.config(
            text="Hold [ Alt + Shift ] to speak your thoughts...",
            fg=TEXT_MUTED
        )
        self.visualizer.set_idle()
        self.btn_ptt.configure(bg=BG_CARD, activebackground=BG_CARD_HOVER)

    def _display_welcome_message(self):
        """Renders the default instructions into the text area."""
        self.output_text.delete("1.0", tk.END)
        welcome = f"""Welcome to {APP_NAME}!

HOW TO USE:
1. Hold [ Alt + Shift ] anytime to start recording your voice.
   (You can also click and hold the "Push & Hold to Talk" button).
2. Speak your thoughts, ideas, tasks, or reflections naturally.
3. Release the keys when you are done speaking.

WHAT HAPPENS NEXT:
• Your voice is transcribed and synthesized into an insightful summary.
• The Python Logic Gates Engine analyzes your Obsidian vault:
    - Matches topics with existing notes as [[Wikilinks]]
    - Organizes insights and actionable checklists
    - Interlocks with your Daily Notes
• Audio logs and Markdown notes are saved to your PC and Obsidian vault.
"""
        self.output_text.insert(tk.END, welcome)

    # -------------------------------------------------------------
    # Obsidian & Settings Actions
    # -------------------------------------------------------------
    def _open_in_obsidian(self):
        """Opens the active journal note in Obsidian or the OS file manager."""
        if not self.last_saved_note_path or not self.last_saved_note_path.exists():
            messagebox.showinfo("No Note Selected", "Record an entry first to open it in Obsidian.")
            return

        try:
            # Try Obsidian URI first
            uri = self.vault_mgr.get_obsidian_uri(self.last_saved_note_path)
            os.startfile(uri)
        except Exception:
            # Fallback: open markdown file directly
            os.startfile(str(self.last_saved_note_path))

    def _open_settings_dialog(self):
        """Opens modal configuration dialog for Vault path and AI API keys."""
        win = tk.Toplevel(self)
        win.title("Voice Journal Settings")
        win.geometry("520x420")
        win.resizable(False, False)
        win.configure(bg=BG_ROOT)
        win.transient(self)
        win.grab_set()

        # Center dialog
        win.update_idletasks()
        cx = self.winfo_x() + (WINDOW_WIDTH - 520) // 2
        cy = self.winfo_y() + (WINDOW_HEIGHT - 420) // 2
        win.geometry(f"+{cx}+{cy}")

        content = SectionCard(win)
        content.pack(fill="both", expand=True, padx=16, pady=16)

        lbl_hdr = tk.Label(content, text="⚙ System Configuration", font=(FONT_FAMILY, 12, "bold"), fg=TEXT_WHITE, bg=BG_CARD)
        lbl_hdr.pack(anchor="w", pady=(0, 14))

        # Vault Path
        lbl_v = tk.Label(content, text="Obsidian Vault Directory:", font=(FONT_FAMILY, 9, "bold"), fg=TEXT_MUTED, bg=BG_CARD)
        lbl_v.pack(anchor="w")
        ent_vault = tk.Entry(content, bg=BG_INPUT, fg=TEXT_WHITE, insertbackground=ACCENT_CYAN, font=(FONT_FAMILY, 10), bd=1, relief="solid")
        ent_vault.insert(0, self.config_data.get("obsidian_vault_path", r"C:\Tethis-System"))
        ent_vault.pack(fill="x", pady=(4, 12))

        # Gemini API Key
        lbl_g = tk.Label(content, text="Google Gemini API Key (Recommended for Fast Audio AI):", font=(FONT_FAMILY, 9, "bold"), fg=TEXT_MUTED, bg=BG_CARD)
        lbl_g.pack(anchor="w")
        ent_gemini = tk.Entry(content, show="*", bg=BG_INPUT, fg=TEXT_WHITE, insertbackground=ACCENT_CYAN, font=(FONT_FAMILY, 10), bd=1, relief="solid")
        ent_gemini.insert(0, self.config_data.get("gemini_api_key", ""))
        ent_gemini.pack(fill="x", pady=(4, 12))

        # OpenAI API Key
        lbl_o = tk.Label(content, text="OpenAI API Key (Optional Alternative):", font=(FONT_FAMILY, 9, "bold"), fg=TEXT_MUTED, bg=BG_CARD)
        lbl_o.pack(anchor="w")
        ent_openai = tk.Entry(content, show="*", bg=BG_INPUT, fg=TEXT_WHITE, insertbackground=ACCENT_CYAN, font=(FONT_FAMILY, 10), bd=1, relief="solid")
        ent_openai.insert(0, self.config_data.get("openai_api_key", ""))
        ent_openai.pack(fill="x", pady=(4, 16))

        # Save Button
        def do_save():
            new_vault = ent_vault.get().strip()
            new_gemini = ent_gemini.get().strip()
            new_openai = ent_openai.get().strip()

            self.config_data["obsidian_vault_path"] = new_vault
            self.config_data["gemini_api_key"] = new_gemini
            self.config_data["openai_api_key"] = new_openai
            save_config(self.config_data)

            # Re-init vault manager and logic engine
            self.vault_mgr = ObsidianVaultManager(new_vault)
            self.logic_engine = LogicGatesEngine(new_vault)
            self.speech_engine.refresh_config()

            v_name = Path(new_vault).name if new_vault else "Vault"
            self.badge_vault.lbl.config(text=f"📂 {v_name}")
            win.destroy()
            messagebox.showinfo("Settings Saved", "Configuration updated successfully!")

        btn_save = StyledButton(
            content,
            text="Save Settings",
            command=do_save,
            bg_color=ACCENT_CYAN,
            fg_color=BG_ROOT,
            hover_color=TEXT_WHITE
        )
        btn_save.pack(anchor="e", pady=(8, 0))

    def _on_close(self):
        """Shuts down hotkey listener and audio streams on exit."""
        try:
            self.hotkey_listener.stop()
            self.recorder.stop()
        except Exception:
            pass
        self.destroy()


def main():
    app = VoiceJournalApp()
    app.mainloop()


if __name__ == "__main__":
    main()

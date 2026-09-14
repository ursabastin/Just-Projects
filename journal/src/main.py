import os
import sys
import time
import queue
import threading
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
from local_stt import LocalSTTProvider
from local_llm import LocalLLMProvider
from logic_gates import LogicGatesEngine
from obsidian_vault import ObsidianVaultManager
from ui_components import (
    StyledButton, Badge, SectionCard, WaveformVisualizer, ModernProgressBar
)

STATE_IDLE = "IDLE"
STATE_RECORDING = "RECORDING"
STATE_PROCESSING = "PROCESSING"
STATE_COMPLETED = "COMPLETED"


class VoiceJournalApp(tk.Tk):
    """
    Local-First Academic Voice & Text Journal.
    Captures daily college experiences, learning, assignments, and problems.
    Organizes automatically into C:\\Tethis-System\\Academy\\Journal\\Journal-YYYY-MM-DD.md.
    """

    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.maxsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.resizable(False, False)  # Locked rectangular format
        self.configure(bg=BG_ROOT)

        # Center on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        cx = max(0, (sw - WINDOW_WIDTH) // 2)
        cy = max(0, (sh - WINDOW_HEIGHT) // 2)
        self.geometry(f"+{cx}+{cy}")

        # Core Services
        self.config_data = load_config()
        self.vault_path = self.config_data.get("obsidian_vault_path", detect_obsidian_vault())
        self.storage = StorageManager()
        self.recorder = AudioRecorder()
        self.stt_provider = LocalSTTProvider()
        self.llm_provider = LocalLLMProvider()
        self.vault_mgr = ObsidianVaultManager(self.vault_path)
        self.logic_engine = LogicGatesEngine(self.vault_path)

        # State
        self.state = STATE_IDLE
        self.msg_queue = queue.Queue()
        self.last_saved_note_path: Optional[Path] = None

        # Build UI
        self._build_header()
        self._build_status_card()
        self._build_input_card()
        self._build_results_viewer()
        self._build_bottom_bar()

        # Start Hotkey Listener for Alt+Shift
        self.hotkey_listener = PushToTalkListener(
            on_press=self._on_hotkey_down,
            on_release=self._on_hotkey_up
        )
        self.hotkey_listener.start()

        # Message Pump
        self.after(25, self._process_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -------------------------------------------------------------
    # UI Layout Construction
    # -------------------------------------------------------------
    def _build_header(self):
        """Top bar displaying branding, vault badge, model indicator, and settings."""
        header_frame = tk.Frame(self, bg=BG_ROOT)
        header_frame.pack(fill="x", padx=20, pady=(12, 8))

        # Left: Title
        left_box = tk.Frame(header_frame, bg=BG_ROOT)
        left_box.pack(side="left")

        lbl_icon = tk.Label(left_box, text="🎓", font=(FONT_FAMILY, 15), bg=BG_ROOT, fg=ACCENT_CYAN)
        lbl_icon.pack(side="left", padx=(0, 8))

        lbl_title = tk.Label(
            left_box,
            text=APP_NAME,
            font=(FONT_FAMILY, 14, "bold"),
            bg=BG_ROOT,
            fg=TEXT_WHITE
        )
        lbl_title.pack(side="left")

        # Right: Badges and Settings
        right_box = tk.Frame(header_frame, bg=BG_ROOT)
        right_box.pack(side="right")

        model_name = self.config_data.get("local_llm_model", "qwen2.5")
        self.badge_model = Badge(right_box, text=f"⚡ {model_name}", color=ACCENT_PURPLE)
        self.badge_model.pack(side="left", padx=(0, 8))

        vault_name = Path(self.vault_path).name if self.vault_path else "Vault"
        self.badge_vault = Badge(right_box, text=f"📂 {vault_name}", color=ACCENT_CYAN)
        self.badge_vault.pack(side="left", padx=(0, 8))

        btn_settings = StyledButton(
            right_box,
            text="⚙",
            command=self._open_settings_dialog,
            font_size=10,
            padx=8,
            pady=2
        )
        btn_settings.pack(side="left")

    def _build_status_card(self):
        """Recording visualizer, duration timer, and status badge."""
        self.status_card = SectionCard(self)
        self.status_card.pack(fill="x", padx=20, pady=(0, 10))

        top_row = tk.Frame(self.status_card, bg=BG_CARD)
        top_row.pack(fill="x", pady=(0, 6))

        self.badge_state = Badge(top_row, text="● READY", color=ACCENT_EMERALD)
        self.badge_state.pack(side="left")

        self.lbl_timer = tk.Label(
            top_row,
            text="00:00",
            font=(FONT_FAMILY, 11, "bold"),
            bg=BG_CARD,
            fg=TEXT_MUTED
        )
        self.lbl_timer.pack(side="right")

        # Dynamic Audio Waveform
        self.visualizer = WaveformVisualizer(self.status_card, height=42)
        self.visualizer.pack(fill="x", pady=(0, 6))

        # Progress bar
        self.prog_bar = ModernProgressBar(self.status_card, height=3)
        self.prog_bar.pack(fill="x", pady=(0, 6))

        # Instruction ticker
        self.lbl_status = tk.Label(
            self.status_card,
            text="Hold [ Alt + Shift ] to speak, or type notes below.",
            font=(FONT_FAMILY, 9, "italic"),
            bg=BG_CARD,
            fg=TEXT_MUTED
        )
        self.lbl_status.pack()

    def _build_input_card(self):
        """Direct text input area with Submit button (Ctrl+Enter support)."""
        input_card = SectionCard(self)
        input_card.pack(fill="x", padx=20, pady=(0, 10))

        lbl_row = tk.Frame(input_card, bg=BG_CARD)
        lbl_row.pack(fill="x", pady=(0, 4))

        lbl_in = tk.Label(
            lbl_row,
            text="✏ Quick Capture (Speak or Type):",
            font=(FONT_FAMILY, 9, "bold"),
            bg=BG_CARD,
            fg=TEXT_WHITE
        )
        lbl_in.pack(side="left")

        lbl_hint = tk.Label(
            lbl_row,
            text="Press Ctrl+Enter to save",
            font=(FONT_FAMILY, 8),
            bg=BG_CARD,
            fg=TEXT_DIM
        )
        lbl_hint.pack(side="right")

        # Text input box
        self.entry_text = tk.Text(
            input_card,
            height=3,
            wrap="word",
            bg=BG_INPUT,
            fg=TEXT_WHITE,
            insertbackground=ACCENT_CYAN,
            font=(FONT_FAMILY, 9),
            relief="flat",
            bd=6,
            highlightbackground=BORDER_SUBTLE,
            highlightthickness=1
        )
        self.entry_text.pack(fill="x", pady=(0, 6))
        self.entry_text.bind("<Control-Return>", lambda _: self._on_text_submit())

        # Submit button row
        btn_row = tk.Frame(input_card, bg=BG_CARD)
        btn_row.pack(fill="x")

        self.btn_ptt = StyledButton(
            btn_row,
            text="🎙 Hold to Talk",
            bg_color=BG_CARD_HOVER,
            hover_color=BORDER_SUBTLE,
            font_size=9,
            padx=12,
            pady=4
        )
        self.btn_ptt.pack(side="left")
        self.btn_ptt.bind("<ButtonPress-1>", lambda _: self._on_hotkey_down())
        self.btn_ptt.bind("<ButtonRelease-1>", lambda _: self._on_hotkey_up())

        self.btn_submit = StyledButton(
            btn_row,
            text="Process & Save Entry",
            command=self._on_text_submit,
            bg_color=ACCENT_CYAN,
            fg_color=BG_ROOT,
            hover_color=TEXT_WHITE,
            font_size=9,
            padx=14,
            pady=4
        )
        self.btn_submit.pack(side="right")

    def _build_results_viewer(self):
        """Scrollable results area displaying Daily Journal preview and Wikilinks."""
        results_card = SectionCard(self)
        results_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        top_row = tk.Frame(results_card, bg=BG_CARD)
        top_row.pack(fill="x", pady=(0, 4))

        self.lbl_journal_target = tk.Label(
            top_row,
            text=f"Journal Target: Academy/Journal/Journal-{datetime.now().strftime('%Y-%m-%d')}.md",
            font=(FONT_FAMILY, 9, "bold"),
            bg=BG_CARD,
            fg=ACCENT_CYAN
        )
        self.lbl_journal_target.pack(side="left")

        # Text display
        text_frame = tk.Frame(results_card, bg=BG_INPUT, highlightbackground=BORDER_SUBTLE, highlightthickness=1)
        text_frame.pack(fill="both", expand=True, pady=(2, 6))

        self.display_text = tk.Text(
            text_frame,
            wrap="word",
            bg=BG_INPUT,
            fg=TEXT_WHITE,
            insertbackground=ACCENT_CYAN,
            font=(FONT_FAMILY, 9),
            relief="flat",
            bd=6,
            selectbackground=BORDER_SUBTLE,
            selectforeground=TEXT_WHITE
        )
        self.display_text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.display_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.display_text.configure(yscrollcommand=scrollbar.set)

        self._show_welcome_text()

        # Wikilinks container
        wiki_row = tk.Frame(results_card, bg=BG_CARD)
        wiki_row.pack(fill="x")

        lbl_w = tk.Label(wiki_row, text="🔗 Links:", font=(FONT_FAMILY, 8, "bold"), bg=BG_CARD, fg=TEXT_MUTED)
        lbl_w.pack(side="left", padx=(0, 6))

        self.links_container = tk.Frame(wiki_row, bg=BG_CARD)
        self.links_container.pack(side="left", fill="x", expand=True)

    def _build_bottom_bar(self):
        """Bottom toolbar with Open in Obsidian and New Entry."""
        bottom_bar = tk.Frame(self, bg=BG_ROOT)
        bottom_bar.pack(fill="x", padx=20, pady=(0, 14))

        lbl_vault_note = tk.Label(
            bottom_bar,
            text="Stored in C:\\Tethis-System",
            font=(FONT_FAMILY, 8),
            bg=BG_ROOT,
            fg=TEXT_DIM
        )
        lbl_vault_note.pack(side="left")

        self.btn_open = StyledButton(
            bottom_bar,
            text="↗ Open Today's Journal in Obsidian",
            command=self._open_in_obsidian,
            bg_color=BG_CARD,
            hover_color=BG_CARD_HOVER,
            font_size=9,
            padx=12,
            pady=4
        )
        self.btn_open.pack(side="right")

    # -------------------------------------------------------------
    # Capture & Processing Flow
    # -------------------------------------------------------------
    def _on_hotkey_down(self):
        if self.state in (STATE_RECORDING, STATE_PROCESSING):
            return
        self.msg_queue.put(("START_RECORDING", None))

    def _on_hotkey_up(self):
        if self.state != STATE_RECORDING:
            return
        self.msg_queue.put(("STOP_RECORDING", None))

    def _on_text_submit(self):
        if self.state == STATE_PROCESSING:
            return
        text = self.entry_text.get("1.0", tk.END).strip()
        if not text:
            return
        self.entry_text.delete("1.0", tk.END)
        self._start_processing(raw_text=text, audio_path=None, duration=0.0)

    def _process_queue(self):
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

                elif msg_type == "PROGRESS":
                    pct, text = payload
                    self.prog_bar.set_progress(pct)
                    self.lbl_status.config(text=text)

                elif msg_type == "ENTRY_COMPLETE":
                    self._render_completed_entry(payload)

                elif msg_type == "ERROR":
                    self._render_error(payload)

        except Exception as e:
            print(f"[Main] Queue pump error: {e}")

        self.after(25, self._process_queue)

    def _start_recording(self):
        self.state = STATE_RECORDING
        self.badge_state.lbl.config(text="● RECORDING", fg=ACCENT_ROSE)
        self.badge_state.config(highlightbackground=ACCENT_ROSE)
        self.lbl_status.config(text="Listening... Release [Alt+Shift] when finished.", fg=ACCENT_ROSE)
        self.btn_ptt.configure(bg=ACCENT_ROSE, activebackground=ACCENT_ROSE)
        self.prog_bar.set_progress(0.0)

        started = self.recorder.start(
            rms_callback=lambda rms: self.msg_queue.put(("RMS_UPDATE", rms))
        )
        if not started:
            self._reset_idle()
            messagebox.showerror("Mic Error", "Could not start audio recording stream.")

    def _stop_recording_and_process(self):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H%M%S")
        audio_filename = f"voice_{date_str}_{time_str}.wav"
        save_dir = self.vault_mgr.get_voice_attachments_dir()
        save_path = save_dir / audio_filename

        saved_path, duration, raw_bytes = self.recorder.stop(save_path=save_path)
        self.visualizer.set_idle()

        if duration < 0.3 or not raw_bytes:
            self._reset_idle()
            self.lbl_status.config(text="Recording too brief (< 0.3s). Try again.", fg=TEXT_MUTED)
            return

        # Hand off to worker
        self._start_processing(raw_text=None, audio_path=saved_path, duration=duration)

    def _start_processing(self, raw_text: Optional[str], audio_path: Optional[Path], duration: float):
        self.state = STATE_PROCESSING
        self.badge_state.lbl.config(text="● PROCESSING", fg=ACCENT_AMBER)
        self.badge_state.config(highlightbackground=ACCENT_AMBER)
        self.btn_ptt.configure(bg=BG_CARD_HOVER, activebackground=BORDER_SUBTLE)
        self.lbl_status.config(text="AI understanding & Python organization...", fg=ACCENT_AMBER)
        self.prog_bar.set_progress(0.15)

        now = datetime.now()
        threading.Thread(
            target=self._worker_pipeline,
            args=(raw_text, audio_path, duration, now),
            daemon=True
        ).start()

    def _worker_pipeline(self, raw_text: Optional[str], audio_path: Optional[Path], duration: float, now: datetime):
        try:
            # 1. Speech-to-text if audio
            if not raw_text and audio_path:
                self.msg_queue.put(("PROGRESS", (0.30, "Transcribing voice recording locally...")))
                raw_text = self.stt_provider.transcribe(audio_path)
                if not raw_text:
                    raw_text = f"[Spoken entry recorded at {now.strftime('%H:%M:%S')}]"

            # 2. Local AI Understanding
            self.msg_queue.put(("PROGRESS", (0.55, "Local LLM understanding academic concepts...")))
            ai_data = self.llm_provider.analyze_academic_input(raw_text)

            # 3. Inspect Vault & Read Today's Journal
            self.msg_queue.put(("PROGRESS", (0.75, "Python Logic Gates resolving entities against vault...")))
            existing_content = self.vault_mgr.read_existing_daily_journal(now)

            # 4. Run Logic Gates
            gate_result = self.logic_engine.process_academic_entry(
                raw_text=raw_text,
                ai_data=ai_data,
                timestamp_dt=now,
                existing_journal_content=existing_content
            )

            # 5. Save to Canonical Journal-YYYY-MM-DD.md
            self.msg_queue.put(("PROGRESS", (0.90, "Saving to Academy/Journal/Journal-YYYY-MM-DD.md...")))
            journal_path = self.vault_mgr.save_daily_journal(now, gate_result["journal_markdown"])

            # 6. Save Internal SQLite audit
            entry_id = now.strftime("%Y%m%d-%H%M%S")
            self.storage.insert_entry({
                "id": entry_id,
                "date": gate_result["date_str"],
                "timestamp": now.isoformat(),
                "entry_type": "voice" if audio_path else "text",
                "audio_path": str(audio_path) if audio_path else None,
                "audio_duration": duration,
                "raw_transcript": raw_text,
                "summary": gate_result["summary"],
                "ai_data": ai_data,
                "vault_file_path": str(journal_path),
                "status": "processed"
            })

            self.msg_queue.put(("PROGRESS", (1.0, f"Saved to {journal_path.name}!")))
            self.msg_queue.put(("ENTRY_COMPLETE", {
                "journal_path": journal_path,
                "raw_text": raw_text,
                "gate_result": gate_result,
                "now": now
            }))

        except Exception as e:
            self.msg_queue.put(("ERROR", str(e)))

    def _render_completed_entry(self, payload: Dict[str, Any]):
        self.state = STATE_COMPLETED
        self.last_saved_note_path = payload["journal_path"]
        raw_text = payload["raw_text"]
        res = payload["gate_result"]
        now = payload["now"]

        self.badge_state.lbl.config(text="✔ SAVED", fg=ACCENT_EMERALD)
        self.badge_state.config(highlightbackground=ACCENT_EMERALD)
        self.lbl_status.config(text=f"✔ Updated {self.last_saved_note_path.name}", fg=ACCENT_EMERALD)

        # Update text view
        self.display_text.delete("1.0", tk.END)

        rendered = f"""=== 📝 ORIGINAL ENTRY (Preserved) ===
> [{now.strftime('%H:%M')}] {raw_text}

=== 🧠 SUMMARY ===
{res.get('summary', '')}
"""
        if res.get("what_i_learned"):
            rendered += "\n=== 💡 WHAT I LEARNED ===\n"
            for item in res["what_i_learned"]:
                rendered += f"• {item}\n"

        if res.get("problems"):
            rendered += "\n=== ❓ PROBLEMS / GAPS ===\n"
            for item in res["problems"]:
                rendered += f"• {item}\n"

        if res.get("actions"):
            rendered += "\n=== 🎯 NEXT ACTIONS ===\n"
            for item in res["actions"]:
                rendered += f"☐ {item}\n"

        rendered += f"\n=== 📂 OBSIDIAN FILE ===\n{self.last_saved_note_path}\n"
        self.display_text.insert(tk.END, rendered)

        # Update link badges
        for child in self.links_container.winfo_children():
            child.destroy()

        links = res.get("connections", [])
        if links:
            for lk in links[:6]:
                b = Badge(self.links_container, text=lk, color=ACCENT_CYAN, font_size=8)
                b.pack(side="left", padx=(0, 4))
        else:
            lbl_none = tk.Label(self.links_container, text="None", font=(FONT_FAMILY, 8), fg=TEXT_DIM, bg=BG_CARD)
            lbl_none.pack(side="left")

    def _render_error(self, err: str):
        self.state = STATE_IDLE
        self.badge_state.lbl.config(text="● ERROR", fg=ACCENT_ROSE)
        self.badge_state.config(highlightbackground=ACCENT_ROSE)
        self.lbl_status.config(text=f"Error: {err}", fg=ACCENT_ROSE)
        self.prog_bar.set_progress(0.0)

    def _reset_idle(self):
        self.state = STATE_IDLE
        self.badge_state.lbl.config(text="● READY", fg=ACCENT_EMERALD)
        self.badge_state.config(highlightbackground=ACCENT_EMERALD)
        self.lbl_timer.config(text="00:00")
        self.prog_bar.set_progress(0.0)
        self.lbl_status.config(text="Hold [ Alt + Shift ] to speak, or type notes below.", fg=TEXT_MUTED)
        self.visualizer.set_idle()
        self.btn_ptt.configure(bg=BG_CARD_HOVER, activebackground=BORDER_SUBTLE)

    def _show_welcome_text(self):
        self.display_text.delete("1.0", tk.END)
        welcome = f"""Academic Journal — Daily Capture

WORKFLOW:
1. Speak: Hold [ Alt + Shift ] (or click & hold "Hold to Talk").
2. Type: Enter thoughts into the quick capture box and press Ctrl+Enter.

HOW IT ORGANIZES:
• Consolidates all events into ONE daily note:
  Academy/Journal/Journal-{datetime.now().strftime('%Y-%m-%d')}.md
• Preserves your exact wording under "## Original Entry".
• Uses Local AI & Python Logic Gates to identify:
  - What you learned
  - Unresolved problems & learning gaps
  - Assignments & Next Actions
  - Links to existing subjects & Science Faculty teacher notes.
"""
        self.display_text.insert(tk.END, welcome)

    # -------------------------------------------------------------
    # Obsidian & Settings Actions
    # -------------------------------------------------------------
    def _open_in_obsidian(self):
        target = self.last_saved_note_path or self.vault_mgr.get_daily_journal_path(datetime.now())
        if not target.exists():
            messagebox.showinfo("No File", f"No journal file created yet for today ({target.name}).")
            return
        try:
            uri = self.vault_mgr.get_obsidian_uri(target)
            os.startfile(uri)
        except Exception:
            os.startfile(str(target))

    def _open_settings_dialog(self):
        win = tk.Toplevel(self)
        win.title("Academic Journal Settings")
        win.geometry("520x460")
        win.resizable(False, False)
        win.configure(bg=BG_ROOT)
        win.transient(self)
        win.grab_set()

        content = SectionCard(win)
        content.pack(fill="both", expand=True, padx=16, pady=16)

        lbl_hdr = tk.Label(content, text="⚙ Local AI & Vault Configuration", font=(FONT_FAMILY, 12, "bold"), fg=TEXT_WHITE, bg=BG_CARD)
        lbl_hdr.pack(anchor="w", pady=(0, 12))

        # Vault Path
        lbl_v = tk.Label(content, text="Obsidian Vault Directory:", font=(FONT_FAMILY, 9, "bold"), fg=TEXT_MUTED, bg=BG_CARD)
        lbl_v.pack(anchor="w")
        ent_vault = tk.Entry(content, bg=BG_INPUT, fg=TEXT_WHITE, insertbackground=ACCENT_CYAN, font=(FONT_FAMILY, 9), bd=1, relief="solid")
        ent_vault.insert(0, self.config_data.get("obsidian_vault_path", r"C:\Tethis-System"))
        ent_vault.pack(fill="x", pady=(2, 10))

        # Local LLM Server URL
        lbl_u = tk.Label(content, text="Local LLM URL (Ollama, llama-server, LM Studio):", font=(FONT_FAMILY, 9, "bold"), fg=TEXT_MUTED, bg=BG_CARD)
        lbl_u.pack(anchor="w")
        ent_url = tk.Entry(content, bg=BG_INPUT, fg=TEXT_WHITE, insertbackground=ACCENT_CYAN, font=(FONT_FAMILY, 9), bd=1, relief="solid")
        ent_url.insert(0, self.config_data.get("local_llm_url", "http://localhost:11434/v1"))
        ent_url.pack(fill="x", pady=(2, 10))

        # Local Model Name
        lbl_m = tk.Label(content, text="Local Model (e.g. qwen2.5:7b-instruct):", font=(FONT_FAMILY, 9, "bold"), fg=TEXT_MUTED, bg=BG_CARD)
        lbl_m.pack(anchor="w")
        ent_model = tk.Entry(content, bg=BG_INPUT, fg=TEXT_WHITE, insertbackground=ACCENT_CYAN, font=(FONT_FAMILY, 9), bd=1, relief="solid")
        ent_model.insert(0, self.config_data.get("local_llm_model", "qwen2.5:7b-instruct"))
        ent_model.pack(fill="x", pady=(2, 10))

        # Optional Gemini Fallback
        lbl_g = tk.Label(content, text="Optional Cloud Fallback (Gemini API Key):", font=(FONT_FAMILY, 9, "bold"), fg=TEXT_MUTED, bg=BG_CARD)
        lbl_g.pack(anchor="w")
        ent_gem = tk.Entry(content, show="*", bg=BG_INPUT, fg=TEXT_WHITE, insertbackground=ACCENT_CYAN, font=(FONT_FAMILY, 9), bd=1, relief="solid")
        ent_gem.insert(0, self.config_data.get("gemini_api_key", ""))
        ent_gem.pack(fill="x", pady=(2, 14))

        def do_save():
            self.config_data["obsidian_vault_path"] = ent_vault.get().strip()
            self.config_data["local_llm_url"] = ent_url.get().strip()
            self.config_data["local_llm_model"] = ent_model.get().strip()
            self.config_data["gemini_api_key"] = ent_gem.get().strip()
            save_config(self.config_data)

            self.vault_path = self.config_data["obsidian_vault_path"]
            self.vault_mgr = ObsidianVaultManager(self.vault_path)
            self.logic_engine = LogicGatesEngine(self.vault_path)
            self.llm_provider.refresh_config()

            v_name = Path(self.vault_path).name if self.vault_path else "Vault"
            self.badge_vault.lbl.config(text=f"📂 {v_name}")
            self.badge_model.lbl.config(text=f"⚡ {self.config_data['local_llm_model']}")
            win.destroy()
            messagebox.showinfo("Saved", "Settings updated.")

        btn_save = StyledButton(content, text="Save Settings", command=do_save, bg_color=ACCENT_CYAN, fg_color=BG_ROOT)
        btn_save.pack(anchor="e")

    def _on_close(self):
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

# Voice Journal (`journal`)

A modern desktop-integrated Python voice-journaling system with a locked fixed-ratio GUI, global `Alt + Shift` push-to-talk microphone capture, multimodal AI cognitive synthesis, deterministic **Python "Logic Gates" Linking Engine**, and deep bi-directional integration with your Obsidian Knowledge Vault (`C:\Tethis-System`).

---

## Key Features

- **Global Terminal Command**: Launch instantly from any PowerShell, Command Prompt, or Windows Terminal simply by typing:
  ```cmd
  journal
  ```
- **Fixed-Ratio Rectangular GUI**: Strict aspect ratio locked window (`640x760`, `resizable(False, False)`) with a luxury dark theme matching `c:\Just-Projects\universal-download` and `no-fap`.
- **`Alt + Shift` Push-to-Talk Capture**:
  - Hold `Alt + Shift` (or click & hold on-screen): mic activates with live animated waveform visualizer.
  - Release `Alt + Shift`: microphone stops and automatically triggers AI synthesis.
- **Multimodal AI Cognitive Synthesis**:
  - Powered by **Google Gemini 2.5 Flash** (with fallback to OpenAI Whisper or local heuristics).
  - Extracts title, verbatim transcript, multi-sentence executive summary, key insights, and actionable checkboxes (`- [ ]`).
- **Python "Logic Gates" Rule & Graph Engine**:
  - **Gate 1 (Vault Indexer)**: Scans your Obsidian vault (`C:\Tethis-System`) for existing notes, aliases, and tags.
  - **Gate 2 (Entity Resolution)**: Resolves spoken concepts via exact match, alias match, fuzzy Levenshtein match, or new concept nodes.
  - **Gate 3 (Wikilink Formatter)**: Embeds bidirectional `[[Wikilinks]]` into the summary without double-linking.
  - **Gate 4 (Routing & Frontmatter)**: Writes an atomic note under `Journal/Voice/YYYY-MM-DD_HHMMSS.md` with full YAML metadata and audio player embed.
  - **Gate 5 (Daily Note Interlock)**: Appends a timestamped reflection line to `Daily Notes/YYYY-MM-DD.md`.
- **Dual Local Persistence**:
  - Saved in **SQLite Registry** (`data/journal_registry.db`).
  - Saved in **Obsidian Vault** (`C:\Tethis-System`) alongside recorded WAV logs (`Attachments/VoiceLogs/`).

---

## Directory Structure

```
c:\Just-Projects\journal\
├── bin\
│   ├── journal.bat           # Launcher (registered in WindowsApps)
│   ├── journal.cmd
│   └── journal.ps1
├── src\
│   ├── main.py               # Fixed-ratio GUI application & state machine
│   ├── ui_components.py      # Waveform visualizer, styled cards, buttons & badges
│   ├── audio_recorder.py     # sounddevice audio stream with real-time RMS meter
│   ├── hotkey_listener.py    # Windows GetAsyncKeyState Alt+Shift push-to-talk detector
│   ├── speech_engine.py      # Gemini multimodal & Whisper synthesis engine
│   ├── logic_gates.py        # The 5 Python Logic Gates for Obsidian graph linking
│   ├── obsidian_vault.py     # Obsidian markdown writer & daily note linker
│   ├── storage.py            # Local SQLite database registry
│   └── config.py             # App configurations, palette, and vault paths
├── data\
│   └── journal_registry.db   # Local SQLite database
├── test_journal.py           # Unit and integration test suite
├── requirements.txt
└── README.md
```

---

## Setup & Configuration

1. **Install Requirements**:
   ```cmd
   pip install -r requirements.txt
   ```
2. **Launch Application**:
   ```cmd
   journal
   ```
3. **Configure API Key (Optional but Recommended)**:
   - Click **⚙ Settings** in the top-right header of the app.
   - Enter your **Google Gemini API Key** (Free tier supported).
   - Verify your **Obsidian Vault Directory** (defaults to `C:\Tethis-System`).

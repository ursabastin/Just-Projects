# Academic Journal (`journal`)

A fast, local-first Python desktop application designed for daily college life capture (lectures, practicals, labs, assignments, concepts, problems, ideas, and faculty interactions) integrating directly with the Obsidian knowledge vault (`C:\Tethis-System`).

---

## 🎯 The Core Purpose & Workflow

$$\text{OPEN APPLICATION} \longrightarrow \text{SPEAK OR TYPE} \longrightarrow \text{LOCAL AI UNDERSTANDS} \longrightarrow \text{PYTHON ORGANIZES} \longrightarrow \text{SAVE TO OBSIDIAN} \longrightarrow \text{CLOSE}$$

- **Zero Manual Organization**: The student never has to manually decide folders, file names, YAML properties, or Wikilinks. Deterministic Python rules decide.
- **Local-First AI Brain**: Powered by a runtime-agnostic `LocalLLMProvider` (llama.cpp/llama-server, Ollama, LM Studio) supporting Qwen-family models without cloud dependencies.
- **Local Speech-to-Text**: Fast, private microphone audio transcription.
- **Strict Canonical Single-File Daily Journal**: Exactly **ONE** Markdown journal file per calendar day at:
  ```
  C:\Tethis-System\Academy\Journal\Journal-YYYY-MM-DD.md
  ```
  Multiple events throughout the day are cleanly merged into the same file without overwriting earlier notes.
- **Strict Original Preservation**: Raw spoken or typed input is preserved verbatim under `## Original Entry`.
- **Knowledge Base Entity Reuse**: Automatically searches `C:\Tethis-System` to link existing faculty/teacher notes and subjects before creating any new notes.

---

## ⚡ Global Launch

Launch anytime from any PowerShell, Command Prompt, or Windows Terminal:
```cmd
journal
```

---

## 🏛️ Architecture

```
                 STUDENT
                   │
                   ▼
            PYTHON GUI (640x760 Fixed Ratio)
                   │
          ┌────────┴────────┐
          │                 │
       TYPED TEXT        MICROPHONE (Alt+Shift)
          │                 │
          │                 ▼
          │           LOCAL STT ENGINE
          │                 │
          └────────┬────────┘
                   │
                   ▼
            RAW INPUT BUFFER (Strictly Preserved)
                   │
                   ▼
       LocalLLMProvider (Qwen / Local Server)
                   │
                   ▼
        STRUCTURED ACADEMIC JSON
                   │
                   ▼
         PYTHON LOGIC GATES ENGINE
          • Gate 1: Vault Graph Indexer (C:\Tethis-System)
          • Gate 2: Entity & Faculty Resolution
          • Gate 3: Wikilink Formatting ([[C++]], [[Loops]])
          • Gate 4: Single Daily Note Aggregator
          • Gate 5: Resilient Offline Fallback
                   │
                   ▼
            OBSIDIAN VAULT
       C:\Tethis-System\Academy\Journal\Journal-YYYY-MM-DD.md
```

---

## 📋 Canonical Daily Journal Format

```markdown
---
type: journal
date: 2026-09-14
domain: academy
status: active
---

# Journal — 2026-09-14

## Original Entry
> [10:15] Today was my first C++ practical. Sir explained variables and data types but I still don't understand type casting.
> [14:30] In the afternoon lab, I practiced 5 basic C++ programs on loops.

## Summary
The user attended their first C++ practical and covered variables and data types.
- **14:30**: Completed lab practice on loops.

## What I Learned
- Variables and data types in C++.
- Syntax of for loop and while loop.

## Connections
- [[C++ Programming]]
- [[Variables]]
- [[Data Types]]
- [[Loops]]
- [[Science Faculty]]

## Problems
- Does not yet understand type casting between float and int.

## Next Actions
- [ ] Review type casting chapter.
- [ ] Submit lab report by Friday.
```

*(Only relevant sections are created. Empty placeholder sections are never generated.)*

---

## 📁 Directory Structure

```
c:\Just-Projects\journal\
├── bin\
│   ├── journal.bat           # Global launcher (registered in WindowsApps)
│   ├── journal.cmd
│   └── journal.ps1
├── src\
│   ├── main.py               # Fixed-ratio GUI with dual Speak & Type capture
│   ├── ui_components.py      # Dark-mode UI components (waveform visualizer, cards, badges)
│   ├── audio_recorder.py     # sounddevice audio stream with real-time RMS meter
│   ├── hotkey_listener.py    # Windows GetAsyncKeyState Alt+Shift push-to-talk detector
│   ├── local_stt.py          # Local Speech-to-Text provider
│   ├── local_llm.py          # LocalLLMProvider abstraction (OpenAI-compatible / Qwen)
│   ├── logic_gates.py        # The 5 Python Logic Gates for Obsidian graph & daily notes
│   ├── obsidian_vault.py     # Obsidian vault manager for Academy/Journal
│   ├── storage.py            # Local SQLite database for audit and recovery
│   └── config.py             # App configurations, palette, and vault paths
├── data\
│   └── journal_registry.db   # Local SQLite database
├── test_journal.py           # Comprehensive unit & integration test suite
├── requirements.txt
└── README.md
```

---

## ⚙ Configuration

Settings can be customized directly in the GUI by clicking **⚙** in the top right:
- **Obsidian Vault Directory**: `C:\Tethis-System` (Default)
- **Local LLM URL**: `http://localhost:11434/v1` (Default for Ollama), `http://localhost:8080/v1` (llama-server), or `http://localhost:1234/v1` (LM Studio).
- **Local Model**: `qwen2.5:7b-instruct` (or any installed local model).
- **Cloud Fallback**: Optional Gemini API key if ever needed when offline.

---

## 🧪 Testing

Run all unit and integration tests:
```cmd
python test_journal.py
```

# No-Fap Discipline Ledger (`no-fap`)

An immutable, cryptographically sealed habit and sobriety tracking system for Windows. Built with Python and Tkinter, it eliminates rationalization, retroactive editing, and habit evasion through an append-only SHA-256 hash-chain, Windows DPAPI encryption, and an unyielding morning accountability daemon.

---

## Key Principles & Philosophy

- **Zero Retroactive Edits**: You cannot backfill past missed days or rewrite history. Once a day is recorded, it is mathematically sealed forever.
- **Evaluation of Complete Days Only**: You can only evaluate **yesterday**. Today is always ongoing and cannot be closed or evaluated until the next morning.
- **No Cheat Codes or Reset Buttons**: The ledger data is encrypted with Windows DPAPI and chained with SHA-256 block hashes. Any manual file modification triggers tamper detection and invalidates the ledger.
- **Unyielding Accountability**: An unclosable morning guardian daemon pops up immediately after screen unlock from 8:00 AM onwards until yesterday's status is recorded.
- **Zero Third-Party Dependencies**: Pure Python standard library (`tkinter`, `ctypes`, `hashlib`, `calendar`, `json`). No `pip install` required.

---

## Core Features

### 1. Modern Dark-Themed Discipline Calendar (`src/main.py`)
- **Visual Month View**: Fast, responsive grid showing every day of the month with high-contrast status coding:
  - 🟢 **Clean (Sealed)**: Completed day without slips.
  - 🔴 **Slip (Sealed)**: Slipped day, permanently logged.
  - ⚡ **Yesterday (Active Record Pending)**: Amber-highlighted; the only clickable date for logging.
  - 🔷 **Today (In Progress)**: Cyan-bordered, actively running day.
  - ⬛ **Future & Past Closed**: Future dates cannot be logged; past missed dates remain unlogged and closed.
- **Live Streak & Metric Tracking**:
  - **Current Streak**: Consecutive clean days leading up to yesterday.
  - **Best Streak**: All-time longest streak recorded in the ledger.
  - **Total Clean**: Total historical clean days.
  - **Monthly Completion Bar**: Visual progress indicator and clean percentage for the currently viewed month.
- **Month Navigation**: Easily jump backward/forward across months or jump straight back to today.

### 2. Cryptographic Immutable Ledger (`src/storage.py`)
- **SHA-256 Block Chaining**:
  - Each entry is stored as a block containing `index`, `date`, `status`, ISO-8601 UTC `timestamp`, `prev_hash`, and computed `hash`.
  - Every block is cryptographically linked to the previous block starting from the Genesis hash (`0000000000000000000000000000000000000000000000000000000000000000`).
- **Windows DPAPI Encryption**:
  - Raw JSON ledger contents are encrypted using Windows Cryptographic API (`CryptProtectData`).
  - Decryption (`CryptUnprotectData`) is strictly bound to the authenticated Windows user account.
- **OS-Level Tamper Resistance**:
  - The ledger file (`data/tracker_ledger.dat`) is marked read-only at the OS level (`stat.S_IREAD`) to prevent external text editor modifications.
  - The storage engine actively verifies the full hash chain on load. Corrupted or altered files raise a `TamperDetectedError`.

### 3. Morning Accountability Guardian (`src/guardian_daemon.py`)
- **Active from 08:00 AM**: Respects rest schedule prior to 8:00 AM.
- **Screen Unlock Trigger**: Uses Windows `OpenInputDesktop` API to detect when the workstation is unlocked or the laptop lid is opened.
- **Persistent Pop-Up (`accountability_guard.py`)**:
  - Forces topmost window state (`-topmost`).
  - Anti-minimize listener automatically restores the window if minimized.
  - If closed via `X` or `Alt+F4`, the daemon relaunches it in **3 seconds** until yesterday is logged.
  - Once submitted, sleeps quietly and uses under 20 MB RAM.

### 4. Emergency Urge Redirection Protocol (`src/urge_protocol.py`)
- **Cognitive Reframing**: Provides stoic reminders emphasizing that urge spikes naturally crest and subside within 10–15 minutes.
- **Box Breathing Orb (4-4-4-4)**: Visual animated breathing guide (Inhale 4s -> Hold 4s -> Exhale 4s -> Hold 4s) to activate parasympathetic nervous system regulation.
- **Physical Desk Challenges**: Actionable physical pattern interrupts (e.g. step away from desk for 60 seconds, splash cold water, drink a glass of water, keep hands visible).

---

## Quick Start & Usage

### 1. Launch the Calendar UI
Launch from Command Prompt or PowerShell:
```cmd
no-fap
```
*(Or use `nofap`)*

Alternatively, run directly with Python:
```cmd
pythonw c:\Just-Projects\no-fap\src\main.py
```

### 2. Start the Background Morning Guardian
To start the persistent background daemon that watches for screen unlocks after 8:00 AM:
```cmd
c:\Just-Projects\no-fap\bin\start-guardian.bat
```
*(You can place a shortcut to this `.bat` inside `shell:startup` to have it start automatically on Windows boot).*

### 3. Record Yesterday's Status
1. Open the calendar or wait for the Morning Guardian prompt.
2. Click **"⚠️ RECORD YESTERDAY"** or click on yesterday's cell in the calendar grid.
3. Choose:
   - 🛡️ **I HAVEN'T DONE ANYTHING (CLEAN)**
   - 💥 **I DID IT (SLIP)**
4. Confirm your selection. The entry is immediately hashed, encrypted, and sealed.

---

## Project Structure

```
c:\Just-Projects\no-fap\
├── bin\
│   ├── no-fap.bat                 # Primary CLI launcher
│   ├── no-fap.cmd                 # CMD wrapper
│   ├── no-fap.ps1                 # PowerShell launcher
│   ├── nofap.bat                  # Alternate CLI alias
│   ├── nofap.cmd                  # Alternate CMD alias
│   ├── nofap.ps1                  # Alternate PowerShell alias
│   ├── start-guardian.bat         # Starts background morning guardian
│   └── start-reminder-service.bat # Starts guardian with startup confirmation
├── data\
│   └── tracker_ledger.dat         # DPAPI-encrypted, SHA-256 hash-chained ledger
├── src\
│   ├── accountability_guard.py    # Topmost, anti-evasion modal for morning check-in
│   ├── daemon.py                  # Proxy launcher for guardian daemon
│   ├── evening_popup.py           # Evening / manual check-in modal
│   ├── guardian_daemon.py         # Unlock detector and continuous background monitor
│   ├── main.py                    # Main calendar GUI and streak metrics dashboard
│   ├── record_popup.py            # Yesterday evaluation confirmation popup
│   ├── storage.py                 # DPAPI encryption and cryptographic hash-chain engine
│   ├── ui_components.py           # Custom dark Tkinter components and habit widgets
│   └── urge_protocol.py           # Emergency urge killer (box breathing & desk challenges)
└── README.md                      # Project documentation
```

---

## Technical Specifications

| Feature | Specification |
| :--- | :--- |
| **Operating System** | Windows 10 / 11 (requires Windows DPAPI & user32 APIs) |
| **Language Runtime** | Python 3.10+ (tested on Python 3.14) |
| **UI Framework** | Tkinter (Custom canvas animations & themed dark palette) |
| **Cryptographic Hash** | SHA-256 with Genesis Block linkage |
| **Data Encryption** | Windows DPAPI (`CryptProtectData` via `ctypes.windll.crypt32`) |
| **Memory Footprint** | ~15-20 MB in background |
| **External Dependencies**| None (100% Python standard library) |

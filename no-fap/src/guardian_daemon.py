import os
import sys
import time
import subprocess
import ctypes
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from storage import Storage

PYTHON_EXE = sys.executable
if PYTHON_EXE.endswith("python.exe"):
    cand = os.path.join(os.path.dirname(PYTHON_EXE), "pythonw.exe")
    if os.path.exists(cand):
        PYTHON_EXE = cand

GUARD_SCRIPT = os.path.join(current_dir, "accountability_guard.py")
DESKTOP_SWITCHDESKTOP = 0x0100

def is_screen_locked() -> bool:
    """Returns True if the workstation is locked or sleeping; False if interactive/unlocked."""
    try:
        hDesktop = ctypes.windll.user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
        if not hDesktop:
            return True
        ctypes.windll.user32.CloseDesktop(hDesktop)
        return False
    except Exception:
        return False

def is_morning_active(force: bool = False) -> bool:
    """
    Returns True if current time is >= 8:00 AM (08:00:00).
    Before 8:00 AM (00:00 to 07:59:59), returns False so the user is not disturbed.
    """
    if force:
        return True
    now = datetime.now()
    return now.hour >= 8

def run_guardian():
    """
    Unyielding Morning Accountability Guardian:
    - Initiates ONLY from 8:00 AM in the morning onwards.
    - Whenever laptop is opened or screen is unlocked:
      If yesterday is unrecorded, pops up directly after screen unlock.
    - NO time limit / NO 10-minute timeout: remains active all day until registered.
    - If user closes window with 'X', Alt+F4, or avoids it:
      Re-appears in 3 seconds until registered!
    - Once registered: sleeps peacefully until next day 8:00 AM.
    - Low memory: < 20 MB RAM.
    """
    force_mode = ("--force" in sys.argv) or ("--test" in sys.argv)

    while True:
        try:
            # 1. Hour check: Only from 8:00 AM onwards (unless forced for testing)
            if not is_morning_active(force_mode):
                # Before 8:00 AM: User is resting; check every 30 seconds
                time.sleep(30)
                continue

            # 2. Ledger check: Is yesterday already sealed?
            storage = Storage()
            if storage.is_yesterday_recorded():
                # Already registered! Sleep quietly, re-check every 60s
                time.sleep(60)
                continue

            # 3. Workstation lock check: Don't pop up on a locked lock-screen
            if is_screen_locked():
                # Screen is locked or laptop lid is closed: wait for unlock
                time.sleep(1)
                continue

            # 4. Pop up directly after unlock!
            proc = subprocess.run([PYTHON_EXE, GUARD_SCRIPT], capture_output=False)

            # 5. Anti-avoidance re-check: Did the user register?
            storage = Storage()
            if not storage.is_yesterday_recorded():
                # User dismissed with 'X', Alt+F4, or tried to avoid:
                # Re-appear in 3 seconds until registration is complete!
                time.sleep(3)
                continue
            else:
                # Registration is complete and sealed! Rest peacefully
                time.sleep(60)
                continue

        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    run_guardian()

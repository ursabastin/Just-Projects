import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
guardian_script = os.path.join(current_dir, "guardian_daemon.py")
os.execv(sys.executable, [sys.executable, guardian_script] + sys.argv[1:])

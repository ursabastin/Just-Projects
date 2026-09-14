import time
import threading
import ctypes
from typing import Callable, Optional

# Windows Virtual Key Codes
VK_SHIFT = 0x10
VK_MENU = 0x12  # Alt key

class PushToTalkListener:
    """
    Monitors Alt+Shift key combination globally using low-overhead Windows GetAsyncKeyState.
    Triggers on_press when Alt+Shift is held down, and on_release when released.
    """

    def __init__(self, on_press: Callable[[], None], on_release: Callable[[], None]):
        self.on_press_callback = on_press
        self.on_release_callback = on_release
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._is_held = False
        self._enabled = True

    def _is_alt_pressed(self) -> bool:
        return bool(ctypes.windll.user32.GetAsyncKeyState(VK_MENU) & 0x8000)

    def _is_shift_pressed(self) -> bool:
        return bool(ctypes.windll.user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)

    def _poll_loop(self):
        """Background loop to detect press and release of Alt+Shift."""
        while self._running:
            if not self._enabled:
                time.sleep(0.05)
                continue

            alt = self._is_alt_pressed()
            shift = self._is_shift_pressed()
            both_pressed = alt and shift

            if both_pressed and not self._is_held:
                # Key combo pressed down
                self._is_held = True
                try:
                    self.on_press_callback()
                except Exception as e:
                    print(f"[PushToTalk] Error in on_press: {e}")

            elif not both_pressed and self._is_held:
                # One or both keys released
                self._is_held = False
                try:
                    self.on_release_callback()
                except Exception as e:
                    print(f"[PushToTalk] Error in on_release: {e}")

            time.sleep(0.015)  # 15ms resolution

    def start(self):
        """Starts monitoring hotkeys in a daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="PushToTalkHotkeyThread")
        self._thread.start()

    def stop(self):
        """Stops monitoring."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)

    def set_enabled(self, enabled: bool):
        """Pause or resume hotkey detection."""
        self._enabled = enabled
        if not enabled and self._is_held:
            self._is_held = False

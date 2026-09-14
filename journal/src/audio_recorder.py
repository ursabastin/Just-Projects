import io
import math
import wave
import time
import queue
import threading
from pathlib import Path
from typing import Optional, Callable
import numpy as np
import sounddevice as sd

from config import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS

class AudioRecorder:
    """Non-blocking audio recorder capturing microphone stream with real-time RMS energy."""

    def __init__(self, sample_rate: int = AUDIO_SAMPLE_RATE, channels: int = AUDIO_CHANNELS):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self._stream: Optional[sd.InputStream] = None
        self._frames = []
        self._lock = threading.Lock()
        self.start_time: float = 0.0
        self.rms_level: float = 0.0
        self.rms_callback: Optional[Callable[[float], None]] = None

    def start(self, rms_callback: Optional[Callable[[float], None]] = None) -> bool:
        """Starts recording audio stream."""
        with self._lock:
            if self.is_recording:
                return True
            
            self._frames = []
            self.rms_callback = rms_callback
            self.start_time = time.time()
            self.rms_level = 0.0

            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype='int16',
                    callback=self._audio_callback
                )
                self._stream.start()
                self.is_recording = True
                return True
            except Exception as e:
                print(f"[AudioRecorder] Failed to start audio input stream: {e}")
                self.is_recording = False
                self._stream = None
                return False

    def _audio_callback(self, indata, frames, time_info, status):
        """Internal callback invoked by sounddevice for each chunk of audio."""
        if not self.is_recording:
            return
        
        # Save raw bytes
        raw_bytes = indata.tobytes()
        self._frames.append(raw_bytes)

        # Compute RMS for live visualization
        try:
            # indata is int16 array
            data_sq = indata.astype(np.float32) ** 2
            mean_sq = np.mean(data_sq)
            rms = math.sqrt(mean_sq) if mean_sq > 0 else 0.0
            
            # Normalize approx 0 to 1 with logarithmic curve for responsive visualization
            # 32767 is max int16
            norm_rms = min(1.0, max(0.0, (math.log10(rms + 1.0) / 4.5)))
            self.rms_level = norm_rms
            
            if self.rms_callback:
                self.rms_callback(norm_rms)
        except Exception:
            pass

    def stop(self, save_path: Optional[Path] = None) -> tuple[Optional[Path], float, bytes]:
        """
        Stops recording and saves to the designated WAV file.
        Returns: (saved_path, duration_seconds, raw_audio_bytes)
        """
        with self._lock:
            if not self.is_recording:
                return None, 0.0, b""

            self.is_recording = False
            duration = time.time() - self.start_time

            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    print(f"[AudioRecorder] Error closing audio stream: {e}")
                self._stream = None

            full_audio_bytes = b"".join(self._frames)
            self._frames = []

            if not full_audio_bytes or duration < 0.2:
                return None, duration, b""

            # If save_path specified, write WAV
            if save_path:
                save_path = Path(save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with wave.open(str(save_path), "wb") as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(2) # 16-bit
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(full_audio_bytes)

            return save_path, duration, full_audio_bytes

    def get_duration(self) -> float:
        """Returns elapsed recording time in seconds."""
        if self.is_recording:
            return time.time() - self.start_time
        return 0.0

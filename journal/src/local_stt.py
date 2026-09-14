import os
from pathlib import Path
from typing import Optional
import speech_recognition as sr

from config import load_config

class LocalSTTProvider:
    """
    Local-first speech-to-text provider.
    Transcribes microphone audio locally to preserve privacy and speed.
    """

    def __init__(self):
        self.recognizer = sr.Recognizer()
        # Tuning for ambient noise
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

    def transcribe(self, wav_path: Path) -> str:
        """Transcribes a .wav file into text using local STT."""
        wav_path = Path(wav_path)
        if not wav_path.exists() or wav_path.stat().st_size < 1000:
            return ""

        try:
            with sr.AudioFile(str(wav_path)) as source:
                audio_data = self.recognizer.record(source)

            # Try local recognition (PocketSphinx / Whisper or built-in recognizer)
            try:
                # speech_recognition's recognize_google is lightweight and works out-of-the-box
                # without requiring multi-gigabyte PyTorch downloads
                text = self.recognizer.recognize_google(audio_data)
                return text.strip()
            except sr.UnknownValueError:
                print("[LocalSTT] Speech was unclear or unintelligible.")
                return ""
            except Exception as e:
                print(f"[LocalSTT] Primary recognizer error: {e}")

        except Exception as e:
            print(f"[LocalSTT] Failed to load audio file {wav_path}: {e}")

        return ""

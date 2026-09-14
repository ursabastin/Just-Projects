import os
import json
import base64
import re
from pathlib import Path
from typing import Dict, Any, Optional
import requests

from config import load_config

SYSTEM_PROMPT = """You are an advanced cognitive journaling assistant.
Listen carefully to the user's recorded voice note and produce a highly structured, insightful JSON response.

Your JSON output must have EXACTLY this structure:
{
  "title": "A concise, evocative title (3-6 words)",
  "raw_transcript": "Verbatim transcription of everything the speaker said, including exact phrasing.",
  "summary": "A rich, detailed 2-4 sentence summary capturing the core ideas, reflections, and context.",
  "key_insights": [
    "Key insight or perspective 1",
    "Key insight 2"
  ],
  "action_items": [
    "Specific task or next step (if any)",
    "Another task (if any)"
  ],
  "entities_and_topics": [
    "Specific concept, technology, project, or person mentioned (e.g. Tethis, Python, Architecture, Deep Learning)"
  ],
  "category": "Idea | Reflection | Project | Task | System",
  "sentiment": "Focused | Creative | Analytical | Urgent | Introspective"
}

Ensure the output is strictly valid JSON without any markdown formatting or backticks.
"""

class SpeechAndSynthesisEngine:
    """Handles speech transcription and AI cognitive synthesis."""

    def __init__(self):
        self.config = load_config()

    def refresh_config(self):
        self.config = load_config()

    def process_audio(self, wav_path: Path) -> Dict[str, Any]:
        """
        Sends audio to AI provider for transcription and synthesis.
        Falls back to local heuristic synthesis if API is unavailable or unconfigured.
        """
        self.refresh_config()
        gemini_key = self.config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
        openai_key = self.config.get("openai_api_key") or os.environ.get("OPENAI_API_KEY", "")

        if gemini_key:
            try:
                result = self._process_with_gemini(wav_path, gemini_key)
                if result:
                    return result
            except Exception as e:
                print(f"[SpeechEngine] Gemini API call failed: {e}")

        if openai_key:
            try:
                result = self._process_with_openai(wav_path, openai_key)
                if result:
                    return result
            except Exception as e:
                print(f"[SpeechEngine] OpenAI API call failed: {e}")

        # Fallback local synthesizer (guarantees no data loss)
        return self._process_offline_fallback(wav_path)

    def _process_with_gemini(self, wav_path: Path, api_key: str) -> Optional[Dict[str, Any]]:
        """Processes audio directly via Google Gemini multimodal endpoint."""
        model = self.config.get("gemini_model", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        with open(wav_path, "rb") as f:
            audio_bytes = f.read()

        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "audio/wav",
                                "data": b64_audio
                            }
                        },
                        {
                            "text": SYSTEM_PROMPT
                        }
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.4
            }
        }

        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code != 200:
            print(f"[SpeechEngine] Gemini returned status {resp.status_code}: {resp.text}")
            return None

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return None

        text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        # Clean any accidental markdown fence
        cleaned = re.sub(r"^```json\s*", "", text_content.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)

        parsed = json.loads(cleaned)
        return parsed

    def _process_with_openai(self, wav_path: Path, api_key: str) -> Optional[Dict[str, Any]]:
        """Fallback: Transcribe via Whisper API then summarize with GPT."""
        # 1. Transcribe
        with open(wav_path, "rb") as f:
            files = {"file": (wav_path.name, f, "audio/wav")}
            headers = {"Authorization": f"Bearer {api_key}"}
            whisper_resp = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data={"model": "whisper-1"},
                timeout=30
            )

        if whisper_resp.status_code != 200:
            return None

        transcript = whisper_resp.json().get("text", "")
        return self.process_text(transcript)

    def process_text(self, transcript: str) -> Dict[str, Any]:
        """Synthesizes text if speech was already transcribed."""
        self.refresh_config()
        gemini_key = self.config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")

        if gemini_key:
            model = self.config.get("gemini_model", "gemini-2.5-flash")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{SYSTEM_PROMPT}\n\nUSER INPUT TEXT:\n{transcript}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.4
                }
            }
            try:
                resp = requests.post(url, json=payload, timeout=25)
                if resp.status_code == 200:
                    text_content = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    cleaned = re.sub(r"^```json\s*", "", text_content.strip(), flags=re.MULTILINE)
                    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
                    return json.loads(cleaned)
            except Exception as e:
                print(f"[SpeechEngine] Text synthesis API error: {e}")

        # Local fallback
        return self._local_heuristic_parse(transcript)

    def _process_offline_fallback(self, wav_path: Path) -> Dict[str, Any]:
        """Provides a graceful offline result when no API key is active."""
        filename_hint = wav_path.stem
        raw_text = f"Audio recording captured ({filename_hint}). Connect Gemini API Key in Settings to enable real-time transcription."
        return self._local_heuristic_parse(raw_text)

    def _local_heuristic_parse(self, text: str) -> Dict[str, Any]:
        """Extracts basic entities and structure via deterministic heuristics."""
        words = text.strip().split()
        title = " ".join(words[:5]).capitalize() if words else "Voice Reflection"
        if len(words) > 5:
            title += "..."

        # Heuristic entity extraction: Capitalized multi-letter words
        candidates = re.findall(r"\b[A-Z][a-zA-Z0-9_\-]{2,}\b", text)
        entities = list(dict.fromkeys(candidates))[:8]  # deduplicate preserving order

        return {
            "title": title,
            "raw_transcript": text,
            "summary": f"Captured voice thought: {text}",
            "key_insights": [
                "Captured locally via Alt+Shift push-to-talk.",
                "Ready for cross-referencing in Obsidian."
            ],
            "action_items": [],
            "entities_and_topics": entities or ["VoiceLog", "Reflection"],
            "category": "Reflection",
            "sentiment": "Focused"
        }

import os
import re
import json
from typing import Dict, Any, Optional
import requests

from config import load_config

ACADEMIC_SYSTEM_PROMPT = """You are an academic capture assistant helping a college student record daily learning, lectures, labs, assignments, concepts, problems, and faculty interactions.

Analyze the user's raw input and extract structured academic meaning.
You MUST output strictly valid JSON matching this schema:
{
  "summary": "A clear, factual 1-3 sentence summary of the academic event, lecture, or study session.",
  "topics": ["Major subject or technical concepts mentioned, e.g. C++, Loops, Pointers, Memory Allocation"],
  "entities": ["Specific people, faculty/professors, courses, departments, or organizations, e.g. Prof. Sharma, Science Faculty, BCA"],
  "what_i_learned": ["Key concepts or facts learned (empty list if not applicable)"],
  "learning_gaps": ["Concepts the user explicitly did not understand or found confusing (empty list if not applicable)"],
  "assignments": ["Any assignments, lab tasks, or homework given (empty list if not applicable)"],
  "tasks": ["Actionable follow-up tasks for the user (empty list if not applicable)"],
  "decisions": ["Any academic decisions made, e.g. laptop choice, elective selection (empty list if not applicable)"],
  "progress": ["Milestones or completed work (empty list if not applicable)"],
  "knowledge_updates": ["Durable concept definitions or explanations worth remembering (empty list if not applicable)"],
  "suggested_links": ["Key concept names for Obsidian Wikilinks, e.g. C++ Programming, Variables, Pointers"]
}

Rules:
1. Focus strictly on academic and technical substance. Do NOT output sentiment or mood tags.
2. If a section does not apply, use an empty list [].
3. Do not invent information not in the user's input.
4. Output strictly valid JSON without markdown wrapping.
"""

class LocalLLMProvider:
    """
    Runtime-agnostic Local LLM Provider.
    Works seamlessly with llama.cpp/llama-server, Ollama, LM Studio, or any OpenAI-compatible local server.
    """

    def __init__(self):
        self.config = load_config()

    def refresh_config(self):
        self.config = load_config()

    def analyze_academic_input(self, text: str) -> Dict[str, Any]:
        """
        Sends user text to the configured local LLM runtime.
        Falls back to rule-based academic heuristics if the local server is unreachable.
        """
        self.refresh_config()
        base_url = self.config.get("local_llm_url", "http://localhost:11434/v1").rstrip("/")
        model = self.config.get("local_llm_model", "qwen2.5:7b-instruct")
        timeout = int(self.config.get("local_llm_timeout", 20))

        # 1. Attempt Local Inference via standard OpenAI-compatible endpoint
        try:
            url = f"{base_url}/chat/completions"
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": ACADEMIC_SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"}
            }
            # (2.0s connect timeout, timeout read timeout) prevents GUI freeze when server is offline
            resp = requests.post(url, json=payload, timeout=(2.0, timeout))
            if resp.status_code == 200:
                data = resp.json()
                raw_content = data["choices"][0]["message"]["content"]
                parsed = self._safe_parse_json(raw_content)
                if parsed:
                    return self._validate_and_sanitize(parsed, text)
        except Exception as e:
            print(f"[LocalLLM] Local inference server ({base_url}) unreachable: {e}")

        # 2. Check for optional cloud fallback (Gemini) if configured
        gemini_key = self.config.get("gemini_api_key")
        if gemini_key:
            try:
                cloud_result = self._try_gemini_fallback(text, gemini_key)
                if cloud_result:
                    return self._validate_and_sanitize(cloud_result, text)
            except Exception as e:
                print(f"[LocalLLM] Cloud fallback error: {e}")

        # 3. Deterministic Local Fallback (Gate 5 - Never lose data)
        return self._rule_based_academic_fallback(text)

    def _safe_parse_json(self, raw_str: str) -> Optional[Dict[str, Any]]:
        """Cleans and parses JSON string safely."""
        try:
            cleaned = re.sub(r"^```json\s*", "", raw_str.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
            return json.loads(cleaned)
        except Exception:
            # Try finding first { and last }
            start = raw_str.find("{")
            end = raw_str.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw_str[start:end+1])
                except Exception:
                    pass
        return None

    def _try_gemini_fallback(self, text: str, api_key: str) -> Optional[Dict[str, Any]]:
        """Optional cloud fallback using Gemini REST API."""
        model = self.config.get("gemini_model", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": f"{ACADEMIC_SYSTEM_PROMPT}\n\nUSER INPUT:\n{text}"}]
            }],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2}
        }
        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code == 200:
            content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return self._safe_parse_json(content)
        return None

    def _validate_and_sanitize(self, data: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """Ensures all expected academic fields exist as lists or strings."""
        return {
            "summary": str(data.get("summary") or original_text[:120]),
            "topics": [str(x).strip() for x in data.get("topics", []) if x],
            "entities": [str(x).strip() for x in data.get("entities", []) if x],
            "what_i_learned": [str(x).strip() for x in data.get("what_i_learned", []) if x],
            "learning_gaps": [str(x).strip() for x in data.get("learning_gaps", []) if x],
            "assignments": [str(x).strip() for x in data.get("assignments", []) if x],
            "tasks": [str(x).strip() for x in data.get("tasks", []) if x],
            "decisions": [str(x).strip() for x in data.get("decisions", []) if x],
            "progress": [str(x).strip() for x in data.get("progress", []) if x],
            "knowledge_updates": [str(x).strip() for x in data.get("knowledge_updates", []) if x],
            "suggested_links": [str(x).strip() for x in data.get("suggested_links", []) if x]
        }

    def _rule_based_academic_fallback(self, text: str) -> Dict[str, Any]:
        """
        Deterministic rule-based parser used when LLM is unavailable.
        Extracts academic entities, topics, learning gaps, and assignments via pattern matching.
        """
        lower = text.lower()
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]

        summary = sentences[0] if sentences else text[:140]

        # Extract topics (Programming languages, CS terms)
        known_academic_terms = [
            "c++", "python", "java", "dsa", "data structures", "algorithms",
            "variables", "data types", "type casting", "pointers", "arrays",
            "loops", "for loop", "while loop", "functions", "recursion",
            "oop", "classes", "objects", "inheritance", "polymorphism",
            "operating systems", "dbms", "sql", "networking", "bca", "computer science"
        ]

        detected_topics = []
        for term in known_academic_terms:
            if re.search(r'\b' + re.escape(term) + r'\b', lower):
                detected_topics.append(term.title() if len(term) > 3 else term.upper())

        # Extract faculty / entities (e.g. Sir, Prof., Teacher)
        entities = []
        if "sir" in lower or "professor" in lower or "prof" in lower or "faculty" in lower:
            entities.append("Science Faculty")

        # Detect learning gaps ("don't understand", "confused", "didn't get", "struggling")
        learning_gaps = []
        for s in sentences:
            s_low = s.lower()
            if any(cue in s_low for cue in ["don't understand", "dont understand", "didn't understand", "confused about", "struggling with", "hard to follow"]):
                learning_gaps.append(s)

        # Detect assignments / tasks ("assignment", "homework", "practical", "programs to write")
        assignments = []
        tasks = []
        for s in sentences:
            s_low = s.lower()
            if any(cue in s_low for cue in ["assignment", "homework", "write programs", "lab exercise", "task"]):
                assignments.append(s)
                tasks.append(f"Complete: {s}")

        # Detect learnings ("learned", "explained", "understood", "taught")
        what_i_learned = []
        for s in sentences:
            s_low = s.lower()
            if any(cue in s_low for cue in ["learned", "explained", "taught", "understood", "studied"]):
                if s not in learning_gaps:
                    what_i_learned.append(s)

        suggested_links = list(dict.fromkeys(detected_topics + entities))

        return {
            "summary": summary,
            "topics": detected_topics,
            "entities": entities,
            "what_i_learned": what_i_learned,
            "learning_gaps": learning_gaps,
            "assignments": assignments,
            "tasks": tasks,
            "decisions": [],
            "progress": [],
            "knowledge_updates": [],
            "suggested_links": suggested_links
        }

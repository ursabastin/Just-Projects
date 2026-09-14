import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from config import DB_PATH

class StorageManager:
    """Manages the local SQLite registry for voice recordings, raw transcripts, and AI outputs."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS journal_entries (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    audio_path TEXT,
                    audio_duration REAL DEFAULT 0.0,
                    raw_transcript TEXT NOT NULL,
                    title TEXT,
                    summary TEXT,
                    key_insights_json TEXT,
                    action_items_json TEXT,
                    entities_json TEXT,
                    vault_file_path TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entries_timestamp 
                ON journal_entries(timestamp DESC);
            """)
            conn.commit()

    def insert_entry(self, entry: Dict[str, Any]) -> str:
        """Inserts a new journal entry record."""
        entry_id = entry.get("id") or datetime.now().strftime("%Y%m%d-%H%M%S")
        timestamp = entry.get("timestamp") or datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO journal_entries (
                    id, timestamp, audio_path, audio_duration,
                    raw_transcript, title, summary,
                    key_insights_json, action_items_json, entities_json,
                    vault_file_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id,
                timestamp,
                entry.get("audio_path"),
                float(entry.get("audio_duration", 0.0)),
                entry.get("raw_transcript", ""),
                entry.get("title", "Untitled Thought"),
                entry.get("summary", ""),
                json.dumps(entry.get("key_insights", []), ensure_ascii=False),
                json.dumps(entry.get("action_items", []), ensure_ascii=False),
                json.dumps(entry.get("entities", []), ensure_ascii=False),
                entry.get("vault_file_path")
            ))
            conn.commit()
        return entry_id

    def get_recent_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent journal entries ordered by timestamp descending."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM journal_entries 
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            results = []
            for row in rows:
                item = dict(row)
                item["key_insights"] = json.loads(item.get("key_insights_json") or "[]")
                item["action_items"] = json.loads(item.get("action_items_json") or "[]")
                item["entities"] = json.loads(item.get("entities_json") or "[]")
                results.append(item)
            return results

    def get_entry_count(self) -> int:
        """Returns total entries stored."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM journal_entries")
            return cursor.fetchone()[0]

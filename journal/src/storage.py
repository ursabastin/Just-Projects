import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from config import DB_PATH

class StorageManager:
    """
    Internal SQLite database for audit, recovery, and raw transcript preservation.
    Note: The human-readable knowledge store remains the Obsidian vault.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS academic_entries (
                    id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    entry_type TEXT DEFAULT 'voice',
                    audio_path TEXT,
                    audio_duration REAL DEFAULT 0.0,
                    raw_transcript TEXT NOT NULL,
                    summary TEXT,
                    ai_json TEXT,
                    vault_file_path TEXT,
                    status TEXT DEFAULT 'processed',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_academic_date 
                ON academic_entries(date DESC, timestamp DESC);
            """)
            conn.commit()

    def insert_entry(self, entry: Dict[str, Any]) -> str:
        """Saves entry to local internal registry."""
        now = datetime.now()
        entry_id = entry.get("id") or now.strftime("%Y%m%d-%H%M%S")
        date_str = entry.get("date") or now.strftime("%Y-%m-%d")
        timestamp = entry.get("timestamp") or now.isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO academic_entries (
                    id, date, timestamp, entry_type, audio_path, audio_duration,
                    raw_transcript, summary, ai_json, vault_file_path, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id,
                date_str,
                timestamp,
                entry.get("entry_type", "voice"),
                entry.get("audio_path"),
                float(entry.get("audio_duration", 0.0)),
                entry.get("raw_transcript", ""),
                entry.get("summary", ""),
                json.dumps(entry.get("ai_data", {}), ensure_ascii=False),
                entry.get("vault_file_path"),
                entry.get("status", "processed")
            ))
            conn.commit()
        return entry_id

    def get_recent_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent entries for audit or review."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM academic_entries 
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            results = []
            for row in rows:
                item = dict(row)
                try:
                    item["ai_data"] = json.loads(item.get("ai_json") or "{}")
                except Exception:
                    item["ai_data"] = {}
                results.append(item)
            return results

    def get_entry_count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM academic_entries")
            return cursor.fetchone()[0]

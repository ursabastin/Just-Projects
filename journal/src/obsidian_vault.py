import os
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import load_config

class ObsidianVaultManager:
    r"""
    Manages direct interactions with the Obsidian knowledge vault (C:\Tethis-System).
    Enforces the single-file canonical journal structure: Academy/Journal/Journal-YYYY-MM-DD.md.
    """

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path) if vault_path else None
        self.vault_name = self.vault_path.name if self.vault_path else "Tethis-System"

    def is_valid_vault(self) -> bool:
        """Verifies the vault directory exists."""
        return bool(self.vault_path and self.vault_path.is_dir())

    def get_journal_dir(self, subfolder: str = "Academy/Journal") -> Path:
        """Returns the canonical journal folder, creating it if necessary."""
        target = self.vault_path / subfolder
        target.mkdir(parents=True, exist_ok=True)
        return target

    def get_voice_attachments_dir(self, subfolder: str = "Academy/Journal/Attachments/VoiceLogs") -> Path:
        """Returns the audio attachments directory."""
        target = self.vault_path / subfolder
        target.mkdir(parents=True, exist_ok=True)
        return target

    def get_daily_journal_path(self, timestamp_dt: datetime, subfolder: str = "Academy/Journal") -> Path:
        """Returns the full path to today's canonical Journal-YYYY-MM-DD.md file."""
        journal_dir = self.get_journal_dir(subfolder)
        date_str = timestamp_dt.strftime("%Y-%m-%d")
        return journal_dir / f"Journal-{date_str}.md"

    def read_existing_daily_journal(self, timestamp_dt: datetime, subfolder: str = "Academy/Journal") -> Optional[str]:
        """Reads existing content of today's journal if present."""
        daily_path = self.get_daily_journal_path(timestamp_dt, subfolder)
        if daily_path.exists():
            try:
                with open(daily_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"[VaultManager] Error reading {daily_path}: {e}")
        return None

    def save_daily_journal(self, timestamp_dt: datetime, content: str, subfolder: str = "Academy/Journal") -> Path:
        """Writes or updates today's Journal-YYYY-MM-DD.md file."""
        daily_path = self.get_daily_journal_path(timestamp_dt, subfolder)
        with open(daily_path, "w", encoding="utf-8") as f:
            f.write(content)
        return daily_path

    def get_obsidian_uri(self, file_path: Path) -> str:
        """Generates obsidian:// URI to open the note directly in the Obsidian desktop application."""
        if not self.vault_path:
            return ""
        try:
            rel_path = file_path.relative_to(self.vault_path).as_posix()
            encoded_vault = urllib.parse.quote(self.vault_name)
            encoded_file = urllib.parse.quote(rel_path)
            return f"obsidian://open?vault={encoded_vault}&file={encoded_file}"
        except Exception:
            return f"file:///{str(file_path).replace(chr(92), '/')}"

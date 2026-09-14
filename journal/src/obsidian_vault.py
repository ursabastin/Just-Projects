import os
import re
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

class ObsidianVaultManager:
    """Handles writing notes, attaching audio, and interlocking with Daily Notes in the Obsidian Vault."""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path) if vault_path else None
        self.vault_name = self.vault_path.name if self.vault_path else "Tethis-System"

    def is_valid_vault(self) -> bool:
        """Checks if vault directory exists and has .obsidian or is a valid directory."""
        if not self.vault_path:
            return False
        return self.vault_path.is_dir()

    def get_attachments_dir(self, subfolder: str = "Attachments/VoiceLogs") -> Path:
        """Returns the directory for saving audio logs."""
        target = self.vault_path / subfolder
        target.mkdir(parents=True, exist_ok=True)
        return target

    def save_journal_note(
        self,
        timestamp_dt: datetime,
        markdown_content: str,
        subfolder: str = "Journal/Voice"
    ) -> Path:
        """Writes the primary atomic voice note to the vault."""
        target_dir = self.vault_path / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{timestamp_dt.strftime('%Y-%m-%d_%H%M%S')}.md"
        file_path = target_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return file_path

    def update_daily_note(
        self,
        timestamp_dt: datetime,
        snippet: str,
        daily_folder: str = "Daily Notes"
    ) -> Optional[Path]:
        """Interlocks with Daily Notes by appending the voice note reference."""
        if not self.vault_path or not self.vault_path.is_dir():
            return None

        daily_dir = self.vault_path / daily_folder
        daily_dir.mkdir(parents=True, exist_ok=True)

        date_str = timestamp_dt.strftime("%Y-%m-%d")
        daily_file = daily_dir / f"{date_str}.md"

        header = "\n## 🎙️ Voice Reflections\n"

        if daily_file.exists():
            with open(daily_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if "## 🎙️ Voice Reflections" in content:
                # Append under section
                content += f"\n{snippet}"
            else:
                # Add section
                content += f"{header}{snippet}"

            with open(daily_file, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            # Create fresh daily note
            fresh_content = f"""---
date: {date_str}
type: daily-note
tags:
  - daily
---

# 📅 Daily Note: {date_str}

{header}{snippet}
"""
            with open(daily_file, "w", encoding="utf-8") as f:
                f.write(fresh_content)

        return daily_file

    def get_obsidian_uri(self, file_path: Path) -> str:
        """Generates an obsidian://open URI to directly focus this file in Obsidian."""
        rel_path = file_path.relative_to(self.vault_path).as_posix()
        encoded_vault = urllib.parse.quote(self.vault_name)
        encoded_file = urllib.parse.quote(rel_path)
        return f"obsidian://open?vault={encoded_vault}&file={encoded_file}"

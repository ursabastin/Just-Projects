import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

APP_NAME = "Voice Journal"
APP_VERSION = "1.0.0"

# Fixed Window Dimensions (Strict rectangular format)
WINDOW_WIDTH = 640
WINDOW_HEIGHT = 760

# Palette matching strict dark modern aesthetic
BG_ROOT = "#090d16"
BG_CARD = "#131b2e"
BG_CARD_HOVER = "#18223a"
BG_INPUT = "#0c1322"
BORDER_SUBTLE = "#23304a"
BORDER_FOCUS = "#38bdf8"
ACCENT_CYAN = "#38bdf8"
ACCENT_EMERALD = "#10b981"
ACCENT_AMBER = "#fbbf24"
ACCENT_ROSE = "#f43f5e"
ACCENT_PURPLE = "#a855f7"
TEXT_WHITE = "#f8fafc"
TEXT_MUTED = "#94a3b8"
TEXT_DIM = "#64748b"

FONT_FAMILY = "Segoe UI"

# Base and Data directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "journal_registry.db"
CONFIG_FILE = DATA_DIR / "config.json"

# Audio parameters
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
RMS_REFRESH_MS = 30

def detect_obsidian_vault() -> str:
    """Attempts to auto-detect active Obsidian vault from obsidian.json."""
    default_vault = r"C:\Tethis-System"
    obsidian_conf = Path(os.environ.get("APPDATA", "")) / "obsidian" / "obsidian.json"
    if obsidian_conf.exists():
        try:
            with open(obsidian_conf, "r", encoding="utf-8") as f:
                data = json.load(f)
                vaults = data.get("vaults", {})
                for v_info in vaults.values():
                    v_path = v_info.get("path")
                    if v_path and os.path.isdir(v_path):
                        return v_path
        except Exception:
            pass
    return default_vault

DEFAULT_CONFIG: Dict[str, Any] = {
    "obsidian_vault_path": detect_obsidian_vault(),
    "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
    "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
    "ai_provider": "gemini",  # "gemini" or "openai" or "offline"
    "gemini_model": "gemini-2.5-flash",
    "hotkey": "alt+shift",
    "save_audio_attachments": True,
    "attachments_folder": "Attachments/VoiceLogs",
    "journal_folder": "Journal/Voice",
    "daily_notes_folder": "Daily Notes",
    "auto_link_vault": True
}

def load_config() -> Dict[str, Any]:
    """Loads configuration from config.json or initializes with defaults."""
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # Ensure all keys exist
            merged = DEFAULT_CONFIG.copy()
            merged.update(cfg)
            return merged
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(cfg: Dict[str, Any]) -> None:
    """Saves configuration dict to config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")

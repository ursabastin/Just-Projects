import os
import sys
import shutil
import ctypes
from ctypes import wintypes
from pathlib import Path

APP_NAME = "Universal Downloader"
APP_VERSION = "1.0.0"

def get_windows_videos_folder() -> Path:
    """Retrieve the authentic Windows Videos folder path (accounting for redirection)."""
    try:
        # CSIDL_MYVIDEO = 0x000e, SHGFP_TYPE_CURRENT = 0
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, 0x000e, None, 0, buf)
        if buf.value:
            return Path(buf.value)
    except Exception:
        pass
    
    # Fallback to standard user Videos path
    user_videos = Path(os.path.expanduser("~")) / "Videos"
    if user_videos.exists():
        return user_videos
    return Path(os.path.expanduser("~"))

# Default download directory in Videos
VIDEOS_DIR = get_windows_videos_folder()
DOWNLOAD_DIR = VIDEOS_DIR / "UniversalDownloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

def find_ffmpeg() -> str | None:
    """Locate ffmpeg executable from PATH, imageio_ffmpeg, or common locations."""
    # 1. System PATH
    ffmpeg_cmd = shutil.which("ffmpeg")
    if ffmpeg_cmd:
        return ffmpeg_cmd
    
    # 2. imageio-ffmpeg bundled binary
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass
    
    # 3. Known disk locations
    candidates = [
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg\bin\ffmpeg.exe",
        str(Path(__file__).parent.parent / "bin" / "ffmpeg.exe")
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

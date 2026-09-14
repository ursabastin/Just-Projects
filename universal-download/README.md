# Universal Downloader (`universal-download`)

A strict, modern dark-themed desktop media downloader built with Python and Tkinter, powered by `yt-dlp` and `ffmpeg`.

## Key Features
- **Global Terminal Command**: Launch anytime, anywhere by typing `download ext` (or `download`).
- **Universal Platform Support**: YouTube, Instagram, Facebook, TikTok, Twitter/X, Reddit, and 1800+ media sites.
- **Smart Link & Playlist Detection**:
  - Automatically identifies whether a link is a single video or a playlist.
  - For playlists, displays the video count in brackets: `(Found 42 videos)`.
  - Offers two clean playlist options:
    1. **Download First N Videos**: specify count e.g. 5, 10, etc.
    2. **Download Complete Playlist**: downloads all items in playlist.
- **Streamlined Quality Presets**:
  - 🎬 **High Quality Video (MP4)**: Best video + best audio merged with ffmpeg.
  - 🎵 **High Quality Audio (MP3)**: Best audio converted to 320kbps MP3.
  - No convoluted dropdowns or bitrate selection spirals.
- **Direct Save to Videos Folder**:
  - Files are automatically saved to `C:\Users\<User>\Videos\UniversalDownloads`.
  - Includes a quick **"Open Videos Folder"** button to view downloaded files immediately.
- **Robust Error Diagnostics**:
  - Catches private media, login requirements, rate limits (HTTP 429), deleted videos, geo-blocks, and provides clear suggestions.

## Usage
From any Command Prompt or PowerShell:
```cmd
download ext
```
Or directly inspect a link from the terminal:
```cmd
download https://www.youtube.com/watch?v=...
```

## Structure
```
c:\Just-Projects\universal-download\
├── bin\
│   ├── download.bat
│   ├── download.cmd
│   ├── download.ps1
│   ├── download-ext.bat
│   └── universal-download.bat
├── src\
│   ├── main.py               # Tkinter GUI application
│   ├── downloader.py         # yt-dlp backend & inspection
│   ├── ui_components.py      # Strict dark-theme UI components
│   ├── error_handler.py      # Human-friendly error analyzer
│   └── config.py             # Paths & ffmpeg resolution
├── requirements.txt
└── README.md
```

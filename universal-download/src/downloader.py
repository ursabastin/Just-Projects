import os
import sys
import threading
import time
from typing import Callable, Optional
import yt_dlp

from config import DOWNLOAD_DIR, find_ffmpeg
from error_handler import analyze_error

class DownloadCancelledError(Exception):
    """Raised when user cancels a download in progress."""
    pass

def format_bytes(size: float) -> str:
    """Format bytes to human-readable string (KB, MB, GB)."""
    if not size or size <= 0:
        return "0 KB"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"

def format_duration(seconds: Optional[float]) -> str:
    """Format duration in seconds into HH:MM:SS or MM:SS."""
    if not seconds or seconds <= 0:
        return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

class MediaInspector:
    """Inspects URLs without downloading to detect single video vs playlist and extract metadata."""
    
    @staticmethod
    def inspect(url: str) -> dict:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'playlistend': 1000,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        }
        
        ffmpeg_path = find_ffmpeg()
        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise ValueError("Could not retrieve media information from this URL.")
                
                # Detect playlist
                is_playlist = (
                    info.get('_type') == 'playlist' or 
                    'entries' in info or
                    'playlist_count' in info
                )

                if is_playlist:
                    raw_entries = list(info.get('entries') or [])
                    count = len(raw_entries) if raw_entries else info.get('playlist_count', 0)
                    
                    # Sometimes count is in playlist_count
                    if count == 0 and 'playlist_count' in info:
                        count = info['playlist_count']

                    title = info.get('title') or "Untitled Playlist"
                    uploader = info.get('uploader') or info.get('channel') or "Unknown Channel"
                    
                    # Try to get thumbnail from first entry or playlist
                    thumbnail = info.get('thumbnail')
                    if not thumbnail and raw_entries and isinstance(raw_entries[0], dict):
                        thumbnail = raw_entries[0].get('thumbnail')

                    return {
                        "is_playlist": True,
                        "title": title,
                        "uploader": uploader,
                        "count": count,
                        "thumbnail": thumbnail,
                        "url": url,
                        "raw_info": info
                    }
                else:
                    # Single video
                    title = info.get('title') or "Untitled Video"
                    uploader = info.get('uploader') or info.get('channel') or "Unknown Creator"
                    duration = info.get('duration')
                    thumbnail = info.get('thumbnail')
                    
                    return {
                        "is_playlist": False,
                        "title": title,
                        "uploader": uploader,
                        "duration_str": format_duration(duration),
                        "duration": duration,
                        "thumbnail": thumbnail,
                        "url": url,
                        "raw_info": info
                    }
        except Exception as e:
            analyzed = analyze_error(e)
            raise RuntimeError(f"{analyzed['title']}: {analyzed['message']} ({analyzed['hint']})")

class DownloaderEngine:
    """Manages threaded media downloads with real-time status callbacks and cancellation."""
    
    def __init__(self, on_progress: Callable[[dict], None], on_log: Callable[[str], None], on_complete: Callable[[dict], None]):
        self.on_progress = on_progress
        self.on_log = on_log
        self.on_complete = on_complete
        self._cancel_requested = False
        self._thread: Optional[threading.Thread] = None
        self._current_ydl: Optional[yt_dlp.YoutubeDL] = None

    def cancel(self):
        """Signal the current download to abort immediately."""
        self._cancel_requested = True
        self.on_log("⚠️ Cancellation requested by user...")

    def start_download(self, url: str, is_playlist: bool, mode: str = "video", 
                       playlist_limit: Optional[int] = None):
        """
        Starts download in a separate background thread.
        mode: 'video' (HQ Video+Audio MP4) | 'audio' (HQ Audio MP3)
        playlist_limit: None for complete playlist, or int N for first N videos
        """
        self._cancel_requested = False
        self._thread = threading.Thread(
            target=self._run_download,
            args=(url, is_playlist, mode, playlist_limit),
            daemon=True
        )
        self._thread.start()

    def _progress_hook(self, d: dict):
        if self._cancel_requested:
            raise DownloadCancelledError("Download was cancelled by user.")

        status = d.get('status', '')
        
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes') or 0
            percent = (downloaded / total * 100.0) if total > 0 else 0.0
            
            speed = d.get('speed')
            speed_str = f"{format_bytes(speed)}/s" if speed else "-- KB/s"
            
            eta = d.get('eta')
            eta_str = f"{eta}s" if eta else "--"

            filename = os.path.basename(d.get('filename') or '')
            
            # Playlist indexing info
            info_dict = d.get('info_dict') or {}
            playlist_index = info_dict.get('playlist_index')
            playlist_count = info_dict.get('n_entries')

            self.on_progress({
                "status": "downloading",
                "percent": percent,
                "downloaded_str": format_bytes(downloaded),
                "total_str": format_bytes(total),
                "speed_str": speed_str,
                "eta_str": eta_str,
                "filename": filename,
                "playlist_index": playlist_index,
                "playlist_count": playlist_count
            })

        elif status == 'finished':
            self.on_progress({
                "status": "processing",
                "percent": 100.0,
                "message": "Finalizing and processing media stream..."
            })

    def _run_download(self, url: str, is_playlist: bool, mode: str, playlist_limit: Optional[int]):
        ffmpeg_path = find_ffmpeg()
        
        # Build clean output path template inside Videos/UniversalDownloads
        if is_playlist:
            out_template = os.path.join(
                str(DOWNLOAD_DIR), 
                "%(playlist_title,playlist)s", 
                "%(playlist_index)02d - %(title)s [%(id)s].%(ext)s"
            )
        else:
            out_template = os.path.join(
                str(DOWNLOAD_DIR), 
                "%(title)s [%(id)s].%(ext)s"
            )

        ydl_opts = {
            'outtmpl': out_template,
            'windowsfilenames': True,
            'progress_hooks': [self._progress_hook],
            'logger': _YtdlLogger(self.on_log),
            'nocheckcertificate': True,
            'ignoreerrors': True if is_playlist else False,
            'no_warnings': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        }

        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_path

        # Stream Quality Selection
        if mode == "audio":
            self.on_log("🎵 Quality preset: High Quality Audio Only (MP3)")
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }] if ffmpeg_path else []
            })
        else:
            self.on_log("🎬 Quality preset: High Quality Video + Audio (MP4)")
            if ffmpeg_path:
                ydl_opts.update({
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
                    'merge_output_format': 'mp4',
                })
            else:
                # Fallback if no ffmpeg available (pre-merged stream)
                ydl_opts.update({
                    'format': 'best[ext=mp4]/best',
                })

        # Playlist options
        if is_playlist:
            if playlist_limit and playlist_limit > 0:
                self.on_log(f"📋 Playlist mode: Downloading first {playlist_limit} videos...")
                ydl_opts['playlistend'] = playlist_limit
                ydl_opts['playlist_items'] = f"1-{playlist_limit}"
            else:
                self.on_log("📋 Playlist mode: Downloading complete playlist...")
                ydl_opts['noplaylist'] = False
        else:
            ydl_opts['noplaylist'] = True

        start_time = time.time()
        success = False
        error_info = None

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self._current_ydl = ydl
                self.on_log(f"🚀 Starting download: {url}")
                ydl.download([url])
                
            if not self._cancel_requested:
                success = True
                elapsed = time.time() - start_time
                self.on_log(f"✅ Download completed successfully in {elapsed:.1f}s!")
        except DownloadCancelledError:
            self.on_log("🛑 Download was cancelled by user.")
            error_info = {"title": "Cancelled", "message": "Download stopped by user."}
        except Exception as e:
            analyzed = analyze_error(e)
            error_info = analyzed
            self.on_log(f"❌ Error: {analyzed['title']} - {analyzed['message']}")
            if analyzed.get('hint'):
                self.on_log(f"💡 Suggestion: {analyzed['hint']}")
        finally:
            self._current_ydl = None
            self.on_complete({
                "success": success,
                "cancelled": self._cancel_requested,
                "error": error_info,
                "output_dir": str(DOWNLOAD_DIR)
            })

class _YtdlLogger:
    """Redirects yt-dlp logging output to GUI activity log."""
    def __init__(self, log_fn: Callable[[str], None]):
        self.log_fn = log_fn

    def debug(self, msg: str):
        # Filter out noisy debug lines, keep informative ones
        if msg.startswith('[download]') or msg.startswith('[Merger]') or msg.startswith('[ExtractAudio]'):
            self.log_fn(msg)

    def info(self, msg: str):
        self.log_fn(msg)

    def warning(self, msg: str):
        self.log_fn(f"⚠️ {msg}")

    def error(self, msg: str):
        self.log_fn(f"❌ {msg}")

import os
import sys
import unittest
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import config
from error_handler import analyze_error
from downloader import format_bytes, format_duration, MediaInspector

class TestUniversalDownloader(unittest.TestCase):
    def test_config_paths(self):
        self.assertTrue(config.VIDEOS_DIR.exists(), f"Videos directory not found: {config.VIDEOS_DIR}")
        self.assertTrue(config.DOWNLOAD_DIR.exists(), f"Download directory not found: {config.DOWNLOAD_DIR}")
        
        ffmpeg_exe = config.find_ffmpeg()
        self.assertIsNotNone(ffmpeg_exe, "FFmpeg executable could not be located")
        self.assertTrue(os.path.isfile(ffmpeg_exe), f"FFmpeg path does not exist: {ffmpeg_exe}")
        print(f"[PASS] FFmpeg verified at: {ffmpeg_exe}")
        print(f"[PASS] Videos directory: {config.DOWNLOAD_DIR}")

    def test_formatters(self):
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1048576), "1.0 MB")
        self.assertEqual(format_duration(65), "01:05")
        self.assertEqual(format_duration(3665), "1:01:05")
        print("[PASS] Byte and duration formatters verified")

    def test_error_diagnostics(self):
        # Test Instagram private error
        res1 = analyze_error(Exception("Instagram post requires login: private video"))
        self.assertIn("Instagram", res1["title"])
        self.assertTrue("private" in res1["message"].lower())

        # Test Rate Limit (429)
        res2 = analyze_error(Exception("HTTP Error 429: Too Many Requests"))
        self.assertIn("Rate Limit", res2["title"])

        # Test Unsupported URL
        res3 = analyze_error(Exception("Unsupported URL: ftp://example.com/file"))
        self.assertIn("Unsupported", res3["title"])

        print("[PASS] Error diagnostics verified")

    def test_gui_instantiation(self):
        from main import UniversalDownloaderApp
        app = UniversalDownloaderApp()
        self.assertIsNotNone(app)
        app.update_idletasks()
        # Verify initial widgets
        self.assertEqual(app.download_mode.get(), "video")
        self.assertEqual(app.playlist_mode.get(), "complete")
        app.destroy()
        print("[PASS] Tkinter GUI initialized cleanly without errors")

if __name__ == "__main__":
    unittest.main()

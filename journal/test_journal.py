import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from storage import StorageManager
from logic_gates import LogicGatesEngine, VaultGraphIndexer, EntityTopicResolutionGate
from obsidian_vault import ObsidianVaultManager
from speech_engine import SpeechAndSynthesisEngine

class TestVoiceJournalSystem(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_journal_")
        self.vault_dir = Path(self.test_dir) / "TestVault"
        self.vault_dir.mkdir(parents=True)
        self.db_path = Path(self.test_dir) / "test_registry.db"

        # Create mock notes in test vault
        (self.vault_dir / "Deep Learning.md").write_text(
            "---\naliases: [DL, Neural Nets]\ntags: [ai, tech]\n---\n# Deep Learning\nContent here.",
            encoding="utf-8"
        )
        (self.vault_dir / "Project Tethis.md").write_text(
            "---\naliases: [Tethis System]\ntags: [projects]\n---\n# Project Tethis\nSystem specifications.",
            encoding="utf-8"
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_storage_registry(self):
        """Verify SQLite insertion, queries, and count."""
        storage = StorageManager(db_path=self.db_path)
        entry_id = storage.insert_entry({
            "id": "20260914-001",
            "timestamp": "2026-09-14T12:00:00",
            "audio_path": "/fake/audio.wav",
            "audio_duration": 4.5,
            "raw_transcript": "This is a test recording about machine learning.",
            "title": "Test Thought",
            "summary": "Summary of test recording.",
            "key_insights": ["Insight 1", "Insight 2"],
            "action_items": ["Action 1"],
            "entities": [{"target": "Deep Learning", "wikilink": "[[Deep Learning]]"}],
            "vault_file_path": "/fake/vault/note.md"
        })
        self.assertEqual(entry_id, "20260914-001")
        self.assertEqual(storage.get_entry_count(), 1)
        entries = storage.get_recent_entries(limit=5)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["title"], "Test Thought")
        self.assertEqual(len(entries[0]["key_insights"]), 2)

    def test_logic_gates_indexing_and_resolution(self):
        """Verify the 5 Python Logic Gates for Obsidian graph linking."""
        engine = LogicGatesEngine(str(self.vault_dir))

        # Test Exact Match (Gate 2)
        res_exact = engine.entity_gate.resolve_topic("Deep Learning")
        self.assertEqual(res_exact["match_type"], "exact")
        self.assertEqual(res_exact["wikilink"], "[[Deep Learning]]")

        # Test Alias Match (Gate 2)
        res_alias = engine.entity_gate.resolve_topic("Neural Nets")
        self.assertEqual(res_alias["match_type"], "alias")
        self.assertEqual(res_alias["wikilink"], "[[Deep Learning|Neural Nets]]")

        # Test Fuzzy Match (Gate 2)
        res_fuzzy = engine.entity_gate.resolve_topic("Deep Learnin")
        self.assertEqual(res_fuzzy["match_type"], "fuzzy")
        self.assertEqual(res_fuzzy["wikilink"], "[[Deep Learning|Deep Learnin]]")

        # Test New Topic (Gate 2)
        res_new = engine.entity_gate.resolve_topic("Quantum Cryptography")
        self.assertEqual(res_new["match_type"], "new_topic")
        self.assertEqual(res_new["wikilink"], "[[Quantum Cryptography]]")

        # Test Full Pipeline (Gate 3, 4, 5)
        ai_payload = {
            "title": "Neural Pipeline Optimization",
            "raw_transcript": "We should use Deep Learning for Project Tethis and study Quantum Cryptography.",
            "summary": "Exploring Deep Learning applications within Project Tethis.",
            "key_insights": ["High computational requirement", "Obsidian linking improves recall"],
            "action_items": ["Run benchmark tests"],
            "entities_and_topics": ["Deep Learning", "Project Tethis", "Quantum Cryptography"],
            "category": "Project",
            "sentiment": "Analytical"
        }
        now = datetime(2026, 9, 14, 14, 30, 0)
        result = engine.process_entry(
            ai_data=ai_payload,
            entry_id="20260914-143000",
            timestamp_dt=now,
            audio_rel_path="Attachments/VoiceLogs/voice_test.wav"
        )

        md = result["markdown_content"]
        self.assertIn("# 🎙️ Neural Pipeline Optimization", md)
        self.assertIn("[[Deep Learning]]", md)
        self.assertIn("[[Project Tethis]]", md)
        self.assertIn("[[Quantum Cryptography]]", md)
        self.assertIn("![[Attachments/VoiceLogs/voice_test.wav]]", md)
        self.assertIn("category: \"Project\"", md)

    def test_obsidian_vault_writer(self):
        """Verify Obsidian file generation and daily note interlocking."""
        vault_mgr = ObsidianVaultManager(str(self.vault_dir))
        self.assertTrue(vault_mgr.is_valid_vault())

        now = datetime(2026, 9, 14, 14, 30, 0)
        note_path = vault_mgr.save_journal_note(
            timestamp_dt=now,
            markdown_content="# Note Content",
            subfolder="Journal/Voice"
        )
        self.assertTrue(note_path.exists())
        self.assertEqual(note_path.name, "2026-09-14_143000.md")

        # Daily note interlock
        daily_path = vault_mgr.update_daily_note(
            timestamp_dt=now,
            snippet="- **14:30** [[Journal/Voice/2026-09-14_143000|🎙️ Test]]: Some reflection",
            daily_folder="Daily Notes"
        )
        self.assertTrue(daily_path.exists())
        content = daily_path.read_text(encoding="utf-8")
        self.assertIn("## 🎙️ Voice Reflections", content)
        self.assertIn("2026-09-14_143000", content)

    def test_speech_engine_offline_fallback(self):
        """Verify speech engine offline fallback works gracefully without internet/key."""
        engine = SpeechAndSynthesisEngine()
        result = engine.process_text("Discussing Quantum Architecture with Alice and Bob on Monday.")
        self.assertIn("title", result)
        self.assertIn("summary", result)
        self.assertIn("entities_and_topics", result)
        self.assertIn("Architecture", result["entities_and_topics"])


if __name__ == "__main__":
    unittest.main()

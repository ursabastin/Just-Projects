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
from logic_gates import LogicGatesEngine, VaultGraphIndexer, EntityTopicResolutionGate, DailyJournalBuilderGate
from obsidian_vault import ObsidianVaultManager
from local_llm import LocalLLMProvider

class TestAcademicJournalSystem(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_academic_journal_")
        self.vault_dir = Path(self.test_dir) / "Tethis-System"
        self.vault_dir.mkdir(parents=True)
        self.db_path = Path(self.test_dir) / "test_registry.db"

        # Create existing faculty & subject notes in test vault
        faculty_dir = self.vault_dir / "Faculty"
        faculty_dir.mkdir()
        (faculty_dir / "Prof. Sharma.md").write_text(
            "---\naliases: [Sharma Sir, Science Faculty - Sharma]\ntags: [faculty, science]\n---\n# Prof. Sharma\nHead of Computer Science.",
            encoding="utf-8"
        )
        subjects_dir = self.vault_dir / "Subjects"
        subjects_dir.mkdir()
        (subjects_dir / "C++ Programming.md").write_text(
            "---\naliases: [C plus plus, CPP, C++]\ntags: [programming, bca]\n---\n# C++ Programming\nCourse material.",
            encoding="utf-8"
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_local_llm_schema_and_deterministic_fallback(self):
        """Verify LocalLLMProvider produces structured academic JSON without sentiment fields."""
        llm = LocalLLMProvider()
        sample_input = "Today was my first C++ practical. Sir explained variables and data types but I still don't understand type casting. We got an assignment to write five programs."
        result = llm.analyze_academic_input(sample_input)

        # Verify expected academic fields
        self.assertIn("summary", result)
        self.assertIn("topics", result)
        self.assertIn("entities", result)
        self.assertIn("what_i_learned", result)
        self.assertIn("learning_gaps", result)
        self.assertIn("assignments", result)
        self.assertIn("tasks", result)
        self.assertIn("suggested_links", result)

        # Verify NO sentiment field
        self.assertNotIn("sentiment", result)
        self.assertNotIn("mood", result)

        # Verify extracted academic understanding
        self.assertTrue(any("c++" in t.lower() or "variable" in t.lower() for t in result["topics"]))
        self.assertTrue(len(result["learning_gaps"]) > 0, "Should detect type casting learning gap")
        self.assertTrue(len(result["assignments"]) > 0, "Should detect 5 programs assignment")

    def test_entity_resolution_and_faculty_reuse(self):
        """Verify Gate 2 resolves spoken terms against existing vault notes without creating duplicates."""
        indexer = VaultGraphIndexer(str(self.vault_dir))
        indexer.refresh_index()
        resolver = EntityTopicResolutionGate(indexer)

        # Exact match
        res1 = resolver.resolve_topic("C++ Programming")
        self.assertEqual(res1["match_type"], "exact")
        self.assertEqual(res1["wikilink"], "[[C++ Programming]]")

        # Alias match for faculty
        res2 = resolver.resolve_topic("Sharma Sir")
        self.assertEqual(res2["match_type"], "alias")
        self.assertEqual(res2["wikilink"], "[[Prof. Sharma]]")

        # Academic normalization (C plus plus -> C++ Programming)
        res3 = resolver.resolve_topic("C plus plus")
        self.assertEqual(res3["wikilink"], "[[C++ Programming]]")

    def test_canonical_daily_journal_initial_build(self):
        """Verify canonical single-file Journal-YYYY-MM-DD.md format and raw preservation."""
        engine = LogicGatesEngine(str(self.vault_dir))
        vault_mgr = ObsidianVaultManager(str(self.vault_dir))

        now = datetime(2026, 9, 14, 10, 15, 0)
        raw_text = "Today was my first C++ practical. Sir explained variables and data types but I still don't understand type casting."

        ai_data = {
            "summary": "Attended first C++ practical and covered variables and data types, noting type casting as a learning gap.",
            "topics": ["C++ Programming", "Variables", "Data Types"],
            "entities": ["Prof. Sharma"],
            "what_i_learned": ["Variables allocate memory based on data type."],
            "learning_gaps": ["Type casting rules between float and int."],
            "assignments": [],
            "tasks": ["Review type casting chapter."],
            "decisions": [],
            "progress": [],
            "suggested_links": ["C++ Programming", "Variables", "Prof. Sharma"]
        }

        gate_res = engine.process_academic_entry(
            raw_text=raw_text,
            ai_data=ai_data,
            timestamp_dt=now,
            existing_journal_content=None
        )

        # Save to vault
        journal_path = vault_mgr.save_daily_journal(now, gate_res["journal_markdown"])
        self.assertTrue(journal_path.exists())
        self.assertEqual(journal_path.name, "Journal-2026-09-14.md")
        self.assertEqual(journal_path.parent.name, "Journal")
        self.assertEqual(journal_path.parent.parent.name, "Academy")

        content = journal_path.read_text(encoding="utf-8")

        # Verify Canonical Schema
        self.assertIn("type: journal", content)
        self.assertIn("date: 2026-09-14", content)
        self.assertIn("domain: academy", content)
        self.assertIn("# Journal — 2026-09-14", content)

        # Strict Rule: Raw input preserved verbatim
        self.assertIn("## Original Entry", content)
        self.assertIn(raw_text, content)

        # Verify Structured Sections
        self.assertIn("## Summary", content)
        self.assertIn("## What I Learned", content)
        self.assertIn("## Connections", content)
        self.assertIn("[[C++ Programming]]", content)
        self.assertIn("[[Prof. Sharma]]", content)
        self.assertIn("## Problems", content)
        self.assertIn("Type casting rules", content)
        self.assertIn("## Next Actions", content)
        self.assertIn("- [ ] Review type casting chapter.", content)

        # Empty sections must NOT exist
        self.assertNotIn("## Sources", content)
        self.assertNotIn("## Progress", content)
        self.assertNotIn("## Decisions", content)

    def test_multi_entry_same_day_merge(self):
        """Verify multiple events on the same calendar day are appended into the single Journal-YYYY-MM-DD.md."""
        engine = LogicGatesEngine(str(self.vault_dir))
        vault_mgr = ObsidianVaultManager(str(self.vault_dir))

        # Event 1: Morning lecture at 09:30
        now1 = datetime(2026, 9, 14, 9, 30, 0)
        raw1 = "Morning lecture with Sharma Sir. He introduced BCA course syllabus."
        ai1 = {
            "summary": "Sharma Sir introduced BCA course syllabus.",
            "topics": ["BCA"],
            "entities": ["Prof. Sharma"],
            "what_i_learned": ["Overview of semester subjects."],
            "learning_gaps": [],
            "assignments": [],
            "tasks": [],
            "decisions": [],
            "progress": [],
            "suggested_links": ["BCA", "Prof. Sharma"]
        }
        res1 = engine.process_academic_entry(raw1, ai1, now1, existing_journal_content=None)
        file_path = vault_mgr.save_daily_journal(now1, res1["journal_markdown"])

        # Event 2: Afternoon practical at 14:30 on the SAME day
        now2 = datetime(2026, 9, 14, 14, 30, 0)
        raw2 = "Afternoon lab: wrote 3 programs for C++ variables and loops."
        ai2 = {
            "summary": "Completed lab programs on variables and loops.",
            "topics": ["C++ Programming", "Variables", "Loops"],
            "entities": [],
            "what_i_learned": ["Syntax of for loop in C++."],
            "learning_gaps": ["Nested loops iteration logic."],
            "assignments": ["Submit lab report by Friday."],
            "tasks": ["Submit lab report by Friday."],
            "decisions": [],
            "progress": ["Wrote 3 programs."],
            "suggested_links": ["C++ Programming", "Variables", "Loops"]
        }

        existing_content = vault_mgr.read_existing_daily_journal(now2)
        self.assertIsNotNone(existing_content)

        res2 = engine.process_academic_entry(raw2, ai2, now2, existing_journal_content=existing_content)
        vault_mgr.save_daily_journal(now2, res2["journal_markdown"])

        # Verify only 1 journal file exists for this day
        journal_files = list(vault_mgr.get_journal_dir().glob("*.md"))
        self.assertEqual(len(journal_files), 1, "Must have exactly ONE journal file per day")
        self.assertEqual(journal_files[0].name, "Journal-2026-09-14.md")

        final_content = journal_files[0].read_text(encoding="utf-8")

        # Verify BOTH raw entries are preserved
        self.assertIn("Morning lecture with Sharma Sir", final_content)
        self.assertIn("Afternoon lab: wrote 3 programs", final_content)

        # Verify sections aggregated cleanly
        self.assertIn("[[Prof. Sharma]]", final_content)
        self.assertIn("[[C++ Programming]]", final_content)
        self.assertIn("Overview of semester subjects.", final_content)
        self.assertIn("Syntax of for loop in C++.", final_content)
        self.assertIn("Nested loops iteration logic.", final_content)
        self.assertIn("Submit lab report by Friday.", final_content)

    def test_storage_registry(self):
        """Verify internal SQLite database stores audit entries."""
        storage = StorageManager(db_path=self.db_path)
        entry_id = storage.insert_entry({
            "id": "20260914-101500",
            "date": "2026-09-14",
            "entry_type": "text",
            "raw_transcript": "Studied C++ variables.",
            "summary": "Learned C++ variables.",
            "ai_data": {"topics": ["C++"]},
            "vault_file_path": "/path/to/Journal-2026-09-14.md"
        })
        self.assertEqual(entry_id, "20260914-101500")
        self.assertEqual(storage.get_entry_count(), 1)


if __name__ == "__main__":
    unittest.main()

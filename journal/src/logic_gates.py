import os
import re
import difflib
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from datetime import datetime

class VaultGraphIndexer:
    r"""
    Gate 1: Scans and incrementally indexes all existing Markdown notes, aliases, and tags in C:\Tethis-System.
    Builds an in-memory knowledge index for fast link and faculty resolution.
    """

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path) if vault_path else None
        self.note_titles: Dict[str, str] = {}      # lowercase_title -> original_title
        self.note_paths: Dict[str, Path] = {}      # original_title -> Path
        self.aliases: Dict[str, str] = {}          # lowercase_alias -> canonical_original_title
        self.all_tags: Set[str] = set()
        self.file_mtimes: Dict[str, float] = {}    # file_path -> last_mtime
        self.last_indexed: Optional[datetime] = None

    def refresh_index(self, force: bool = False) -> None:
        """Incrementally scans the vault directory without rescanning unchanged files."""
        if not self.vault_path or not self.vault_path.is_dir():
            return

        if force:
            self.note_titles.clear()
            self.note_paths.clear()
            self.aliases.clear()
            self.all_tags.clear()
            self.file_mtimes.clear()

        for md_file in self.vault_path.rglob("*.md"):
            # Exclude hidden files / .obsidian
            if ".obsidian" in md_file.parts:
                continue

            try:
                mtime = md_file.stat().st_mtime
                rel_key = str(md_file)
                if rel_key in self.file_mtimes and self.file_mtimes[rel_key] == mtime:
                    continue  # File unchanged, skip parsing

                self.file_mtimes[rel_key] = mtime
                orig_title = md_file.stem
                lower_title = orig_title.lower()
                self.note_titles[lower_title] = orig_title
                self.note_paths[orig_title] = md_file

                # Parse frontmatter for aliases and tags
                with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(2048)
                    self._parse_frontmatter(content, orig_title)
            except Exception:
                pass

        self.last_indexed = datetime.now()

    def _parse_frontmatter(self, content: str, orig_title: str) -> None:
        """Extracts aliases and tags from YAML frontmatter."""
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, flags=re.DOTALL)
        if not fm_match:
            return

        fm_text = fm_match.group(1)
        for line in fm_text.splitlines():
            line = line.strip()
            # Parse aliases
            if line.startswith("aliases:") or line.startswith("alias:"):
                raw_aliases = re.sub(r"^alias(es)?:\s*", "", line)
                if raw_aliases.startswith("[") and raw_aliases.endswith("]"):
                    items = [x.strip().strip("\"'") for x in raw_aliases[1:-1].split(",")]
                    for item in items:
                        if item:
                            self.aliases[item.lower()] = orig_title
                elif raw_aliases:
                    self.aliases[raw_aliases.strip("\"'").lower()] = orig_title

            # Parse tags
            elif line.startswith("tags:"):
                raw_tags = line.replace("tags:", "").strip()
                if raw_tags.startswith("[") and raw_tags.endswith("]"):
                    items = [x.strip().strip("\"'#") for x in raw_tags[1:-1].split(",")]
                    self.all_tags.update(items)


class EntityTopicResolutionGate:
    """
    Gate 2: Resolves extracted candidate academic topics against existing vault notes.
    Applies exact matching, alias lookup, strong fuzzy matching, and common academic entity normalization.
    """

    # Academic term normalizations (spoken variations -> canonical terms)
    KNOWN_NORMALIZATIONS = {
        "c plus plus": "C++ Programming",
        "cpp": "C++ Programming",
        "c++": "C++ Programming",
        "dsa": "Data Structures & Algorithms",
        "data structure": "Data Structures",
        "os": "Operating Systems",
        "dbms": "Database Management Systems",
        "oops": "Object Oriented Programming",
        "oop": "Object Oriented Programming",
        "pointers": "Pointers",
        "type casting": "Type Casting",
        "variables": "Variables",
        "data types": "Data Types"
    }

    def __init__(self, indexer: VaultGraphIndexer):
        self.indexer = indexer

    def resolve_topic(self, topic: str) -> Dict[str, Any]:
        """
        Resolves a topic string into a structured Wikilink target.
        Prefers existing vault notes over creating new ones.
        """
        clean_topic = self._clean_filename(topic.strip())
        if not clean_topic:
            return {"target": topic, "wikilink": f"[[{topic}]]", "match_type": "new_entity"}

        lower = clean_topic.lower()

        # 0. Check Academic Normalization table
        if lower in self.KNOWN_NORMALIZATIONS:
            normalized = self.KNOWN_NORMALIZATIONS[lower]
            # If normalized exists in vault, use it
            if normalized.lower() in self.indexer.note_titles:
                canonical = self.indexer.note_titles[normalized.lower()]
                return {"target": canonical, "wikilink": f"[[{canonical}]]", "match_type": "exact"}
            # Otherwise use normalized title
            return {"target": normalized, "wikilink": f"[[{normalized}]]", "match_type": "normalized"}

        # 1. Exact Match with existing vault note
        if lower in self.indexer.note_titles:
            canonical = self.indexer.note_titles[lower]
            return {"target": canonical, "wikilink": f"[[{canonical}]]", "match_type": "exact"}

        # 2. Alias Match
        if lower in self.indexer.aliases:
            canonical = self.indexer.aliases[lower]
            return {"target": canonical, "wikilink": f"[[{canonical}]]", "match_type": "alias"}

        # 3. Strong Fuzzy Match (similarity cutoff >= 0.85)
        existing_keys = list(self.indexer.note_titles.keys())
        matches = difflib.get_close_matches(lower, existing_keys, n=1, cutoff=0.85)
        if matches:
            canonical = self.indexer.note_titles[matches[0]]
            return {"target": canonical, "wikilink": f"[[{canonical}]]", "match_type": "fuzzy"}

        # 4. New Concept Node (only when no existing match found)
        return {
            "target": clean_topic,
            "wikilink": f"[[{clean_topic}]]",
            "match_type": "new_entity"
        }

    @staticmethod
    def _clean_filename(name: str) -> str:
        return re.sub(r'[\\/:*?"<>|]', '', name).strip()


class WikilinkFormatterGate:
    """
    Gate 3: Formats and validates Obsidian [[Wikilinks]] ensuring clean syntax without illegal characters.
    """

    @staticmethod
    def format_wikilinks(resolved_topics: List[Dict[str, Any]]) -> List[str]:
        """Returns unique list of formatted Wikilinks."""
        links = []
        seen = set()
        for r in resolved_topics:
            wl = r.get("wikilink")
            if wl and wl not in seen:
                seen.add(wl)
                links.append(wl)
        return links


class DailyJournalBuilderGate:
    """
    Gate 4: Single Daily Journal Builder (Journal-YYYY-MM-DD.md).
    Follows canonical schema:
    ---
    type: journal
    date: YYYY-MM-DD
    domain: academy
    status: active
    ---
    Only populates applicable sections.
    Merges subsequent entries on the same day without overwriting.
    """

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path) if vault_path else None

    def build_initial_daily_journal(
        self,
        date_str: str,
        time_str: str,
        raw_transcript: str,
        summary: str,
        what_i_learned: List[str],
        connections: List[str],
        progress: List[str],
        problems: List[str],
        decisions: List[str],
        next_actions: List[str],
        sources: List[str]
    ) -> str:
        """Constructs a fresh Journal-YYYY-MM-DD.md document."""
        lines = [
            "---",
            "type: journal",
            f"date: {date_str}",
            "domain: academy",
            "status: active",
            "---",
            "",
            f"# Journal — {date_str}",
            "",
            "## Original Entry",
            f"> [{time_str}] {raw_transcript.strip()}",
            "",
            "## Summary",
            summary.strip()
        ]

        if what_i_learned:
            lines.append("")
            lines.append("## What I Learned")
            for item in what_i_learned:
                lines.append(f"- {item}")

        if connections:
            lines.append("")
            lines.append("## Connections")
            for item in connections:
                lines.append(f"- {item}")

        if progress:
            lines.append("")
            lines.append("## Progress")
            for item in progress:
                lines.append(f"- {item}")

        if problems:
            lines.append("")
            lines.append("## Problems")
            for item in problems:
                lines.append(f"- {item}")

        if decisions:
            lines.append("")
            lines.append("## Decisions")
            for item in decisions:
                lines.append(f"- {item}")

        if next_actions:
            lines.append("")
            lines.append("## Next Actions")
            for item in next_actions:
                lines.append(f"- [ ] {item}")

        if sources:
            lines.append("")
            lines.append("## Sources")
            for item in sources:
                lines.append(f"- {item}")

        lines.append("")
        return "\n".join(lines)

    def merge_into_existing_daily_journal(
        self,
        existing_content: str,
        time_str: str,
        raw_transcript: str,
        summary: str,
        what_i_learned: List[str],
        connections: List[str],
        progress: List[str],
        problems: List[str],
        decisions: List[str],
        next_actions: List[str],
        sources: List[str]
    ) -> str:
        """
        Merges a subsequent academic event into today's existing Journal-YYYY-MM-DD.md.
        Appends raw input, summary, and relevant section items without losing earlier records.
        """
        content = existing_content

        # 1. Append to ## Original Entry
        raw_snippet = f"\n> [{time_str}] {raw_transcript.strip()}"
        if "## Original Entry" in content:
            content = self._append_to_section(content, "## Original Entry", raw_snippet)
        else:
            content += f"\n\n## Original Entry{raw_snippet}"

        # 2. Append to ## Summary
        summary_snippet = f"\n- **{time_str}**: {summary.strip()}"
        if "## Summary" in content:
            content = self._append_to_section(content, "## Summary", summary_snippet)
        else:
            content += f"\n\n## Summary{summary_snippet}"

        # 3. Append to ## What I Learned
        if what_i_learned:
            learned_snippet = "\n" + "\n".join(f"- {item}" for item in what_i_learned)
            content = self._ensure_or_append_section(content, "## What I Learned", learned_snippet)

        # 4. Append to ## Connections (prevent exact duplicates)
        if connections:
            conn_snippet = "\n" + "\n".join(f"- {item}" for item in connections if item not in content)
            if conn_snippet.strip():
                content = self._ensure_or_append_section(content, "## Connections", conn_snippet)

        # 5. Append to ## Progress
        if progress:
            prog_snippet = "\n" + "\n".join(f"- {item}" for item in progress)
            content = self._ensure_or_append_section(content, "## Progress", prog_snippet)

        # 6. Append to ## Problems
        if problems:
            prob_snippet = "\n" + "\n".join(f"- {item}" for item in problems)
            content = self._ensure_or_append_section(content, "## Problems", prob_snippet)

        # 7. Append to ## Decisions
        if decisions:
            dec_snippet = "\n" + "\n".join(f"- {item}" for item in decisions)
            content = self._ensure_or_append_section(content, "## Decisions", dec_snippet)

        # 8. Append to ## Next Actions
        if next_actions:
            act_snippet = "\n" + "\n".join(f"- [ ] {item}" for item in next_actions)
            content = self._ensure_or_append_section(content, "## Next Actions", act_snippet)

        # 9. Append to ## Sources
        if sources:
            src_snippet = "\n" + "\n".join(f"- {item}" for item in sources if item not in content)
            if src_snippet.strip():
                content = self._ensure_or_append_section(content, "## Sources", src_snippet)

        return content

    @staticmethod
    def _append_to_section(content: str, section_header: str, new_text: str) -> str:
        """Appends text right before the next ## section header or end of file."""
        pos = content.find(section_header)
        if pos == -1:
            return content + f"\n\n{section_header}{new_text}"

        start_search = pos + len(section_header)
        next_sec = content.find("\n## ", start_search)
        if next_sec != -1:
            return content[:next_sec].rstrip() + f"{new_text}\n\n" + content[next_sec:].lstrip()
        else:
            return content.rstrip() + f"{new_text}\n"

    def _ensure_or_append_section(self, content: str, section_header: str, items_text: str) -> str:
        if section_header in content:
            return self._append_to_section(content, section_header, items_text)
        else:
            return content.rstrip() + f"\n\n{section_header}{items_text}\n"


class LogicGatesEngine:
    """
    Master Academic Logic Gates Controller:
    - Index vault & resolve faculty / subjects
    - Format valid Wikilinks
    - Assemble single-file daily journal (Journal-YYYY-MM-DD.md)
    - Fallback preservation
    """

    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.indexer = VaultGraphIndexer(vault_path)
        self.entity_gate = EntityTopicResolutionGate(self.indexer)
        self.formatter_gate = WikilinkFormatterGate()
        self.daily_builder = DailyJournalBuilderGate(vault_path)
        self.indexer.refresh_index()

    def process_academic_entry(
        self,
        raw_text: str,
        ai_data: Dict[str, Any],
        timestamp_dt: datetime,
        existing_journal_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Orchestrates entity resolution, wikilink formation, and daily journal markdown generation.
        """
        self.indexer.refresh_index()
        date_str = timestamp_dt.strftime("%Y-%m-%d")
        time_str = timestamp_dt.strftime("%H:%M")

        summary = ai_data.get("summary", raw_text)
        topics = ai_data.get("topics", [])
        entities = ai_data.get("entities", [])
        suggested = ai_data.get("suggested_links", [])
        what_i_learned = ai_data.get("what_i_learned", [])
        problems = ai_data.get("learning_gaps", [])
        assignments = ai_data.get("assignments", [])
        tasks = ai_data.get("tasks", [])
        decisions = ai_data.get("decisions", [])
        progress = ai_data.get("progress", [])

        # Combine tasks and assignments for Next Actions
        all_actions = list(dict.fromkeys(tasks + [f"Assignment: {a}" for a in assignments]))

        # Gate 2: Entity & Topic Resolution
        all_candidates = list(dict.fromkeys(topics + entities + suggested))
        resolved_entities = [self.entity_gate.resolve_topic(c) for c in all_candidates if c.strip()]

        # Gate 3: Wikilink Formatting
        connections = self.formatter_gate.format_wikilinks(resolved_entities)

        # Gate 4: Build or Merge into Daily Journal
        if existing_journal_content:
            journal_markdown = self.daily_builder.merge_into_existing_daily_journal(
                existing_content=existing_journal_content,
                time_str=time_str,
                raw_transcript=raw_text,
                summary=summary,
                what_i_learned=what_i_learned,
                connections=connections,
                progress=progress,
                problems=problems,
                decisions=decisions,
                next_actions=all_actions,
                sources=[]
            )
        else:
            journal_markdown = self.daily_builder.build_initial_daily_journal(
                date_str=date_str,
                time_str=time_str,
                raw_transcript=raw_text,
                summary=summary,
                what_i_learned=what_i_learned,
                connections=connections,
                progress=progress,
                problems=problems,
                decisions=decisions,
                next_actions=all_actions,
                sources=[]
            )

        return {
            "date_str": date_str,
            "filename": f"Journal-{date_str}.md",
            "journal_markdown": journal_markdown,
            "summary": summary,
            "connections": connections,
            "actions": all_actions,
            "problems": problems,
            "what_i_learned": what_i_learned,
            "resolved_entities": resolved_entities
        }

import os
import re
import difflib
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional
from datetime import datetime

class VaultGraphIndexer:
    """
    Gate 1: Scans and indexes all existing Markdown notes, aliases, and tags in the Obsidian vault.
    Builds an in-memory knowledge index for fast link resolution.
    """

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path) if vault_path else None
        self.note_titles: Dict[str, str] = {}  # lowercase_title -> original_title
        self.aliases: Dict[str, str] = {}      # lowercase_alias -> original_title
        self.all_tags: Set[str] = set()
        self.last_indexed: Optional[datetime] = None

    def refresh_index(self) -> None:
        """Scans the vault directory and builds the knowledge graph index."""
        if not self.vault_path or not self.vault_path.is_dir():
            return

        self.note_titles.clear()
        self.aliases.clear()
        self.all_tags.clear()

        for md_file in self.vault_path.rglob("*.md"):
            # Exclude hidden files / .obsidian
            if ".obsidian" in md_file.parts:
                continue

            orig_title = md_file.stem
            lower_title = orig_title.lower()
            self.note_titles[lower_title] = orig_title

            # Parse frontmatter for aliases and tags
            try:
                with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(2048)  # Read header chunk
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
            if line.startswith("aliases:"):
                raw_aliases = line.replace("aliases:", "").strip()
                if raw_aliases.startswith("[") and raw_aliases.endswith("]"):
                    items = [x.strip().strip("\"'") for x in raw_aliases[1:-1].split(",")]
                    for item in items:
                        if item:
                            self.aliases[item.lower()] = orig_title
            # Parse tags
            elif line.startswith("tags:"):
                raw_tags = line.replace("tags:", "").strip()
                if raw_tags.startswith("[") and raw_tags.endswith("]"):
                    items = [x.strip().strip("\"'#") for x in raw_tags[1:-1].split(",")]
                    self.all_tags.update(items)


class EntityTopicResolutionGate:
    """
    Gate 2: Resolves extracted candidate topics against existing vault notes.
    Applies exact matching, alias lookup, and Levenshtein fuzzy matching.
    """

    def __init__(self, indexer: VaultGraphIndexer):
        self.indexer = indexer

    def resolve_topic(self, topic: str) -> Dict[str, Any]:
        """
        Resolves a topic string into a structured link target.
        Returns: {
            "original": str,
            "target": str,
            "wikilink": str,
            "match_type": "exact" | "alias" | "fuzzy" | "new_topic"
        }
        """
        clean_topic = self._clean_filename(topic.strip())
        if not clean_topic:
            return {
                "original": topic,
                "target": topic,
                "wikilink": f"[[{topic}]]",
                "match_type": "new_topic"
            }

        lower = clean_topic.lower()

        # 1. Exact Match with existing note title
        if lower in self.indexer.note_titles:
            canonical = self.indexer.note_titles[lower]
            return {
                "original": topic,
                "target": canonical,
                "wikilink": f"[[{canonical}]]",
                "match_type": "exact"
            }

        # 2. Alias Match
        if lower in self.indexer.aliases:
            canonical = self.indexer.aliases[lower]
            return {
                "original": topic,
                "target": canonical,
                "wikilink": f"[[{canonical}|{clean_topic}]]",
                "match_type": "alias"
            }

        # 3. Fuzzy Match against existing notes (similarity >= 0.85)
        existing_keys = list(self.indexer.note_titles.keys())
        matches = difflib.get_close_matches(lower, existing_keys, n=1, cutoff=0.85)
        if matches:
            canonical = self.indexer.note_titles[matches[0]]
            return {
                "original": topic,
                "target": canonical,
                "wikilink": f"[[{canonical}|{clean_topic}]]",
                "match_type": "fuzzy"
            }

        # 4. New Concept Node
        return {
            "original": topic,
            "target": clean_topic,
            "wikilink": f"[[{clean_topic}]]",
            "match_type": "new_topic"
        }

    @staticmethod
    def _clean_filename(name: str) -> str:
        """Removes illegal Windows and Obsidian filename characters."""
        return re.sub(r'[\\/:*?"<>|]', '', name).strip()


class WikilinkFormatterGate:
    """
    Gate 3: Formats entities and keywords inside markdown content with Obsidian [[Wikilinks]].
    Avoids double-linking existing brackets.
    """

    @staticmethod
    def format_wikilinks_in_text(text: str, resolved_entities: List[Dict[str, Any]]) -> str:
        """Embeds [[Wikilinks]] into the summary text for mentioned concepts."""
        result = text
        for ent in resolved_entities:
            target = ent["target"]
            orig = ent["original"]
            wikilink = ent["wikilink"]
            
            # Avoid replacing if already inside [[ ... ]]
            pattern = re.compile(rf'(?<!\[\[)\b{re.escape(orig)}\b(?!\]\])', re.IGNORECASE)
            result = pattern.sub(wikilink, result, count=1)
        return result


class NoteRoutingAndInterlockGate:
    """
    Gate 4 & 5: Determines destination paths, formats Obsidian YAML frontmatter,
    embeds audio attachment references, and formats the Daily Note cross-link block.
    """

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path) if vault_path else None

    def build_markdown_document(
        self,
        entry_id: str,
        title: str,
        timestamp_dt: datetime,
        raw_transcript: str,
        summary: str,
        key_insights: List[str],
        action_items: List[str],
        resolved_entities: List[Dict[str, Any]],
        category: str,
        sentiment: str,
        audio_rel_path: Optional[str] = None
    ) -> str:
        """Constructs a production-grade Obsidian Markdown document with full frontmatter."""
        date_str = timestamp_dt.strftime("%Y-%m-%d")
        time_str = timestamp_dt.strftime("%H:%M:%S")

        # Tags
        tags = ["journal/voice", f"type/{category.lower()}"]
        if sentiment:
            tags.append(f"sentiment/{sentiment.lower()}")

        # Build wikilink list
        wikilinks_formatted = "\n".join([f"- {e['wikilink']}" for e in resolved_entities])
        if not wikilinks_formatted:
            wikilinks_formatted = "- _None detected_"

        # Build insights list
        insights_formatted = "\n".join([f"- {item}" for item in key_insights]) or "- _No specific insights recorded._"

        # Build action items
        action_formatted = "\n".join([f"- [ ] {item}" for item in action_items]) or "- _No active tasks identified._"

        # Audio player embed
        audio_embed = f"![[{audio_rel_path}]]" if audio_rel_path else "_No audio attachment_"

        doc = f"""---
id: "{entry_id}"
title: "{title}"
date: {date_str}
time: {time_str}
type: voice-journal
category: "{category}"
sentiment: "{sentiment}"
tags:
{chr(10).join(f'  - {t}' for t in tags)}
audio_file: "{audio_rel_path or ''}"
---

# 🎙️ {title}
> *Recorded on **{date_str}** at **{time_str}*** | [[Daily Notes/{date_str}|📅 Daily Note]]

---

## 🎧 Audio Recording
{audio_embed}

---

## 🧠 Synthesized Summary
{summary}

---

## 💡 Key Insights & Reflections
{insights_formatted}

---

## 🎯 Action Items & Next Steps
{action_formatted}

---

## 🔗 Knowledge Graph Connections
{wikilinks_formatted}

---

## 📝 Raw Voice Transcript
```text
{raw_transcript}
```
"""
        return doc


class LogicGatesEngine:
    """
    Master Controller orchestrating all 5 Python Logic Gates:
    1. Scan & Index Vault
    2. Match & Classify Entities
    3. Format Wikilinks
    4. Route Note & Build Document
    5. Daily Note Interlock
    """

    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.indexer = VaultGraphIndexer(vault_path)
        self.entity_gate = EntityTopicResolutionGate(self.indexer)
        self.formatter_gate = WikilinkFormatterGate()
        self.routing_gate = NoteRoutingAndInterlockGate(vault_path)
        self.indexer.refresh_index()

    def process_entry(
        self,
        ai_data: Dict[str, Any],
        entry_id: str,
        timestamp_dt: datetime,
        audio_rel_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs the full logic gate pipeline on an AI synthesis dictionary.
        Returns: {
            "title": str,
            "markdown_content": str,
            "resolved_entities": List[dict],
            "daily_note_entry": str
        }
        """
        title = ai_data.get("title", "Voice Thought")
        raw_transcript = ai_data.get("raw_transcript", "")
        summary = ai_data.get("summary", "")
        key_insights = ai_data.get("key_insights", [])
        action_items = ai_data.get("action_items", [])
        raw_entities = ai_data.get("entities_and_topics", [])
        category = ai_data.get("category", "Reflection")
        sentiment = ai_data.get("sentiment", "Focused")

        # Gate 1 & 2: Resolve topics against vault index
        resolved = [self.entity_gate.resolve_topic(t) for t in raw_entities if t.strip()]

        # Gate 3: Format wikilinks within summary
        linked_summary = self.formatter_gate.format_wikilinks_in_text(summary, resolved)

        # Gate 4: Assemble Markdown Document
        doc = self.routing_gate.build_markdown_document(
            entry_id=entry_id,
            title=title,
            timestamp_dt=timestamp_dt,
            raw_transcript=raw_transcript,
            summary=linked_summary,
            key_insights=key_insights,
            action_items=action_items,
            resolved_entities=resolved,
            category=category,
            sentiment=sentiment,
            audio_rel_path=audio_rel_path
        )

        # Gate 5: Build daily note interlock snippet
        time_str = timestamp_dt.strftime("%H:%M")
        daily_snippet = f"- **{time_str}** [[Journal/Voice/{timestamp_dt.strftime('%Y-%m-%d_%H%M%S')}|🎙️ {title}]]: {summary}\n"

        return {
            "title": title,
            "markdown_content": doc,
            "resolved_entities": resolved,
            "daily_note_snippet": daily_snippet,
            "category": category,
            "sentiment": sentiment
        }

"""
Tests for Quack Mapper Module.

Tests mapping from QuackAI format to CCv3 format.
Verifies all hard constraints:
- HTML greeting preservation (byte-level)
- attrs formatting as [Label: Value]
- constant=true lore entries with empty keys
- selective dynamic calculation
"""

import json
from pathlib import Path

import pytest

from app.core.quack_mapper import (
    format_attrs,
    extract_personality,
    extract_greetings,
    extract_tags,
    map_lorebook_entry,
    map_lorebook,
    map_quack_to_v3,
    map_quack_lorebook_only,
)
from app.core.card_models import CharacterCardV3, Lorebook


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "golden_files"


class TestFormatAttrs:
    """Tests for format_attrs function."""

    def test_format_attrs_basic(self):
        """Format basic attrs to [Label: Value]."""
        attrs = [
            {"label": "Name", "value": "TestChar", "isVisible": True},
            {"label": "Age", "value": "25", "isVisible": True},
        ]
        result = format_attrs(attrs)
        assert result == "[Name: TestChar]\n[Age: 25]"

    def test_format_attrs_visible_only(self):
        """Only include visible attrs when visible_only=True."""
        attrs = [
            {"label": "Name", "value": "TestChar", "isVisible": True},
            {"label": "Secret", "value": "Hidden", "isVisible": False},
        ]
        result = format_attrs(attrs, visible_only=True)
        assert "[Name: TestChar]" in result
        assert "[Secret: Hidden]" not in result

    def test_format_attrs_include_hidden(self):
        """Include hidden attrs when visible_only=False."""
        attrs = [
            {"label": "Name", "value": "TestChar", "isVisible": True},
            {"label": "Secret", "value": "Hidden", "isVisible": False},
        ]
        result = format_attrs(attrs, visible_only=False)
        assert "[Name: TestChar]" in result
        assert "[Secret: Hidden]" in result

    def test_format_attrs_empty_list(self):
        """Empty attrs list returns empty string."""
        result = format_attrs([])
        assert result == ""

    def test_format_attrs_missing_label_or_value(self):
        """Skip attrs with missing label or value."""
        attrs = [
            {"label": "Name", "value": "TestChar"},
            {"label": "", "value": "NoLabel"},
            {"label": "NoValue", "value": ""},
        ]
        result = format_attrs(attrs)
        assert result == "[Name: TestChar]"

    def test_format_attrs_default_visibility(self):
        """Attrs without isVisible default to visible."""
        attrs = [{"label": "Name", "value": "TestChar"}]
        result = format_attrs(attrs, visible_only=True)
        assert result == "[Name: TestChar]"


class TestExtractPersonality:
    """Tests for extract_personality function."""

    def test_extract_personality_found(self):
        """Extract personality from attrs."""
        attrs = [
            {"label": "Name", "value": "TestChar"},
            {"label": "Personality", "value": "Cheerful, optimistic"},
        ]
        result = extract_personality(attrs)
        assert result == "Cheerful, optimistic"

    def test_extract_personality_case_insensitive(self):
        """Personality extraction is case-insensitive."""
        attrs = [{"label": "PERSONALITY", "value": "Bold"}]
        result = extract_personality(attrs)
        assert result == "Bold"

    def test_extract_personality_not_found(self):
        """Return empty string if no personality attr."""
        attrs = [{"label": "Name", "value": "TestChar"}]
        result = extract_personality(attrs)
        assert result == ""


class TestExtractGreetings:
    """Tests for extract_greetings function."""

    def test_extract_greetings_from_alternate_greetings(self):
        """Extract from alternate_greetings field."""
        quack_info = {
            "firstMes": "Hello!",
            "alternate_greetings": ["<p>Hi there!</p>", "<div>Welcome!</div>"],
        }
        first_mes, alternates = extract_greetings(quack_info)
        assert first_mes == "Hello!"
        assert alternates == ["<p>Hi there!</p>", "<div>Welcome!</div>"]

    def test_extract_greetings_from_prologue(self):
        """Extract from prologue.greetings when alternate_greetings empty."""
        quack_info = {
            "prologue": {
                "greetings": [
                    {"key": "g1", "value": "<p>First greeting</p>"},
                    {"key": "g2", "value": "<p>Second greeting</p>"},
                ]
            }
        }
        first_mes, alternates = extract_greetings(quack_info)
        assert first_mes == "<p>First greeting</p>"
        assert alternates == ["<p>Second greeting</p>"]

    def test_extract_greetings_from_firstMes_fallback(self):
        """Fall back to firstMes when no other sources."""
        quack_info = {"firstMes": "<p>Hello!</p>"}
        first_mes, alternates = extract_greetings(quack_info)
        assert first_mes == "<p>Hello!</p>"
        assert alternates == []

    def test_extract_greetings_html_preserved(self):
        """HTML tags are preserved exactly (byte-level constraint)."""
        html_greeting = '<div class="greeting-container"><p>Hello! <span class="highlight">I\'m QuackTestChar!</span></p><p>Nice to meet you~ ♪</p></div>'
        quack_info = {"firstMes": html_greeting}
        first_mes, _ = extract_greetings(quack_info)
        assert first_mes == html_greeting


class TestExtractTags:
    """Tests for extract_tags function."""

    def test_extract_tags_from_tags_field(self):
        """Extract tags from tags field."""
        quack_info = {"tags": ["fantasy", "adventure"]}
        char = {}
        result = extract_tags(quack_info, char)
        assert "QuackAI" in result
        assert "fantasy" in result
        assert "adventure" in result

    def test_extract_tags_quackai_always_first(self):
        """QuackAI tag is always added and first."""
        quack_info = {"tags": ["fantasy"]}
        char = {}
        result = extract_tags(quack_info, char)
        assert result[0] == "QuackAI"

    def test_extract_tags_quackai_not_duplicated(self):
        """QuackAI tag is not duplicated if already present."""
        quack_info = {"tags": ["QuackAI", "fantasy"]}
        char = {}
        result = extract_tags(quack_info, char)
        assert result.count("QuackAI") == 1

    def test_extract_tags_empty_uses_image_tags(self):
        """Extract from generateImage.allTags if tags empty."""
        quack_info = {"tags": []}
        char = {
            "generateImage": {
                "allTags": [
                    {"label": "anime"},
                    {"label": "fantasy"},
                ]
            }
        }
        result = extract_tags(quack_info, char)
        assert "QuackAI" in result
        assert "anime" in result


class TestMapLorebookEntry:
    """Tests for map_lorebook_entry function."""

    def test_map_basic_entry(self):
        """Map basic lorebook entry."""
        entry = {
            "name": "Background",
            "keywords": ["history", "background"],
            "content": "This is the background story.",
            "constant": False,
        }
        result = map_lorebook_entry(entry, 0)
        assert result.name == "Background"
        assert result.keys == ["history", "background"]
        assert result.content == "This is the background story."
        assert result.constant is False
        assert result.selective is False

    def test_map_entry_constant_empty_keys(self):
        """HARD CONSTRAINT: constant=true entries can have empty keys."""
        entry = {
            "name": "Always Active",
            "keywords": [],
            "content": "Always active content.",
            "constant": True,
        }
        result = map_lorebook_entry(entry, 0)
        assert result.keys == []
        assert result.constant is True

    def test_map_entry_empty_keys_fallback_to_name(self):
        """Empty keys fallback to name when NOT constant."""
        entry = {
            "name": "Some Entry",
            "keywords": [],
            "content": "Content here.",
            "constant": False,
        }
        result = map_lorebook_entry(entry, 0)
        assert result.keys == ["Some Entry"]

    def test_map_entry_selective_with_secondary_keys(self):
        """HARD CONSTRAINT: selective=True only when secondary_keys exist."""
        entry = {
            "name": "Entry",
            "keywords": ["trigger"],
            "content": "Content",
            "constant": False,
            "secondaryKeys": ["secondary"],
        }
        result = map_lorebook_entry(entry, 0)
        assert result.selective is True
        assert result.secondary_keys == ["secondary"]

    def test_map_entry_selective_without_secondary_keys(self):
        """selective=False when no secondary_keys."""
        entry = {
            "name": "Entry",
            "keywords": ["trigger"],
            "content": "Content",
            "constant": False,
        }
        result = map_lorebook_entry(entry, 0)
        assert result.selective is False
        assert result.secondary_keys == []

    def test_map_entry_position_before_char(self):
        """position=0 maps to 'before_char'."""
        entry = {"name": "Entry", "keywords": ["k"], "content": "c", "position": 0}
        result = map_lorebook_entry(entry, 0)
        assert result.position == "before_char"

    def test_map_entry_position_after_char(self):
        """position=1 maps to 'after_char'."""
        entry = {"name": "Entry", "keywords": ["k"], "content": "c", "position": 1}
        result = map_lorebook_entry(entry, 0)
        assert result.position == "after_char"

    def test_map_entry_extensions_preserved(self):
        """Quack-specific fields preserved in extensions."""
        entry = {
            "name": "Entry",
            "keywords": ["k"],
            "content": "c",
            "matchWholeWords": True,
            "scanDepth": 100,
            "depth": 4,
            "role": 1,
        }
        result = map_lorebook_entry(entry, 0)
        assert result.extensions.get("match_whole_words") is True
        assert result.extensions.get("scan_depth") == 100
        assert result.extensions.get("depth") == 4
        assert result.extensions.get("role") == 1


class TestMapLorebook:
    """Tests for map_lorebook function."""

    def test_map_lorebook_basic(self):
        """Map basic lorebook."""
        entries = [
            {"name": "Entry 1", "keywords": ["k1"], "content": "c1"},
            {"name": "Entry 2", "keywords": ["k2"], "content": "c2"},
        ]
        result = map_lorebook(entries, "Test Book")
        assert isinstance(result, Lorebook)
        assert result.name == "Test Book"
        assert len(result.entries) == 2

    def test_map_lorebook_empty(self):
        """Map empty lorebook."""
        result = map_lorebook([])
        assert len(result.entries) == 0


class TestMapQuackToV3:
    """Tests for map_quack_to_v3 function (main mapping)."""

    def test_map_quack_to_v3_basic(self):
        """Map basic Quack data to V3."""
        quack_info = {
            "name": "TestChar",
            "intro": "A test character",
            "charList": [
                {
                    "name": "TestChar",
                    "attrs": [
                        {"label": "Name", "value": "TestChar", "isVisible": True},
                        {"label": "Age", "value": "25", "isVisible": True},
                    ],
                }
            ],
            "firstMes": "Hello!",
            "tags": ["test"],
            "authorName": "TestAuthor",
        }
        result = map_quack_to_v3(quack_info)
        
        assert isinstance(result, CharacterCardV3)
        assert result.spec == "chara_card_v3"
        assert result.spec_version == "3.0"
        assert result.data.name == "TestChar"
        assert result.data.first_mes == "Hello!"
        assert "QuackAI" in result.data.tags
        assert result.data.creator == "TestAuthor"

    def test_map_quack_to_v3_description_with_attrs(self):
        """Description includes formatted attrs."""
        quack_info = {
            "intro": "Character intro.",
            "charList": [
                {
                    "name": "Char",
                    "attrs": [
                        {"label": "Gender", "value": "Female", "isVisible": True},
                    ],
                }
            ],
        }
        result = map_quack_to_v3(quack_info)
        
        assert "Character intro." in result.data.description
        assert "[Gender: Female]" in result.data.description

    def test_map_quack_to_v3_html_greeting_preserved(self):
        """HARD CONSTRAINT: HTML greeting preserved byte-level."""
        html_greeting = '<div class="greeting-container"><p>Hello! <span class="highlight">Test!</span></p></div>'
        quack_info = {
            "charList": [{"name": "Char"}],
            "firstMes": html_greeting,
        }
        result = map_quack_to_v3(quack_info)
        
        assert result.data.first_mes == html_greeting

    def test_map_quack_to_v3_with_lorebook(self):
        """Map Quack data with lorebook."""
        quack_info = {
            "charList": [{"name": "Char"}],
            "firstMes": "Hello!",
        }
        lorebook_entries = [
            {"name": "Entry 1", "keywords": ["k1"], "content": "c1", "constant": False},
            {"name": "Entry 2", "keywords": [], "content": "c2", "constant": True},
        ]
        result = map_quack_to_v3(quack_info, lorebook_entries)
        
        assert result.data.character_book is not None
        assert len(result.data.character_book.entries) == 2
        # Verify constant entry with empty keys is preserved
        constant_entry = result.data.character_book.entries[1]
        assert constant_entry.constant is True
        assert constant_entry.keys == []

    def test_map_quack_to_v3_assets_default(self):
        """Default assets include icon."""
        quack_info = {"charList": [{"name": "Char"}]}
        result = map_quack_to_v3(quack_info)
        
        assert result.data.assets is not None
        assert len(result.data.assets) == 1
        assert result.data.assets[0].type == "icon"
        assert result.data.assets[0].uri == "ccdefault:"

    def test_map_quack_to_v3_personality_extracted(self):
        """Personality extracted from attrs."""
        quack_info = {
            "charList": [
                {
                    "name": "Char",
                    "attrs": [
                        {"label": "Personality", "value": "Brave and kind", "isVisible": True}
                    ],
                }
            ],
        }
        result = map_quack_to_v3(quack_info)
        
        assert result.data.personality == "Brave and kind"


class TestMapQuackToV3GoldenFile:
    """Tests using golden files."""

    def test_map_quack_export_json(self):
        """Map quack_export.json golden file."""
        quack_file = FIXTURES_DIR / "quack_export.json"
        if not quack_file.exists():
            pytest.skip("Golden file not found")
        
        quack_info = json.loads(quack_file.read_text())
        result = map_quack_to_v3(quack_info)
        
        assert result.data.name == "QuackTestChar"
        assert "QuackAI" in result.data.tags
        # Verify HTML preserved
        assert '<div class="greeting-container">' in result.data.first_mes
        assert '<span class="highlight">' in result.data.first_mes

    def test_map_quack_lorebook_json(self):
        """Map quack_lorebook.json golden file."""
        lorebook_file = FIXTURES_DIR / "quack_lorebook.json"
        if not lorebook_file.exists():
            pytest.skip("Golden file not found")
        
        lorebook_data = json.loads(lorebook_file.read_text())
        entries = []
        for item in lorebook_data.get("data", []):
            entries.extend(item.get("entryList", []))
        
        result = map_quack_lorebook_only(entries)
        
        assert isinstance(result, Lorebook)
        assert len(result.entries) == 3
        
        # Verify constant entry with empty keys
        constant_entry = next(e for e in result.entries if e.name == "Always Active Lore")
        assert constant_entry.constant is True
        assert constant_entry.keys == []


class TestMapQuackToV3IntegrationWithLorebook:
    """Integration tests for full Quack to V3 mapping with lorebook."""

    def test_map_with_golden_files_combined(self):
        """Map quack_export.json with quack_lorebook.json."""
        quack_file = FIXTURES_DIR / "quack_export.json"
        lorebook_file = FIXTURES_DIR / "quack_lorebook.json"
        
        if not quack_file.exists() or not lorebook_file.exists():
            pytest.skip("Golden files not found")
        
        quack_info = json.loads(quack_file.read_text())
        lorebook_data = json.loads(lorebook_file.read_text())
        
        entries = []
        for item in lorebook_data.get("data", []):
            entries.extend(item.get("entryList", []))
        
        result = map_quack_to_v3(quack_info, entries)
        
        # Verify character
        assert result.data.name == "QuackTestChar"
        
        # Verify lorebook
        assert result.data.character_book is not None
        assert len(result.data.character_book.entries) == 3
        
        # Verify HTML greeting preserved
        assert '<div class="greeting-container">' in result.data.first_mes
        
        # Verify attrs formatted
        assert "[Name: QuackTestChar]" in result.data.description
        assert "[Gender: Female]" in result.data.description

    def test_selective_logic(self):
        """Test selective field is correctly calculated."""
        entries = [
            {
                "name": "No Secondary",
                "keywords": ["trigger"],
                "content": "Content",
            },
            {
                "name": "With Secondary",
                "keywords": ["trigger"],
                "content": "Content",
                "secondaryKeys": ["secondary1", "secondary2"],
            },
        ]
        
        result = map_lorebook(entries)
        
        assert result.entries[0].selective is False
        assert result.entries[0].secondary_keys == []
        assert result.entries[1].selective is True
        assert result.entries[1].secondary_keys == ["secondary1", "secondary2"]

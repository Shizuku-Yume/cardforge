"""
Quack to Character Card V3 Mapper Module

Converts QuackAI character data to SillyTavern CCv3 format.
Handles strict preservation requirements:
- HTML greeting preservation (byte-level)
- attrs formatting as [Label: Value]
- constant=true lore entries with empty keys
- selective dynamic calculation based on secondary_keys
"""

import time
from typing import Any, Dict, List, Optional

from .card_models import (
    Asset,
    CharacterCardData,
    CharacterCardV3,
    Lorebook,
    LorebookEntry,
)


def format_attrs(attrs: List[Dict[str, Any]], visible_only: bool = True) -> str:
    """
    Format Quack attrs to [Label: Value] format.
    
    This is a HARD CONSTRAINT - attrs MUST be formatted exactly as [Label: Value].
    
    Args:
        attrs: List of attr dicts with 'label', 'value', and optionally 'isVisible'
        visible_only: If True, only include visible attrs
        
    Returns:
        Formatted string with each attr on a new line
    """
    lines = []
    for attr in attrs:
        if visible_only and not attr.get("isVisible", True):
            continue
        
        label = attr.get("label", "")
        value = attr.get("value", "")
        
        if label and value:
            lines.append(f"[{label}: {value}]")
    
    return "\n".join(lines)


def extract_personality(attrs: List[Dict[str, Any]]) -> str:
    """
    Extract personality from attrs.
    
    Args:
        attrs: List of attr dicts
        
    Returns:
        Personality value or empty string
    """
    for attr in attrs:
        label = attr.get("label", "").lower()
        if label == "personality":
            return attr.get("value", "")
    return ""


def extract_greetings(quack_info: Dict[str, Any]) -> tuple[str, List[str]]:
    """
    Extract first_mes and alternate_greetings from Quack data.
    
    HARD CONSTRAINT: HTML must be preserved byte-level.
    
    Priority:
    1. alternate_greetings field (already extracted)
    2. prologue.greetings array
    3. firstMes field
    
    Args:
        quack_info: Quack character info dict
        
    Returns:
        Tuple of (first_mes, alternate_greetings)
    """
    # Check if alternate_greetings is already provided
    alt_greetings = quack_info.get("alternate_greetings", [])
    first_mes = quack_info.get("firstMes", "")
    
    if alt_greetings and isinstance(alt_greetings, list):
        # Use firstMes as the main greeting, alternate_greetings as alternatives
        return first_mes, alt_greetings
    
    # Extract from prologue.greetings
    prologue = quack_info.get("prologue", {}) or {}
    prologue_greetings = prologue.get("greetings", []) or []
    
    if prologue_greetings and isinstance(prologue_greetings, list):
        greetings_values = []
        for g in prologue_greetings:
            if isinstance(g, dict):
                # Preserve HTML exactly as-is
                greetings_values.append(g.get("value", ""))
            elif isinstance(g, str):
                greetings_values.append(g)
        
        if greetings_values:
            # First greeting becomes first_mes, rest become alternates
            if not first_mes:
                first_mes = greetings_values[0]
                return first_mes, greetings_values[1:]
            else:
                return first_mes, greetings_values
    
    return first_mes, []


def extract_tags(quack_info: Dict[str, Any], char: Dict[str, Any]) -> List[str]:
    """
    Extract tags from Quack data.
    
    Args:
        quack_info: Quack character info dict
        char: Character data from charList[0]
        
    Returns:
        List of tags (always includes 'QuackAI')
    """
    tags = quack_info.get("tags", []) or []
    
    if not tags:
        # Try to extract from generateImage.allTags
        image_tags = char.get("generateImage", {}).get("allTags", [])
        tags = [t.get("label", t.get("value", "")) for t in image_tags if isinstance(t, dict)]
    
    # Ensure we have a list of strings
    tags = [str(t) for t in tags if t]
    
    # Force include QuackAI tag
    if "QuackAI" not in tags:
        tags.insert(0, "QuackAI")
    
    return tags


def map_lorebook_entry(entry: Dict[str, Any], index: int) -> LorebookEntry:
    """
    Map a single Quack lorebook entry to CCv3 LorebookEntry.
    
    HARD CONSTRAINTS:
    - constant=true entries can have empty keys (must not be dropped)
    - selective is dynamically calculated based on secondary_keys presence
    
    Args:
        entry: Quack lorebook entry dict
        index: Entry index for insertion_order and id
        
    Returns:
        LorebookEntry model
    """
    # Extract keys (may be 'keywords' or 'triggerKeywords')
    keys = entry.get("keywords", entry.get("triggerKeywords", []))
    if not isinstance(keys, list):
        keys = [keys] if keys else []
    
    # Ensure all keys are strings
    keys = [str(k) for k in keys if k is not None]
    
    # Check constant flag
    constant = entry.get("constant", False)
    
    # HARD CONSTRAINT: If keys are empty and NOT constant, fall back to name
    if not keys and not constant:
        name = entry.get("name", "")
        if name:
            keys = [name]
    
    # HARD CONSTRAINT: constant=true entries can have empty keys - DO NOT DROP
    
    # Extract secondary keys
    secondary_keys = entry.get("secondaryKeys", entry.get("secondary_keys", []))
    if not isinstance(secondary_keys, list):
        secondary_keys = [secondary_keys] if secondary_keys else []
    secondary_keys = [str(k) for k in secondary_keys if k is not None]
    
    # HARD CONSTRAINT: selective is True ONLY when secondary_keys exist
    selective = len(secondary_keys) > 0
    
    # Map position (0 = before_char, 1 = after_char)
    position_val = entry.get("position", 0)
    position = "after_char" if position_val == 1 else "before_char"
    
    # Build extensions with Quack-specific metadata
    extensions = {}
    if "matchWholeWords" in entry:
        extensions["match_whole_words"] = entry.get("matchWholeWords", False)
    if "scanDepth" in entry:
        extensions["scan_depth"] = entry.get("scanDepth", 50)
    if entry.get("depth"):
        extensions["depth"] = entry.get("depth")
    if entry.get("role"):
        extensions["role"] = entry.get("role")
    
    return LorebookEntry(
        keys=keys,
        content=entry.get("content", ""),
        extensions=extensions,
        enabled=entry.get("enabled", True),
        insertion_order=index + 1,
        case_sensitive=False,
        use_regex=False,
        constant=constant,
        name=entry.get("name", ""),
        priority=10,
        id=index + 1,
        selective=selective,
        secondary_keys=secondary_keys,
        position=position,
    )


def map_lorebook(entries: List[Dict[str, Any]], book_name: str = "Quack Lore") -> Lorebook:
    """
    Map Quack lorebook entries to CCv3 Lorebook.
    
    Args:
        entries: List of Quack lorebook entries
        book_name: Name for the world book
        
    Returns:
        Lorebook model
    """
    mapped_entries = [
        map_lorebook_entry(entry, i) for i, entry in enumerate(entries)
    ]
    
    return Lorebook(
        name=book_name,
        description="",
        scan_depth=50,
        token_budget=500,
        recursive_scanning=False,
        extensions={},
        entries=mapped_entries,
    )


def map_quack_to_v3(
    quack_info: Dict[str, Any],
    lorebook_entries: Optional[List[Dict[str, Any]]] = None,
) -> CharacterCardV3:
    """
    Convert Quack character data to CCv3 format.
    
    This is the main mapping function that enforces all hard constraints:
    - HTML greeting preservation (byte-level)
    - attrs formatted as [Label: Value]
    - constant=true lore entries preserved even with empty keys
    - selective dynamically calculated from secondary_keys
    
    Args:
        quack_info: Quack character info dict (pure Dict input, decoupled from HTTP client)
        lorebook_entries: Optional list of world book entries
        
    Returns:
        CharacterCardV3 model
    """
    # Extract character from charList (usually index 0)
    char_list = quack_info.get("charList", [])
    char = char_list[0] if char_list else {}
    
    # Get character name
    name = char.get("name", quack_info.get("name", "Unknown"))
    
    # Extract attrs
    attrs = char.get("attrs", []) or []
    advise_attrs = char.get("adviseAttrs", []) or []
    custom_attrs = char.get("customAttrs", []) or []
    all_attrs = attrs + advise_attrs + custom_attrs
    
    # Build description: intro + formatted attrs
    intro = quack_info.get("intro", char.get("intro", ""))
    attr_block = format_attrs(all_attrs, visible_only=True)
    
    if attr_block:
        description = f"{intro}\n\n{attr_block}" if intro else attr_block
    else:
        description = intro
    
    # Extract personality from attrs
    personality = extract_personality(all_attrs)
    
    # Extract greetings (HTML preserved exactly)
    first_mes, alternate_greetings = extract_greetings(quack_info)
    
    # Extract tags
    tags = extract_tags(quack_info, char)
    
    # Build lorebook
    character_book = None
    if lorebook_entries:
        character_book = map_lorebook(lorebook_entries)
    elif quack_info.get("characterbooks"):
        # Handle inline characterbooks
        books = quack_info.get("characterbooks")
        if isinstance(books, list) and books:
            all_entries = []
            for book in books:
                if isinstance(book, dict) and "entryList" in book:
                    all_entries.extend(book.get("entryList", []))
            if all_entries:
                character_book = map_lorebook(all_entries)
    
    # Get creator info
    creator = quack_info.get("authorName", quack_info.get("author", ""))
    creator_notes = quack_info.get("charCreatorNotes", "")
    
    # Build timestamp
    current_time = int(time.time())
    
    # Build assets
    assets = [
        Asset(
            type="icon",
            uri="ccdefault:",
            name="main",
            ext="png",
        )
    ]
    
    # Build CharacterCardData
    card_data = CharacterCardData(
        name=name,
        description=description,
        personality=personality,
        scenario="",
        first_mes=first_mes,
        mes_example="",
        creator_notes=creator_notes,
        system_prompt="",
        post_history_instructions="",
        alternate_greetings=alternate_greetings,
        tags=tags,
        creator=creator,
        character_version="1.0",
        extensions={},
        character_book=character_book,
        group_only_greetings=[],
        assets=assets,
        creation_date=current_time,
        modification_date=current_time,
    )
    
    return CharacterCardV3(
        spec="chara_card_v3",
        spec_version="3.0",
        data=card_data,
    )


def map_quack_lorebook_only(
    lorebook_entries: List[Dict[str, Any]],
    book_name: str = "Quack Lore",
) -> Lorebook:
    """
    Map only the lorebook entries without full character conversion.
    
    Useful for "only_lorebook" mode where user just wants the world book.
    
    Args:
        lorebook_entries: List of Quack lorebook entries
        book_name: Name for the world book
        
    Returns:
        Lorebook model
    """
    return map_lorebook(lorebook_entries, book_name)


__all__ = [
    "format_attrs",
    "extract_personality",
    "extract_greetings",
    "extract_tags",
    "map_lorebook_entry",
    "map_lorebook",
    "map_quack_to_v3",
    "map_quack_lorebook_only",
]

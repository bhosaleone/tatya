"""Indic linguistic utilities, script detection, and boundary matching.

Solves the Brahmic combining mark trap where Python's standard `\\b` matches
inside words like 'नमस्कार' or 'தமிழ்' because dependent vowel signs (matras,
pulli, virama) are classified as non-word characters.
"""

import re
import unicodedata
from typing import Optional

# Unicode ranges for the 10 target Indic scripts + Latin
SCRIPT_RANGES: dict[str, tuple[int, int]] = {
    "devanagari": (0x0900, 0x097F),
    "bengali": (0x0980, 0x09FF),
    "gurmukhi": (0x0A00, 0x0A7F),
    "gujarati": (0x0A80, 0x0AFF),
    "oriya": (0x0B00, 0x0B7F),
    "tamil": (0x0B80, 0x0BFF),
    "telugu": (0x0C00, 0x0C7F),
    "kannada": (0x0C80, 0x0CFF),
    "malayalam": (0x0D00, 0x0D7F),
    "latin": (0x0020, 0x024F),
}

# All Indic combining marks and letter codepoints for boundary matching
INDIC_CHAR_PATTERN = r"[\w\u0900-\u0D7F]"

# Devanagari transliteration mapping to consonant skeleton
DEVANAGARI_TO_LATIN = {
    "क": "k", "ख": "k", "ग": "g", "घ": "g", "ङ": "n",
    "च": "c", "छ": "c", "ज": "j", "झ": "j", "ञ": "n",
    "ट": "t", "ठ": "t", "ड": "d", "ढ": "d", "ण": "n",
    "त": "t", "थ": "t", "द": "d", "ध": "d", "न": "n",
    "प": "p", "फ": "p", "ब": "b", "भ": "b", "म": "m",
    "य": "y", "र": "r", "ऱ": "r", "ल": "l", "व": "v", "श": "s",
    "ष": "s", "स": "s", "ह": "h", "ळ": "l", "क्ष": "k",
    "ज्ञ": "j",
}


def char_script(ch: str) -> Optional[str]:
    """Returns script name for a single character."""
    code = ord(ch)
    for script, (start, end) in SCRIPT_RANGES.items():
        if start <= code <= end:
            return script
    return None


def script_of(text: str) -> str:
    """Classifies the overall script of a string.

    Returns: 'devanagari', 'tamil', 'telugu', 'latin', 'mixed', or 'other'.
    """
    counts: dict[str, int] = {}
    for ch in text:
        if ch.isspace() or unicodedata.category(ch).startswith("P"):
            continue
        s = char_script(ch)
        if s:
            counts[s] = counts.get(s, 0) + 1

    if not counts:
        return "other"

    total = sum(counts.values())
    sorted_scripts = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    top_script, top_count = sorted_scripts[0]

    # If top script has >= 85% of letters, consider it dominant
    if top_count / total >= 0.85:
        return top_script

    # Otherwise if multiple scripts have significant presence, it's mixed
    return "mixed"


def primary_script_ratio(text: str) -> float:
    """Returns the fraction of characters belonging to the dominant script."""
    counts: dict[str, int] = {}
    for ch in text:
        if not ch.isspace() and not unicodedata.category(ch).startswith("P"):
            s = char_script(ch)
            if s:
                counts[s] = counts.get(s, 0) + 1
    if not counts:
        return 0.0
    return max(counts.values()) / sum(counts.values())


def fold(text: str) -> str:
    """Normalizes text with Unicode NFC, lowercase, and zero-width strip."""
    normalized = unicodedata.normalize("NFC", text.strip().lower())
    # Strip Zero-Width Non-Joiner (ZWNJ U+200C) and Zero-Width Joiner (ZWJ U+200D)
    normalized = normalized.replace("\u200c", "").replace("\u200d", "")
    return re.sub(r"\s+", " ", normalized)


def dedup_key(text: str) -> str:
    """Case, whitespace, and punctuation-folded key used for query deduplication.

    Does NOT strip vowels, preserving distinct alphabet expansions.
    """
    folded = fold(text)
    # Remove standard punctuation symbols but keep script letters and numbers
    return re.sub(r"[^\w\u0900-\u0D7F]+", "", folded)


def word_boundary_regex(term: str) -> re.Pattern:
    """Builds a regex pattern for term that respects Brahmic combining marks.

    Standard '\\b' fails because matras count as non-word boundaries.
    This pattern ensures the match is neither preceded nor followed by an Indic char or \\w.
    """
    escaped = re.escape(term)
    prefix = rf"(?<!{INDIC_CHAR_PATTERN})"
    suffix = rf"(?!{INDIC_CHAR_PATTERN})"
    return re.compile(f"{prefix}{escaped}{suffix}", re.IGNORECASE | re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Tokenizes Indic/Latin text without severing combining marks."""
    clean = fold(text)
    pattern = rf"{INDIC_CHAR_PATTERN}+"
    return re.findall(pattern, clean, re.UNICODE)


def sibling_key(text: str) -> str:
    """Exact transliteration key mapping Devanagari to Latin representation."""
    folded = fold(text)
    res = []
    for ch in folded:
        if ch in DEVANAGARI_TO_LATIN:
            res.append(DEVANAGARI_TO_LATIN[ch])
        elif ord(ch) < 128 and ch.isalnum():
            res.append(ch)
    return "".join(res)


def topic_key(text: str) -> str:
    """Extracts a lossy consonant skeleton to group cross-script topics.

    Example: 'मराठी शेती' and 'marathi sheti' both reduce to 'mrtst'.
    Used exclusively for topic clustering and competition fallback lookup.
    Never used for query expansion de-duplication (MATH.md §3.1).
    """
    key = sibling_key(text)
    # Strip vowels, aspirate 'h', and collapsed duplicated consonants
    consonants = re.sub(r"[aeiouh]", "", key)
    # Collapse double consonants: e.g. 'kk' -> 'k'
    collapsed = re.sub(r"(.)\1+", r"\1", consonants)
    # If the key is too short (< 4 consonants), fall back to sibling_key to prevent over-clustering
    if len(collapsed) < 4:
        return key if len(key) >= 2 else dedup_key(text)
    return collapsed

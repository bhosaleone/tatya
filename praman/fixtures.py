"""Deterministic synthetic fixture generator for offline testing.

Ensures pipeline and parser exercise realistic shapes (including cross-script
suggestions and question templates) without connecting to the network.
Fixture data is never presented as a real finding.
"""

import hashlib
from typing import Sequence

from praman.languages import get_language_spec


def _stable_hash(s: str) -> int:
    """Returns a stable 64-bit integer hash from a string across Python processes."""
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:16], 16)


def generate_fixture_suggestions(query: str, language_code: str = "mr") -> list[str]:
    """Deterministically generates synthetic autocomplete suggestions based on query hash."""
    clean_q = query.strip()
    if not clean_q:
        return []

    spec = get_language_spec(language_code)
    h = _stable_hash(f"{language_code}:{clean_q}")

    # 10% chance of measured absence (empty list), representing queries with no demand
    if (h % 10) == 0 and len(clean_q.split()) > 2:
        return []

    # Number of suggestions between 3 and 10
    count = 3 + (h % 8)

    results: list[str] = []

    # First suggestion is usually the exact query itself (simulating Google's echo / depth 1.0)
    results.append(clean_q)

    # Subsequent suggestions add suffixes, modifiers, or transliterations
    modifiers = [m[0] for m in spec.modifier_templates]
    questions = [q.replace("{t}", "").strip() for q in spec.question_templates]

    candidates = [
        f"{clean_q} {modifiers[h % len(modifiers)]}",
        f"{clean_q} {modifiers[(h + 1) % len(modifiers)]}",
        f"{clean_q} {questions[h % len(questions)]}",
        f"{clean_q} 2026",
        f"{clean_q} pdf",
        f"{clean_q} online",
        f"{clean_q} माहिती",
        f"{clean_q} app",
        f"{clean_q} news",
        f"{clean_q} list",
    ]

    for item in candidates:
        if len(results) >= count:
            break
        if item not in results:
            results.append(item)

    return results

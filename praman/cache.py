"""Content-addressed, language-partitioned response cache.

Invariants:
- Cache MUST be partitioned by (language, region) to prevent cross-language collisions.
- Retrieved entry MUST verify that stored query matches requested query.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

from praman.autocomplete import AutocompleteResult
from praman.script import fold

logger = logging.getLogger("praman.cache")


class AutocompleteCache:
    """Stores and retrieves AutocompleteResult objects partitioned by language/region."""

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)

    def _partition_dir(self, language: str, region: str) -> Path:
        p = self.root_dir / f"{language.lower()}_{region.lower()}"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _file_path(self, query: str, language: str, region: str) -> Path:
        normalized = fold(query)
        q_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
        return self._partition_dir(language, region) / f"{q_hash}.json"

    def get(self, query: str, language: str, region: str) -> Optional[AutocompleteResult]:
        file_path = self._file_path(query, language, region)
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Defensive verification: query in cache file MUST match requested query
            if fold(data.get("query", "")) != fold(query):
                logger.warning(
                    "Cache entry mismatch: file '%s' has query '%s', expected '%s'. Ignoring.",
                    file_path.name,
                    data.get("query"),
                    query,
                )
                return None

            return AutocompleteResult(
                query=data["query"],
                suggestions=tuple(data.get("suggestions", ())),
                measured=bool(data.get("measured", True)),
                source="cache",
                error=data.get("error"),
                echoed_query=data.get("echoed_query"),
            )
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            logger.warning("Failed to read cache file %s: %s", file_path, exc)
            return None

    def set(self, result: AutocompleteResult, language: str, region: str) -> None:
        file_path = self._file_path(result.query, language, region)
        payload = {
            "query": result.query,
            "language": language,
            "region": region,
            "suggestions": list(result.suggestions),
            "measured": result.measured,
            "source": result.source,
            "error": result.error,
            "echoed_query": result.echoed_query,
        }
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.warning("Failed to write cache file %s: %s", file_path, exc)

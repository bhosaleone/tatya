"""Human-observed SERP competition tracking and tri-state observation parser.

Follows the strict discipline of NO_API.md & METHODOLOGY.md §7:
- No SERP scraping.
- Blank cells parse to None (unrecorded), NEVER False.
- Competition band requires at least 2 recorded observations.
- Carries weight 0 in demand blend.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from praman.script import dedup_key, topic_key

CSV_HEADER = ["keyword", "top_results_stale", "thin_results", "weak_domains", "own_sites_ranking", "notes"]

TRUE_TOKENS = {"y", "yes", "true", "1", "होय", "हाँ", "ஆம்", "అవును", "হ্যাঁ"}
FALSE_TOKENS = {"n", "no", "false", "0", "नाही", "नहीं", "இல்லை", "కాదు", "না"}


@dataclass(frozen=True)
class SerpObservation:
    keyword: str
    top_results_stale: Optional[bool]
    thin_results: Optional[bool]
    weak_domains: Optional[bool]
    own_sites_ranking: Optional[bool]
    notes: str
    band: Optional[str]                     # 'low', 'medium', 'high', 'very_high', or None
    recorded_count: int


def _parse_tristate(val: Optional[str]) -> Optional[bool]:
    """Parses a CSV cell value to True, False, or None (blank)."""
    if val is None:
        return None
    cleaned = val.strip().lower()
    if not cleaned:
        return None
    if cleaned in TRUE_TOKENS:
        return True
    if cleaned in FALSE_TOKENS:
        return False
    raise ValueError(f"Unrecognized boolean value in SERP observation: '{val}'")


def derive_competition_band(
    thin: Optional[bool],
    weak: Optional[bool],
    stale: Optional[bool],
) -> tuple[Optional[str], int]:
    """Derives a competition band if >= 2 fields are recorded (METHODOLOGY.md §7).

    Returns (band, recorded_count).
    """
    fields = [thin, weak, stale]
    recorded_count = sum(1 for f in fields if f is not None)

    if recorded_count < 2:
        return (None, recorded_count)

    if weak is True:
        return ("low" if thin is True else "medium", recorded_count)

    if weak is False:
        return ("very_high" if thin is False else "high", recorded_count)

    # weak is None (unknown), but thin and stale are recorded
    if thin is True and stale is True:
        return ("medium", recorded_count)
    if thin is False and stale is False:
        return ("high", recorded_count)
    return ("medium", recorded_count)


def write_observation_template(
    seeds: Sequence[str],
    out_path: Path,
    overwrite: bool = False,
) -> None:
    """Writes an empty observation template CSV for human evaluation."""
    target = Path(out_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Observation file '{target}' already exists. Refusing to overwrite.")

    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for seed in seeds:
            writer.writerow([seed, "", "", "", "", ""])


class CompetitionIndex:
    """Index of human SERP observations with exact-key and topic-key lookup."""

    def __init__(self, observations: Sequence[SerpObservation]):
        self._exact_map: dict[str, SerpObservation] = {}
        self._topic_map: dict[str, SerpObservation] = {}

        for obs in observations:
            e_key = dedup_key(obs.keyword)
            t_key = topic_key(obs.keyword)
            self._exact_map[e_key] = obs
            if t_key not in self._topic_map:
                self._topic_map[t_key] = obs

    @classmethod
    def from_csv(cls, path: Path) -> "CompetitionIndex":
        observations: list[SerpObservation] = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                kw = row.get("keyword", "").strip()
                if not kw:
                    continue
                thin = _parse_tristate(row.get("thin_results"))
                weak = _parse_tristate(row.get("weak_domains"))
                stale = _parse_tristate(row.get("top_results_stale"))
                own = _parse_tristate(row.get("own_sites_ranking"))
                notes = row.get("notes", "").strip()

                band, count = derive_competition_band(thin, weak, stale)
                observations.append(
                    SerpObservation(
                        keyword=kw,
                        top_results_stale=stale,
                        thin_results=thin,
                        weak_domains=weak,
                        own_sites_ranking=own,
                        notes=notes,
                        band=band,
                        recorded_count=count,
                    )
                )
        return cls(observations)

    def lookup(self, keyword: str) -> Optional[SerpObservation]:
        """Lookups competition note by exact dedup_key first, then topic_key fallback."""
        e_key = dedup_key(keyword)
        if e_key in self._exact_map:
            return self._exact_map[e_key]

        t_key = topic_key(keyword)
        return self._topic_map.get(t_key)

"""Demand signal extractors implementing formal equations in MATH.md §5.

Calculates:
- coverage (head presence)
- breadth (expansion breadth)
- depth (rank depth)
- density (question density)
- cross-script split & script affinity
- axis yield (yield per expansion kind)
- discovered candidate keywords
"""

from dataclasses import dataclass, field
import re
from typing import Optional, Sequence

from praman.autocomplete import AutocompleteResult
from praman.expand import ExpansionQuery
from praman.intent import looks_like_question
from praman.languages import detect_buyer_intent
from praman.script import dedup_key, script_of


@dataclass
class SeedSignals:
    seed: str
    coverage: Optional[float]
    breadth: Optional[float]
    depth: Optional[float]
    density: Optional[float]
    best_rank: Optional[int]
    suggestions_seen: int
    cross_script_split: dict[str, int]
    script_affinity: Optional[float]
    axis_yield: dict[str, tuple[int, int]]       # kind -> (hits, measured)
    discovered: list[str] = field(default_factory=list)                       # High-quality candidate keywords (alias to research_candidates)
    research_candidates: list[str] = field(default_factory=list)              # Filtered high-quality research candidates
    raw_observations: list[str] = field(default_factory=list)                 # Complete uncurated raw observations
    breadth_comparable: bool = True
    queries_asked: int = 0
    queries_measured: int = 0
    queries_absent: int = 0
    queries_failed: int = 0
    buyer_intent_score: Optional[float] = None                                # Commercial intent density (0.0 to 1.0)
    buyer_intent_aspects: list[str] = field(default_factory=list)             # Unique buyer intent dimensions matched


def calculate_seed_signals(
    seed: str,
    queries: list[ExpansionQuery],
    results: dict[str, AutocompleteResult],
    all_seeds: Sequence[str],
    breadth_comparable: bool = True,
    language_code: str = "mr",
) -> SeedSignals:
    """Calculates all 4 demand axes and diagnostic signals for a seed."""
    clean_seed = seed.strip()
    seed_key = dedup_key(clean_seed)
    all_seed_keys = {dedup_key(s) for s in all_seeds}

    head_res: Optional[AutocompleteResult] = None
    expansion_results: list[tuple[ExpansionQuery, AutocompleteResult]] = []

    for q in queries:
        res = results.get(q.query)
        if not res:
            continue
        if q.kind == "head":
            head_res = res
        else:
            expansion_results.append((q, res))

    # --- 1. Coverage (MATH.md §5.1) ---
    if head_res is None or not head_res.measured:
        coverage = None
    elif len(head_res.suggestions) > 0:
        coverage = 1.0
    else:
        coverage = 0.0

    # --- 2. Breadth (MATH.md §5.2) ---
    measured_expansions = [r for (_, r) in expansion_results if r.measured]
    present_expansions = [r for r in measured_expansions if len(r.suggestions) > 0]

    if len(measured_expansions) > 0:
        breadth = len(present_expansions) / len(measured_expansions)
    else:
        breadth = None

    # --- 3. Depth & Best Rank (MATH.md §5.3) ---
    best_rank: Optional[int] = None
    if head_res is None or not head_res.measured or len(head_res.suggestions) == 0:
        # If head is unmeasured or empty, depth is None (unknown)
        depth = None
    else:
        # Search for seed in head suggestions
        found_idx: Optional[int] = None
        for idx, sug in enumerate(head_res.suggestions):
            if dedup_key(sug) == seed_key:
                found_idx = idx
                break

        if found_idx is not None:
            best_rank = found_idx + 1
            depth = 1.0 / best_rank
        else:
            best_rank = None
            depth = 0.0

    # --- 4. Question Density (MATH.md §5.4) ---
    # Construct suggestion pool U(s)
    if head_res and head_res.measured and len(head_res.suggestions) > 0:
        pool_u = list(head_res.suggestions)
    elif head_res and head_res.measured and len(head_res.suggestions) == 0:
        # Fallback to deduplicated union of expansion suggestions
        seen_sugs: set[str] = set()
        pool_u = []
        for r in measured_expansions:
            for s in r.suggestions:
                k = dedup_key(s)
                if k not in seen_sugs:
                    seen_sugs.add(k)
                    pool_u.append(s)
    else:
        pool_u = []

    if pool_u:
        q_count = sum(1 for s in pool_u if looks_like_question(s, language_code))
        density = q_count / len(pool_u)
    else:
        density = None

    # --- 5. Suggestions Seen (MATH.md §5.5) ---
    # Seed dedup set with head suggestions first
    seen_suggestions: set[str] = set()
    ordered_seen: list[str] = []

    if head_res and head_res.measured:
        for s in head_res.suggestions:
            k = dedup_key(s)
            if k not in seen_suggestions:
                seen_suggestions.add(k)
                ordered_seen.append(s)

    for r in measured_expansions:
        for s in r.suggestions:
            k = dedup_key(s)
            if k not in seen_suggestions:
                seen_suggestions.add(k)
                ordered_seen.append(s)

    suggestions_seen = len(ordered_seen)

    # --- 6. Cross-Script Split & Script Affinity (MATH.md §8.2, §8.3) ---
    script_counts = {"devanagari": 0, "latin": 0, "mixed": 0, "other": 0}
    for s in ordered_seen:
        sc = script_of(s)
        if sc in script_counts:
            script_counts[sc] += 1
        else:
            script_counts["other"] += 1

    seed_script = script_of(clean_seed)
    if suggestions_seen > 0:
        if seed_script == "devanagari":
            affinity = (script_counts["devanagari"] + script_counts["mixed"]) / suggestions_seen
        elif seed_script == "latin":
            affinity = (script_counts["latin"] + script_counts["mixed"]) / suggestions_seen
        else:
            affinity = (script_counts.get(seed_script, 0) + script_counts["mixed"]) / suggestions_seen
    else:
        affinity = None

    # --- 7. Per-Axis Yield (MATH.md §8.4) ---
    yields: dict[str, tuple[int, int]] = {}
    # Count head
    if head_res:
        head_hit = 1 if (head_res.measured and len(head_res.suggestions) > 0) else 0
        head_meas = 1 if head_res.measured else 0
        yields["head"] = (head_hit, head_meas)

    # Count other kinds: alphabet, modifier, question
    kind_stats: dict[str, list[int]] = {}
    for q, r in expansion_results:
        if q.kind not in kind_stats:
            kind_stats[q.kind] = [0, 0]  # [hits, measured]
        if r.measured:
            kind_stats[q.kind][1] += 1
            if len(r.suggestions) > 0:
                kind_stats[q.kind][0] += 1

    for k, (hits, meas) in kind_stats.items():
        yields[k] = (hits, meas)

    # --- 8. Discovered Candidates vs Raw Observations ---
    raw_observations: list[str] = []
    research_candidates: list[str] = []

    # Regex detecting raw alphabet expansion artifacts:
    # 1. Trailing single consonant or letter: e.g. "शेती क", "marathi sheti a"
    # 2. Isolated single consonant probe in middle: e.g. "पीक विमा क 2026", "शेती क तुलना"
    artifact_pattern = re.compile(
        r"(\s[\w\u0900-\u0D7F]$)|(\s[bcdfghjklmnpqrstvwxyzक-ह]\s)",
        re.IGNORECASE | re.UNICODE,
    )

    for s in ordered_seen:
        k = dedup_key(s)
        if k in all_seed_keys:
            continue
        raw_observations.append(s)

        # Candidate quality rules
        if artifact_pattern.search(s) or len(s.strip()) <= 3:
            continue
        research_candidates.append(s)

    # --- 9. Buyer Intent & Commercial Density ---
    buyer_intent_count = 0
    buyer_aspects_set: set[str] = set()
    for s in ordered_seen:
        cat = detect_buyer_intent(s)
        if cat:
            buyer_intent_count += 1
            buyer_aspects_set.add(cat)

    buyer_intent_score = (buyer_intent_count / len(ordered_seen)) if ordered_seen else 0.0
    buyer_intent_aspects = sorted(list(buyer_aspects_set))

    # Counters
    all_res = [r for r in results.values() if r.query in {q.query for q in queries}]
    queries_asked = len(queries)
    queries_measured = sum(1 for r in all_res if r.measured)
    queries_absent = sum(1 for r in all_res if r.is_absence)
    queries_failed = sum(1 for r in all_res if not r.measured)

    return SeedSignals(
        seed=clean_seed,
        coverage=coverage,
        breadth=breadth,
        depth=depth,
        density=density,
        best_rank=best_rank,
        suggestions_seen=suggestions_seen,
        cross_script_split=script_counts,
        script_affinity=affinity,
        axis_yield=yields,
        discovered=research_candidates,
        research_candidates=research_candidates,
        raw_observations=raw_observations,
        breadth_comparable=breadth_comparable,
        queries_asked=queries_asked,
        queries_measured=queries_measured,
        queries_absent=queries_absent,
        queries_failed=queries_failed,
        buyer_intent_score=buyer_intent_score,
        buyer_intent_aspects=buyer_intent_aspects,
    )

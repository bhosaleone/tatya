"""End-to-end execution pipeline for Praman."""

from typing import Optional, Sequence

from praman.autocomplete import AutocompleteResult, create_autocomplete
from praman.cache import AutocompleteCache
from praman.competition import CompetitionIndex
from praman.config import Settings
from praman.expand import create_expansion_plan
from praman.intent import classify_intent
from praman.scoring import KeywordScore, ScoreResult, score_seed
from praman.signals import calculate_seed_signals


def run_research(
    seeds: Sequence[str],
    settings: Settings,
    competition_index: Optional[CompetitionIndex] = None,
) -> ScoreResult:
    """Executes a full research run across a list of seeds."""
    cache = AutocompleteCache(settings.cache_dir)
    fetcher = create_autocomplete(settings)

    # 1. Expand seeds deterministically
    plan = create_expansion_plan(
        seeds=list(seeds),
        language_code=settings.language,
        latin_expansion=settings.latin_expansion,
        commercial_expansion=settings.commercial_expansion,
        max_seeds=settings.max_seeds,
        max_queries=settings.max_queries,
    )

    # 2. Execute queries (using cache when available)
    results: dict[str, AutocompleteResult] = {}
    for q in plan.all_queries:
        cached = cache.get(q.query, settings.language, settings.region)
        if cached:
            results[q.query] = cached
        else:
            res = fetcher.fetch(q.query, settings.language, settings.region)
            results[q.query] = res
            if res.measured:
                cache.set(res, settings.language, settings.region)

    # 3. Calculate signals and scores for each seed
    scores: list[KeywordScore] = []
    for seed in plan.seeds_used:
        expansion = plan.expansions[seed]
        signals = calculate_seed_signals(
            seed=seed,
            queries=expansion.queries,
            results=results,
            all_seeds=plan.seeds_used,
            breadth_comparable=expansion.breadth_comparable,
            language_code=settings.language,
        )
        intent = classify_intent(seed, settings.language)
        competition = competition_index.lookup(seed) if competition_index else None
        scored = score_seed(signals, intent, competition, settings.weights)
        scores.append(scored)

    return ScoreResult(
        scores=scores,
        weights=settings.weights,
        is_truncated=plan.is_truncated,
        not_asked_seeds=plan.not_asked_seeds,
    )

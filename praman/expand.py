"""Deterministic expansion engine.

Constructs expansion queries in strict order:
1. Head (seed itself)
2. Alphabet (consonants only)
3. Modifiers (intent templates)
4. Questions (bare interrogative templates)

Calculates expected counts and manages truncation flags according to MATH.md §4, §7.
"""

from dataclasses import dataclass, field
from typing import Optional

from praman.languages import LATIN_ALPHABET, get_commercial_modifiers, get_language_spec
from praman.script import dedup_key, script_of


@dataclass(frozen=True)
class ExpansionQuery:
    """A single query to be issued to autocomplete."""
    query: str
    seed: str
    kind: str           # 'head', 'alphabet', 'modifier', 'question', 'commercial'
    tag: str            # e.g. letter 'क', modifier 'pdf', question 'काय', commercial 'commercial_price'


@dataclass
class SeedExpansion:
    """The generated expansion queries for a given seed."""
    seed: str
    queries: list[ExpansionQuery]
    expected_count: int
    truncated: bool = False
    not_asked: list[str] = field(default_factory=list)

    @property
    def breadth_comparable(self) -> bool:
        """Breadth is only comparable if the seed was not truncated (MATH.md §7)."""
        return not self.truncated


def expected_expansion_count(
    seed: str,
    language_code: str = "mr",
    latin_expansion: bool = False,
    commercial_expansion: bool = False,
) -> int:
    """Calculates the theoretical complete query count for a seed."""
    spec = get_language_spec(language_code)
    is_latin = script_of(seed) == "latin"
    alphabet_len = len(LATIN_ALPHABET) if is_latin else len(spec.consonants)
    if latin_expansion and not is_latin:
        alphabet_len += len(LATIN_ALPHABET)

    head_count = 1
    std_mods = {mod for mod, _ in spec.modifier_templates}
    modifier_count = len(std_mods)
    question_count = len(spec.question_templates)

    if commercial_expansion:
        comm_mods = {mod for mod, _ in get_commercial_modifiers(language_code)}
        commercial_count = len(comm_mods - std_mods)
    else:
        commercial_count = 0

    return head_count + alphabet_len + modifier_count + question_count + commercial_count


def expand_seed(
    seed: str,
    language_code: str = "mr",
    latin_expansion: bool = False,
    commercial_expansion: bool = False,
) -> SeedExpansion:
    """Generates all expansion queries for a seed in deterministic order.

    Deduping is by dedup_key (MATH.md §3.1), never topic_key.
    """
    clean_seed = seed.strip()
    spec = get_language_spec(language_code)
    is_latin = script_of(clean_seed) == "latin"

    queries: list[ExpansionQuery] = []
    seen_keys: set[str] = set()

    def _add(q: str, kind: str, tag: str) -> None:
        key = dedup_key(q)
        if key not in seen_keys and q.strip():
            seen_keys.add(key)
            queries.append(ExpansionQuery(query=q.strip(), seed=clean_seed, kind=kind, tag=tag))

    # 1. Head query
    _add(clean_seed, "head", "head")

    # 2. Alphabet queries (consonants only)
    primary_alphabet = LATIN_ALPHABET if is_latin else spec.consonants
    for letter in primary_alphabet:
        _add(f"{clean_seed} {letter}", "alphabet", letter)

    if latin_expansion and not is_latin:
        for letter in LATIN_ALPHABET:
            _add(f"{clean_seed} {letter}", "alphabet", letter)

    # 3. Modifier queries
    for mod_text, _intent in spec.modifier_templates:
        _add(f"{clean_seed} {mod_text}", "modifier", mod_text)

    # 4. Question queries (bare interrogative templates)
    for q_tmpl in spec.question_templates:
        filled = q_tmpl.replace("{t}", clean_seed)
        _add(filled, "question", q_tmpl)

    # 5. Commercial & affiliate intent modifier queries (optional)
    if commercial_expansion:
        for mod_text, intent_type in get_commercial_modifiers(language_code):
            _add(f"{clean_seed} {mod_text}", "commercial", intent_type)

    expected = expected_expansion_count(clean_seed, language_code, latin_expansion, commercial_expansion)
    return SeedExpansion(seed=clean_seed, queries=queries, expected_count=expected)


@dataclass
class ExpansionPlan:
    """Plan of all queries across all seeds, respecting budget ceilings."""
    seeds_used: list[str]
    not_asked_seeds: list[str]
    expansions: dict[str, SeedExpansion]
    all_queries: list[ExpansionQuery]
    is_truncated: bool


def create_expansion_plan(
    seeds: list[str],
    language_code: str = "mr",
    latin_expansion: bool = False,
    commercial_expansion: bool = False,
    max_seeds: Optional[int] = None,
    max_queries: Optional[int] = None,
) -> ExpansionPlan:
    """Generates the multi-seed expansion plan applying --max-seeds and --max-queries."""
    seeds_to_process = [s.strip() for s in seeds if s.strip()]
    not_asked_seeds: list[str] = []

    if max_seeds is not None and len(seeds_to_process) > max_seeds:
        not_asked_seeds.extend(seeds_to_process[max_seeds:])
        seeds_to_process = seeds_to_process[:max_seeds]

    expansions: dict[str, SeedExpansion] = {}
    total_query_count = 0
    all_queries: list[ExpansionQuery] = []
    is_truncated_run = False

    for seed in seeds_to_process:
        seed_exp = expand_seed(seed, language_code, latin_expansion, commercial_expansion)

        if max_queries is None:
            expansions[seed] = seed_exp
            all_queries.extend(seed_exp.queries)
            total_query_count += len(seed_exp.queries)
        else:
            remaining_budget = max_queries - total_query_count
            if remaining_budget <= 0:
                # Budget completely exhausted: mark seed as truncated with 0 admitted queries
                seed_exp.truncated = True
                seed_exp.not_asked = [q.query for q in seed_exp.queries]
                seed_exp.queries = []
                expansions[seed] = seed_exp
                is_truncated_run = True
            elif remaining_budget < len(seed_exp.queries):
                # Budget partially admits queries: truncate this seed
                seed_exp.truncated = True
                admitted = seed_exp.queries[:remaining_budget]
                dropped = seed_exp.queries[remaining_budget:]
                seed_exp.queries = admitted
                seed_exp.not_asked = [q.query for q in dropped]
                expansions[seed] = seed_exp
                all_queries.extend(admitted)
                total_query_count += len(admitted)
                is_truncated_run = True
            else:
                expansions[seed] = seed_exp
                all_queries.extend(seed_exp.queries)
                total_query_count += len(seed_exp.queries)

    return ExpansionPlan(
        seeds_used=seeds_to_process,
        not_asked_seeds=not_asked_seeds,
        expansions=expansions,
        all_queries=all_queries,
        is_truncated=is_truncated_run,
    )

"""Markdown, CSV, and JSON report emitters with mandatory provenance banners."""

import csv
from io import StringIO
import json
from typing import Sequence

from praman.config import Mode
from praman.scoring import KeywordScore, ScoreResult


def _format_float(val: float | None) -> str:
    return f"{val:.3f}" if val is not None else "⊥ (unmeasured)"


def render_markdown_report(result: ScoreResult, mode: Mode) -> str:
    """Generates the primary Markdown research report with provenance banner."""
    lines: list[str] = []

    # 1. Provenance Banner (METHODOLOGY.md §2)
    mode_label = mode.value.upper()
    lines.append(f"# Praman Demand Research Report — [{mode_label} MODE]")
    if mode == Mode.FIXTURE:
        lines.append("> ⚠️ **FIXTURE RUN**: Generated from hash-deterministic synthetic data. Proves nothing about real search demand.")
    elif mode == Mode.RECORDED:
        lines.append("> ℹ️ **RECORDED RUN**: Replayed offline from verified historical responses.")
    elif mode == Mode.LIVE:
        lines.append("> 🟢 **LIVE RUN**: Live Google Autocomplete probe executed.")

    if result.is_truncated:
        lines.append("> ⚠️ **TRUNCATED RUN**: Query ceiling was hit during expansion. Breadth scores marked with ⚠ are non-comparable.")

    lines.append("")

    # 2. Main Demand Table
    lines.append("## Measured Keywords")
    lines.append("| Seed | Demand | Priority | Intent | Breadth | Coverage | Density | Depth | Competition | Suggestions |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")

    # Sort descending by demand
    sorted_scores = sorted(result.scores, key=lambda s: s.demand if s.demand is not None else -1.0, reverse=True)

    for s in sorted_scores:
        d_str = f"{s.demand:.3f}" if s.demand is not None else "⊥"
        if not s.demand_complete and s.demand is not None:
            d_str += " (partial)"

        brd_str = _format_float(s.signals.breadth)
        if not s.signals.breadth_comparable:
            brd_str = f"⚠ {brd_str}"

        cov_str = _format_float(s.signals.coverage)
        den_str = _format_float(s.signals.density)
        dep_str = _format_float(s.signals.depth)

        comp_str = s.competition.band if (s.competition and s.competition.band) else "unmeasured"

        lines.append(
            f"| `{s.seed}` | **{d_str}** | `{s.priority_band}` | {s.intent.intent} | {brd_str} | {cov_str} | {den_str} | {dep_str} | {comp_str} | {s.signals.suggestions_seen} |"
        )

    lines.append("")

    # 3. Ceilings / Not Asked Section
    if result.not_asked_seeds:
        lines.append("## Ceilings Hit (Never Asked)")
        lines.append("The following seeds exceeded budget limits and were never expanded:")
        for s in result.not_asked_seeds:
            lines.append(f"- `{s}`")
        lines.append("")

    # 4. Discovered Candidates
    lines.append("## Discovered Candidate Keywords (Unvalidated)")
    lines.append("Suggestions surfaced during expansion that are candidates for future measurement:")
    all_disc: set[str] = set()
    for s in sorted_scores:
        for c in s.signals.discovered[:8]:
            all_disc.add(c)

    for c in sorted(all_disc)[:25]:
        lines.append(f"- {c}")

    return "\n".join(lines)


def render_csv_report(result: ScoreResult) -> str:
    """Generates standard CSV output of measured metrics."""
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "seed",
        "demand",
        "demand_complete",
        "priority_band",
        "intent",
        "breadth",
        "breadth_comparable",
        "coverage",
        "density",
        "depth",
        "competition_band",
        "suggestions_seen",
        "queries_asked",
        "queries_measured",
        "queries_absent",
    ])

    for s in result.scores:
        writer.writerow([
            s.seed,
            f"{s.demand:.4f}" if s.demand is not None else "",
            s.demand_complete,
            s.priority_band,
            s.intent.intent,
            f"{s.signals.breadth:.4f}" if s.signals.breadth is not None else "",
            s.signals.breadth_comparable,
            f"{s.signals.coverage:.4f}" if s.signals.coverage is not None else "",
            f"{s.signals.density:.4f}" if s.signals.density is not None else "",
            f"{s.signals.depth:.4f}" if s.signals.depth is not None else "",
            s.competition.band if (s.competition and s.competition.band) else "",
            s.signals.suggestions_seen,
            s.signals.queries_asked,
            s.signals.queries_measured,
            s.signals.queries_absent,
        ])

    return out.getvalue()


def render_json_report(result: ScoreResult, mode: Mode) -> str:
    """Generates complete machine-readable JSON."""
    payload = {
        "mode": mode.value,
        "is_truncated": result.is_truncated,
        "not_asked_seeds": result.not_asked_seeds,
        "weights": result.weights.as_dict(),
        "keywords": [
            {
                "seed": s.seed,
                "demand": s.demand,
                "demand_complete": s.demand_complete,
                "measured_mass": s.measured_mass,
                "priority_band": s.priority_band,
                "intent": s.intent.intent,
                "article_shape": s.intent.article_shape,
                "axes": s.raw_axes,
                "components": s.components,
                "competition": {
                    "band": s.competition.band if s.competition else None,
                    "recorded_count": s.competition.recorded_count if s.competition else 0,
                    "notes": s.competition.notes if s.competition else "",
                } if s.competition else None,
                "signals": {
                    "suggestions_seen": s.signals.suggestions_seen,
                    "breadth_comparable": s.signals.breadth_comparable,
                    "cross_script_split": s.signals.cross_script_split,
                    "script_affinity": s.signals.script_affinity,
                    "discovered": s.signals.discovered[:20],
                },
            }
            for s in result.scores
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

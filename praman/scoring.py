"""Scoring engine implementing the formal pinned-weight blend from MATH.md §6.

Enforces:
- Eq 6: demand(s) = Σ_{i ∈ A(s)} W_i * v_i(s)
- Denominator does NOT move (no silent renormalization).
- c(s) measured mass tracking and partiality flagging (Theorem 1-3).
- Distinction between raw axes and weighted demand_components (Theorem 3).
"""

from dataclasses import dataclass
from typing import Optional

from praman.competition import SerpObservation
from praman.config import Weights
from praman.intent import IntentResult
from praman.signals import SeedSignals


@dataclass
class KeywordScore:
    """Complete evaluation of a seed keyword."""
    seed: str
    demand: Optional[float]
    demand_complete: bool
    measured_mass: float                 # c(s) ∈ [0, 1]
    raw_axes: dict[str, Optional[float]] # Raw values in [0, 1] or None
    components: dict[str, Optional[float]] # W_i * v_i
    unmeasured_voices: list[str]
    intent: IntentResult
    competition: Optional[SerpObservation]
    signals: SeedSignals
    priority_band: str = "medium"
    evidence_band: str = "moderate"

    @property
    def actionable(self) -> bool:
        """True if keyword has measured demand and is not navigational."""
        return self.demand is not None and self.intent.intent != "navigational"


@dataclass
class ScoreResult:
    """Aggregated output of a scoring run."""
    scores: list[KeywordScore]
    weights: Weights
    is_truncated: bool
    not_asked_seeds: list[str]


def determine_evidence_band(demand: Optional[float]) -> str:
    """Classifies demand evidence according to product calibration:
    - strong: demand >= 0.50
    - moderate: demand >= 0.25
    - weak: demand < 0.25
    - insufficient: demand is None (unmeasured)
    """
    if demand is None:
        return "insufficient"
    if demand >= 0.50:
        return "strong"
    if demand >= 0.25:
        return "moderate"
    return "weak"


def determine_priority_band(demand: Optional[float], intent: str, competition_band: Optional[str]) -> str:
    """Assigns priority band label for planning (METHODOLOGY.md §8)."""
    if demand is None:
        return "needs-measurement"
    if intent == "navigational":
        return "skip-navigational"

    if demand >= 0.50:
        base = "high"
    elif demand >= 0.25:
        base = "medium"
    else:
        base = "low"

    if competition_band == "very_high":
        return f"{base}/very-high-competition"
    if competition_band == "high":
        return f"{base}/high-competition"
    return base


def score_seed(
    signals: SeedSignals,
    intent: IntentResult,
    competition: Optional[SerpObservation] = None,
    weights: Weights = Weights(),
) -> KeywordScore:
    """Scores a single seed adhering strictly to MATH.md §6 and Theorems 1-3."""
    raw_axes: dict[str, Optional[float]] = {
        "breadth": signals.breadth,
        "coverage": signals.coverage,
        "density": signals.density,
        "depth": signals.depth,
    }

    w_dict = weights.as_dict()
    measured_axes: list[str] = []
    unmeasured_voices: list[str] = []
    components: dict[str, Optional[float]] = {}
    weighted_sum = 0.0
    measured_mass = 0.0

    for voice, raw_val in raw_axes.items():
        w = w_dict[voice]
        if raw_val is not None:
            comp = w * raw_val
            components[voice] = comp
            weighted_sum += comp
            measured_mass += w
            measured_axes.append(voice)
        else:
            components[voice] = None
            unmeasured_voices.append(voice)

    if not measured_axes:
        demand = None
        demand_complete = False
    else:
        demand = weighted_sum
        demand_complete = (measured_mass >= 1.0 - 1e-5)

    comp_band = competition.band if competition else None
    priority = determine_priority_band(demand, intent.intent, comp_band)
    evidence = determine_evidence_band(demand)

    return KeywordScore(
        seed=signals.seed,
        demand=demand,
        demand_complete=demand_complete,
        measured_mass=measured_mass,
        raw_axes=raw_axes,
        components=components,
        unmeasured_voices=unmeasured_voices,
        intent=intent,
        competition=competition,
        priority_band=priority,
        evidence_band=evidence,
        signals=signals,
    )

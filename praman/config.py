"""Configuration, execution modes, and weight definitions for Praman."""

from dataclasses import dataclass, field
from enum import Enum
import math
from pathlib import Path
from typing import Optional

from praman.errors import ConfigurationError


class Mode(str, Enum):
    FIXTURE = "fixture"      # Hash-derived deterministic synthetic responses (no network)
    RECORDED = "recorded"    # Real historical responses replayed from JSON (no network)
    LIVE = "live"            # Live requests to Google Autocomplete (network enabled)


@dataclass(frozen=True)
class Weights:
    """Pinned demand voice weights.

    Invariants:
    - Sum of weights must equal 1.0.
    - Each weight must be non-negative.
    - Weights NEVER re-normalize when a voice is unmeasured (MATH.md Theorem 1-3).
    """
    breadth: float = 0.50
    coverage: float = 0.25
    density: float = 0.15
    depth: float = 0.10

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        voices = [self.breadth, self.coverage, self.density, self.depth]
        for v in voices:
            if v < 0:
                raise ConfigurationError(f"Weights must be non-negative, got {v}")
        total = sum(voices)
        if not math.isclose(total, 1.0, rel_tol=1e-5):
            raise ConfigurationError(f"Weights must sum to 1.0, got {total}")

    def as_dict(self) -> dict[str, float]:
        return {
            "breadth": self.breadth,
            "coverage": self.coverage,
            "density": self.density,
            "depth": self.depth,
        }


@dataclass
class Settings:
    """Runtime settings for a Praman research run."""
    language: str = "mr"                    # Default Marathi ('mr')
    region: str = "IN"                      # Default India ('IN')
    mode: Mode = Mode.FIXTURE               # Default offline fixture
    max_seeds: Optional[int] = None         # Seed budget ceiling
    max_queries: Optional[int] = None       # Query budget ceiling
    suggestions_per_query: int = 10         # Capped at 1..10 by Google
    latin_expansion: bool = False           # Add Latin A-Z expansion to native seeds
    commercial_expansion: bool = False      # Add Indian commercial & affiliate modifier probes
    cache_dir: Path = field(default_factory=lambda: Path(".praman_cache"))
    recorded_file: Optional[Path] = None    # Path to recorded.json if mode=RECORDED
    weights: Weights = field(default_factory=Weights)

    def __post_init__(self) -> None:
        if not (1 <= self.suggestions_per_query <= 10):
            raise ConfigurationError("suggestions_per_query must be between 1 and 10")
        if isinstance(self.mode, str):
            self.mode = Mode(self.mode)
        if isinstance(self.cache_dir, str):
            self.cache_dir = Path(self.cache_dir)
        if isinstance(self.recorded_file, str) and self.recorded_file:
            self.recorded_file = Path(self.recorded_file)

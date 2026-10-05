"""Praman — Evidence-first Indic keyword demand research & content planning."""

from praman.config import Settings, Weights, Mode
from praman.errors import (
    AutocompleteProtocolError,
    BudgetExceededError,
    BrowserDriverError,
    CaptchaDetectedError,
    SerpAutomationError,
)
from praman.scoring import KeywordScore, ScoreResult

__version__ = "0.1.1"
__all__ = [
    "Settings",
    "Weights",
    "Mode",
    "AutocompleteProtocolError",
    "BudgetExceededError",
    "BrowserDriverError",
    "CaptchaDetectedError",
    "SerpAutomationError",
    "KeywordScore",
    "ScoreResult",
]

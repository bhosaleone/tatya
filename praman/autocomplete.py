"""Google Autocomplete client with 3-state logic and protocol validation.

Enforces:
1. Measured absence vs Unmeasured error distinction.
2. AutocompleteProtocolError raised on malformed 200 responses.
3. Clean abstraction across Live, Recorded, and Fixture modes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import logging
from typing import Optional
import urllib.parse
import urllib.request
import urllib.error

from praman.config import Mode, Settings
from praman.errors import AutocompleteProtocolError
from praman.fixtures import generate_fixture_suggestions

logger = logging.getLogger("praman.autocomplete")

GOOGLE_AUTOCOMPLETE_URL = "https://suggestqueries.google.com/complete/search"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"


@dataclass(frozen=True)
class AutocompleteResult:
    """The result of an autocomplete probe."""
    query: str
    suggestions: tuple[str, ...]
    measured: bool
    source: str                         # 'live', 'recorded', 'fixture'
    error: Optional[str] = None
    echoed_query: Optional[str] = None

    @property
    def is_absence(self) -> bool:
        """True if the query was successfully measured and returned empty suggestions."""
        return self.measured and len(self.suggestions) == 0


class BaseAutocomplete(ABC):
    """Abstract interface for querying suggestions."""

    @abstractmethod
    def fetch(self, query: str, language: str = "mr", region: str = "IN") -> AutocompleteResult:
        pass


class LiveAutocomplete(BaseAutocomplete):
    """Live HTTP fetcher against Google Autocomplete endpoint."""

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT, timeout_seconds: float = 5.0):
        self.user_agent = user_agent
        self.timeout = timeout_seconds

    def fetch(self, query: str, language: str = "mr", region: str = "IN") -> AutocompleteResult:
        params = {
            "client": "firefox",
            "hl": language,
            "gl": region,
            "q": query,
        }
        url = f"{GOOGLE_AUTOCOMPLETE_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json, text/javascript, */*; q=0.01",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status != 200:
                    return AutocompleteResult(
                        query=query,
                        suggestions=(),
                        measured=False,
                        source="live",
                        error=f"HTTP {response.status}",
                    )
                raw_bytes = response.read()
                raw_text = raw_bytes.decode("utf-8", errors="replace")

        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return AutocompleteResult(
                query=query,
                suggestions=(),
                measured=False,
                source="live",
                error=f"Network error: {str(exc)}",
            )

        # Parse and validate protocol format: [echoed_query, [sug1, sug2, ...], ...]
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise AutocompleteProtocolError(f"Non-JSON response from endpoint: {exc}", raw_body=raw_text) from exc

        if not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], list):
            raise AutocompleteProtocolError(
                f"Response body is not expected [query, [sug, ...]]: {data}", raw_body=raw_text
            )

        echoed = str(data[0]) if data else query
        suggestions = tuple(str(s) for s in data[1] if isinstance(s, (str, int, float)))

        return AutocompleteResult(
            query=query,
            suggestions=suggestions,
            measured=True,
            source="live",
            echoed_query=echoed,
        )


class RecordedAutocomplete(BaseAutocomplete):
    """Replays responses from an offline recorded JSON file."""

    def __init__(self, recorded_data: dict[str, list[str]]):
        self.recorded_data = recorded_data

    @classmethod
    def from_file(cls, path: str) -> "RecordedAutocomplete":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)

    def fetch(self, query: str, language: str = "mr", region: str = "IN") -> AutocompleteResult:
        if query in self.recorded_data:
            sugs = self.recorded_data[query]
            return AutocompleteResult(
                query=query,
                suggestions=tuple(sugs),
                measured=True,
                source="recorded",
                echoed_query=query,
            )
        # If query is missing from the recorded file, it is UNMEASURED, never zero!
        return AutocompleteResult(
            query=query,
            suggestions=(),
            measured=False,
            source="recorded",
            error="No recorded response found for query",
        )


class FixtureAutocomplete(BaseAutocomplete):
    """Deterministic hash-derived synthetic responses for offline testing."""

    def fetch(self, query: str, language: str = "mr", region: str = "IN") -> AutocompleteResult:
        sugs = generate_fixture_suggestions(query, language)
        return AutocompleteResult(
            query=query,
            suggestions=tuple(sugs),
            measured=True,
            source="fixture",
            echoed_query=query,
        )


def create_autocomplete(settings: Settings) -> BaseAutocomplete:
    """Instantiates the appropriate autocomplete client based on runtime settings."""
    if settings.mode == Mode.LIVE:
        return LiveAutocomplete()
    if settings.mode == Mode.RECORDED:
        if not settings.recorded_file or not settings.recorded_file.exists():
            # Fall back to fixture if recorded file is missing or not provided
            return FixtureAutocomplete()
        return RecordedAutocomplete.from_file(str(settings.recorded_file))
    return FixtureAutocomplete()

"""Automated SERP competition signal extraction with Selenium.

Parses Google SERP DOM to derive tri-state competition signals
(top_results_stale, thin_results, weak_domains, own_sites_ranking)
following METHODOLOGY.md §7 discipline: blank/unmeasured remains None (NEVER False).

This is an opt-in automation that produces the same SerpObservation shape
as the manual CSV workflow.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from praman.competition import SerpObservation, derive_competition_band
from praman.script import dedup_key, topic_key

# Weak/low-authority domain patterns commonly appearing in SERPs
WEAK_DOMAIN_PATTERNS = re.compile(
    r"(quora\.com|stackoverflow\.com|stackexchange\.com|reddit\.com|answers\.com|wiki\.answers\.com|"
    r"yahoo\.com|yahoo\.co\.in|indiatimes\.com|timesofindia\.indiatimes\.com|"
    r"digitalmarketingcommunity\.com|medium\.com|blogspot\.com|wordpress\.com|"
    r"wixsite\.com|weebly\.com|tumblr\.com|pinterest\.com|hubpages\.com|"
    r"ezinearticles\.com|slideshare\.net|scribd\.com|academia\.edu|"
    r"justanswer\.com|ask\.com|allexperts\.com|answerbag\.com|"
    r"merriam-webster\.com|dictionary\.com|"
    r"facebook\.com|instagram\.com|linkedin\.com|twitter\.com|x\.com)",
    re.IGNORECASE,
)

# Date-like patterns in snippets (rough heuristic for staleness)
DATE_PATTERNS = [
    re.compile(r"\b(19|20)\d{2}\b"),  # 1990-2099
    re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[\w\s,.-]*(\d{4})\b", re.IGNORECASE),
    re.compile(r"\b\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\s+(\d{4})\b", re.IGNORECASE),
    re.compile(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b"),
    re.compile(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b"),
    re.compile(r"\b(\d+)\s+(day|days|week|weeks|month|months|year|years)\s+ago\b", re.IGNORECASE),
]

ORGANIC_SELECTOR_CANDIDATES = [
    "div.g",
    "div.MjjYud",
    "div#search div.g",
    "div.tF2Cxc",
    "div.yuRUbf",
]

CAPTCHA_INDICATORS = [
    "recaptcha",
    "captcha",
    "unusual traffic",
    "prove you're not a robot",
    "security check",
    "detected unusual activity",
]


@dataclass(frozen=True)
class SerpParsedSignals:
    """Raw parsed signals from SERP HTML."""

    keyword: str
    organic_count: int = 0
    weak_domain_count: int = 0
    has_stale_dates: bool = False
    has_dates: bool = False
    own_sites_count: int = 0
    organic_links: list[str] = field(default_factory=list)
    organic_domains: list[str] = field(default_factory=list)
    notes_fragments: list[str] = field(default_factory=list)
    captcha_detected: bool = False


@dataclass(frozen=True)
class AutoSerpObservation:
    """Auto-derived SERP observation before final banding."""

    keyword: str
    top_results_stale: Optional[bool]
    thin_results: Optional[bool]
    weak_domains: Optional[bool]
    own_sites_ranking: Optional[bool]
    notes: str
    organic_count: int
    weak_domain_count: int


def _extract_domain(url: str) -> Optional[str]:
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.netloc:
            domain = parsed.netloc.lower()
            # strip www.
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
    except Exception:
        pass
    return None


def _normalize_url(u: str) -> str:
    try:
        from urllib.parse import urlparse, urlunparse

        p = urlparse(u)
        if not p.netloc:
            return u
        scheme = p.scheme or "https"
        return urlunparse((scheme, p.netloc, p.path, "", "", ""))
    except Exception:
        return u


def detect_captcha(html: str, title: str = "") -> bool:
    if not html and not title:
        return False
    combined = (html + " " + title).lower()
    for ind in CAPTCHA_INDICATORS:
        if ind in combined:
            return True
    return False


def parse_serp_html(html: str, keyword: str, own_domains: Sequence[str] | None = None) -> SerpParsedSignals:
    """Parse Google SERP HTML and extract structural signals."""
    if detect_captcha(html, ""):
        return SerpParsedSignals(keyword=keyword, captcha_detected=True)

    from html.parser import HTMLParser

    class LinkParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.organic_links: list[str] = []
            self.in_link = False
            self.current_href: Optional[str] = None

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                attrs_dict = dict(attrs)
                href = attrs_dict.get("href")
                if href and href.startswith(("http://", "https://")):
                    # skip google internal links
                    if "google." in href and any(p in href for p in ["/search?", "/url?", "/imgres?", "webcache", "translate", "maps.google", "accounts.google", "support.google"]):
                        return
                    if href.startswith("https://www.google.com/url?"):
                        try:
                            from urllib.parse import parse_qs, urlparse

                            qs = parse_qs(urlparse(href).query)
                            real = qs.get("q", [None])[0]
                            if real:
                                href = real
                        except Exception:
                            pass
                    self.current_href = href
                    self.in_link = True

        def handle_endtag(self, tag):
            if tag == "a" and self.in_link and self.current_href:
                self.organic_links.append(self.current_href)
                self.in_link = False
                self.current_href = None

        def handle_data(self, data):
            pass

    parser = LinkParser()
    try:
        parser.feed(html)
    except Exception:
        pass

    organic_links: list[str] = []
    seen_norm: set[str] = set()
    for l in parser.organic_links:
        norm = _normalize_url(l)
        if norm not in seen_norm:
            seen_norm.add(norm)
            organic_links.append(norm)

    organic_domains: list[str] = []
    weak_domain_count = 0
    own_sites_count = 0
    own_list = [d.lower().strip() for d in (own_domains or []) if d.strip()]

    for l in organic_links:
        d = _extract_domain(l)
        if not d:
            continue
        if d not in organic_domains:
            organic_domains.append(d)
        if WEAK_DOMAIN_PATTERNS.search(d):
            weak_domain_count += 1
        for od in own_list:
            if od == d or d.endswith("." + od):
                own_sites_count += 1

    text_blob = html.lower()
    has_dates = False
    has_stale_dates = False
    if any(DATE_PATTERNS):
        for pat in DATE_PATTERNS:
            if pat.search(html):
                has_dates = True
                break
    if "ago" in text_blob:
        has_stale_dates = True
    elif re.search(r"\b(20\d{2}|19\d{2})\b", html):
        has_stale_dates = has_stale_dates or False

    notes_fragments: list[str] = []
    if weak_domain_count > 0:
        notes_fragments.append(f"weak_domains={weak_domain_count}")
    if has_stale_dates or has_dates:
        notes_fragments.append("dates_seen")
    if own_sites_count > 0:
        notes_fragments.append(f"own_ranking={own_sites_count}")

    return SerpParsedSignals(
        keyword=keyword,
        organic_count=len(organic_links),
        weak_domain_count=weak_domain_count,
        has_stale_dates=has_stale_dates or has_dates,
        has_dates=has_dates,
        own_sites_count=own_sites_count,
        organic_links=organic_links[:20],
        organic_domains=organic_domains[:20],
        notes_fragments=notes_fragments,
        captcha_detected=False,
    )


def signals_to_observation(
    keyword: str,
    parsed: SerpParsedSignals,
    own_domains: Sequence[str] | None = None,
) -> AutoSerpObservation:
    """Map parsed signals to tri-state SERP fields (None means unrecorded)."""

    # thin_results: organic results sparse? Use conservative threshold
    thin_results: Optional[bool] = None
    if parsed.organic_count >= 0:
        if parsed.organic_count < 3:
            thin_results = True
        elif parsed.organic_count >= 8:
            thin_results = False
        else:
            thin_results = None

    # weak_domains: need enough signal? require >=1 weak domain OR multiple? conservative
    weak_domains: Optional[bool] = None
    if parsed.weak_domain_count > 0:
        weak_domains = True
    else:
        weak_domains = False

    # top_results_stale: dates seen in top area? heuristic
    top_results_stale: Optional[bool] = parsed.has_stale_dates if parsed.has_dates or parsed.has_stale_dates else None

    # own_sites_ranking
    own_list = [d.lower().strip() for d in (own_domains or []) if d.strip()]
    own_sites_ranking: Optional[bool] = None
    if own_list:
        own_sites_ranking = parsed.own_sites_count > 0
    else:
        own_sites_ranking = None  # not recorded if not specified

    notes_parts = []
    notes_parts.append(f"auto:organic={parsed.organic_count}")
    notes_parts.append(f"weak={parsed.weak_domain_count}")
    if parsed.has_dates:
        notes_parts.append("dates=seen")
    if own_list and parsed.own_sites_count > 0:
        notes_parts.append(f"own={parsed.own_sites_count}")
    if parsed.captcha_detected:
        notes_parts.append("captcha=detected")
    notes = "; ".join(notes_parts)

    return AutoSerpObservation(
        keyword=keyword,
        top_results_stale=top_results_stale,
        thin_results=thin_results,
        weak_domains=weak_domains,
        own_sites_ranking=own_sites_ranking,
        notes=notes,
        organic_count=parsed.organic_count,
        weak_domain_count=parsed.weak_domain_count,
    )


def auto_to_serp_observation(auto: AutoSerpObservation) -> SerpObservation:
    band, count = derive_competition_band(auto.thin_results, auto.weak_domains, auto.top_results_stale)
    return SerpObservation(
        keyword=auto.keyword,
        top_results_stale=auto.top_results_stale,
        thin_results=auto.thin_results,
        weak_domains=auto.weak_domains,
        own_sites_ranking=auto.own_sites_ranking,
        notes=auto.notes,
        band=band,
        recorded_count=count,
    )


@dataclass
class SerpCacheEntry:
    keyword: str
    lang: str
    region: str
    ts: float
    signals: dict


class SerpAutoCache:
    def __init__(self, cache_dir: Path = Path(".praman_serp_cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, keyword: str, lang: str, region: str) -> Path:
        k = dedup_key(f"{keyword}|{lang}|{region}")
        return self.cache_dir / f"{k}.json"

    def get(self, keyword: str, lang: str, region: str) -> Optional[AutoSerpObservation]:
        p = self._key_path(keyword, lang, region)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            auto = AutoSerpObservation(
                keyword=data["keyword"],
                top_results_stale=data.get("top_results_stale"),
                thin_results=data.get("thin_results"),
                weak_domains=data.get("weak_domains"),
                own_sites_ranking=data.get("own_sites_ranking"),
                notes=data.get("notes", ""),
                organic_count=data.get("organic_count", 0),
                weak_domain_count=data.get("weak_domain_count", 0),
            )
            return auto
        except Exception:
            return None

    def set(self, auto: AutoSerpObservation, lang: str, region: str) -> None:
        p = self._key_path(auto.keyword, lang, region)
        try:
            data = asdict(auto)
            data["lang"] = lang
            data["region"] = region
            data["ts"] = datetime.utcnow().timestamp()
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

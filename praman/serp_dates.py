"""SERP date extraction: extract published/modified dates for Google top results.

Provides both a lightweight parser and a Selenium-powered extractor.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Optional, Sequence

from praman.serp_browser import SerpBrowser, SerpDatesCache, SerpDateExtracted, SerpResultRow


@dataclass
class DateExtractionResult:
    rows: list[SerpResultRow]
    query: str
    num: int


def _domain(url: str) -> str:
    try:
        from urllib.parse import urlparse

        d = urlparse(url).netloc
        if d.startswith("www."):
            d = d[4:]
        return d
    except Exception:
        return ""


def extract_dates_simple(url: str) -> SerpDateExtracted:
    try:
        import urllib.request

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return SerpDateExtracted(source="ERROR", confidence="NONE")

    # quick checks
    # JSON-LD
    import re

    for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE):
        try:
            data = json.loads(m.group(1))
            objs = data if isinstance(data, list) else [data]
            for o in objs:
                if isinstance(o, dict):
                    pub = o.get("datePublished") or o.get("datepublished")
                    mod = o.get("dateModified") or o.get("datemodified")
                    if pub or mod:
                        return SerpDateExtracted(published=str(pub) if pub else None, modified=str(mod) if mod else None, source="JSON-LD", confidence="HIGH")
        except Exception:
            pass
    # time
    m = re.search(r'<time[^>]*datetime=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m:
        return SerpDateExtracted(published=m.group(1), source="TIME", confidence="MEDIUM")
    # meta
    for pat in [r'<meta[^>]*property=["\']article:published_time["\'][^>]*content=["\']([^"\']+)["\']', r'<meta[^>]*name=["\']date["\'][^>]*content=["\']([^"\']+)["\']']:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            return SerpDateExtracted(published=m.group(1), source="META", confidence="MEDIUM")
    return SerpDateExtracted(source="NONE", confidence="NONE")

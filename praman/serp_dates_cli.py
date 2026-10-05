"""CLI integration helpers for SERP dates."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from praman.serp_browser import SerpBrowser, SerpDatesCache, SerpDateExtracted, SerpResultRow
from praman.serp_dates import extract_dates_simple


def _domain(url: str) -> str:
    try:
        from urllib.parse import urlparse

        d = urlparse(url).netloc
        if d.startswith("www."):
            d = d[4:]
        return d
    except Exception:
        return ""


def run_serp_dates(
    query: str,
    num: int = 10,
    lang: str = "mr",
    region: str = "IN",
    use_selenium: bool = True,
    headless: bool = False,
    min_delay: float = 18.0,
    max_delay: float = 28.0,
    out: Optional[Path] = None,
    cache: bool = True,
) -> list[SerpResultRow]:
    cache_obj = SerpDatesCache() if cache else None
    rows: list[SerpResultRow] = []
    results = []
    if use_selenium:
        try:
            browser = SerpBrowser(headless=headless, min_delay=min_delay, max_delay=max_delay)
            results = browser.get_top_results(query, num=num, lang=lang, region=region)
        except Exception:
            use_selenium = False
    if not use_selenium:
        try:
            from urllib.parse import quote_plus
            import urllib.request

            url = f"https://www.google.com/search?q={quote_plus(query)}&num={num}&hl={lang}&gl={region}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            # naive parse
            import re

            for m in re.finditer(r'<div class="MjjYud">.*?<a href="([^"]+)".*?<h3[^>]*>(.*?)</h3>', html, re.DOTALL | re.IGNORECASE):
                href = m.group(1)
                title = re.sub(r'<[^>]+>', '', m.group(2))
                results.append({"title": title, "url": href, "domain": _domain(href)})
                if len(results) >= num:
                    break
        except Exception:
            results = []

    for i, r in enumerate(results, 1):
        ext = None
        if cache and cache_obj:
            ext = cache_obj.get(r["url"])
        if ext is None:
            if use_selenium:
                try:
                    browser = SerpBrowser(headless=headless, min_delay=min_delay, max_delay=max_delay)
                    ext = browser._extract_dates(r["url"], query)
                except Exception:
                    ext = SerpDateExtracted(source="ERROR", confidence="NONE")
            else:
                ext = extract_dates_simple(r["url"])
            if cache and cache_obj and ext and ext.source != "ERROR":
                cache_obj.set(r["url"], ext)
        row = SerpResultRow(
            rank=i,
            title=r["title"],
            url=r["url"],
            domain=r["domain"],
            published_date=ext.published if ext else None,
            modified_date=ext.modified if ext else None,
            date_source=ext.source if ext else "NONE",
            date_confidence=ext.confidence if ext else "NONE",
            extracted_at=datetime.utcnow().isoformat() + "Z",
            error=None,
        )
        rows.append(row)

    if out:
        out_p = Path(out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        if out_p.suffix.lower() == ".json":
            out_p.write_text(json.dumps([x.to_dict() for x in rows], ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            with open(out_p, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["rank", "title", "url", "domain", "published_date", "modified_date", "date_source", "date_confidence", "extracted_at"])
                for x in rows:
                    w.writerow([x.rank, x.title, x.url, x.domain, x.published_date or "", x.modified_date or "", x.date_source, x.date_confidence, x.extracted_at or ""])
    return rows

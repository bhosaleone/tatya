"""Continuous Fresh Link Crawler and Live Feed Monitor for Marathi Web.

Monitors:
- Real-time RSS/Atom feeds (Agrowon, Saamana, Deshdoot, MajhaPaper, BolBhidu, PaisaMarg, etc.)
- Google News XML sitemaps and Daily sitemaps
- Instant extraction of authentic Marathi titles and publication timestamps
- Automatic immediate indexing into SQLite FTS5 for zero-latency search discovery.
"""

from __future__ import annotations
import concurrent.futures
import datetime
import html
import re
import ssl
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from praman.crawler.db import CrawlerDB
from praman.search.engine import extract_pure_marathi_headline, DOMAIN_MARATHI_NAMES
from praman.search.indexer import SearchIndexer, extract_search_tokens
from praman.script import fold


@dataclass
class FreshLinkItem:
    url: str
    title: str
    domain: str
    published_at: str
    category: str
    summary: Optional[str] = None


# High-frequency Marathi News & Knowledge Feeds
LIVE_MARATHI_FEEDS = [
    {
        "url": "https://agrowon.esakal.com/feed/",
        "domain": "agrowon.esakal.com",
        "category": "Agriculture",
        "type": "rss",
    },
    {
        "url": "https://saamana.com/feed/",
        "domain": "saamana.com",
        "category": "News & Media",
        "type": "rss",
    },
    {
        "url": "https://deshdoot.com/feed/",
        "domain": "deshdoot.com",
        "category": "News & Media",
        "type": "rss",
    },
    {
        "url": "https://www.majhapaper.com/feed/",
        "domain": "majhapaper.com",
        "category": "News & Media",
        "type": "rss",
    },
    {
        "url": "https://bolbhidu.com/feed/",
        "domain": "bolbhidu.com",
        "category": "Literature & Culture",
        "type": "rss",
    },
    {
        "url": "https://paisamarg.com/feed/",
        "domain": "paisamarg.com",
        "category": "Finance & Banking",
        "type": "rss",
    },
    {
        "url": "https://agrowon.esakal.com/news_sitemap.xml",
        "domain": "agrowon.esakal.com",
        "category": "Agriculture",
        "type": "sitemap",
    },
    {
        "url": "https://dainikgomantak.esakal.com/news_sitemap.xml",
        "domain": "dainikgomantak.esakal.com",
        "category": "News & Media",
        "type": "sitemap",
    },
]


class FreshnessCrawler:
    """Discovers, parses, and indexes newly published Marathi articles in real-time."""

    def __init__(self, db: CrawlerDB):
        self.db = db
        self.indexer = SearchIndexer(db)
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

    def _fetch_single_source(self, source: dict[str, str]) -> tuple[dict[str, str], list[FreshLinkItem]]:
        f_url = source["url"]
        dom = source["domain"]
        cat = source["category"]
        feed_type = source["type"]

        items: list[FreshLinkItem] = []
        try:
            req = urllib.request.Request(
                f_url, 
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}
            )
            with urllib.request.urlopen(req, timeout=4.5, context=self.ssl_ctx) as resp:
                raw_data = resp.read()

            if feed_type == "rss":
                items = self._parse_rss_feed(raw_data, dom, cat)
            elif feed_type == "sitemap":
                items = self._parse_news_sitemap(raw_data, dom, cat)
        except Exception:
            pass
        return source, items

    def crawl_once(self) -> int:
        """Runs a single concurrent round of live feed checks and indexes new links."""
        conn = self.db.get_connection()
        total_new = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(self._fetch_single_source, src) for src in LIVE_MARATHI_FEEDS]
            for fut in concurrent.futures.as_completed(futures):
                try:
                    src, items = fut.result()
                    if items:
                        new_count = self._store_and_index_items(conn, items, src["domain"], src["category"])
                        total_new += new_count
                        if new_count > 0:
                            print(f"  + [{src['domain']}] नवीन {new_count} ताज्या बातम्या जोडल्या.")
                except Exception:
                    pass

        return total_new

    def _parse_rss_feed(self, data: bytes, domain: str, category: str) -> list[FreshLinkItem]:
        """Parses RSS XML into list of FreshLinkItems."""
        items: list[FreshLinkItem] = []
        try:
            root = ET.fromstring(data)
            for it in root.findall(".//item"):
                t_elem = it.find("title")
                l_elem = it.find("link")
                d_elem = it.find("pubDate")
                desc_elem = it.find("description")

                title = html.unescape(t_elem.text).strip() if t_elem is not None and t_elem.text else ""
                link = l_elem.text.strip() if l_elem is not None and l_elem.text else ""
                pub_date = d_elem.text.strip() if d_elem is not None and d_elem.text else ""
                desc = html.unescape(desc_elem.text).strip() if desc_elem is not None and desc_elem.text else None

                # Clean summary from HTML tags
                if desc:
                    desc = re.sub(r"<[^>]+>", "", desc).strip()[:200]

                if link and title:
                    # Parse pub date into ISO
                    iso_date = self._parse_date_to_iso(pub_date)
                    items.append(FreshLinkItem(
                        url=link,
                        title=title,
                        domain=domain,
                        published_at=iso_date,
                        category=category,
                        summary=desc,
                    ))
        except Exception:
            pass
        return items

    def _parse_news_sitemap(self, data: bytes, domain: str, category: str) -> list[FreshLinkItem]:
        """Parses Google News sitemap XML into FreshLinkItems."""
        items: list[FreshLinkItem] = []
        try:
            root = ET.fromstring(data)
            # Handle default and news namespaces
            for url_tag in root.findall("{*}url"):
                loc_elem = url_tag.find("{*}loc")
                if loc_elem is None or not loc_elem.text:
                    continue
                url = loc_elem.text.strip()

                title = ""
                pub_date = ""

                news_elem = url_tag.find("{*}news")
                if news_elem is not None:
                    title_elem = news_elem.find("{*}title")
                    if title_elem is not None and title_elem.text:
                        title = html.unescape(title_elem.text).strip()
                    date_elem = news_elem.find("{*}publication_date")
                    if date_elem is not None and date_elem.text:
                        pub_date = date_elem.text.strip()

                if not pub_date:
                    lastmod_elem = url_tag.find("{*}lastmod")
                    if lastmod_elem is not None and lastmod_elem.text:
                        pub_date = lastmod_elem.text.strip()

                if url and title:
                    items.append(FreshLinkItem(
                        url=url,
                        title=title,
                        domain=domain,
                        published_at=pub_date or datetime.datetime.now().isoformat(),
                        category=category,
                    ))
        except Exception:
            pass
        return items

    def _parse_date_to_iso(self, date_str: str) -> str:
        """Converts RFC 822 or other formats to standard ISO format."""
        if not date_str:
            return datetime.datetime.now().isoformat()
        try:
            # e.g. "Sun, 04 Oct 2026 20:00:00 +0000"
            dt = datetime.datetime.strptime(date_str[:25].strip(), "%a, %d %b %Y %H:%M:%S")
            return dt.strftime("%Y-%m-%dT%H:%M:%S+05:30")
        except Exception:
            return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+05:30")

    def _store_and_index_items(
        self, 
        conn: sqlite3.Connection, 
        items: list[FreshLinkItem], 
        domain: str, 
        category: str
    ) -> int:
        """Inserts new items into pages and updates FTS index."""
        # Find website_id
        cur = conn.execute("SELECT id FROM websites WHERE domain = ? LIMIT 1;", (domain,))
        row = cur.fetchone()
        if not row:
            # Register website if not present
            conn.execute("BEGIN IMMEDIATE;")
            conn.execute("""
                INSERT INTO websites (domain, root_url, category, pagerank, authority_score, marathi_char_ratio)
                VALUES (?, ?, ?, 0.05, 0.5, 0.85);
            """, (domain, f"https://{domain}/", category))
            conn.execute("COMMIT;")
            cur = conn.execute("SELECT id FROM websites WHERE domain = ? LIMIT 1;", (domain,))
            row = cur.fetchone()

        website_id = row[0]
        new_indexed = 0

        conn.execute("BEGIN;")
        try:
            for it in items:
                # Check if URL already exists
                cur = conn.execute("SELECT id, title FROM pages WHERE url = ? LIMIT 1;", (it.url,))
                existing = cur.fetchone()

                clean_title = extract_pure_marathi_headline(it.title) or it.title
                is_marathi = 1 if any('\u0900' <= ch <= '\u097f' for ch in clean_title) else 0

                parsed = urllib.parse.urlsplit(it.url)
                path = parsed.path or "/"

                if not existing:
                    cur = conn.execute("""
                        INSERT INTO pages (website_id, url, path, title, is_marathi, sitemap_lastmod, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                    """, (website_id, it.url, path, clean_title, is_marathi, it.published_at, datetime.datetime.now().isoformat()))
                    page_id = cur.lastrowid

                    # Index directly into pages_fts
                    combined = f"{clean_title} {path} {domain}"
                    search_tokens = extract_search_tokens(combined)
                    conn.execute("""
                        INSERT INTO pages_fts (rowid, title, url, domain, category, search_tokens)
                        VALUES (?, ?, ?, ?, ?, ?);
                    """, (page_id, clean_title, it.url, domain, category, search_tokens))
                    new_indexed += 1
                else:
                    # Update title if previous was empty
                    p_id, old_title = existing
                    if not old_title and clean_title:
                        conn.execute("UPDATE pages SET title = ?, sitemap_lastmod = ? WHERE id = ?;", (clean_title, it.published_at, p_id))
                        # Update FTS
                        combined = f"{clean_title} {path} {domain}"
                        search_tokens = extract_search_tokens(combined)
                        conn.execute("DELETE FROM pages_fts WHERE rowid = ?;", (p_id,))
                        conn.execute("""
                            INSERT INTO pages_fts (rowid, title, url, domain, category, search_tokens)
                            VALUES (?, ?, ?, ?, ?, ?);
                        """, (p_id, clean_title, it.url, domain, category, search_tokens))
                        new_indexed += 1

            conn.execute("COMMIT;")
        except Exception:
            conn.execute("ROLLBACK;")
            raise

        return new_indexed

    def run_daemon(self, interval_seconds: int = 300) -> None:
        """Runs the live freshness crawler continuously in background."""
        print(f"🚀 Marathi Freshness & Live Discover Crawler started (interval: {interval_seconds}s)...")
        while True:
            t0 = time.time()
            new_links = self.crawl_once()
            elapsed = time.time() - t0
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{now_str}] क्रॉल फेरी पूर्ण: {new_links} नवीन बातम्या मिळाल्या ({elapsed:.1f}s). पुढील फेरी {interval_seconds} सेकंदांत...")
            time.sleep(interval_seconds)

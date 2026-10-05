"""High-Concurrency Crawler Engine for Mapping Marathi Websites and Sitemaps.

Supports:
- Worker bot pool with configurable concurrency (10 to 100+ bots).
- Per-domain polite rate limiting to prevent host overload.
- Transparent robots.txt and sitemap hierarchy resolution.
- Batch database inserts for maximum I/O throughput.
- Error provenance tracking adhering to METHODOLOGY.md and MATH.md.
"""

from __future__ import annotations
import concurrent.futures
from dataclasses import dataclass, field
import io
import logging
import random
import re
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Optional

from praman.crawler.db import CrawlerDB
from praman.crawler.html_parser import analyze_html_content, normalize_domain, clean_url
from praman.crawler.seeds import MARATHI_SEEDS, SeedDomain
from praman.crawler.sitemap_parser import SitemapParser, SitemapResult, SitemapUrlEntry


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (compatible; MarathiWebGraphBot/1.0)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (compatible; MarathiWebGraphBot/1.0)",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0 (compatible; MarathiWebGraphBot/1.0)",
]

STANDARD_SITEMAP_CANDIDATES = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/wp-sitemap.xml",
    "/news_sitemap.xml",
    "/sitemap-news.xml",
    "/feed",
    "/rss",
]


@dataclass
class CrawlerConfig:
    num_workers: int = 24
    per_domain_delay: float = 0.4
    request_timeout: float = 10.0
    max_sitemaps_per_domain: int = 5
    max_pages_per_domain: int = 25
    user_agent: Optional[str] = None
    verify_marathi: bool = True


class DomainRateLimiter:
    """Thread-safe per-domain rate limiter."""

    def __init__(self, min_delay: float = 0.5):
        self.min_delay = min_delay
        self._last_access: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait_for_domain(self, domain: str) -> None:
        dom = normalize_domain(domain)
        with self._lock:
            now = time.monotonic()
            last = self._last_access.get(dom, 0.0)
            elapsed = now - last
            to_sleep = self.min_delay - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)
            self._last_access[dom] = time.monotonic()


class CrawlerEngine:
    """Orchestrates multi-worker crawler bots for Marathi web indexing."""

    def __init__(self, db: CrawlerDB, config: Optional[CrawlerConfig] = None):
        self.db = db
        self.config = config or CrawlerConfig()
        socket.setdefaulttimeout(self.config.request_timeout)
        self.rate_limiter = DomainRateLimiter(min_delay=self.config.per_domain_delay)
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        self._progress_callback: Optional[Callable[[str, int, int], None]] = None

    def set_progress_callback(self, cb: Callable[[str, int, int], None]) -> None:
        self._progress_callback = cb

    def _fetch_url(self, url: str) -> tuple[int, bytes, str, dict[str, str]]:
        """Performs HTTP GET with error provenance. Returns (status_code, body, content_type, headers)."""
        parsed = urllib.parse.urlsplit(url)
        domain = normalize_domain(parsed.netloc)
        self.rate_limiter.wait_for_domain(domain)

        ua = self.config.user_agent or random.choice(USER_AGENTS)
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "mr,mr-IN;q=0.9,hi;q=0.7,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "close",
        }

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.config.request_timeout, context=self.ssl_context) as resp:
                status = resp.status
                raw_data = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                hdrs = {k.lower(): v for k, v in resp.headers.items()}
                # Transparently decompress gzip
                decompressed = SitemapParser.decompress_if_gzip(raw_data)
                return (status, decompressed, content_type, hdrs)
        except urllib.error.HTTPError as e:
            err_data = b""
            try:
                err_data = e.read()
            except Exception:
                pass
            return (e.code, err_data, "", {})
        except urllib.error.URLError as e:
            # Network failure / timeout
            return (599, b"", "", {"error": str(e.reason)})
        except (socket.timeout, TimeoutError):
            return (598, b"", "", {"error": "Timeout"})
        except Exception as e:
            return (597, b"", "", {"error": str(e)})

    def discover_and_parse_sitemaps(self, site_id: int, domain: str, root_url: str) -> tuple[Optional[str], str, Optional[str], int]:
        """Discovers sitemaps via robots.txt and fallback candidate paths.
        
        Returns: (chosen_sitemap_url, sitemap_status, sitemap_type, total_discovered_urls)
        """
        discovered_sitemap_urls: list[str] = []
        robots_url = urllib.parse.urljoin(root_url, "/robots.txt")
        code, body, _, _ = self._fetch_url(robots_url)

        if code == 200 and body:
            robots_txt = body.decode("utf-8", errors="ignore")
            from_robots = SitemapParser.extract_sitemaps_from_robots(robots_txt, root_url)
            discovered_sitemap_urls.extend(from_robots)

        # If robots.txt had no sitemaps, probe standard candidate paths
        if not discovered_sitemap_urls:
            for cand in STANDARD_SITEMAP_CANDIDATES:
                cand_url = urllib.parse.urljoin(root_url, cand)
                c_code, c_body, c_type, _ = self._fetch_url(cand_url)
                if c_code == 200 and len(c_body) > 100:
                    # Check if it looks like XML or RSS
                    snip = c_body[:300].lower()
                    if b"<?xml" in snip or b"<urlset" in snip or b"<sitemapindex" in snip or b"<rss" in snip or b"<feed" in snip:
                        discovered_sitemap_urls.append(cand_url)
                        break

        if not discovered_sitemap_urls:
            return (None, "absent", "none", 0)

        primary_sitemap_url = discovered_sitemap_urls[0]
        total_urls = 0
        primary_type = "standard"

        # Queue to resolve sitemaps recursively up to max_sitemaps_per_domain
        sitemaps_to_process = list(discovered_sitemap_urls[:self.config.max_sitemaps_per_domain])
        processed_sitemaps: set[str] = set()
        sitemap_limit = self.config.max_sitemaps_per_domain

        while sitemaps_to_process and len(processed_sitemaps) < sitemap_limit:
            s_url = sitemaps_to_process.pop(0)
            if s_url in processed_sitemaps:
                continue
            processed_sitemaps.add(s_url)

            s_code, s_body, _, _ = self._fetch_url(s_url)
            if s_code != 200 or not s_body:
                self.db.insert_sitemap(
                    website_id=site_id,
                    sitemap_url=s_url,
                    sitemap_type="error",
                    url_count=0,
                    status_code=s_code,
                    error_message=f"HTTP {s_code}",
                )
                continue

            parsed_res: SitemapResult = SitemapParser.parse_sitemap_xml(s_body, s_url)
            
            if parsed_res.sitemap_type == "sitemapindex":
                primary_type = "sitemapindex"
                self.db.insert_sitemap(
                    website_id=site_id,
                    sitemap_url=s_url,
                    sitemap_type="sitemapindex",
                    url_count=len(parsed_res.child_sitemaps),
                    status_code=s_code,
                )
                # Queue children (most recent / top children first)
                for child in parsed_res.child_sitemaps:
                    if child not in processed_sitemaps and child not in sitemaps_to_process:
                        sitemaps_to_process.append(child)

            elif parsed_res.sitemap_type in ("urlset", "feed"):
                if primary_type != "sitemapindex":
                    primary_type = parsed_res.sitemap_type

                self.db.insert_sitemap(
                    website_id=site_id,
                    sitemap_url=s_url,
                    sitemap_type=parsed_res.sitemap_type,
                    url_count=len(parsed_res.urls),
                    status_code=s_code,
                )

                # Batch store discovered URLs into pages table
                pages_to_insert = []
                for entry in parsed_res.urls:
                    parsed_loc = urllib.parse.urlsplit(entry.loc)
                    pages_to_insert.append({
                        "url": entry.loc,
                        "title": entry.title,
                        "path": parsed_loc.path or "/",
                        "is_marathi": 1 if (entry.title and any('\u0900' <= ch <= '\u097f' for ch in entry.title)) else None,
                        "sitemap_priority": entry.priority,
                        "sitemap_lastmod": entry.lastmod,
                        "crawl_depth": 1,
                    })

                total_urls += len(pages_to_insert)
                self.db.insert_pages_batch(site_id, pages_to_insert)

        return (primary_sitemap_url, "found", primary_type, total_urls)

    def crawl_site_pages(self, site_id: int, domain: str, root_url: str) -> dict[str, Any]:
        """Crawls root page and a sample of sitemap URLs to extract internal/external links and Marathi script ratio."""
        links_batch: list[dict[str, Any]] = []
        pages_to_visit = [root_url]

        # Retrieve a batch of unvisited pages for this website
        conn = self.db.get_connection()
        cur = conn.execute(
            "SELECT url FROM pages WHERE website_id = ? AND status_code IS NULL LIMIT ?;",
            (site_id, self.config.max_pages_per_domain),
        )
        for row in cur.fetchall():
            u = row["url"]
            if u not in pages_to_visit:
                pages_to_visit.append(u)

        crawled_count = 0
        marathi_ratios: list[float] = []
        site_title: Optional[str] = None
        site_desc: Optional[str] = None

        for page_url in pages_to_visit[:self.config.max_pages_per_domain]:
            status_code, body, content_type, _ = self._fetch_url(page_url)
            crawled_count += 1

            if status_code == 200 and body:
                html_text = body.decode("utf-8", errors="ignore")
                analysis = analyze_html_content(page_url, html_text)

                if page_url == root_url:
                    site_title = analysis.title
                    site_desc = analysis.meta_description

                if analysis.marathi_char_ratio is not None:
                    marathi_ratios.append(analysis.marathi_char_ratio)

                # Update page record in DB
                parsed_p = urllib.parse.urlsplit(page_url)
                self.db.insert_pages_batch(site_id, [{
                    "url": page_url,
                    "path": parsed_p.path or "/",
                    "title": analysis.title,
                    "status_code": status_code,
                    "content_type": content_type,
                    "marathi_char_ratio": analysis.marathi_char_ratio,
                    "is_marathi": 1 if analysis.is_marathi else 0,
                    "fetched_at": self.db.now_iso(),
                }])

                # Collect internal & external edges
                for link in analysis.internal_links:
                    links_batch.append({
                        "source_domain": link.source_domain,
                        "target_domain": link.target_domain,
                        "source_url": link.source_url,
                        "target_url": link.target_url,
                        "anchor_text": link.anchor_text,
                    })

                for link in analysis.external_links:
                    links_batch.append({
                        "source_domain": link.source_domain,
                        "target_domain": link.target_domain,
                        "source_url": link.source_url,
                        "target_url": link.target_url,
                        "anchor_text": link.anchor_text,
                    })

            else:
                parsed_p = urllib.parse.urlsplit(page_url)
                self.db.insert_pages_batch(site_id, [{
                    "url": page_url,
                    "path": parsed_p.path or "/",
                    "status_code": status_code,
                    "fetched_at": self.db.now_iso(),
                }])

        # Insert graph links in batch
        self.db.insert_links_batch(links_batch)

        # Compute aggregate Marathi script ratio for this domain
        avg_ratio = round(sum(marathi_ratios) / len(marathi_ratios), 4) if marathi_ratios else None
        verified = 1 if (avg_ratio is not None and avg_ratio >= 0.35) else (0 if avg_ratio is not None else None)

        self.db.update_website_language_metrics(
            domain=domain,
            marathi_char_ratio=avg_ratio,
            language_verified=verified,
            title=site_title,
            meta_desc=site_desc,
        )

        return {
            "domain": domain,
            "crawled_pages": crawled_count,
            "links_extracted": len(links_batch),
            "marathi_ratio": avg_ratio,
            "verified": verified,
        }

    def process_single_seed(self, seed: SeedDomain) -> dict[str, Any]:
        """End-to-end processing for a single seed domain."""
        dom = normalize_domain(seed.domain)
        site_id = self.db.upsert_website(
            domain=dom,
            root_url=seed.root_url,
            category=seed.category,
            title=seed.title_mr,
            discovered_via="seed_registry",
        )

        # 1. Sitemap Discovery
        s_url, s_status, s_type, total_sitemap_urls = self.discover_and_parse_sitemaps(
            site_id=site_id,
            domain=dom,
            root_url=seed.root_url,
        )
        self.db.update_website_sitemap_info(
            domain=dom,
            sitemap_url=s_url,
            sitemap_status=s_status,
            sitemap_type=s_type,
            total_sitemap_urls=total_sitemap_urls if s_status == "found" else (0 if s_status == "absent" else None),
        )

        # 2. Page & Link Crawler
        crawl_stats = self.crawl_site_pages(site_id=site_id, domain=dom, root_url=seed.root_url)

        return {
            "domain": dom,
            "category": seed.category,
            "sitemap_status": s_status,
            "sitemap_url": s_url,
            "total_sitemap_urls": total_sitemap_urls,
            "pages_crawled": crawl_stats["crawled_pages"],
            "links_extracted": crawl_stats["links_extracted"],
            "marathi_ratio": crawl_stats["marathi_ratio"],
        }

    def run_crawler_pool(self, seeds: list[SeedDomain]) -> list[dict[str, Any]]:
        """Spawns max number of concurrent worker bots across the domain seeds."""
        total = len(seeds)
        workers = min(self.config.num_workers, total)
        results: list[dict[str, Any]] = []

        print(f"\n🚀 Launching Marathi Web Crawler Engine with {workers} concurrent worker bots...")
        print(f"🎯 Target Seeds: {total} Marathi domains across News, Finance, Agri, Wiki, Govt & Blogs.")

        completed = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_seed = {executor.submit(self.process_single_seed, s): s for s in seeds}
            for future in concurrent.futures.as_completed(future_to_seed):
                seed = future_to_seed[future]
                completed += 1
                try:
                    res = future.result()
                    results.append(res)
                    s_str = f"[{res['sitemap_status']}] {res['total_sitemap_urls']} urls" if res['sitemap_status'] == 'found' else f"[{res['sitemap_status']}]"
                    mr_str = f"{int(res['marathi_ratio']*100)}% mr" if res['marathi_ratio'] is not None else "no-text"
                    print(f"[{completed}/{total}] {seed.domain:26} | Sitemaps: {s_str:20} | Crawled: {res['pages_crawled']} pgs, {res['links_extracted']} links | Script: {mr_str}")
                except Exception as e:
                    print(f"[{completed}/{total}] {seed.domain:26} | ERROR: {e}", file=sys.stderr)
                if self._progress_callback:
                    self._progress_callback(seed.domain, completed, total)

        return results

    def run_recursive_discovery(self, max_candidates: int = 150) -> list[dict[str, Any]]:
        """Auto-discovers new Marathi websites and blogs from existing cross-domain links.
        
        Filters out global utility domains, probes candidates for Devanagari script integrity,
        and automatically indexes verified Marathi domains and their sitemaps.
        """
        from praman.crawler.seeds import GLOBAL_IGNORE_DOMAINS

        conn = self.db.get_connection()
        cur = conn.execute("""
            SELECT target_domain, COUNT(*) as in_refs, MIN(target_url) as sample_url
            FROM links
            WHERE is_internal = 0 
              AND target_domain NOT IN (SELECT domain FROM websites)
            GROUP BY target_domain
            ORDER BY in_refs DESC;
        """)
        candidates_raw = cur.fetchall()

        candidate_domains = []
        for row in candidates_raw:
            dom = row["target_domain"].strip().lower()
            if not dom or dom in GLOBAL_IGNORE_DOMAINS:
                continue
            # Filter obvious CDN/API/Ad domains
            if any(dom.endswith(suffix) for suffix in (
                "google.com", "facebook.com", "twitter.com", "x.com", "instagram.com",
                "youtube.com", "whatsapp.com", "apple.com", "amazon.com", "cloudflare.com",
                ".doubleclick.net", ".googlesyndication.com", ".akamai.net", ".cloudfront.net"
            )):
                continue
            candidate_domains.append((dom, row["sample_url"], row["in_refs"]))

        candidate_domains = candidate_domains[:max_candidates]
        print(f"\n🔍 Discovered {len(candidate_domains)} unmapped candidate external domains from links graph.")
        print(f"⚡ Probing with {self.config.num_workers} concurrent worker bots for Marathi language & sitemaps...")

        discovered_marathi: list[dict[str, Any]] = []

        def probe_candidate(item: tuple[str, str, int]) -> Optional[dict[str, Any]]:
            dom, sample_url, refs = item
            root_url = f"https://{dom}/"
            status, body, _, _ = self._fetch_url(root_url)
            if status != 200 or not body:
                # Try with http or sample url
                status, body, _, _ = self._fetch_url(sample_url)
                if status != 200 or not body:
                    return None

            html_text = body.decode("utf-8", errors="ignore")
            analysis = analyze_html_content(root_url, html_text)

            is_mr = False
            if analysis.marathi_char_ratio is not None and analysis.marathi_char_ratio >= 0.20:
                is_mr = True
            elif analysis.html_lang and "mr" in analysis.html_lang:
                is_mr = True
            elif analysis.title and any('\u0900' <= ch <= '\u097f' for ch in analysis.title):
                is_mr = True

            if not is_mr:
                return None

            # Categorize discovered site
            cat = "Blogs & General"
            t_lower = (analysis.title or "").lower()
            d_lower = dom.lower()
            if any(w in t_lower or w in d_lower for w in ("news", "बातमी", "पत्र", "वृत्त", "tv", "times", "live", "epaper")):
                cat = "News & Media"
            elif any(w in t_lower or w in d_lower for w in ("finance", "शेअर", "पैसा", "नोकरी", "job", "recruitment", "bharti")):
                cat = "Finance & Career"
            elif any(w in t_lower or w in d_lower for w in ("शेती", "krushi", "agri", "मंडी", "बाजार")):
                cat = "Agriculture"
            elif any(w in t_lower or w in d_lower for w in ("gov", "शासन", "महा", "योजना")):
                cat = "Government"
            elif any(w in t_lower or w in d_lower for w in ("साहित्य", "कविता", "कथा", "ज्ञान", "कोश")):
                cat = "Community & Literature"

            # Register into DB
            seed = SeedDomain(
                domain=dom,
                root_url=root_url,
                category=cat,
                title_mr=analysis.title or dom,
                notes=f"Auto-discovered via {refs} inbound citations.",
            )
            res = self.process_single_seed(seed)
            return res

        completed = 0
        total = len(candidate_domains)
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.num_workers) as executor:
            future_to_dom = {executor.submit(probe_candidate, item): item for item in candidate_domains}
            for future in concurrent.futures.as_completed(future_to_dom):
                item = future_to_dom[future]
                completed += 1
                try:
                    res = future.result()
                    if res:
                        discovered_marathi.append(res)
                        s_str = f"[{res['sitemap_status']}] {res['total_sitemap_urls']} urls" if res['sitemap_status'] == 'found' else f"[{res['sitemap_status']}]"
                        mr_str = f"{int(res['marathi_ratio']*100)}% mr" if res['marathi_ratio'] is not None else "no-text"
                        print(f"✨ [NEW MARATHI DOMAIN] {res['domain']:26} | Category: {res['category']:20} | Sitemaps: {s_str:20} | Script: {mr_str}")
                except Exception:
                    pass

        print(f"\n🎉 Auto-discovery completed: Found and mapped {len(discovered_marathi)} NEW Marathi websites!")
        return discovered_marathi


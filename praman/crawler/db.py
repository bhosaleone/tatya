"""SQLite Database layer for Marathi Web Crawler and Knowledge Graph.

Features:
- WAL (Write-Ahead Logging) mode for concurrent readers and writer.
- Strict schema with foreign keys and covering indexes.
- Distinguishes absent measurements (None) from measured zeros (0.0) per MATH.md.
"""

from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any, Optional
import datetime
import threading


class CrawlerDB:
    """Thread-safe SQLite database manager for Marathi Web Graph."""

    def __init__(self, db_path: Path | str = "marathi_web.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=60.0,
                check_same_thread=False,
                isolation_level=None,  # Autocommit mode, we manage transactions explicitly
            )
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def _init_db(self) -> None:
        """Creates tables, constraints, and indexes if they do not exist."""
        conn = self.get_connection()
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='websites';")
        if cur.fetchone() is not None:
            return

        with self._lock:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='websites';")
            if cur.fetchone() is not None:
                return
            conn.execute("BEGIN IMMEDIATE;")
            try:
                # 1. Websites table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS websites (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        domain TEXT UNIQUE NOT NULL,
                        root_url TEXT NOT NULL,
                        title TEXT,
                        meta_description TEXT,
                        category TEXT NOT NULL DEFAULT 'General',
                        marathi_char_ratio REAL,            -- NULL if unmeasured, float in [0.0, 1.0]
                        language_verified INTEGER,          -- NULL: unmeasured, 1: confirmed mr, 0: not mr
                        sitemap_url TEXT,
                        sitemap_status TEXT DEFAULT 'unmeasured', -- 'unmeasured', 'found', 'absent', 'error', 'timeout'
                        sitemap_type TEXT,                  -- 'sitemapindex', 'urlset', 'rss', 'none'
                        total_sitemap_urls INTEGER,         -- NULL if unmeasured, int >= 0
                        pages_crawled INTEGER DEFAULT 0,
                        internal_links_count INTEGER DEFAULT 0,
                        external_links_count INTEGER DEFAULT 0,
                        in_degree INTEGER DEFAULT 0,
                        out_degree INTEGER DEFAULT 0,
                        pagerank REAL,                      -- NULL if uncomputed, float
                        hub_score REAL,                     -- HITS hub score
                        authority_score REAL,               -- HITS authority score
                        status TEXT DEFAULT 'active',       -- 'active', 'unreachable', 'blocked'
                        discovered_via TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                """)

                # 2. Sitemaps table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sitemaps (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        website_id INTEGER NOT NULL REFERENCES websites(id) ON DELETE CASCADE,
                        sitemap_url TEXT UNIQUE NOT NULL,
                        parent_sitemap_url TEXT,
                        sitemap_type TEXT NOT NULL,        -- 'index', 'urlset', 'gz', 'rss'
                        url_count INTEGER,                  -- NULL if unmeasured, int >= 0
                        status_code INTEGER,
                        error_message TEXT,
                        discovered_at TEXT NOT NULL
                    );
                """)

                # 3. Pages table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS pages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        website_id INTEGER NOT NULL REFERENCES websites(id) ON DELETE CASCADE,
                        url TEXT UNIQUE NOT NULL,
                        path TEXT NOT NULL,
                        title TEXT,
                        status_code INTEGER,
                        content_type TEXT,
                        marathi_char_ratio REAL,            -- NULL if unmeasured
                        is_marathi INTEGER,                 -- NULL if unmeasured, 1 or 0
                        sitemap_priority REAL,
                        sitemap_lastmod TEXT,
                        crawl_depth INTEGER DEFAULT 0,
                        internal_outlinks INTEGER DEFAULT 0,
                        external_outlinks INTEGER DEFAULT 0,
                        in_degree INTEGER DEFAULT 0,
                        pagerank REAL,
                        fetched_at TEXT
                    );
                """)

                # 4. Links table (Edges in the Web Knowledge Graph)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS links (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_domain TEXT NOT NULL,
                        target_domain TEXT NOT NULL,
                        source_url TEXT NOT NULL,
                        target_url TEXT NOT NULL,
                        anchor_text TEXT,
                        is_internal INTEGER NOT NULL,       -- 1 if source_domain == target_domain, else 0
                        discovered_at TEXT NOT NULL,
                        UNIQUE(source_url, target_url)
                    );
                """)

                # 5. Graph snapshots and macro metrics
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS graph_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        calculated_at TEXT NOT NULL,
                        total_domains INTEGER NOT NULL,
                        total_pages INTEGER NOT NULL,
                        total_sitemaps INTEGER NOT NULL,
                        total_internal_links INTEGER NOT NULL,
                        total_external_links INTEGER NOT NULL,
                        cross_domain_edges INTEGER NOT NULL,
                        graph_density REAL,
                        reciprocity REAL,
                        top_authorities_json TEXT,
                        top_hubs_json TEXT,
                        category_distribution_json TEXT
                    );
                """)

                # Indexes for lightning-fast queries
                conn.execute("CREATE INDEX IF NOT EXISTS idx_websites_domain ON websites(domain);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_websites_category ON websites(category);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sitemaps_website ON sitemaps(website_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_pages_website ON pages(website_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_pages_url ON pages(url);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_links_src_tgt ON links(source_domain, target_domain);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_links_internal ON links(is_internal);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_links_source_url ON links(source_url);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_links_target_url ON links(target_url);")

                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    def now_iso(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def upsert_website(
        self,
        domain: str,
        root_url: str,
        category: str = "General",
        title: Optional[str] = None,
        discovered_via: Optional[str] = None,
    ) -> int:
        """Inserts or retrieves website record id."""
        conn = self.get_connection()
        now = self.now_iso()
        with self._lock:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                conn.execute(
                    """
                    INSERT INTO websites (domain, root_url, category, title, discovered_via, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(domain) DO UPDATE SET
                        category = COALESCE(websites.category, excluded.category),
                        title = COALESCE(excluded.title, websites.title),
                        updated_at = excluded.updated_at
                    ;
                    """,
                    (domain, root_url, category, title, discovered_via, now, now),
                )
                cur = conn.execute("SELECT id FROM websites WHERE domain = ?", (domain,))
                row = cur.fetchone()
                conn.execute("COMMIT;")
                return row["id"] if row else 0
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    def update_website_sitemap_info(
        self,
        domain: str,
        sitemap_url: Optional[str],
        sitemap_status: str,
        sitemap_type: Optional[str],
        total_sitemap_urls: Optional[int],
    ) -> None:
        """Updates sitemap status for a domain with strict provenance."""
        conn = self.get_connection()
        now = self.now_iso()
        with self._lock:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                conn.execute(
                    """
                    UPDATE websites SET
                        sitemap_url = COALESCE(?, sitemap_url),
                        sitemap_status = ?,
                        sitemap_type = COALESCE(?, sitemap_type),
                        total_sitemap_urls = ?,
                        updated_at = ?
                    WHERE domain = ?;
                    """,
                    (sitemap_url, sitemap_status, sitemap_type, total_sitemap_urls, now, domain),
                )
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    def update_website_language_metrics(
        self,
        domain: str,
        marathi_char_ratio: Optional[float],
        language_verified: Optional[int],
        title: Optional[str] = None,
        meta_desc: Optional[str] = None,
    ) -> None:
        """Updates Marathi script ratio and title for a domain."""
        conn = self.get_connection()
        now = self.now_iso()
        with self._lock:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                conn.execute(
                    """
                    UPDATE websites SET
                        marathi_char_ratio = ?,
                        language_verified = ?,
                        title = COALESCE(?, title),
                        meta_description = COALESCE(?, meta_description),
                        updated_at = ?
                    WHERE domain = ?;
                    """,
                    (marathi_char_ratio, language_verified, title, meta_desc, now, domain),
                )
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    def insert_sitemap(
        self,
        website_id: int,
        sitemap_url: str,
        sitemap_type: str,
        url_count: Optional[int],
        parent_sitemap_url: Optional[str] = None,
        status_code: Optional[int] = 200,
        error_message: Optional[str] = None,
    ) -> int:
        """Records a discovered sitemap or sub-sitemap."""
        conn = self.get_connection()
        now = self.now_iso()
        with self._lock:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                conn.execute(
                    """
                    INSERT INTO sitemaps (website_id, sitemap_url, parent_sitemap_url, sitemap_type, url_count, status_code, error_message, discovered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(sitemap_url) DO UPDATE SET
                        url_count = COALESCE(excluded.url_count, sitemaps.url_count),
                        status_code = excluded.status_code,
                        error_message = excluded.error_message
                    ;
                    """,
                    (website_id, sitemap_url, parent_sitemap_url, sitemap_type, url_count, status_code, error_message, now),
                )
                cur = conn.execute("SELECT id FROM sitemaps WHERE sitemap_url = ?", (sitemap_url,))
                row = cur.fetchone()
                conn.execute("COMMIT;")
                return row["id"] if row else 0
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    def insert_pages_batch(
        self,
        website_id: int,
        pages_data: list[dict[str, Any]],
    ) -> int:
        """Batch inserts pages found in sitemaps or crawling. Returns count of inserted pages."""
        if not pages_data:
            return 0
        conn = self.get_connection()
        now = self.now_iso()
        inserted = 0
        with self._lock:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                for p in pages_data:
                    cur = conn.execute(
                        """
                        INSERT INTO pages (
                            website_id, url, path, title, status_code, content_type,
                            marathi_char_ratio, is_marathi, sitemap_priority, sitemap_lastmod,
                            crawl_depth, fetched_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(url) DO UPDATE SET
                            title = COALESCE(excluded.title, pages.title),
                            status_code = COALESCE(excluded.status_code, pages.status_code),
                            marathi_char_ratio = COALESCE(excluded.marathi_char_ratio, pages.marathi_char_ratio),
                            is_marathi = COALESCE(excluded.is_marathi, pages.is_marathi),
                            sitemap_lastmod = COALESCE(excluded.sitemap_lastmod, pages.sitemap_lastmod),
                            fetched_at = COALESCE(excluded.fetched_at, pages.fetched_at)
                        ;
                        """,
                        (
                            website_id,
                            p["url"],
                            p.get("path", ""),
                            p.get("title"),
                            p.get("status_code"),
                            p.get("content_type"),
                            p.get("marathi_char_ratio"),
                            p.get("is_marathi"),
                            p.get("sitemap_priority"),
                            p.get("sitemap_lastmod"),
                            p.get("crawl_depth", 0),
                            p.get("fetched_at", now),
                        ),
                    )
                    if cur.rowcount > 0:
                        inserted += 1
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise
        return inserted

    def insert_links_batch(self, links_data: list[dict[str, Any]]) -> int:
        """Batch inserts graph edges (links between pages and domains)."""
        if not links_data:
            return 0
        conn = self.get_connection()
        now = self.now_iso()
        inserted = 0
        with self._lock:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                for link in links_data:
                    is_int = 1 if link["source_domain"] == link["target_domain"] else 0
                    cur = conn.execute(
                        """
                        INSERT OR IGNORE INTO links (
                            source_domain, target_domain, source_url, target_url, anchor_text, is_internal, discovered_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            link["source_domain"],
                            link["target_domain"],
                            link["source_url"],
                            link["target_url"],
                            link.get("anchor_text", ""),
                            is_int,
                            now,
                        ),
                    )
                    if cur.rowcount > 0:
                        inserted += 1
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise
        return inserted

    def get_all_websites(self) -> list[dict[str, Any]]:
        """Returns all website records."""
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM websites ORDER BY id ASC;")
        return [dict(row) for row in cur.fetchall()]

    def get_website_by_domain(self, domain: str) -> Optional[dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM websites WHERE domain = ?;", (domain,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_domain_link_matrix(self) -> list[dict[str, Any]]:
        """Returns aggregated directed edges between domains for the Knowledge Graph."""
        conn = self.get_connection()
        cur = conn.execute("""
            SELECT
                source_domain,
                target_domain,
                is_internal,
                COUNT(*) as link_count
            FROM links
            GROUP BY source_domain, target_domain;
        """)
        return [dict(row) for row in cur.fetchall()]

    def update_graph_scores(
        self,
        domain_scores: dict[str, dict[str, float | int]],
    ) -> None:
        """Updates in_degree, out_degree, pagerank, hub_score, authority_score for domains."""
        conn = self.get_connection()
        now = self.now_iso()
        with self._lock:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                for domain, scores in domain_scores.items():
                    conn.execute(
                        """
                        UPDATE websites SET
                            in_degree = ?,
                            out_degree = ?,
                            pagerank = ?,
                            hub_score = ?,
                            authority_score = ?,
                            internal_links_count = ?,
                            external_links_count = ?,
                            updated_at = ?
                        WHERE domain = ?;
                        """,
                        (
                            scores.get("in_degree", 0),
                            scores.get("out_degree", 0),
                            scores.get("pagerank", 0.0),
                            scores.get("hub_score", 0.0),
                            scores.get("authority_score", 0.0),
                            scores.get("internal_links", 0),
                            scores.get("external_links", 0),
                            now,
                            domain,
                        ),
                    )
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    def record_graph_snapshot(self, snapshot: dict[str, Any]) -> int:
        """Stores a historical macro snapshot of the Marathi Web Knowledge Graph."""
        conn = self.get_connection()
        now = self.now_iso()
        with self._lock:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                cur = conn.execute(
                    """
                    INSERT INTO graph_snapshots (
                        calculated_at, total_domains, total_pages, total_sitemaps,
                        total_internal_links, total_external_links, cross_domain_edges,
                        graph_density, reciprocity, top_authorities_json, top_hubs_json,
                        category_distribution_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        now,
                        snapshot["total_domains"],
                        snapshot["total_pages"],
                        snapshot["total_sitemaps"],
                        snapshot["total_internal_links"],
                        snapshot["total_external_links"],
                        snapshot["cross_domain_edges"],
                        snapshot["graph_density"],
                        snapshot["reciprocity"],
                        snapshot["top_authorities_json"],
                        snapshot["top_hubs_json"],
                        snapshot["category_distribution_json"],
                    ),
                )
                snap_id = cur.lastrowid
                conn.execute("COMMIT;")
                return snap_id or 0
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    def get_summary_stats(self) -> dict[str, Any]:
        """Calculates global counts across the database."""
        conn = self.get_connection()
        total_domains = conn.execute("SELECT COUNT(*) FROM websites;").fetchone()[0]
        verified_mr = conn.execute("SELECT COUNT(*) FROM websites WHERE language_verified = 1;").fetchone()[0]
        sitemaps_found = conn.execute("SELECT COUNT(*) FROM websites WHERE sitemap_status = 'found';").fetchone()[0]
        total_sitemaps = conn.execute("SELECT COUNT(*) FROM sitemaps;").fetchone()[0]
        total_pages = conn.execute("SELECT COUNT(*) FROM pages;").fetchone()[0]
        total_links = conn.execute("SELECT COUNT(*) FROM links;").fetchone()[0]
        internal_links = conn.execute("SELECT COUNT(*) FROM links WHERE is_internal = 1;").fetchone()[0]
        external_links = conn.execute("SELECT COUNT(*) FROM links WHERE is_internal = 0;").fetchone()[0]
        total_sitemap_urls = conn.execute("SELECT SUM(total_sitemap_urls) FROM websites WHERE total_sitemap_urls IS NOT NULL;").fetchone()[0] or 0

        return {
            "total_domains": total_domains,
            "verified_marathi_domains": verified_mr,
            "domains_with_sitemaps": sitemaps_found,
            "total_sitemaps_indexed": total_sitemaps,
            "total_sitemap_urls_discovered": total_sitemap_urls,
            "total_pages_stored": total_pages,
            "total_links_stored": total_links,
            "internal_links": internal_links,
            "external_links": external_links,
        }

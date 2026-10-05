"""High-speed Sitemap and Robots.txt Parser for Marathi Websites.

Handles:
- robots.txt discovery and Sitemap directives extraction.
- Standard sitemapindex with recursive resolution.
- URL set parsing with <loc>, <lastmod>, <priority>.
- Gzipped sitemaps (.xml.gz).
- RSS / Atom feed fallback when XML sitemaps are absent.
"""

from __future__ import annotations
import gzip
import io
import re
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional


@dataclass
class SitemapUrlEntry:
    loc: str
    title: Optional[str] = None
    lastmod: Optional[str] = None
    priority: Optional[float] = None
    changefreq: Optional[str] = None


@dataclass
class SitemapResult:
    sitemap_url: str
    sitemap_type: str  # 'sitemapindex', 'urlset', 'feed', 'error'
    child_sitemaps: list[str]
    urls: list[SitemapUrlEntry]
    raw_status: int = 200
    error: Optional[str] = None


class SitemapParser:
    """Parses robots.txt, XML sitemaps, sitemapindex, and feeds."""

    @staticmethod
    def extract_sitemaps_from_robots(robots_txt_content: str, base_url: str) -> list[str]:
        """Extracts all 'Sitemap: ...' directives from robots.txt content."""
        sitemaps: list[str] = []
        for line in robots_txt_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"^sitemap:\s*(.+)$", line, re.IGNORECASE)
            if match:
                raw_url = match.group(1).strip()
                full_url = urllib.parse.urljoin(base_url, raw_url)
                if full_url not in sitemaps:
                    sitemaps.append(full_url)
        return sitemaps

    @staticmethod
    def decompress_if_gzip(raw_bytes: bytes) -> bytes:
        """Decompresses gzip bytes if magic header (1f 8b) is present."""
        if len(raw_bytes) >= 2 and raw_bytes[:2] == b"\x1f\x8b":
            try:
                with gzip.GzipFile(fileobj=io.BytesIO(raw_bytes)) as gz:
                    return gz.read()
            except Exception:
                return raw_bytes
        return raw_bytes

    @classmethod
    def parse_sitemap_xml(cls, content_bytes: bytes, sitemap_url: str) -> SitemapResult:
        """Parses sitemap XML content, detecting whether it is an index or urlset."""
        data = cls.decompress_if_gzip(content_bytes)
        
        # Quick strip of UTF-8 BOM if present
        if data.startswith(b"\xef\xbb\xbf"):
            data = data[3:]

        try:
            # Parse XML tree
            root = ET.fromstring(data)
        except ET.ParseError as pe:
            # Fallback regex extraction if XML is slightly malformed
            return cls._fallback_regex_parse(data.decode("utf-8", errors="ignore"), sitemap_url, str(pe))

        tag = root.tag.split("}")[-1].lower()

        if tag == "sitemapindex":
            # Nested sitemaps
            child_sitemaps: list[str] = []
            for sitemap_node in root.findall(".//{*}sitemap"):
                loc_node = sitemap_node.find("{*}loc")
                if loc_node is not None and loc_node.text:
                    url_clean = loc_node.text.strip()
                    if url_clean:
                        child_sitemaps.append(url_clean)
            return SitemapResult(
                sitemap_url=sitemap_url,
                sitemap_type="sitemapindex",
                child_sitemaps=child_sitemaps,
                urls=[],
                raw_status=200,
            )

        elif tag == "urlset":
            # Direct URLs
            entries: list[SitemapUrlEntry] = []
            for url_node in root.findall(".//{*}url"):
                loc_node = url_node.find("{*}loc")
                if loc_node is None or not loc_node.text:
                    continue
                loc_val = loc_node.text.strip()
                if not loc_val:
                    continue

                lastmod_node = url_node.find("{*}lastmod")
                lastmod_val = lastmod_node.text.strip() if lastmod_node is not None and lastmod_node.text else None

                prio_node = url_node.find("{*}priority")
                prio_val = None
                if prio_node is not None and prio_node.text:
                    try:
                        prio_val = float(prio_node.text.strip())
                    except ValueError:
                        pass

                title_node = url_node.find(".//{*}title")
                title_val = title_node.text.strip() if title_node is not None and title_node.text else None

                entries.append(SitemapUrlEntry(
                    loc=loc_val,
                    title=title_val,
                    lastmod=lastmod_val,
                    priority=prio_val,
                    changefreq=cf_val,
                ))

            return SitemapResult(
                sitemap_url=sitemap_url,
                sitemap_type="urlset",
                child_sitemaps=[],
                urls=entries,
                raw_status=200,
            )

        elif tag in ("rss", "feed"):
            # RSS or Atom feed acting as a sitemap
            return cls._parse_feed_xml(root, sitemap_url)

        else:
            return SitemapResult(
                sitemap_url=sitemap_url,
                sitemap_type="unknown",
                child_sitemaps=[],
                urls=[],
                raw_status=200,
                error=f"Unrecognized XML root tag: {root.tag}",
            )

    @classmethod
    def _parse_feed_xml(cls, root: ET.Element, sitemap_url: str) -> SitemapResult:
        """Extracts URLs from RSS <item><link> or Atom <entry><link>."""
        entries: list[SitemapUrlEntry] = []
        # RSS 2.0
        for item in root.findall(".//item"):
            link_node = item.find("link")
            if link_node is not None and link_node.text:
                pubdate = item.find("pubDate")
                title_node = item.find("title")
                title_val = title_node.text.strip() if title_node is not None and title_node.text else None
                entries.append(SitemapUrlEntry(
                    loc=link_node.text.strip(),
                    title=title_val,
                    lastmod=pubdate.text.strip() if pubdate is not None and pubdate.text else None,
                ))

        # Atom
        for entry in root.findall(".//{*}entry"):
            link_node = entry.find("{*}link")
            href = link_node.get("href") if link_node is not None else None
            updated = entry.find("{*}updated")
            title_node = entry.find("{*}title")
            title_val = title_node.text.strip() if title_node is not None and title_node.text else None
            if href:
                entries.append(SitemapUrlEntry(
                    loc=href.strip(),
                    title=title_val,
                    lastmod=updated.text.strip() if updated is not None and updated.text else None,
                ))

        return SitemapResult(
            sitemap_url=sitemap_url,
            sitemap_type="feed",
            child_sitemaps=[],
            urls=entries,
            raw_status=200,
        )

    @classmethod
    def _fallback_regex_parse(cls, text: str, sitemap_url: str, parse_err: str) -> SitemapResult:
        """Regex fallback to rescue URLs if XML has minor encoding or tag syntax errors."""
        loc_pattern = re.compile(r"<loc>\s*(https?://[^\s<>]+)\s*</loc>", re.IGNORECASE)
        matches = loc_pattern.findall(text)
        if not matches:
            return SitemapResult(
                sitemap_url=sitemap_url,
                sitemap_type="error",
                child_sitemaps=[],
                urls=[],
                raw_status=200,
                error=f"XML ParseError: {parse_err}",
            )

        # Decide if matches look like child sitemaps or URLs
        is_index = any(".xml" in m.lower() for m in matches[:5])
        if is_index and "<sitemap>" in text.lower():
            return SitemapResult(
                sitemap_url=sitemap_url,
                sitemap_type="sitemapindex",
                child_sitemaps=matches,
                urls=[],
                raw_status=200,
            )
        else:
            entries = [SitemapUrlEntry(loc=m) for m in matches]
            return SitemapResult(
                sitemap_url=sitemap_url,
                sitemap_type="urlset",
                child_sitemaps=[],
                urls=entries,
                raw_status=200,
            )

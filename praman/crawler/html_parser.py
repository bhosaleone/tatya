"""Lightweight streaming HTML link, title, and Marathi script parser.

Zero external dependencies (uses standard library html.parser.HTMLParser).
Computes:
- Title and meta description
- Marathi Devanagari character ratio
- Internal and external link extraction with anchor texts
- URL normalization and query cleaning
"""

from __future__ import annotations
import html
from html.parser import HTMLParser
import re
import urllib.parse
from dataclasses import dataclass
from typing import Optional

from praman.script import char_script


@dataclass
class ExtractedLink:
    source_url: str
    target_url: str
    source_domain: str
    target_domain: str
    is_internal: bool
    anchor_text: str


@dataclass
class HtmlAnalysisResult:
    url: str
    domain: str
    title: Optional[str]
    meta_description: Optional[str]
    html_lang: Optional[str]
    marathi_char_ratio: Optional[float]  # None if no text was found
    is_marathi: Optional[bool]           # None if unmeasured
    internal_links: list[ExtractedLink]
    external_links: list[ExtractedLink]


def normalize_domain(netloc: str) -> str:
    """Normalizes netloc: strips port, lowercases, removes leading www. for clean grouping."""
    host = netloc.split(":")[0].lower().strip()
    # Strip leading www. so www.loksatta.com and loksatta.com map to loksatta.com
    if host.startswith("www."):
        host = host[4:]
    return host


def clean_url(base_url: str, raw_href: str) -> Optional[str]:
    """Resolves relative link to absolute URL and strips tracking noise and fragments."""
    if not raw_href:
        return None
    raw_href = raw_href.strip()
    if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:", "data:", "whatsapp:")):
        return None

    try:
        resolved = urllib.parse.urljoin(base_url, raw_href)
        parsed = urllib.parse.urlsplit(resolved)
        if parsed.scheme not in ("http", "https"):
            return None
        if not parsed.netloc:
            return None

        # Clean query parameters: remove utm_*, fbclid, gclid
        clean_query_pairs = []
        if parsed.query:
            qs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            for k, v in qs:
                k_lower = k.lower()
                if not (k_lower.startswith("utm_") or k_lower in ("fbclid", "gclid", "ref", "mc_cid")):
                    clean_query_pairs.append((k, v))
        new_query = urllib.parse.urlencode(clean_query_pairs)

        clean_path = parsed.path or "/"
        # Collapse double slashes
        clean_path = re.sub(r"/+", "/", clean_path)

        clean_tuple = (parsed.scheme, parsed.netloc.lower(), clean_path, new_query, "")
        return urllib.parse.urlunsplit(clean_tuple)
    except Exception:
        return None


class StreamingHtmlParser(HTMLParser):
    """Fast streaming HTML parser to extract links, title, and Marathi text."""

    def __init__(self, page_url: str, page_domain: str):
        super().__init__()
        self.page_url = page_url
        self.page_domain = normalize_domain(page_domain)
        
        self.in_title = False
        self.title_parts: list[str] = []
        self.title: Optional[str] = None
        self.meta_desc: Optional[str] = None
        self.html_lang: Optional[str] = None

        self.current_a_href: Optional[str] = None
        self.current_a_text: list[str] = []
        self.links: list[ExtractedLink] = []
        self._seen_target_urls: set[str] = set()

        self.visible_text_parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        tag_lower = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if tag_lower == "html":
            if "lang" in attr_dict:
                self.html_lang = attr_dict["lang"].strip().lower()

        elif tag_lower == "title":
            self.in_title = True

        elif tag_lower == "meta":
            name = attr_dict.get("name", "").lower()
            prop = attr_dict.get("property", "").lower()
            content = attr_dict.get("content", "").strip()
            if (name == "description" or prop == "og:description") and not self.meta_desc:
                self.meta_desc = html.unescape(content)

        elif tag_lower in ("script", "style", "noscript", "svg"):
            self._skip_depth += 1

        elif tag_lower == "a":
            href = attr_dict.get("href")
            if href:
                self.current_a_href = href
                self.current_a_text = []

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower == "title":
            self.in_title = False
            raw_title = "".join(self.title_parts).strip()
            self.title = html.unescape(raw_title) if raw_title else None

        elif tag_lower in ("script", "style", "noscript", "svg"):
            if self._skip_depth > 0:
                self._skip_depth -= 1

        elif tag_lower == "a":
            if self.current_a_href:
                target_url = clean_url(self.page_url, self.current_a_href)
                if target_url and target_url not in self._seen_target_urls and target_url != self.page_url:
                    self._seen_target_urls.add(target_url)
                    parsed_target = urllib.parse.urlsplit(target_url)
                    target_dom = normalize_domain(parsed_target.netloc)
                    is_int = (target_dom == self.page_domain) or target_dom.endswith("." + self.page_domain)
                    anchor_txt = html.unescape(" ".join(self.current_a_text).strip())

                    self.links.append(ExtractedLink(
                        source_url=self.page_url,
                        target_url=target_url,
                        source_domain=self.page_domain,
                        target_domain=target_dom,
                        is_internal=is_int,
                        anchor_text=anchor_txt[:150],
                    ))
            self.current_a_href = None
            self.current_a_text = []

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.current_a_href is not None:
            self.current_a_text.append(data.strip())
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self.visible_text_parts.append(stripped)


def analyze_html_content(page_url: str, html_content: str) -> HtmlAnalysisResult:
    """Parses HTML string and returns analysis with language metrics and links."""
    parsed_page = urllib.parse.urlsplit(page_url)
    domain = normalize_domain(parsed_page.netloc)
    
    parser = StreamingHtmlParser(page_url, domain)
    try:
        parser.feed(html_content)
    except Exception:
        pass  # html.parser gracefully handles partial recovery

    # Script / Devanagari ratio calculation
    full_text = " ".join(parser.visible_text_parts)
    alpha_count = 0
    devanagari_count = 0

    for ch in full_text:
        s = char_script(ch)
        if s is not None:
            alpha_count += 1
            if s == "devanagari":
                devanagari_count += 1

    if alpha_count > 0:
        ratio = round(devanagari_count / alpha_count, 4)
        is_mr = ratio >= 0.40 or (parser.html_lang and "mr" in parser.html_lang)
    else:
        # Absence of text measurement: MATH.md I1
        ratio = None
        is_mr = None

    internal = [l for l in parser.links if l.is_internal]
    external = [l for l in parser.links if not l.is_internal]

    return HtmlAnalysisResult(
        url=page_url,
        domain=domain,
        title=parser.title,
        meta_description=parser.meta_desc,
        html_lang=parser.html_lang,
        marathi_char_ratio=ratio,
        is_marathi=is_mr,
        internal_links=internal,
        external_links=external,
    )

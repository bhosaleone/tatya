"""Selenium-based SERP automation for controlled Google search + date extraction.

Implements human-like pacing, CAPTCHA detection, caching, and structured extraction.
Designed as an opt-in extension to Praman (not imported by core modules).
"""

from __future__ import annotations

import json
import random
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Sequence

from praman.errors import CaptchaDetectedError


CAPTCHA_INDICATORS = [
    "recaptcha",
    "captcha",
    "unusual traffic",
    "prove you're not a robot",
    "security check",
    "detected unusual activity",
    "your computer or network may be sending automated queries",
]


ORGANIC_SELECTOR_CANDIDATES = [
    "div.g",
    "div.MjjYud",
    "div.tF2Cxc",
    "div.yuRUbf",
]


DATE_META_SELECTORS = [
    'meta[property="article:published_time"]',
    'meta[name="date"]',
    'meta[name="publish-date"]',
    'meta[itemprop="datePublished"]',
    'meta[property="og:published_time"]',
]

DATE_MODIFIED_META_SELECTORS = [
    'meta[property="article:modified_time"]',
    'meta[property="og:modified_time"]',
    'meta[itemprop="dateModified"]',
]


@dataclass
class SerpResultRow:
    rank: int
    title: str
    url: str
    domain: str
    published_date: Optional[str] = None
    modified_date: Optional[str] = None
    date_source: str = "NONE"
    date_confidence: str = "NONE"
    extracted_at: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SerpDateExtracted:
    published: Optional[str] = None
    modified: Optional[str] = None
    source: str = "NONE"
    confidence: str = "NONE"


class SerpBrowser:
    def __init__(
        self,
        headless: bool = False,
        min_delay: float = 18.0,
        max_delay: float = 28.0,
        min_page_wait: float = 0.8,
        max_page_wait: float = 1.8,
        close_after_each: bool = True,
        user_agent: Optional[str] = None,
        chrome_options: Optional["object"] = None,  # type: ignore[name-defined]
    ):
        self.headless = headless
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.min_page_wait = min_page_wait
        self.max_page_wait = max_page_wait
        self.close_after_each = close_after_each
        self.user_agent = user_agent
        self.chrome_options = chrome_options
        self.driver = None

    def _init_driver(self):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
        except Exception as e:
            raise ImportError(
                "selenium is required for serp-auto/serp-dates. Install with: pip install selenium"
            ) from e

        options = self.chrome_options or Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--lang=hi,ml,ta,te,bn,gu,kn,mr,en-US,en")
        if self.user_agent:
            options.add_argument(f"--user-agent={self.user_agent}")

        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.set_window_size(random.randint(1280, 1920), random.randint(720, 1080))
        self.driver = driver
        return driver

    def _get_driver(self):
        if self.driver is None or self.close_after_each:
            return self._init_driver()
        return self.driver

    def _close_driver(self):
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def _human_sleep(self, base: float = None):
        base = base or random.uniform(self.min_delay, self.max_delay)
        time.sleep(base)

    def _page_sleep(self):
        time.sleep(random.uniform(self.min_page_wait, self.max_page_wait))

    def _detect_captcha(self, html: str = "", title: str = ""):
        combined = (html + " " + title).lower()
        for ind in CAPTCHA_INDICATORS:
            if ind in combined:
                return True
        try:
            if self.driver:
                for ind in CAPTCHA_INDICATORS:
                    if ind in self.driver.page_source.lower() or ind in self.driver.title.lower():
                        return True
        except Exception:
            pass
        return False

    def _extract_dates(self, url: str, keyword: str) -> SerpDateExtracted:
        driver = self._get_driver()
        try:
            driver.get(url)
            self._page_sleep()
            if self._detect_captcha():
                raise CaptchaDetectedError(f"CAPTCHA detected while visiting {url}")
            html = driver.page_source
        except CaptchaDetectedError:
            self._close_driver()
            raise
        except Exception as e:
            if self.close_after_each:
                self._close_driver()
            return SerpDateExtracted(source="ERROR", confidence="NONE")

        # 1) JSON-LD
        try:
            from selenium.webdriver.common.by import By

            scripts = driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]')
            for script in scripts:
                try:
                    raw = script.get_attribute("innerHTML")
                    data = json.loads(raw)
                    objects = data if isinstance(data, list) else [data]
                    for obj in objects:
                        if isinstance(obj, dict):
                            pub = obj.get("datePublished")
                            mod = obj.get("dateModified")
                            if pub or mod:
                                return SerpDateExtracted(published=pub, modified=mod, source="JSON-LD", confidence="HIGH")
                except Exception:
                    continue
        except Exception:
            pass

        # 2) <time datetime>
        try:
            from selenium.webdriver.common.by import By

            times = driver.find_elements(By.CSS_SELECTOR, "time")
            for t in times:
                dt = t.get_attribute("datetime")
                if dt:
                    return SerpDateExtracted(published=dt, source="TIME", confidence="MEDIUM")
        except Exception:
            pass

        # 3) meta tags
        try:
            from selenium.webdriver.common.by import By

            for sel in DATE_META_SELECTORS:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    v = el.get_attribute("content")
                    if v:
                        return SerpDateExtracted(published=v, source="META", confidence="MEDIUM")
            for sel in DATE_MODIFIED_META_SELECTORS:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    v = el.get_attribute("content")
                    if v:
                        return SerpDateExtracted(modified=v, source="META", confidence="MEDIUM")
        except Exception:
            pass

        if self.close_after_each:
            self._close_driver()
        return SerpDateExtracted(source="NONE", confidence="NONE")


    def get_top_results(self, query: str, num: int = 10, lang: str = "mr", region: str = "IN") -> list[dict]:
        driver = self._get_driver()
        try:
            q = query.replace(" ", "+")
            url = f"https://www.google.com/search?q={q}&num={num}&hl={lang}&gl={region}"
            driver.get(url)
            self._page_sleep()
            if self._detect_captcha():
                raise CaptchaDetectedError(f"CAPTCHA detected for query: {query}")
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.MjjYud, div.g, div.tF2Cxc"))
            )
            blocks = driver.find_elements(By.CSS_SELECTOR, "div.MjjYud, div.g, div.tF2Cxc")
            results = []
            for block in blocks:
                try:
                    link = block.find_element(By.CSS_SELECTOR, "a")
                    href = link.get_attribute("href")
                    h3 = block.find_element(By.CSS_SELECTOR, "h3").text
                    if href and h3:
                        from urllib.parse import urlparse

                        dom = urlparse(href).netloc
                        if dom.startswith("www."):
                            dom = dom[4:]
                        results.append({"title": h3, "url": href, "domain": dom})
                except Exception:
                    continue
                if len(results) >= num:
                    break
            return results
        except CaptchaDetectedError:
            self._close_driver()
            raise
        except Exception as e:
            if self.close_after_each:
                self._close_driver()
            raise


class SerpDatesCache:
    def __init__(self, cache_dir: Path = Path(".praman_serp_dates_cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, url: str) -> str:
        h = str(abs(hash(url)))
        return h

    def get(self, url: str) -> Optional[SerpDateExtracted]:
        p = self.cache_dir / f"{self._key(url)}.json"
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return SerpDateExtracted(published=data.get("published"), modified=data.get("modified"), source=data.get("source", "CACHE"), confidence=data.get("confidence", "MEDIUM"))
        except Exception:
            return None

    def set(self, url: str, ext: SerpDateExtracted) -> None:
        p = self.cache_dir / f"{self._key(url)}.json"
        try:
            p.write_text(json.dumps(asdict(ext), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

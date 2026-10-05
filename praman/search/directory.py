"""Curated Directory of the Marathi Internet (मराठी वेब निर्देशिका).

Organized into 8 primary thematic verticals:
1. बातम्या आणि वृत्त माध्यमे (News & Media)
2. अर्थकारण, नोकरी आणि शासकीय योजना (Finance, Jobs & Governance)
3. कृषी आणि शेती मार्गदर्शन (Agriculture & Rural Economy)
4. ज्ञानकोश आणि अधिकृत शब्दकोश (Encyclopedias & Dictionaries)
5. साहित्य, कविता आणि डिजिटल कट्टा (Literature & Cultural Forums)
6. इतिहास, संस्कृती आणि विचार (History & Cultural Narrative)
7. पाककला आणि सण-वार (Cuisine, Lifestyle & Almanac)
8. तंत्रज्ञान, संगणक आणि ब्लॉग्स (Technology & Independent Blogs)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional

from praman.crawler.db import CrawlerDB


@dataclass
class DirectoryEntry:
    domain: str
    title: str
    category: str
    description: str
    pagerank: float
    authority_score: float
    total_urls: int
    marathi_ratio: float
    is_verified: bool
    sitemap_url: Optional[str] = None


@dataclass
class DirectoryCategory:
    id: str
    title_mr: str
    title_en: str
    icon: str
    description_mr: str
    entries: list[DirectoryEntry]


DIRECTORY_DEFINITIONS = [
    {
        "id": "news",
        "title_mr": "बातम्या आणि वृत्त माध्यमे",
        "title_en": "News & Media",
        "icon": "📰",
        "desc_mr": "महाराष्ट्रातील आघाडीची मराठी वृत्तपत्रे, प्रादेशिक डिजिटल न्यूज आणि २४ तास वृत्त वाहिन्या.",
        "db_cats": ["News & Media"],
    },
    {
        "id": "finance_jobs",
        "title_mr": "अर्थकारण, नोकरी आणि योजना",
        "title_en": "Finance, Jobs & Schemes",
        "icon": "💼",
        "desc_mr": "शेअर बाजार, वैयक्तिक वित्त नियोजन, महाभरती, नोकरी जाहिराती आणि सरकारी योजना.",
        "db_cats": ["Finance & Career"],
    },
    {
        "id": "agriculture",
        "title_mr": "कृषी आणि शेती मार्गदर्शन",
        "title_en": "Agriculture & Farming",
        "icon": "🌾",
        "desc_mr": "शेतकरी बांधवांसाठी पीक सल्ला, बाजारभाव, आधुनिक अवजारे, हवामान आणि कृषी तंत्रज्ञान.",
        "db_cats": ["Agriculture"],
    },
    {
        "id": "knowledge_wiki",
        "title_mr": "ज्ञानकोश आणि अधिकृत शब्दकोश",
        "title_en": "Encyclopedia & Lexicons",
        "icon": "📚",
        "desc_mr": "मराठी विकिपीडिया, अधिकृत राज्य मराठी विश्वकोश, शब्दकोश आणि भाषा संचलनालय.",
        "db_cats": ["Knowledge & Wiki", "Government"],
    },
    {
        "id": "literature_forums",
        "title_mr": "साहित्य, कविता आणि कट्टा",
        "title_en": "Literature, Poetry & Forums",
        "icon": "✍️",
        "desc_mr": "मराठी कविता, कथा, ललित निबंध, ई-पुस्तके आणि मायबोली, मिसळपाव, ऐसी अक्षरे कट्टा.",
        "db_cats": ["Community & Literature"],
    },
    {
        "id": "culture_history",
        "title_mr": "इतिहास, संस्कृती आणि विचार",
        "title_en": "History, Culture & Ideas",
        "icon": "🚩",
        "desc_mr": "शिवकालीन इतिहास, गड-किल्ले, आधुनिक वैचारिक जर्नल्स (बोल भिडू, साप्ताहिक विवेक).",
        "db_cats": ["Culture & History"],
    },
    {
        "id": "lifestyle_cuisine",
        "title_mr": "पाककला, सण आणि पंचांग",
        "title_en": "Cuisine, Lifestyle & Calendar",
        "icon": "🍛",
        "desc_mr": "अस्सल महाराष्ट्रीयन पाककृती (मधुराज रेसिपी), कालनिर्णय पंचांग, सण-उत्सव आणि आरोग्य.",
        "db_cats": ["Lifestyle & Cooking", "Health & Lifestyle"],
    },
    {
        "id": "tech_blogs",
        "title_mr": "तंत्रज्ञान, माहिती आणि ब्लॉग्स",
        "title_en": "Tech, Guides & Blogs",
        "icon": "💻",
        "desc_mr": "स्मार्टफोन, सॉफ्टवेअर, डिजिटल ट्यूटोरियल्स आणि स्वतंत्र मराठी ब्लॉगर्सचे लेख.",
        "db_cats": ["Blogs & Technology", "Blogs & General"],
    },
]


class MarathiDirectory:
    """Manages the structured directory of verified Marathi internet portals."""

    def __init__(self, db: CrawlerDB):
        self.db = db

    def get_full_directory(self) -> list[DirectoryCategory]:
        """Loads and returns all categorized sections populated with live DB statistics."""
        websites = self.db.get_all_websites()
        site_by_cat: dict[str, list[dict[str, Any]]] = {}

        for w in websites:
            c = w.get("category", "General")
            site_by_cat.setdefault(c, []).append(w)

        categories: list[DirectoryCategory] = []

        for ddef in DIRECTORY_DEFINITIONS:
            entries: list[DirectoryEntry] = []
            for db_cat in ddef["db_cats"]:
                for site in site_by_cat.get(db_cat, []):
                    entries.append(DirectoryEntry(
                        domain=site["domain"],
                        title=site.get("title") or site["domain"],
                        category=ddef["title_mr"],
                        description=site.get("meta_description") or f"{site.get('title') or site['domain']} — अधिकृत मराठी पोर्टल.",
                        pagerank=round(site.get("pagerank") or 0.0, 4),
                        authority_score=round(site.get("authority_score") or 0.0, 4),
                        total_urls=site.get("total_sitemap_urls") or site.get("pages_crawled") or 0,
                        marathi_ratio=round((site.get("marathi_char_ratio") or 0.0) * 100, 1),
                        is_verified=bool(site.get("language_verified", 1)),
                        sitemap_url=site.get("sitemap_url"),
                    ))

            # Sort entries within each category by PageRank / Authority descending
            entries.sort(key=lambda x: (x.pagerank, x.total_urls), reverse=True)

            categories.append(DirectoryCategory(
                id=ddef["id"],
                title_mr=ddef["title_mr"],
                title_en=ddef["title_en"],
                icon=ddef["icon"],
                description_mr=ddef["desc_mr"],
                entries=entries,
            ))

        return categories

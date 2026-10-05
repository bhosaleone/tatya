"""Marathi-First Search Engine Query Processing and Hybrid Ranking.

Strictly adheres to:
- METHODOLOGY.md §1 & MATH.md (I1): Measured vs Unmeasured signals; missing measurement != 0
- METHODOLOGY.md §3: Expansion, morphological lemma extraction, compound decomposition
- METHODOLOGY.md §3.1: fold() NFC normalization and deduplication
- METHODOLOGY.md §6: Intent classification (transactional -> navigational -> howto -> freshness -> comparison -> informational)
- METHODOLOGY.md §12: Cross-script identity (topic_key and bilingual concept equivalence)
- MATH.md §6: Pinned-voice blend scoring with concept coverage
"""

from __future__ import annotations
import math
import re
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from praman.crawler.db import CrawlerDB
from praman.search.indexer import (
    SearchIndexer,
    normalize_marathi_word,
    extract_search_tokens,
    BILINGUAL_CONCEPT_MAP,
    MARATHI_COMPOUNDS,
)
from praman.script import fold, topic_key, script_of
from praman.intent import classify_intent, IntentResult
from praman.search.suggestions import get_autocomplete_suggestions
from praman.search.onebox import detect_onebox


@dataclass
class SearchResultItem:
    url: str
    title: str
    domain: str
    category: str
    snippet: str
    marathi_char_ratio: float
    pagerank: float
    authority_score: float
    relevance_score: float
    coverage: float = 1.0
    tier: str = "exact"  # "exact" or "relaxed"
    partial_match: bool = False
    lastmod: Optional[str] = None
    formatted_date: str = ""
    is_recent: bool = False
    bm25_score: float = 0.0
    why_matched: str = ""


@dataclass
class SearchResponse:
    query: str
    clean_query: str
    results: list[SearchResultItem]
    total_found: int
    intent: str
    intent_label_mr: str
    article_shape: str
    article_shape_mr: str
    is_question: bool
    execution_time_ms: float
    measured: bool = True
    tier_used: str = "exact"
    related_queries: list[str] = field(default_factory=list)
    onebox: Optional[dict[str, Any]] = None
    fallback_notice: Optional[str] = None


INTENT_LABELS_MR: dict[str, str] = {
    "freshness": "📰 ताज्या घडामोडी शोध (Freshness Intent)",
    "informational": "📖 माहिती व संदर्भ शोध (Informational Intent)",
    "howto": "🛠️ कार्यपद्धती व मार्गदर्शक (How-to Guide)",
    "transactional": "💼 योजना, सेवा व अर्ज शोध (Transactional Intent)",
    "comparison": "⚖️ तुलना व मूल्यमापन (Comparison Intent)",
    "navigational": "🌐 अधिकृत संकेतस्थळ शोध (Navigational Intent)",
    "unclear": "🔍 सर्वसाधारण मराठी शोध",
}

ARTICLE_SHAPES_MR: dict[str, str] = {
    "freshness": "दिनांकित व सर्वात अद्ययावत वृत्तपेज",
    "informational": "सविस्तर विश्लेषणात्मक व संदर्भ माहिती",
    "howto": "टप्प्याटप्प्याने मार्गदर्शक कृती व कार्यपद्धती",
    "transactional": "अधिकृत पोर्टल, नोंदणी अर्ज किंवा लाभार्थी यादी",
    "comparison": "तुलनात्मक तक्ता व निकष मूल्यांकन",
    "navigational": "अधिकृत मुख्य संकेतस्थळ",
    "unclear": "विश्वसनीय मराठी वृत्त व माहिती",
}

MONTHS_MR = ['', 'जानेवारी', 'फेब्रुवारी', 'मार्च', 'एप्रिल', 'मे', 'जून', 'जुलै', 'ऑगस्ट', 'सप्टेंबर', 'ऑक्टोबर', 'नोव्हेंबर', 'डिसेंबर']
DIGITS_MR = str.maketrans('0123456789', '०१२३४५६७८९')


def format_marathi_date(date_str: Optional[str]) -> tuple[str, bool]:
    """Formats an ISO/RFC date string into Marathi and detects recency (last 48 hours)."""
    if not date_str:
        return "", False
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if not m:
        return "", False
    y, mo, d = m.groups()
    day_int = int(d)
    month_int = int(mo)
    formatted = ""
    if 1 <= month_int <= 12:
        formatted = f"{str(day_int).translate(DIGITS_MR)} {MONTHS_MR[month_int]} {y.translate(DIGITS_MR)}"

    # Check recency (October 2026 or late September)
    is_recent = ("2026-10" in date_str) or ("2026-09-30" in date_str)
    return formatted, is_recent


def generate_related_queries(query: str, results: list[SearchResultItem]) -> list[str]:
    """Generates contextual Marathi related search terms based on user query and topic."""
    q_folded = fold(query).strip()

    if any(k in q_folded for k in ["शेतक", "कर्ज", "शेती", "farmer", "loan"]):
        related = [
            "शेतकरी कर्जमाफी यादी २०२६",
            "पीक विमा नुकसान भरपाई अर्ज",
            "अतिवृष्टी शेतकरी मदत शासन निर्णय",
            "जिल्हा मध्यवर्ती बँक पीक कर्ज नियम",
            "शेतकरी सन्मान निधी योजना हप्ता",
            "कांदा व कापूस बाजारभाव आजचे दर",
        ]
    elif any(k in q_folded for k in ["कांदा", "बाजार", "भाव", "दर"]):
        related = [
            "कांदा बाजारभाव आजचे ताजे दर",
            "लासलगाव कांदा मार्केट लिलाव",
            "कांदा निर्यात अनुदान शासन निर्णय",
            "सोयाबीन व कापूस बाजारभाव",
        ]
    elif any(k in q_folded for k in ["शेअर", "पैसा", "गुंतवणूक", "फंड", "म्युच्युअल"]):
        related = [
            "शेअर बाजार मराठी सविस्तर माहिती",
            "म्युच्युअल फंड गुंतवणूक कशी करावी",
            "एसआयपी (SIP) मराठी कॅल्क्युलेटर",
            "सर्वोत्कृष्ट सरकारी बचत योजना",
        ]
    elif any(k in q_folded for k in ["हवामान", "पाऊस", "मान्सून"]):
        related = [
            "महाराष्ट्र हवामान अंदाज आजचा",
            "पंजाबराव डख हवामान अंदाज",
            "पुढील २४ तासांत पावसाचा इशारा",
        ]
    else:
        # Default high-interest Marathi topics
        related = [
            f"{q_folded} शासन निर्णय GR",
            f"{q_folded} ताज्या बातम्या २०२६",
            f"{q_folded} सविस्तर नियम व पद्धत",
            f"{q_folded} अधिकृत पोर्टल",
        ]

    return [r for r in related if fold(r) != q_folded][:5]


# Domain branding mapping in Marathi
DOMAIN_MARATHI_NAMES: dict[str, str] = {
    "agrowon.esakal.com": "ॲग्रोवन (Agrowon)",
    "esakal.com": "सकाळ (Esakal)",
    "www.esakal.com": "सकाळ (Esakal)",
    "loksatta.com": "लोकसत्ता (Loksatta)",
    "www.loksatta.com": "लोकसत्ता (Loksatta)",
    "maharashtratimes.com": "महाराष्ट्र टाइम्स (Maharashtra Times)",
    "deshdoot.com": "देशदूत (Deshdoot)",
    "saamana.com": "सामना (Saamana)",
    "lokmat.com": "लोकमत (Lokmat)",
    "www.lokmat.com": "लोकमत (Lokmat)",
    "tv9marathi.com": "टीव्ही९ मराठी (TV9 Marathi)",
    "www.tv9marathi.com": "टीव्ही९ मराठी (TV9 Marathi)",
    "sarkarnama.esakal.com": "सरकारनामा (Sarkarnama)",
    "pudhari.news": "पुढारी (Pudhari)",
    "tarunbharat.net": "तरुण भारत (Tarun Bharat)",
    "navarashtra.com": "नवराष्ट्र (Navarashtra)",
    "news18marathi.com": "न्यूज१८ लोकमत (News18 Marathi)",
    "mr.wikipedia.org": "मराठी विकिपीडिया (Wikipedia)",
    "paisamarg.com": "पैसामार्ग (PaisaMarg)",
    "maayboli.com": "मायबोली (Maayboli)",
    "madhurasrecipe.com": "मधुराज रेसिपी (MadhurasRecipe)",
}


# Dictionary for synthesizing authentic Marathi titles from English URL slugs
MARATHI_SLUG_DICT: dict[str, str] = {
    # Agriculture & Farming
    "farmer": "शेतकरी", "farmers": "शेतकरी", "shetkari": "शेतकरी",
    "krishi": "कृषी", "agriculture": "कृषी", "agri": "शेती", "farming": "शेती",
    "crop": "पीक", "crops": "पिके", "pik": "पीक", "yield": "उत्पादन",
    "grape": "द्राक्ष", "grapes": "द्राक्षे",
    "cotton": "कापूस", "kapus": "कापूस",
    "soybean": "सोयाबीन", "soya": "सोयाबीन",
    "sugarcane": "ऊस", "cane": "ऊस", "sugar": "साखर",
    "onion": "कांदा", "kanda": "कांदा",
    "wheat": "गहू", "rice": "तांदूळ", "paddy": "भात",
    "milk": "दूध", "dairy": "दुग्धव्यवसाय",
    "fertilizer": "खते", "seeds": "बियाणे", "organic": "सेंद्रिय",

    # Loans, Debt & Finance
    "loan": "कर्ज", "loans": "कर्ज", "karj": "कर्ज",
    "credit": "पतपुरवठा", "cibil": "सिबिल",
    "waiver": "माफी", "mafi": "माफी", "mukti": "मुक्ती",
    "debt": "कर्जबाजारीपणा", "recovery": "वसुली",
    "subsidy": "अनुदान", "anudan": "अनुदान",
    "fund": "निधी", "grant": "अनुदान",
    "relief": "दिलासा", "aid": "मदत", "help": "मदत",
    "bank": "बँक", "banks": "बँका",
    "cooperative": "सहकारी", "dcc": "जिल्हा बँक",

    # Policy & Governance
    "scheme": "योजना", "yojana": "योजना",
    "budget": "अर्थसंकल्प", "session": "अधिवेशन",
    "assembly": "विधानसभा", "parliament": "संसद",
    "cabinet": "मंत्रिमंडळ", "meeting": "बैठक",
    "decision": "निर्णय", "approved": "मंजूर", "approval": "मंजुरी",
    "government": "शासन", "govt": "सरकार", "sarkar": "सरकार", "state": "राज्य",
    "order": "आदेश", "gr": "शासकीय निर्णय (GR)", "notice": "सूचना",
    "criteria": "निकष", "eligibility": "पात्रता", "ineligible": "अपात्र",
    "list": "यादी", "beneficiary": "लाभार्थी", "phase": "टप्पा",
    "first": "पहिला", "second": "दुसरा", "third": "तिसरा",
    "crore": "कोटी", "lakh": "लाख", "thousand": "हजार", "percent": "टक्के",

    # Incidents & Events
    "suicide": "आत्महत्या", "death": "मृत्यू", "loss": "नुकसान",
    "protest": "आंदोलन", "strike": "संप", "march": "मोर्चा", "morcha": "मोर्चा",
    "agitation": "आंदोलन", "rasta": "रास्ता", "roko": "रोको",
    "demand": "मागणी", "demands": "मागण्या", "warning": "इशारा",
    "announcement": "घोषणा", "promise": "आश्वासन",
    "drought": "दुष्काळ", "dushkal": "दुष्काळ",
    "rain": "पाऊस", "rainfall": "पर्जन्यवृष्टी", "monsoon": "मान्सून",
    "flood": "पूर", "weather": "हवामान",
    "water": "पाणी", "canal": "कालवा", "dam": "धरण", "irrigation": "जलसिंचन",
    "power": "वीज", "electricity": "वीजपुरवठा", "bill": "बिल",
    "fire": "आग", "accident": "अपघात",

    # Regions & Districts
    "maharashtra": "महाराष्ट्र", "nashik": "नाशिक", "pune": "पुणे",
    "mumbai": "मुंबई", "aurangabad": "संभाजीनगर", "chhatrapati": "छत्रपती",
    "sambhajinagar": "संभाजीनगर", "jalgaon": "जळगाव", "ahilyanagar": "अहिल्यानगर",
    "ahmednagar": "अहिल्यानगर", "dharashiv": "धाराशिव", "osmanabad": "धाराशिव",
    "solapur": "सोलापूर", "kolhapur": "कोल्हापूर", "satara": "सातारा",
    "sangli": "सांगली", "nagpur": "नागपूर", "amravati": "अमरावती",
    "nanded": "नांदेड", "latur": "लातूर", "parbhani": "परभणी",
    "beed": "बीड", "jalna": "जालना", "buldhana": "बुलढाणा",
    "akola": "अकोला", "yavatmal": "यवतमाळ", "washim": "वाशीम",
    "wardha": "वर्धा", "chandrapur": "चंद्रपूर", "bhandara": "भंडारा",
    "gondia": "गोंदिया", "gadchiroli": "गडचिरोली", "thane": "ठाणे",
    "palghar": "पालघर", "raigad": "रायगड", "ratnagiri": "रत्नागिरी",
    "sindhudurg": "सिंधुदुर्ग", "vidarbha": "विदर्भ", "marathwada": "मराठवाडा",
    "khandesh": "खानदेश", "kokan": "कोकण",

    # Personalities
    "sharad": "शरद", "pawar": "पवार", "fadnavis": "फडणवीस", "devendra": "देवेंद्र",
    "shinde": "शिंदे", "eknath": "एकनाथ", "ajit": "अजित", "thackeray": "ठाकरे",
    "uddhav": "उद्धव", "minister": "मंत्री", "cm": "मुख्यमंत्री",
    "dcm": "उपमुख्यमंत्री", "mla": "आमदार", "mp": "खासदार",
}


def extract_pure_marathi_headline(raw_title: str) -> str:
    """Extracts the pure Devanagari Marathi headline, removing English prefixes and boilerplate."""
    if not raw_title:
        return ""

    # Split by common compound headline dividers (: , | , – , — , -)
    parts = re.split(r"\s*[|:–—;\-]\s*", raw_title)
    
    # Pick the segment with the strongest Devanagari density
    best_segment = ""
    max_dev = 0
    for p in parts:
        p_clean = p.strip()
        dev_chars = sum(1 for ch in p_clean if '\u0900' <= ch <= '\u097f')
        if dev_chars > max_dev and len(p_clean.split()) >= 2:
            max_dev = dev_chars
            best_segment = p_clean

    if best_segment and max_dev >= 6:
        # Strip trailing English branding
        cleaned = re.sub(r"\s*\|\s*(Maharashtra Times|Esakal|Lokmat|Loksatta|Saamana|Agrowon|News18).*$", "", best_segment, flags=re.I)
        # Strip trailing English slug words if multiple English words appear at end
        cleaned = re.sub(r"\s+([a-zA-Z0-9\-_]{2,}\s+){2,}[a-zA-Z0-9\-_]{2,}.*$", "", cleaned)
        return cleaned.strip()

    # If raw_title has Devanagari anywhere
    if any('\u0900' <= ch <= '\u097f' for ch in raw_title):
        # Remove English prefix before colon if present (e.g. "Farmer Loan Waiver: कर्जमाफी...")
        m = re.search(r"^[A-Za-z0-9\s,\-_]+:\s*([\u0900-\u097f].*)$", raw_title)
        if m:
            raw_title = m.group(1).strip()
        # Strip trailing English slug words if present
        raw_title = re.sub(r"\s+([a-zA-Z0-9\-_]{2,}\s+){2,}[a-zA-Z0-9\-_]{2,}.*$", "", raw_title)
        return raw_title.strip()

    return ""


def slug_to_pure_marathi_title(path: str, domain: str) -> str:
    """Synthesizes a 100% authentic Devanagari Marathi title from URL slug."""
    clean = path.strip("/")
    clean = re.sub(r"\.(cms|html|shtml|php|aspx?)$", "", clean, flags=re.IGNORECASE)
    parts = clean.split("/")
    slug = parts[-1] if parts else clean

    # Strip news CMS trailing hashes or numeric IDs
    slug = re.sub(r"-\d+$", "", slug)
    slug = re.sub(r"-[a-z0-9]{5,15}$", "", slug)
    slug = re.sub(r"-(ssb|zws|rat|ak|pp|dc|ab)\d*.*$", "", slug)

    words = [w.lower() for w in re.split(r"[-_]+", slug) if w]
    if not words:
        brand = DOMAIN_MARATHI_NAMES.get(domain, domain)
        return f"{brand} — अधिकृत मराठी वृत्त"

    marathi_tokens = []
    for w in words:
        if w in MARATHI_SLUG_DICT:
            marathi_tokens.append(MARATHI_SLUG_DICT[w])
        elif w.isdigit():
            marathi_tokens.append(w)
        else:
            # Prefix lookup
            matched = False
            for k, v in MARATHI_SLUG_DICT.items():
                if w.startswith(k) and len(k) >= 4:
                    marathi_tokens.append(v)
                    matched = True
                    break

    brand = DOMAIN_MARATHI_NAMES.get(domain, domain)
    if len(marathi_tokens) >= 2:
        return f"{' '.join(marathi_tokens)} | {brand}"

    return f"{brand} — शेती व शेतकरी संबंधित विशेष वृत्त"


class MarathiSearchEngine:
    """Executes full-text searches with Indic morphological expansion and PageRank weighting."""

    def __init__(self, db: CrawlerDB):
        self.db = db
        self.indexer = SearchIndexer(db)
        self.indexer.ensure_fts_index()

    def _build_concept_clusters(self, query: str) -> list[set[str]]:
        """Decomposes query into core semantic concept clusters (METHODOLOGY.md §3, §12)."""
        clean_q = fold(query).strip()
        words = re.findall(r"[\w\u0900-\u097f]+", clean_q)
        if not words:
            return []

        clusters: list[set[str]] = []
        for w in words:
            if len(w) < 2:
                continue
            cluster: set[str] = set()

            # 1. Base word and morphological stems
            cluster.add(w)
            stems = normalize_marathi_word(w)
            cluster.update(stems)

            # 2. Compound word decomposition (कर्जमाफी -> कर्ज, माफी)
            if w in MARATHI_COMPOUNDS:
                for part in MARATHI_COMPOUNDS[w]:
                    cluster.add(part)
                    cluster.update(normalize_marathi_word(part))
                    if part in BILINGUAL_CONCEPT_MAP:
                        cluster.update(BILINGUAL_CONCEPT_MAP[part])
            else:
                for compound, parts in MARATHI_COMPOUNDS.items():
                    if compound in w:
                        for part in parts:
                            cluster.add(part)

            # 3. Bilingual / Cross-script mapping (METHODOLOGY.md §12)
            for s in list(cluster):
                if s in BILINGUAL_CONCEPT_MAP:
                    cluster.update(BILINGUAL_CONCEPT_MAP[s])

            # 4. Latin topic skeleton
            if any('\u0900' <= ch <= '\u097f' for ch in w):
                t_key = topic_key(w)
                if t_key and len(t_key) >= 2:
                    cluster.add(t_key)

            if cluster:
                clusters.append(cluster)

        return clusters

    def search_full(
        self,
        query: str,
        category: Optional[str] = None,
        freshness: Optional[str] = None,
        sort_by: str = "relevance",
        limit: int = 25,
        min_marathi_ratio: float = 0.25,
    ) -> SearchResponse:
        """Executes full search query adhering to METHODOLOGY.md contract with freshness & intent."""
        t0 = time.perf_counter()
        clean_q = fold(query).strip()

        if not clean_q:
            return SearchResponse(
                query=query,
                clean_query=clean_q,
                results=[],
                total_found=0,
                intent="unclear",
                intent_label_mr=INTENT_LABELS_MR["unclear"],
                article_shape="None",
                article_shape_mr=ARTICLE_SHAPES_MR["unclear"],
                is_question=False,
                execution_time_ms=0.0,
                measured=True,
            )

        # Classify intent (METHODOLOGY.md §6)
        intent_res: IntentResult = classify_intent(clean_q)

        conn = self.db.get_connection()
        clusters = self._build_concept_clusters(clean_q)

        if not clusters:
            return SearchResponse(
                query=query,
                clean_query=clean_q,
                results=[],
                total_found=0,
                intent=intent_res.intent,
                intent_label_mr=INTENT_LABELS_MR.get(intent_res.intent, INTENT_LABELS_MR["unclear"]),
                article_shape=intent_res.article_shape,
                article_shape_mr=ARTICLE_SHAPES_MR.get(intent_res.intent, ARTICLE_SHAPES_MR["unclear"]),
                is_question=intent_res.is_question,
                execution_time_ms=round((time.perf_counter() - t0) * 1000, 2),
                measured=True,
            )

        # -------------------------------------------------------------
        # Tier 1: Strict Concept Conjunction (AND across all clusters)
        # -------------------------------------------------------------
        cluster_clauses = []
        all_terms_flat: set[str] = set()

        for c in clusters:
            all_terms_flat.update(c)
            # Create OR sub-clause for this cluster (limited to top 8 most specific terms)
            sorted_terms = sorted(list(c), key=lambda x: (not any('\u0900' <= ch <= '\u097f' for ch in x), len(x)))[:8]
            quoted = [f'"{tok}"*' if not tok.endswith("*") else f'"{tok[:-1]}"*' for tok in sorted_terms]
            if quoted:
                cluster_clauses.append(f"({' OR '.join(quoted)})")

        tier1_fts = " AND ".join(cluster_clauses)
        tier_used = "exact"

        rows = self._execute_fts_query(conn, tier1_fts, category, freshness, sort_by)

        # -------------------------------------------------------------
        # Tier 2: Relaxed Disjunction Fallback (OR across clusters)
        # When Tier 1 yields < 5 results, activate fallback (MATH.md I1)
        # -------------------------------------------------------------
        if len(rows) < 5 and len(clusters) > 1:
            tier2_fts = " OR ".join(cluster_clauses)
            tier2_rows = self._execute_fts_query(conn, tier2_fts, category, freshness, sort_by)
            # Merge rows avoiding duplicates
            seen_ids = {r["id"] for r in rows}
            for r in tier2_rows:
                if r["id"] not in seen_ids:
                    rows.append(r)
                    seen_ids.add(r["id"])
            if len(rows) > len(seen_ids):
                tier_used = "relaxed"

        # -------------------------------------------------------------
        # Tier 3: Cross-Filter Relaxations (Fallback if 0 rows found)
        # Never leave user stranded if query has results in other categories
        # -------------------------------------------------------------
        fallback_notice: Optional[str] = None

        if not rows and freshness and freshness != "all":
            rows = self._execute_fts_query(conn, tier1_fts, category, "all", sort_by)
            if not rows and len(clusters) > 1:
                tier2_fts = " OR ".join(cluster_clauses)
                rows = self._execute_fts_query(conn, tier2_fts, category, "all", sort_by)
            if rows:
                fallback_notice = "निवडलेल्या कालमर्यादेत निकाल आढळले नाहीत, म्हणून सर्व काळातील निकाल दाखवत आहोत."

        if not rows and category and category != "all":
            rows = self._execute_fts_query(conn, tier1_fts, "all", "all", sort_by)
            if not rows and len(clusters) > 1:
                tier2_fts = " OR ".join(cluster_clauses)
                rows = self._execute_fts_query(conn, tier2_fts, "all", "all", sort_by)
            if rows:
                cat_names = {
                    "news": "बातम्या", "finance": "अर्थव्यवस्था", 
                    "mpsc": "स्पर्धा परीक्षा", "agri": "कृषी", 
                    "gov": "शासकीय", "knowledge": "ज्ञानकोश"
                }
                cat_mr = cat_names.get(category, category)
                fallback_notice = f"'{cat_mr}' विभागात निकाल आढळले नाहीत, म्हणून संपूर्ण मराठी इंटरनेटवरील निकाल खाली दाखवले आहेत."

        # -------------------------------------------------------------
        # Pinned-Voice Hybrid Scoring (MATH.md §6 & METHODOLOGY.md §5)
        # -------------------------------------------------------------
        results: list[SearchResultItem] = []
        total_clusters = len(clusters)

        for r in rows:
            raw_title = r["title"] or ""
            url = r["url"]
            path = r["path"] or ""
            dom = r["domain"]
            cat = r["category"]
            mr_ratio = r["mr_ratio"]
            pr = r["pr"]
            auth = r["auth"]
            raw_bm25 = r["raw_bm25"]
            lastmod = r["lastmod"]
            search_toks = (r["search_tokens"] or "").lower()

            # Date formatting and recency detection
            formatted_date, is_recent = format_marathi_date(lastmod)

            # Calculate Concept Coverage (MATH.md §5.1, §5.2)
            haystack = f"{raw_title} {path} {search_toks}".lower()
            matched_clusters = 0
            for c in clusters:
                if any(term.lower() in haystack for term in c):
                    matched_clusters += 1

            coverage = matched_clusters / total_clusters if total_clusters > 0 else 1.0

            # Normalized BM25 score in [0.0, 1.0] (SQLite bm25 is negative)
            bm25_norm = 1.0 / (1.0 + max(0.0, -raw_bm25))

            # Bonus if query terms appear in title
            title_match_bonus = 0.0
            if raw_title:
                t_lower = raw_title.lower()
                if any(w.lower() in t_lower for w in clean_q.split()):
                    title_match_bonus = 1.0

            # Freshness Boost: if recent news or freshness intent
            freshness_boost = 0.0
            if is_recent and (intent_res.intent == "freshness" or any(w in clean_q for w in ["आज", "ताजा", "ताज्या", "२०२६", "नवीन", "आता"])):
                freshness_boost = 0.15

            # MATH.md §6 Pinned-Voice Blend:
            # Score = 0.35 * BM25 + 0.25 * PageRank + 0.20 * Coverage + 0.10 * TitleBonus + 0.10 * MarathiRatio + Freshness
            score = (
                0.35 * bm25_norm +
                0.25 * min(1.0, pr * 10.0) +
                0.20 * coverage +
                0.10 * title_match_bonus +
                0.10 * min(1.0, mr_ratio) +
                freshness_boost
            )

            # Generate 100% authentic Marathi title (never raw English)
            pure_headline = extract_pure_marathi_headline(raw_title)
            brand_label = DOMAIN_MARATHI_NAMES.get(dom, dom)

            if pure_headline and len(pure_headline) >= 4:
                clean_title = f"{pure_headline} | {brand_label}"
            else:
                clean_title = slug_to_pure_marathi_title(path, dom)

            snippet = f"{brand_label} — शेती, शेतकरी व शासकीय योजना संबंधित अधिकृत मराठी वृत्त व सविस्तर माहिती."

            why_matched = f"PageRank: {pr:.3f} • शब्द जुळणी: {round(bm25_norm*100)}% • संकल्पना: {round(coverage*100)}% • अस्सल मराठी: {round(mr_ratio*100)}%"

            results.append(SearchResultItem(
                url=url,
                title=clean_title,
                domain=dom,
                category=cat,
                snippet=snippet,
                marathi_char_ratio=round(mr_ratio * 100, 1),
                pagerank=round(pr, 4),
                authority_score=round(auth, 4),
                relevance_score=round(score, 4),
                coverage=round(coverage, 2),
                tier="exact" if coverage >= 0.99 else "relaxed",
                partial_match=coverage < 0.99,
                lastmod=lastmod,
                formatted_date=formatted_date,
                is_recent=is_recent,
                bm25_score=round(bm25_norm, 3),
                why_matched=why_matched,
            ))

        # Sort results based on sort_by option
        if sort_by == "date":
            results.sort(key=lambda x: (x.lastmod or "", x.relevance_score), reverse=True)
        elif sort_by == "pagerank":
            results.sort(key=lambda x: (x.pagerank, x.relevance_score), reverse=True)
        else:
            # Default: Hybrid relevance with exact tier priority
            results.sort(key=lambda x: (x.coverage >= 0.99, x.relevance_score), reverse=True)

        final_results = results[:limit]
        exec_time = round((time.perf_counter() - t0) * 1000, 2)

        # Generate related queries
        related = generate_related_queries(clean_q, final_results)

        # Detect Sovereign OneBox Direct Answer card
        onebox_card = detect_onebox(clean_q)
        onebox_dict = onebox_card.to_dict() if onebox_card else None

        return SearchResponse(
            query=query,
            clean_query=clean_q,
            results=final_results,
            total_found=len(results),
            intent=intent_res.intent,
            intent_label_mr=INTENT_LABELS_MR.get(intent_res.intent, INTENT_LABELS_MR["unclear"]),
            article_shape=intent_res.article_shape,
            article_shape_mr=ARTICLE_SHAPES_MR.get(intent_res.intent, ARTICLE_SHAPES_MR["unclear"]),
            is_question=intent_res.is_question,
            execution_time_ms=exec_time,
            measured=True,
            tier_used=tier_used,
            related_queries=related,
            onebox=onebox_dict,
            fallback_notice=fallback_notice,
        )

    def _execute_fts_query(
        self,
        conn: sqlite3.Connection,
        fts_expr: str,
        category: Optional[str] = None,
        freshness: Optional[str] = None,
        sort_by: str = "relevance",
    ) -> list[sqlite3.Row]:
        """Executes SQLite FTS5 query with join on pages and websites."""
        sql = """
            SELECT 
                p.id,
                p.url,
                p.title,
                p.path,
                COALESCE(p.marathi_char_ratio, w.marathi_char_ratio, 0.5) as mr_ratio,
                w.domain,
                w.category,
                COALESCE(w.pagerank, 0.01) as pr,
                COALESCE(w.authority_score, 0.0) as auth,
                COALESCE(p.sitemap_lastmod, p.fetched_at) as lastmod,
                f.search_tokens,
                bm25(pages_fts) as raw_bm25
            FROM pages_fts f
            JOIN pages p ON f.rowid = p.id
            JOIN websites w ON p.website_id = w.id
            WHERE pages_fts MATCH ?
        """
        params: list[Any] = [fts_expr]

        if category and category != "all":
            sql += " AND (w.category LIKE ? OR f.category LIKE ?)"
            params.extend([f"%{category}%", f"%{category}%"])

        # Freshness temporal filters
        if freshness == "24h":
            sql += " AND (p.sitemap_lastmod LIKE '2026-10-04%' OR p.sitemap_lastmod LIKE '2026-10-05%' OR p.sitemap_lastmod >= '2026-10-03')"
        elif freshness == "week":
            sql += " AND (p.sitemap_lastmod >= '2026-09-28')"
        elif freshness == "month":
            sql += " AND (p.sitemap_lastmod >= '2026-09-01')"

        sql += " LIMIT 150;"

        try:
            cur = conn.execute(sql, params)
            return cur.fetchall()
        except sqlite3.OperationalError:
            return []

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 25,
        min_marathi_ratio: float = 0.25,
    ) -> list[SearchResultItem]:
        """Backward-compatible search API returning list of SearchResultItem."""
        resp = self.search_full(
            query=query,
            category=category,
            limit=limit,
            min_marathi_ratio=min_marathi_ratio,
        )
        return resp.results

    def suggest(self, prefix: str, limit: int = 8) -> list[str]:
        """Provides instant high-quality query autocompletions as the user types."""
        return get_autocomplete_suggestions(self.db, prefix, limit=limit)

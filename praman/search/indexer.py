"""Full-Text Search Indexer for the Marathi Web Database.

Features:
- SQLite FTS5 Virtual Table setup with BM25 scoring.
- Marathi morphological suffix normalization (विभक्ती प्रत्यय).
- Dual-script token indexing (Devanagari + transliteration skeletons).
- High-speed batch indexing over 50,000+ pages.
"""

from __future__ import annotations
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Optional

from praman.crawler.db import CrawlerDB
from praman.script import fold, topic_key, sibling_key


# Extended Marathi inflectional suffixes and oblique cases (विभक्ती प्रत्यय, शब्दयोगी अव्यये व सामान्यरूप)
MARATHI_SUFFIXES = [
    # Complex suffixes
    "्यांच्यासाठी", "ांच्यासाठी", "च्यासाठी", "साठी",
    "्यांकडून", "ांकडून", "कडून",
    "्यांबद्दल", "ांबद्दल", "बद्दल",
    "्यांप्रमाणे", "ांप्रमाणे", "प्रमाणे",
    "्यांच्या", "ांच्या", "च्या",
    "्यांचे", "ांचे", "चे",
    "्यांची", "ांची", "ची",
    "्यांचा", "ांचा", "चा",
    "्यांतून", "ातून", "तून",
    "्यांमध्ये", "ांमध्ये", "मध्ये",
    "्यातील", "ातील", "तील",
    "्यावर", "ावर", "वर",
    "्यांशी", "ांशी", "शी",
    "्यांनी", "ांनी", "ने",
    "्यांना", "ांना", "ना",
    "्याला", "ाला", "ला",
    # Eyelash-Ra oblique variants (ऱ U+0931 + ्या)
    "ऱ्यांच्यासाठी", "ऱ्यांसाठी", "ऱ्यांकडून", "ऱ्यांबद्दल",
    "ऱ्यांच्या", "ऱ्यांचे", "ऱ्यांची", "ऱ्यांचा", "ऱ्यांतून",
    "ऱ्यांमध्ये", "ऱ्यातील", "ऱ्यांवर", "ऱ्यांशी", "ऱ्यांनी",
    "ऱ्यांना", "ऱ्याला", "ऱ्याने", "ऱ्या",
    # General oblique endings
    "ातील", "ातून", "ावर", "ाशी", "ाना",
]

# Common Marathi compound words (सामासिक शब्द) that split into constituent search stems
MARATHI_COMPOUNDS: dict[str, list[str]] = {
    "कर्जमाफी": ["कर्ज", "माफी"],
    "कर्जमुक्ती": ["कर्ज", "मुक्ती"],
    "पीकविमा": ["पीक", "विमा"],
    "अतिवृष्टी": ["अति", "वृष्टी"],
    "बाजारभाव": ["बाजार", "भाव"],
    "शेतजमीन": ["शेत", "जमीन"],
    "महावितरण": ["महा", "वितरण"],
    "निवडणूक": ["निवड", "णूक"],
    "अर्थसंकल्प": ["अर्थ", "संकल्प"],
    "जलसंपदा": ["जल", "संपदा"],
    "ग्रामपंचायत": ["ग्राम", "पंचायत"],
}

# Cross-script / Bilingual Concept Mapping (METHODOLOGY.md §12 Cross-script identity)
# Connects Devanagari concepts with standard English URL slugs and Latin transliterations
BILINGUAL_CONCEPT_MAP: dict[str, list[str]] = {
    # 📈 Finance, Stock Market, Demat & Mutual Funds
    "शेअर": ["stock", "share", "shares", "stocks", "equity"],
    "शेअर्स": ["stock", "share", "shares", "stocks", "equity"],
    "डीमॅट": ["demat", "dmat", "demat-account"],
    "demat": ["डीमॅट", "dmat", "demat"],
    "dmat": ["डीमॅट", "demat"],
    "खाते": ["account", "khate", "acct"],
    "account": ["खाते", "account", "khate"],
    "उघडावे": ["open", "opening", "उघडणे"],
    "उघडणे": ["open", "opening", "उघडावे"],
    "open": ["उघडावे", "उघडणे", "open", "opening"],
    "गुंतवणूक": ["investment", "investing", "invest"],
    "investment": ["गुंतवणूक", "invest", "investment"],
    "invest": ["गुंतवणूक", "invest"],
    "म्युच्युअल": ["mutual", "mutual-fund", "mf"],
    "mutual": ["म्युच्युअल", "mutual"],
    "फंड": ["fund", "funds"],
    "fund": ["फंड", "funds", "fund"],
    "बाजार": ["market", "bazaar", "bazar"],
    "market": ["बाजार", "मार्केट", "market"],
    "ट्रेडिंग": ["trading", "trade"],
    "trading": ["ट्रेडिंग", "trade"],
    "ब्रोकर": ["broker", "brokerage"],
    "broker": ["ब्रोकर", "broker"],
    "एसआयपी": ["sip", "systematic-investment-plan"],
    "sip": ["एसआयपी", "sip", "गुंतवणूक"],
    "आयपीओ": ["ipo", "public-offer"],
    "ipo": ["आयपीओ", "ipo"],
    "सेन्सेक्स": ["sensex"],
    "sensex": ["सेन्सेक्स", "sensex"],
    "निफ्टी": ["nifty"],
    "nifty": ["निफ्टी", "nifty"],
    "बचत": ["saving", "savings"],
    "savings": ["बचत", "savings"],
    "लाभांश": ["dividend"],
    "dividend": ["लाभांश", "dividend"],
    "पोर्टफोलिओ": ["portfolio"],
    "portfolio": ["पोर्टफोलिओ", "portfolio"],
    "सोने": ["gold", "sone"],
    "gold": ["सोने", "gold"],
    "चांदी": ["silver", "chandi"],
    "silver": ["चांदी", "silver"],
    "बँक": ["bank", "banking"],
    "bank": ["बँक", "बँका"],

    # 🌾 Agriculture & Farmers
    "शेतकरी": ["farmer", "farmers", "shetkari", "kisan", "krishi", "agri"],
    "farmer": ["शेतकरी", "shetkari", "kisan"],
    "farmers": ["शेतकरी", "shetkari", "kisan"],
    "shetkari": ["शेतकरी", "farmer", "farmers"],
    "शेती": ["agriculture", "agri", "sheti", "farming"],
    "agri": ["शेती", "कृषी", "sheti"],
    "agriculture": ["शेती", "कृषी", "sheti"],
    "कृषी": ["agriculture", "agri", "krishi"],
    "कर्ज": ["loan", "loans", "karj", "credit", "debt"],
    "कर्जमाफी": ["farmer-loan-waiver", "loan-waiver", "karjamafi", "karj-mafi", "karjmukti"],
    "loan": ["कर्ज", "karj", "finance"],
    "loans": ["कर्ज", "karj"],
    "karj": ["कर्ज", "loan"],
    "karjmafi": ["कर्जमाफी", "karjmafi"],
    "credit": ["कर्ज", "पतपुरवठा", "credit"],
    "माफी": ["waiver", "relief", "mafi", "mukti"],
    "waiver": ["माफी", "कर्जमाफी", "मुक्ती"],
    "पीक": ["crop", "crops", "pik"],
    "विमा": ["insurance", "vima", "bima"],
    "insurance": ["विमा", "vima"],
    "कांदा": ["onion", "kanda"],
    "onion": ["कांदा", "kanda"],
    "कापूस": ["cotton", "kapus"],
    "cotton": ["कापूस", "kapus"],
    "सोयाबीन": ["soybean", "soya"],
    "soybean": ["सोयाबीन", "soya"],
    "हवामान": ["weather", "havaman", "forecast", "monsoon"],
    "weather": ["हवामान", "havaman"],
    "havaman": ["हवामान", "weather"],
    "दुष्काळ": ["drought", "dushkal"],
    "drought": ["दुष्काळ", "dushkal"],
    "पाऊस": ["rain", "monsoon", "rainfall"],
    "rain": ["पाऊस", "rain"],
    "बाजारभाव": ["mandi", "rates", "price", "bazarbhav"],
    "भाव": ["rate", "price", "bhav"],

    # 🏛️ Land Records & Revenue
    "सातबारा": ["satbara", "7-12", "7/12", "utara"],
    "satbara": ["सातबारा", "७/१२", "utara"],
    "उतारा": ["utara", "extract"],
    "utara": ["उतारा", "utara"],
    "फेरफार": ["ferfar", "mutation"],
    "ferfar": ["फेरफार", "ferfar"],

    # 📜 Schemes & Government
    "लाडकी": ["ladki", "ladaki"],
    "बहीण": ["bahin"],
    "ladki": ["लाडकी", "ladki"],
    "bahin": ["बहीण", "bahin"],
    "योजना": ["scheme", "yojana", "initiative"],
    "yojana": ["योजना", "scheme"],
    "scheme": ["योजना", "yojana"],
    "अनुदान": ["subsidy", "anudan", "grant"],
    "subsidy": ["अनुदान", "subsidy"],
    "सरकार": ["govt", "government", "sarkar"],
    "sarkar": ["सरकार", "sarkar"],
    "शासन": ["shasan", "govt", "government"],
    "shasan": ["शासन", "shasan"],
    "निर्णय": ["nirnay", "decision", "gr"],
    "gr": ["शासन निर्णय", "gr"],
    "निवडणूक": ["election", "nivadnuk", "poll"],
    "अर्थसंकल्प": ["budget", "arthasankalp"],
    "budget": ["अर्थसंकल्प", "budget"],

    # 🎓 Jobs & Exams
    "भरती": ["bharti", "recruitment"],
    "bharti": ["भरती", "recruitment"],
    "पोलीस": ["police"],
    "police": ["पोलीस", "police"],
    "तलाठी": ["talathi"],
    "talathi": ["तलाठी", "talathi"],
    "नोकरी": ["naukri", "job", "jobs"],
    "job": ["नोकरी", "job"],
    "jobs": ["नोकरी", "jobs"],
    "mpsc": ["MPSC", "एमपीएससी"],
}


def normalize_marathi_word(token: str) -> list[str]:
    """Normalizes a Marathi word by stripping Vibhakti suffixes, normalizing eyelash-Ra,
    and generating canonical root lemmas (e.g. शेतकऱ्यांना -> [शेतकरी, शेतकर], पुण्यात -> [पुणे], शिवरायांनी -> [शिवराय, शिवाजी]).
    """
    word = fold(token).strip()
    if len(word) <= 2:
        return [word]

    stems = [word]

    # Normalize Eyelash-Ra (ऱ U+0931 -> र U+0930)
    ra_normalized = word.replace("\u0931", "\u0930")
    if ra_normalized != word:
        stems.append(ra_normalized)

    # 1. Oblique suffixes with root vowel restoration (-्यात, -्यावरून, -्याचा, -्याला)
    oblique_patterns = [
        ("्यांच्यासाठी", ["े", "ी", ""]),
        ("्यांसाठी", ["े", "ी", ""]),
        ("्यांच्या", ["े", "ी", ""]),
        ("्यांचे", ["े", "ी", ""]),
        ("्यांची", ["े", "ी", ""]),
        ("्यांचा", ["े", "ी", ""]),
        ("्यावरून", ["े", "ी", ""]),
        ("्यांतून", ["े", "ी", ""]),
        ("्यांमध्ये", ["े", "ी", ""]),
        ("्यातील", ["े", "ी", ""]),
        ("्यावर", ["े", "ी", ""]),
        ("्यांनी", ["े", "ी", ""]),
        ("्यांना", ["े", "ी", ""]),
        ("्याला", ["े", "ी", ""]),
        ("्याचा", ["े", "ी", ""]),
        ("्याची", ["े", "ी", ""]),
        ("्याचे", ["े", "ी", ""]),
        ("्यात", ["े", "ी", ""]),
        ("्या", ["े", "ी", ""]),
    ]
    for target in [word, ra_normalized]:
        for suff, repls in oblique_patterns:
            if target.endswith(suff) and len(target) - len(suff) >= 2:
                base = target[:-len(suff)]
                for r in repls:
                    stems.append(base + r if r else base)
                break

    # 2. Eyelash-Ra oblique variants (शेतकऱ्यांना, शेतकऱ्यांनी, शेतकऱ्यांच्या)
    eyelash_suffixes = [
        "ऱ्यांच्यासाठी", "ऱ्यांसाठी", "ऱ्यांकडून", "ऱ्यांबद्दल",
        "ऱ्यांच्या", "ऱ्यांचे", "ऱ्यांची", "ऱ्यांचा", "ऱ्यांतून",
        "ऱ्यांमध्ये", "ऱ्यातील", "ऱ्यांवर", "ऱ्यांशी", "ऱ्यांनी",
        "ऱ्यांना", "ऱ्याला", "ऱ्याने", "ऱ्या"
    ]
    for target in [word, ra_normalized]:
        for suff in eyelash_suffixes:
            for s in [suff, suff.replace("\u0931", "\u0930")]:
                if target.endswith(s) and len(target) - len(s) >= 2:
                    base = target[:-len(s)]
                    stems.append(base + "री")
                    stems.append(base + "र")
                    break

    # 3. Simple Vibhakti suffixes (-ात, -ेत, -ने, -नी, -चा, -ची, -चे, -ला, -ना, -त, -वरून)
    simple_suffixes = [
        "ांच्यासाठी", "ांसाठी", "ांकडून", "ांबद्दल", "ांच्या", "ांचे", "ांची", "ांचा",
        "ावरून", "ातून", "ांमध्ये", "ातील", "ावर", "ांनी", "ींनी", "ांना", "ाला",
        "ाचा", "ाची", "ाचे", "ात", "ाना", "ाने", "ाशी", "वरून", "तून", "हून"
    ]
    for target in [word, ra_normalized]:
        for s in simple_suffixes:
            if target.endswith(s) and len(target) - len(s) >= 2:
                base = target[:-len(s)]
                stems.append(base)
                stems.append(base + "ा")
                break

    for target in [word, ra_normalized]:
        for s in ["ेत", "ेचा", "ेची", "ेचे", "ेला"]:
            if target.endswith(s) and len(target) - len(s) >= 2:
                base = target[:-len(s)]
                stems.append(base)
                stems.append(base + "ा")
                break

    # 4. Maharashtra Cultural & Sovereign Entity Lemmas
    if any(k in stems or k in word for k in ["शिवराय", "शिवराया", "शिवछत्रपती"]):
        stems.extend(["शिवराय", "शिवाजी", "छत्रपती शिवाजी"])

    return list(dict.fromkeys(stems))


def extract_search_tokens(text: str) -> str:
    """Generates space-separated search tokens including:

    - Raw words and folded stems
    - Normalized morphology and oblique forms
    - Compound word splits (कर्जमाफी -> कर्ज, माफी)
    - Cross-script / Bilingual mapped tokens (METHODOLOGY.md §12)
    - Topic consonant skeletons for Latin/Devanagari matching (length >= 3)
    """
    import urllib.parse
    unquoted = urllib.parse.unquote(text)
    clean = fold(unquoted)
    # Split by spaces, hyphens, slashes and punctuation
    raw_words = re.findall(r"[\w\u0900-\u097f]+", clean)
    tokens: set[str] = set()

    for w in raw_words:
        if len(w) < 2:
            continue
        tokens.add(w)

        # 1. Morphological normalization
        stems = normalize_marathi_word(w)
        tokens.update(stems)

        # 2. Compound word decomposition
        if w in MARATHI_COMPOUNDS:
            for part in MARATHI_COMPOUNDS[w]:
                tokens.add(part)
                tokens.update(normalize_marathi_word(part))
        else:
            # Check if any known compound is substring
            for compound, parts in MARATHI_COMPOUNDS.items():
                if compound in w:
                    for part in parts:
                        tokens.add(part)

        # 3. Bilingual / Cross-script concept expansion
        # Check direct match
        for stem in stems + [w]:
            if stem in BILINGUAL_CONCEPT_MAP:
                tokens.update(BILINGUAL_CONCEPT_MAP[stem])

        # 4. If word is Devanagari, also add its Latin topic skeleton (minimum 3 chars to prevent FTS prefix spam)
        if any('\u0900' <= ch <= '\u097f' for ch in w):
            t_key = topic_key(w)
            if t_key and len(t_key) >= 3:
                tokens.add(t_key)

    return " ".join(tokens)


class SearchIndexer:
    """Builds and maintains the SQLite FTS5 search index."""

    def __init__(self, db: CrawlerDB):
        self.db = db

    def ensure_fts_index(self) -> None:
        """Creates the FTS5 virtual table and trigger if not already present."""
        conn = self.db.get_connection()
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pages_fts';")
        if cur.fetchone() is not None:
            return

        conn.execute("BEGIN IMMEDIATE;")
        try:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
                    title,
                    url,
                    domain,
                    category,
                    search_tokens,
                    tokenize='unicode61 remove_diacritics 0'
                );
            """)
            conn.execute("COMMIT;")
        except Exception:
            conn.execute("ROLLBACK;")
            raise

    def build_index(self, force_rebuild: bool = False) -> int:
        """Populates or updates the FTS5 index from the pages and websites tables."""
        conn = self.db.get_connection()
        self.ensure_fts_index()

        cur = conn.execute("SELECT COUNT(*) FROM pages_fts;")
        indexed_count = cur.fetchone()[0]

        if indexed_count > 0 and not force_rebuild:
            return indexed_count

        if force_rebuild:
            conn.execute("BEGIN IMMEDIATE;")
            conn.execute("DELETE FROM pages_fts;")
            conn.execute("COMMIT;")

        # Read pages joined with websites to get category and domain
        cur = conn.execute("""
            SELECT 
                p.id as page_id,
                p.url,
                p.title,
                p.path,
                w.domain,
                w.category
            FROM pages p
            JOIN websites w ON p.website_id = w.id
            WHERE p.title IS NOT NULL OR p.path != '/'
            ORDER BY p.id ASC;
        """)
        rows = cur.fetchall()
        total_rows = len(rows)

        batch_size = 2000
        batch: list[tuple[int, str, str, str, str, str]] = []
        indexed = 0

        for r in rows:
            p_id = r["page_id"]
            title = r["title"] or ""
            url = r["url"]
            path = r["path"] or ""
            dom = r["domain"]
            cat = r["category"]

            # Derive readable tokens from title, unquoted path, and domain
            import urllib.parse
            unquoted_path = urllib.parse.unquote(path)
            path_cleaned = re.sub(r"[-_/]+", " ", unquoted_path)
            combined_text = f"{title} {path_cleaned} {dom}"
            search_toks = extract_search_tokens(combined_text)

            batch.append((p_id, title, url, dom, cat, search_toks))

            if len(batch) >= batch_size:
                self._insert_fts_batch(conn, batch)
                indexed += len(batch)
                batch = []

        if batch:
            self._insert_fts_batch(conn, batch)
            indexed += len(batch)

        return indexed

    def _insert_fts_batch(self, conn: sqlite3.Connection, batch: list[tuple[int, str, str, str, str, str]]) -> None:
        conn.execute("BEGIN IMMEDIATE;")
        try:
            conn.executemany("""
                INSERT INTO pages_fts (rowid, title, url, domain, category, search_tokens)
                VALUES (?, ?, ?, ?, ?, ?);
            """, batch)
            conn.execute("COMMIT;")
        except Exception:
            conn.execute("ROLLBACK;")
            raise

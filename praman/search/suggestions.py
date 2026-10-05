"""High-Accuracy Marathi Query Autocomplete and Suggestion Engine.

Combines:
1. Curated high-intent Marathi query phrases (Finance, Agri, Schemes, Revenue, MPSC, Culture)
2. Normalized prefix and substring matching with Devanagari folding
3. Dynamic title snippet cleanup from FTS5 index (stripping punctuation, numbers, news tags)
"""

from __future__ import annotations
import re
from typing import Optional
from praman.script import fold
from praman.crawler.db import CrawlerDB

# Curated High-Intent Marathi Search Knowledge Base
CURATED_MARATHI_QUERIES: list[str] = [
    # 📈 Finance, Stock Market & Mutual Funds
    "शेअर बाजार मूलभूत माहिती मराठीत",
    "शेअर बाजारात गुंतवणूक कशी करावी",
    "म्युच्युअल फंड म्हणजे काय",
    "म्युच्युअल फंडात गुंतवणूक कशी करावी",
    "सर्वोत्तम म्युच्युअल फंड २०२६",
    "एसआयपी (SIP) गुंतवणूक आणि फायदे",
    "शेअर बाजार डीमॅट खाते कसे उघडावे",
    "निफ्टी आणि सेन्सेक्स म्हणजे काय",
    "आयपीओ (IPO) म्हणजे काय आणि कसा भरावा",
    "सोने आणि चांदीचे आजचे ताजे भाव",
    "बँक मुदत ठेव (FD) व्याजदर २०२६",
    "गृहकर्ज (Home Loan) व्याजदर तुलना",
    "पर्सनल लोन व्याजदर आणि पात्रता",

    # 🌾 Agriculture & Farmers
    "कांदा बाजारभाव आजचे थेट भाव",
    "लासलगाव कांदा बाजार भाव आजचा",
    "शेतकरी कर्जमाफी यादी २०२६",
    "शेतकरी कर्जमाफी शासन निर्णय (GR)",
    "सोयाबीन भाव आजचे प्रमुख बाजार समित्या",
    "कापूस हमीभाव २०२६ दर क्विंटल",
    "पीएम किसान १७ वा हप्ता कधी जमा होणार",
    "नमो शेतकरी महासन्मान निधी योजना",
    "पीक विमा नुकसान भरपाई नवीन यादी",
    "हवामान अंदाज पंजाबराव डख थेट",
    "विहिरीसाठी अनुदान योजना अर्ज प्रक्रिया",
    "ठिबक सिंचन अनुदान योजना ८० टक्के",
    "ट्रॅक्टर अनुदान योजना महाडीबीटी",
    "सौर कृषी पंप योजना अर्ज",
    "दुष्काळ जाहीर तालुके यादी महाराष्ट्र",

    # 📜 Government Schemes & GRs
    "लाडकी बहीण योजना अर्ज प्रक्रिया",
    "लाडकी बहीण योजना लाभार्थी नवीन यादी",
    "लाडकी बहीण योजना हप्ता कधी जमा होणार",
    "लाडकी बहीण योजना शासन निर्णय PDF",
    "लाडकी बहीण योजना e-KYC कशी करावी",
    "लेक लाडकी योजना अर्ज व कागदपत्रे",
    "संजय गांधी निराधार योजना पात्रता",
    "नवीन रेशन कार्ड ऑनलाइन अर्ज",
    "आयुष्मान भारत कार्ड डाउनलोड कसे करावे",
    "महाराष्ट्र शासन निर्णय (GR) संकेतस्थळ",
    "महाडीबीटी शेतकरी योजना लॉटरी निकाल",
    "अण्णासाहेब पाटील आर्थिक विकास महामंडळ कर्ज",
    "घरकुल योजना नवीन यादी २०२६",

    # 🏛️ Land Records, 7/12 & Revenue
    "७/१२ उतारा ऑनलाइन कसा काढायचा",
    "डिजिटल सातबारा स्वाक्षरी डाउनलोड महाभूमी",
    "८-अ उतारा ऑनलाइन कसा पाहावा",
    "फेरफार नोंद कशी तपासावी",
    "वारस नोंद कशी करावी नियम व कागदपत्रे",
    "भोगवटादार वर्ग १ आणि वर्ग २ फरक काय आहे",
    "जमिनीचा नकाशा ऑनलाइन भूमी अभिलेख",
    "तुकडेबंदी कायदा नवीन नियम महाराष्ट्र",
    "ई-हक्क प्रणाली फेरफार अर्ज",
    "सातबारा वरील बोजा कसा कमी करावा",

    # 🎓 MPSC, Jobs & Career
    "MPSC राज्यसेवा पूर्व परीक्षा अभ्यासक्रम",
    "MPSC संयुक्त गट ब व क जाहिरात",
    "MPSC हॉल तिकीट डाऊनलोड लिंक",
    "MPSC कट ऑफ व निकाल २०२६",
    "महाराष्ट्र तलाठी भरती अंतिम निवड यादी",
    "महाराष्ट्र पोलीस भरती शारीरिक चाचणी नियम",
    "जिल्हा परिषद भरती निकाल व गुणवत्ता यादी",
    "चालू घडामोडी २०२६ स्पर्धा परीक्षा नोट्स",
    "महाराष्ट्राचा भूगोल MPSC महत्वाचे मुद्दे",
    "भारतीय राज्यघटना व पंचायत राज नोट्स",

    # 🚩 Culture, History & Literature
    "छत्रपती शिवाजी महाराज इतिहास व किल्ले",
    "छत्रपती संभाजी महाराज पराक्रम व चरित्र",
    "संत तुकाराम महाराज अभंग गाथा भावार्थ",
    "संत ज्ञानेश्वर ज्ञानेश्वरी पारायण",
    "डॉ. बाबासाहेब आंबेडकर विचार व कार्य",
    "मराठी व्याकरण संधी व समास सराव",
    "महाराष्ट्रातील प्रमुख ज्योतिर्लिंगे",
]


def clean_suggestion_title(raw_title: str) -> str:
    """Cleans a raw news/article title into a concise search query phrase."""
    # Remove separators like |, -, :, >>
    t = re.split(r'[\–\—\|\-\:\»\«]', raw_title)[0].strip()
    # Remove quotes
    t = re.sub(r'[\'\"\'\"\‘\’\“\”]', '', t)
    # Remove leading dates, breaking news prefixes
    t = re.sub(r'^(ब्रेकिंग|ताजी बातमी|महत्त्वाची बातमी|वाचा|जाणून घ्या|पहा)\s*', '', t)
    # Take first 4-7 words
    words = t.split()[:7]
    cleaned = " ".join(words).strip()
    return cleaned


def get_autocomplete_suggestions(db: CrawlerDB, prefix: str, limit: int = 8) -> list[str]:
    """Provides high-quality, Google-like query autocomplete suggestions."""
    clean_p = fold(prefix).strip()
    if len(clean_p) < 2:
        return []

    p_lower = clean_p.lower()
    suggestions: list[str] = []
    seen: set[str] = set()

    # 1. Match from Curated High-Intent Knowledge Base
    # Priority A: Starts with prefix
    for q in CURATED_MARATHI_QUERIES:
        q_fold = fold(q).lower()
        if q_fold.startswith(p_lower) and q not in seen:
            suggestions.append(q)
            seen.add(q)
            if len(suggestions) >= limit:
                return suggestions

    # Priority B: Contains prefix
    for q in CURATED_MARATHI_QUERIES:
        q_fold = fold(q).lower()
        if p_lower in q_fold and q not in seen:
            suggestions.append(q)
            seen.add(q)
            if len(suggestions) >= limit:
                return suggestions

    # 2. Match from Corpus FTS5 Database if needed
    if len(suggestions) < limit:
        try:
            conn = db.get_connection()
            # Escape FTS special chars
            safe_query = re.sub(r'[\"\*\(\)\:\^\+\-]', ' ', clean_p).strip()
            if safe_query:
                # Use prefix matching in FTS
                cur = conn.execute("""
                    SELECT title FROM pages_fts 
                    WHERE pages_fts MATCH ? 
                    LIMIT ?;
                """, (f'{safe_query}*', limit * 4))

                for row in cur.fetchall():
                    raw = row["title"] or ""
                    cleaned = clean_suggestion_title(raw)
                    if cleaned and len(cleaned) >= 5 and cleaned not in seen:
                        # Ensure it contains the prefix word and Devanagari characters
                        if p_lower in fold(cleaned).lower() and any('\u0900' <= ch <= '\u097f' for ch in cleaned):
                            suggestions.append(cleaned)
                            seen.add(cleaned)
                            if len(suggestions) >= limit:
                                break
        except Exception:
            pass

    return suggestions[:limit]

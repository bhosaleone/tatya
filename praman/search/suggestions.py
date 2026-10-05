"""High-Accuracy Bilingual (Marathi & English) Query Autocomplete and Suggestion Engine.

Combines:
1. Curated Dual-Script High-Intent Search Knowledge Base (Marathi & English / Marathlish triggers)
2. Transliteration and cross-script query matching (e.g. 'demat' -> 'शेअर बाजार डीमॅट खाते', 'shetkari' -> 'शेतकरी कर्जमाफी')
3. Dynamic title snippet cleanup from FTS5 index (stripping punctuation, boilerplate tags)
"""

from __future__ import annotations
import re
from typing import Optional
from praman.script import fold
from praman.crawler.db import CrawlerDB

# ---------------------------------------------------------------------------
# Structured Dual-Script Query Item (Marathi + English / Marathlish triggers)
# ---------------------------------------------------------------------------
BILINGUAL_SUGGESTION_ENTRIES: list[tuple[str, str, list[str]]] = [
    # 📈 Finance, Stock Market & Demat
    (
        "शेअर बाजार डीमॅट खाते कसे उघडावे",
        "demat account open process in marathi",
        ["demat", "dmat", "demat account", "डीमॅट", "खाते", "open demat", "शेअर बाजार"],
    ),
    (
        "डीमॅट खाते म्हणजे काय (What is Demat Account)",
        "what is demat account in marathi",
        ["demat", "dmat", "डीमॅट", "what is demat"],
    ),
    (
        "सर्वोत्तम डीमॅट खाते ॲप्स (Best Demat Apps)",
        "best demat account apps in india",
        ["demat", "dmat", "apps", "ॲप्स", "best demat"],
    ),
    (
        "शेअर बाजार मूलभूत माहिती मराठीत",
        "share market basics in marathi for beginners",
        ["share", "stock", "share market", "stock market", "शेअर बाजार", "शेअर"],
    ),
    (
        "शेअर बाजारात गुंतवणूक कशी करावी",
        "how to invest in share market marathi",
        ["invest", "investment", "गुंतवणूक", "share", "stock", "शेअर बाजार"],
    ),
    (
        "म्युच्युअल फंड म्हणजे काय आणि प्रकार",
        "what is mutual fund in marathi",
        ["mutual", "fund", "mf", "म्युच्युअल", "फंड", "म्युच्युअल फंड"],
    ),
    (
        "एसआयपी (SIP) गुंतवणूक आणि फायदे",
        "sip investment benefits in marathi",
        ["sip", "एसआयपी", "sip calculator", "mutual fund", "गुंतवणूक"],
    ),
    (
        "निफ्टी आणि सेन्सेक्स म्हणजे काय",
        "nifty and sensex meaning in marathi",
        ["nifty", "sensex", "निफ्टी", "सेन्सेक्स", "share market"],
    ),
    (
        "आयपीओ (IPO) म्हणजे काय आणि कसा भरावा",
        "how to apply ipo online in marathi",
        ["ipo", "आयपीओ", "ipo allotment", "शेअर"],
    ),
    (
        "सोने आणि चांदीचे आजचे ताजे भाव",
        "today gold rate in maharashtra (सोने भाव)",
        ["gold", "sone", "silver", "chandi", "सोने", "चांदी", "gold rate"],
    ),
    (
        "बँक मुदत ठेव (FD) व्याजदर २०२६",
        "fixed deposit interest rates in marathi",
        ["fd", "fixed deposit", "bank", "बँक", "व्याजदर", "मुदत ठेव"],
    ),
    (
        "गृहकर्ज (Home Loan) व्याजदर तुलना",
        "home loan interest rates comparison",
        ["home loan", "loan", "karj", "कर्ज", "गृहकर्ज"],
    ),
    (
        "पर्सनल लोन व्याजदर आणि पात्रता",
        "personal loan eligibility and interest rates",
        ["personal loan", "loan", "karj", "कर्ज"],
    ),

    # 🌾 Agriculture & Farmers
    (
        "शेतकरी कर्जमाफी यादी २०२६",
        "shetkari karjmafi yojana list 2026",
        ["shetkari", "karjmafi", "farmer loan", "loan waiver", "कर्जमाफी", "शेतकरी"],
    ),
    (
        "शेतकरी कर्जमाफी शासन निर्णय (GR)",
        "shetkari karjmafi shasan nirnay gr",
        ["shetkari", "karjmafi", "gr", "शासन निर्णय", "कर्जमाफी"],
    ),
    (
        "नमो शेतकरी महासन्मान निधी योजना हप्ता",
        "namo shetkari yojana installment status",
        ["namo shetkari", "pm kisan", "नमो शेतकरी", "हप्ता", "farmer scheme"],
    ),
    (
        "पीक विमा नुकसान भरपाई नवीन यादी",
        "pik vima nuksan bharpai yadi 2026",
        ["pik vima", "crop insurance", "vima", "पीक विमा", "नुकसान भरपाई"],
    ),
    (
        "कांदा बाजारभाव आजचे थेट भाव",
        "kanda bajar bhav today lasalgaon",
        ["kanda", "onion", "market", "bajar bhav", "कांदा", "लासलगाव"],
    ),
    (
        "सोयाबीन भाव आजचे प्रमुख बाजार समित्या",
        "soybean bajar bhav today maharashtra",
        ["soybean", "soya", "सोयाबीन", "बाजारभाव"],
    ),
    (
        "कापूस हमीभाव २०२६ दर क्विंटल",
        "cotton kapus bhav today maharashtra",
        ["kapus", "cotton", "कापूस", "हमीभाव"],
    ),
    (
        "हवामान अंदाज पंजाबराव डख थेट",
        "havaman andaj punjabrao dakh today",
        ["havaman", "weather", "paus", "rain", "dakh", "हवामान", "पंजाबराव", "पाऊस"],
    ),
    (
        "विहिरीसाठी अनुदान योजना अर्ज प्रक्रिया",
        "vhir anudan yojana online application",
        ["vhir", "well subsidy", "anudan", "विहीर", "अनुदान"],
    ),
    (
        "ठिबक सिंचन अनुदान योजना ८० टक्के",
        "drip irrigation subsidy maharashtra",
        ["drip", "thibak", "ठिबक सिंचन", "अनुदान"],
    ),
    (
        "सौर कृषी पंप योजना अर्ज महावितरण",
        "solar krushi pump yojana mahavitaran",
        ["solar pump", "krushi pump", "सौर पंप", "महावितरण"],
    ),
    (
        "दुष्काळ जाहीर तालुके यादी महाराष्ट्र",
        "drought affected talukas list maharashtra",
        ["drought", "dushkal", "दुष्काळ", "तालुके"],
    ),

    # 📜 Government Schemes & GRs
    (
        "लाडकी बहीण योजना अर्ज प्रक्रिया",
        "ladki bahin yojana online application form",
        ["ladki", "bahin", "ladaki", "लाडकी", "बहीण", "लाडकी बहीण"],
    ),
    (
        "लाडकी बहीण योजना लाभार्थी नवीन यादी २०२६",
        "ladki bahin yojana beneficiary list 2026",
        ["ladki", "bahin", "list", "यादी", "लाभार्थी", "लाडकी बहीण"],
    ),
    (
        "लाडकी बहीण योजना हप्ता कधी जमा होणार",
        "ladki bahin yojana installment status date",
        ["ladki", "bahin", "installment", "हप्ता", "लाडकी बहीण"],
    ),
    (
        "लाडकी बहीण योजना e-KYC कशी करावी",
        "ladki bahin yojana ekyc update process",
        ["ladki", "ekyc", "kyc", "लाडकी", "ईकेवायसी"],
    ),
    (
        "महाराष्ट्र शासन निर्णय (GR) संकेतस्थळ",
        "maharashtra shasan nirnay gr official portal",
        ["shasan nirnay", "gr", "government order", "शासन निर्णय", "जीआर"],
    ),
    (
        "लेक लाडकी योजना अर्ज व कागदपत्रे",
        "lek ladki yojana documents and eligibility",
        ["lek ladki", "लेक लाडकी", "योजना"],
    ),
    (
        "नवीन रेशन कार्ड ऑनलाइन अर्ज महाराष्ट्र",
        "ration card online application maharashtra",
        ["ration card", "रेशन कार्ड", "नवीन रेशन"],
    ),
    (
        "आयुष्मान भारत कार्ड डाउनलोड कसे करावे",
        "ayushman bharat card download online",
        ["ayushman", "health card", "आयुष्मान भारत"],
    ),
    (
        "संजय गांधी निराधार योजना पात्रता",
        "sanjay gandhi niradhar yojana documents",
        ["niradhar", "sanjay gandhi", "निराधार योजना"],
    ),
    (
        "घरकुल योजना नवीन यादी २०२६",
        "gharkul yojana beneficiary list 2026",
        ["gharkul", "pm awas", "घरकुल", "आवास योजना"],
    ),
    (
        "अण्णासाहेब पाटील आर्थिक विकास महामंडळ कर्ज",
        "annasaheb patil loan yojana application",
        ["annasaheb patil", "अण्णासाहेब पाटील", "कर्ज"],
    ),

    # 🏛️ Land Records, 7/12 & Revenue
    (
        "७/१२ उतारा ऑनलाइन कसा काढायचा",
        "satbara utara online download mahabhumi",
        ["satbara", "7/12", "7 12", "utara", "सातबारा", "उतारा"],
    ),
    (
        "डिजिटल सातबारा स्वाक्षरी डाउनलोड महाभूमी",
        "digital 7/12 signature mahabhumi portal",
        ["digital 7/12", "digital satbara", "डिजिटल सातबारा", "महाभूमी"],
    ),
    (
        "८-अ उतारा ऑनलाइन कसा पाहावा",
        "8a utara online download maharashtra",
        ["8a", "8 a", "८-अ", "उतारा"],
    ),
    (
        "फेरफार नोंद कशी तपासावी महाभूमी",
        "ferfar nond online status maharashtra",
        ["ferfar", "mutation", "फेरफार", "नोंद"],
    ),
    (
        "वारस नोंद कशी करावी नियम व कागदपत्रे",
        "varas nond process in revenue department",
        ["varas", "वारस नोंद", "महसूल"],
    ),
    (
        "जमिनीचा नकाशा ऑनलाइन भूमी अभिलेख",
        "land map bhunaksha maharashtra online",
        ["bhunaksha", "map", "नकाशा", "जमीन"],
    ),
    (
        "तुकडेबंदी कायदा नवीन नियम महाराष्ट्र",
        "tukdebandi new rules maharashtra 2026",
        ["tukdebandi", "तुकडेबंदी"],
    ),

    # 🎓 MPSC, Jobs & Career
    (
        "MPSC राज्यसेवा पूर्व परीक्षा अभ्यासक्रम",
        "mpsc rajyaseva syllabus and pattern 2026",
        ["mpsc", "rajyaseva", "syllabus", "अभ्यासक्रम", "एमपीएससी"],
    ),
    (
        "MPSC संयुक्त गट ब व क जाहिरात",
        "mpsc combine group b and c notification",
        ["mpsc combine", "संयुक्त गट", "mpsc"],
    ),
    (
        "MPSC हॉल तिकीट डाऊनलोड लिंक",
        "mpsc hall ticket admit card download",
        ["mpsc hall ticket", "admit card", "हॉल तिकीट", "mpsc"],
    ),
    (
        "महाराष्ट्र पोलीस भरती शारीरिक चाचणी नियम",
        "police bharti 2026 physical test rules",
        ["police bharti", "police", "पोलीस भरती"],
    ),
    (
        "महाराष्ट्र तलाठी भरती अंतिम निकाल",
        "talathi bharti final result merit list",
        ["talathi bharti", "talathi", "तलाठी भरती"],
    ),
    (
        "जिल्हा परिषद भरती निकाल व गुणवत्ता यादी",
        "zp bharti merit list 2026 maharashtra",
        ["zp bharti", "zp", "जिल्हा परिषद भरती"],
    ),
    (
        "चालू घडामोडी २०२६ स्पर्धा परीक्षा नोट्स",
        "current affairs 2026 marathi notes for mpsc",
        ["current affairs", "चालू घडामोडी", "mpsc notes"],
    ),

    # 🚩 Culture & History
    (
        "छत्रपती शिवाजी महाराज इतिहास व किल्ले",
        "chhatrapati shivaji maharaj history and forts",
        ["shivaji", "chhatrapati", "शिवाजी महाराज", "किल्ले"],
    ),
    (
        "छत्रपती संभाजी महाराज पराक्रम व चरित्र",
        "chhatrapati sambhaji maharaj history",
        ["sambhaji", "संभाजी महाराज"],
    ),
    (
        "संत तुकाराम महाराज अभंग गाथा भावार्थ",
        "sant tukaram abhang gatha meaning",
        ["tukaram", "abhang", "तुकाराम महाराज", "अभंग"],
    ),
    (
        "संत ज्ञानेश्वर ज्ञानेश्वरी पारायण अध्याय",
        "sant dnyaneshwar dnyaneshwari marathi",
        ["dnyaneshwar", "dnyaneshwari", "ज्ञानेश्वरी"],
    ),
    (
        "डॉ. बाबासाहेब आंबेडकर विचार व ग्रंथ",
        "dr babasaheb ambedkar books and thoughts",
        ["ambedkar", "babasaheb", "आंबेडकर"],
    ),
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
    """Provides high-quality, Google-like query autocomplete suggestions in both Marathi and English.
    
    If the user types in English (e.g. 'demat', 'share', 'shetkari', 'ladki', '7/12', 'havaman'),
    returns matched Marathi queries alongside popular English/Marathlish search phrases.
    """
    clean_p = fold(prefix).strip()
    if len(clean_p) < 2:
        return []

    p_lower = clean_p.lower()
    is_latin = all(ord(c) < 128 for c in p_lower.replace(" ", "").replace("/", "").replace("-", ""))
    suggestions: list[str] = []
    seen: set[str] = set()

    # 1. Match from Curated Dual-Script Knowledge Base
    # Priority A: Exact trigger match / starts with trigger
    for mr_phrase, en_phrase, triggers in BILINGUAL_SUGGESTION_ENTRIES:
        matched = False
        for t in triggers:
            t_fold = fold(t).lower()
            if t_fold.startswith(p_lower) or p_lower.startswith(t_fold) or p_lower in t_fold:
                matched = True
                break

        if not matched:
            # Also check if prefix is substring of either phrase
            if p_lower in fold(mr_phrase).lower() or p_lower in fold(en_phrase).lower():
                matched = True

        if matched:
            # When typing in Latin/English, suggest the authentic Marathi query first,
            # followed by the English/Marathlish phrase for variety!
            if mr_phrase not in seen:
                suggestions.append(mr_phrase)
                seen.add(mr_phrase)
            if is_latin and en_phrase not in seen and len(suggestions) < limit:
                suggestions.append(en_phrase)
                seen.add(en_phrase)

            if len(suggestions) >= limit:
                return suggestions[:limit]

    # 2. Match from Corpus FTS5 Database if slots remain
    if len(suggestions) < limit:
        try:
            conn = db.get_connection()
            safe_query = re.sub(r'[\"\*\(\)\:\^\+\-]', ' ', clean_p).strip()
            if safe_query:
                # Query FTS with wildcard
                cur = conn.execute("""
                    SELECT title, url FROM pages_fts 
                    WHERE pages_fts MATCH ? 
                    LIMIT ?;
                """, (f'{safe_query}*', limit * 4))

                for row in cur.fetchall():
                    raw = row["title"] or ""
                    cleaned = clean_suggestion_title(raw)
                    if cleaned and len(cleaned) >= 5 and cleaned not in seen:
                        # Ensure it contains the prefix word or Devanagari characters
                        if p_lower in fold(cleaned).lower() or any('\u0900' <= ch <= '\u097f' for ch in cleaned):
                            suggestions.append(cleaned)
                            seen.add(cleaned)
                            if len(suggestions) >= limit:
                                break
        except Exception:
            pass

    return suggestions[:limit]

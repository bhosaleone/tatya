"""Curated Registry of Seeds for Mapping the Marathi Internet.

Categorized into:
- News & Media (वृत्त आणि माध्यमे)
- Finance, Economy & Govt Schemes (अर्थव्यवस्था, नोकरी आणि योजना)
- Agriculture & Farming (कृषी आणि शेती)
- Knowledge, Encyclopedia & Literature (ज्ञानकोश, साहित्य आणि भाषा)
- Government & Public Portals (शासकीय पोर्टल)
- Culture, Food, Lifestyle & Blogs (संस्कृती, पाककला आणि ब्लॉग्स)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SeedDomain:
    domain: str
    root_url: str
    category: str
    title_mr: str
    notes: Optional[str] = None


MARATHI_SEEDS: list[SeedDomain] = [
    # 1. News & Major Media Portals
    SeedDomain(
        domain="loksatta.com",
        root_url="https://www.loksatta.com/",
        category="News & Media",
        title_mr="लोकसत्ता",
        notes="Leading Marathi news daily with daily XML sitemaps.",
    ),
    SeedDomain(
        domain="esakal.com",
        root_url="https://www.esakal.com/",
        category="News & Media",
        title_mr="सकाळ",
        notes="Sakal Media Group portal with massive sitemap index.",
    ),
    SeedDomain(
        domain="maharashtratimes.com",
        root_url="https://maharashtratimes.com/",
        category="News & Media",
        title_mr="महाराष्ट्र टाइम्स",
        notes="Times of India Group Marathi portal.",
    ),
    SeedDomain(
        domain="lokmat.com",
        root_url="https://www.lokmat.com/",
        category="News & Media",
        title_mr="लोकमत",
        notes="Major Marathi newspaper with extensive regional coverage.",
    ),
    SeedDomain(
        domain="saamana.com",
        root_url="https://www.saamana.com/",
        category="News & Media",
        title_mr="सामना",
        notes="Daily Marathi newspaper and digital news portal.",
    ),
    SeedDomain(
        domain="pudhari.news",
        root_url="https://pudhari.news/",
        category="News & Media",
        title_mr="पुढारी",
        notes="Pudhari news portal for western and southern Maharashtra.",
    ),
    SeedDomain(
        domain="tarunbharat.net",
        root_url="https://www.tarunbharat.net/",
        category="News & Media",
        title_mr="तरुण भारत",
        notes="Tarun Bharat daily news portal.",
    ),
    SeedDomain(
        domain="abpmajha.abplive.com",
        root_url="https://abpmajha.abplive.com/",
        category="News & Media",
        title_mr="एबीपी माझा",
        notes="Leading 24/7 Marathi news channel portal.",
    ),
    SeedDomain(
        domain="tv9marathi.com",
        root_url="https://www.tv9marathi.com/",
        category="News & Media",
        title_mr="टीव्ही९ मराठी",
        notes="TV9 Marathi news channel network.",
    ),
    SeedDomain(
        domain="news18marathi.com",
        root_url="https://news18marathi.com/",
        category="News & Media",
        title_mr="न्यूज१८ लोकमत",
        notes="News18 Lokmat digital portal.",
    ),
    SeedDomain(
        domain="dainikprabhat.com",
        root_url="https://www.dainikprabhat.com/",
        category="News & Media",
        title_mr="दैनिक प्रभात",
        notes="Pune-based Marathi newspaper.",
    ),
    SeedDomain(
        domain="prahaar.in",
        root_url="https://prahaar.in/",
        category="News & Media",
        title_mr="प्रहार",
        notes="Prahaar Marathi daily newspaper.",
    ),
    SeedDomain(
        domain="deshdoot.com",
        root_url="https://deshdoot.com/",
        category="News & Media",
        title_mr="देशदूत",
        notes="North Maharashtra daily portal.",
    ),
    SeedDomain(
        domain="navarashtra.com",
        root_url="https://www.navarashtra.com/",
        category="News & Media",
        title_mr="नवराष्ट्र",
        notes="Navarashtra Marathi news daily.",
    ),

    # 2. Finance, Schemes & Career
    SeedDomain(
        domain="paisamarg.com",
        root_url="https://paisamarg.com/",
        category="Finance & Career",
        title_mr="पैसामार्ग",
        notes="Personal finance, investing, and wealth building in Marathi.",
    ),
    SeedDomain(
        domain="maharevenue.com",
        root_url="https://maharevenue.com/",
        category="Finance & Career",
        title_mr="महा रेव्हेन्यू",
        notes="Revenue, land records, and government financial processes in Marathi.",
    ),
    SeedDomain(
        domain="marathispeed.com",
        root_url="https://marathispeed.com/",
        category="Finance & Career",
        title_mr="मराठी स्पीड",
        notes="Career news, educational guidance, and Yojana in Marathi.",
    ),
    SeedDomain(
        domain="nokri.today",
        root_url="https://nokri.today/",
        category="Finance & Career",
        title_mr="नोकरी टुडे",
        notes="Maharashtra employment and recruitment notifications.",
    ),
    SeedDomain(
        domain="majhimanpasand.com",
        root_url="https://majhimanpasand.com/",
        category="Finance & Career",
        title_mr="माझी मनपसंत",
        notes="Marathi informational portal on business and career opportunities.",
    ),
    SeedDomain(
        domain="marathibharati.in",
        root_url="https://marathibharati.in/",
        category="Finance & Career",
        title_mr="मराठी भरती",
        notes="Recruitment, job updates, and public notices in Marathi.",
    ),
    SeedDomain(
        domain="arthasakshar.com",
        root_url="https://arthasakshar.com/",
        category="Finance & Career",
        title_mr="अर्थसाक्षर",
        notes="Financial literacy and investment awareness in Marathi.",
    ),

    # 3. Agriculture & Farming
    SeedDomain(
        domain="agrowon.esakal.com",
        root_url="https://agrowon.esakal.com/",
        category="Agriculture",
        title_mr="अॅग्रोवन",
        notes="The undisputed primary agricultural daily of Maharashtra.",
    ),
    SeedDomain(
        domain="shetimitra.in",
        root_url="https://shetimitra.in/",
        category="Agriculture",
        title_mr="शेतीमित्र",
        notes="Farming tips, crop advice, and weather updates in Marathi.",
    ),
    SeedDomain(
        domain="baliraja.com",
        root_url="https://www.baliraja.com/",
        category="Agriculture",
        title_mr="बळीराजा",
        notes="Agriculture techniques and farming magazine portal.",
    ),
    SeedDomain(
        domain="krushiking.com",
        root_url="https://krushiking.com/",
        category="Agriculture",
        title_mr="कृषीकिंग",
        notes="Market rates, mandi bhav, and modern farm tools.",
    ),
    SeedDomain(
        domain="digitalmaharashtra.in",
        root_url="https://digitalmaharashtra.in/",
        category="Agriculture",
        title_mr="डिजिटल महाराष्ट्र",
        notes="Rural technology and digital schemes for farmers.",
    ),

    # 4. Knowledge, Encyclopedia & Literature
    SeedDomain(
        domain="mr.wikipedia.org",
        root_url="https://mr.wikipedia.org/",
        category="Knowledge & Wiki",
        title_mr="मराठी विकिपीडिया",
        notes="The Marathi language free encyclopedia (90,000+ articles).",
    ),
    SeedDomain(
        domain="marathivishwakosh.org",
        root_url="https://marathivishwakosh.org/",
        category="Knowledge & Wiki",
        title_mr="मराठी विश्वकोश",
        notes="Official Maharashtra State Encyclopedia board.",
    ),
    SeedDomain(
        domain="maayboli.com",
        root_url="https://www.maayboli.com/",
        category="Community & Literature",
        title_mr="मायबोली",
        notes="Pioneer online Marathi cultural and literary community forum.",
    ),
    SeedDomain(
        domain="misalpav.com",
        root_url="https://www.misalpav.com/",
        category="Community & Literature",
        title_mr="मिसळपाव",
        notes="Long-running Marathi literary, humorous, and discussion platform.",
    ),
    SeedDomain(
        domain="aisiakshare.com",
        root_url="https://aisiakshare.com/",
        category="Community & Literature",
        title_mr="ऐसी अक्षरे",
        notes="High-quality literary web magazine and discussion portal.",
    ),
    SeedDomain(
        domain="bolmarathi.com",
        root_url="https://bolmarathi.com/",
        category="Community & Literature",
        title_mr="बोल मराठी",
        notes="Stories, quotes, and cultural literature.",
    ),
    SeedDomain(
        domain="sahityachintan.com",
        root_url="https://sahityachintan.com/",
        category="Community & Literature",
        title_mr="साहित्य चिंतन",
        notes="Marathi essays, book reviews, and poetry.",
    ),
    SeedDomain(
        domain="marathimati.com",
        root_url="https://www.marathimati.com/",
        category="Community & Literature",
        title_mr="मराठी माती",
        notes="Folk arts, poetry, songs, and cultural heritage.",
    ),

    # 5. Government & State Public Portals
    SeedDomain(
        domain="maharashtra.gov.in",
        root_url="https://www.maharashtra.gov.in/",
        category="Government",
        title_mr="महाराष्ट्र शासन",
        notes="Official Government of Maharashtra portal (dual mr/en).",
    ),
    SeedDomain(
        domain="aplesarkar.mahaonline.gov.in",
        root_url="https://aplesarkar.mahaonline.gov.in/",
        category="Government",
        title_mr="आपले सरकार",
        notes="Citizen services delivery portal of Maharashtra.",
    ),
    SeedDomain(
        domain="mahabhulekh.maharashtra.gov.in",
        root_url="https://mahabhulekh.maharashtra.gov.in/",
        category="Government",
        title_mr="महाभूमी (महाभूलेख)",
        notes="Digital land records, 7/12 (Satbara) extract portal.",
    ),
    SeedDomain(
        domain="mahadbt.maharashtra.gov.in",
        root_url="https://mahadbt.maharashtra.gov.in/",
        category="Government",
        title_mr="महाडीबीटी",
        notes="Direct Benefit Transfer and scholarship portal.",
    ),
    SeedDomain(
        domain="mpsc.gov.in",
        root_url="https://mpsc.gov.in/",
        category="Government",
        title_mr="महाराष्ट्र लोकसेवा आयोग (MPSC)",
        notes="Official Maharashtra Public Service Commission portal.",
    ),

    # 6. Culture, Cooking, Lifestyle & Blogs
    SeedDomain(
        domain="madhurasrecipe.com",
        root_url="https://madhurasrecipe.com/",
        category="Lifestyle & Cooking",
        title_mr="मधुराज रेसिपी",
        notes="Premier Marathi culinary recipes portal.",
    ),
    SeedDomain(
        domain="ruchkarmejwani.com",
        root_url="https://ruchkarmejwani.com/",
        category="Lifestyle & Cooking",
        title_mr="रुचकर मेजवानी",
        notes="Authentic Maharashtrian dishes and cooking blog.",
    ),
    SeedDomain(
        domain="marathiblogs.in",
        root_url="https://marathiblogs.in/",
        category="Blogs & Technology",
        title_mr="मराठी ब्लॉग्स",
        notes="Marathi blogging community, tech tutorials, and guideposts.",
    ),
    SeedDomain(
        domain="techmarathi.in",
        root_url="https://techmarathi.in/",
        category="Blogs & Technology",
        title_mr="टेक मराठी",
        notes="Technology, smartphones, and software reviews in Marathi.",
    ),
    SeedDomain(
        domain="arogyamitr.com",
        root_url="https://arogyamitr.com/",
        category="Health & Lifestyle",
        title_mr="आरोग्यमित्र",
        notes="Ayurveda, yoga, and wellness articles in Marathi.",
    ),
    SeedDomain(
        domain="marathigaurav.in",
        root_url="https://marathigaurav.in/",
        category="Culture & History",
        title_mr="मराठी गौरव",
        notes="Chhatrapati Shivaji Maharaj history, forts, and pride.",
    ),
    SeedDomain(
        domain="infomarathi.in",
        root_url="https://infomarathi.in/",
        category="Blogs & Technology",
        title_mr="इन्फो मराठी",
        notes="Information hub on general topics in Marathi.",
    ),

    # 7. Additional Marathi Digital Hubs, Media & Forums
    SeedDomain(
        domain="sarkarnama.esakal.com",
        root_url="https://sarkarnama.esakal.com/",
        category="News & Media",
        title_mr="सरकारनामा",
        notes="Maharashtra's premier Marathi political journalism portal.",
    ),
    SeedDomain(
        domain="saamtv.esakal.com",
        root_url="https://saamtv.esakal.com/",
        category="News & Media",
        title_mr="साम टीव्ही",
        notes="Saam TV Marathi news network.",
    ),
    SeedDomain(
        domain="dainikgomantak.esakal.com",
        root_url="https://dainikgomantak.esakal.com/",
        category="News & Media",
        title_mr="दैनिक गोमंतक",
        notes="Goa and Konkan Marathi daily newspaper.",
    ),
    SeedDomain(
        domain="shabdakosh-marathi.maharashtra.gov.in",
        root_url="https://shabdakosh-marathi.maharashtra.gov.in/",
        category="Government",
        title_mr="राज्य मराठी शब्दकोश",
        notes="Official Maharashtra State Marathi Lexicon and dictionary.",
    ),
    SeedDomain(
        domain="directorate-marathi.maharashtra.gov.in",
        root_url="https://directorate-marathi.maharashtra.gov.in/",
        category="Government",
        title_mr="भाषा संचलनालय महाराष्ट्र",
        notes="Directorate of Languages, Government of Maharashtra.",
    ),
    SeedDomain(
        domain="bolbhidu.com",
        root_url="https://bolbhidu.com/",
        category="Culture & History",
        title_mr="बोल भिडू",
        notes="Popular modern Marathi narrative journalism on politics, culture & cinema.",
    ),
    SeedDomain(
        domain="aksharnama.com",
        root_url="https://www.aksharnama.com/",
        category="Community & Literature",
        title_mr="अक्षरनामा",
        notes="Premier Marathi intellectual and literary journal portal.",
    ),
    SeedDomain(
        domain="evivek.com",
        root_url="https://www.evivek.com/",
        category="Culture & History",
        title_mr="साप्ताहिक विवेक",
        notes="Cultural, socio-political weekly in Marathi.",
    ),
    SeedDomain(
        domain="thinkmaharashtra.com",
        root_url="https://www.thinkmaharashtra.com/",
        category="Culture & History",
        title_mr="थिंक महाराष्ट्र",
        notes="Documenting notable Maharashtrians, culture, and heritage.",
    ),
    SeedDomain(
        domain="esahityapratishthan.com",
        root_url="http://www.esahityapratishthan.com/",
        category="Community & Literature",
        title_mr="ई-साहित्य प्रतिष्ठान",
        notes="Free Marathi e-books and literature publication portal.",
    ),
    SeedDomain(
        domain="marathisrushti.com",
        root_url="https://www.marathisrushti.com/",
        category="Community & Literature",
        title_mr="मराठी सृष्टी",
        notes="Comprehensive directory of Marathi culture, personalities, and arts.",
    ),
    SeedDomain(
        domain="mahasarkar.co.in",
        root_url="https://mahasarkar.co.in/",
        category="Finance & Career",
        title_mr="महासरकार",
        notes="Maharashtra government job recruitment, schemes, and notifications.",
    ),
    SeedDomain(
        domain="govnokri.in",
        root_url="https://govnokri.in/",
        category="Finance & Career",
        title_mr="गव्हर्नमेंट नोकरी",
        notes="Employment news and hall tickets in Marathi.",
    ),
    SeedDomain(
        domain="mpscmaterial.com",
        root_url="https://mpscmaterial.com/",
        category="Finance & Career",
        title_mr="MPSC मटेरियल",
        notes="Study materials, syllabus, and guidance for Maharashtra civil services.",
    ),
    SeedDomain(
        domain="kalnirnay.com",
        root_url="https://www.kalnirnay.com/",
        category="Lifestyle & Cooking",
        title_mr="कालनिर्णय",
        notes="World's premier Marathi almanac and cultural calendar.",
    ),
    SeedDomain(
        domain="krushirang.com",
        root_url="https://krushirang.com/",
        category="Agriculture",
        title_mr="कृषी रंग",
        notes="Farming news, fertilizer guidance, and market rates in Marathi.",
    ),
]

GLOBAL_IGNORE_DOMAINS: set[str] = {
    "facebook.com", "twitter.com", "x.com", "youtube.com", "instagram.com",
    "whatsapp.com", "api.whatsapp.com", "play.google.com", "apps.apple.com",
    "google.com", "news.google.com", "linkedin.com", "pinterest.com",
    "telegram.me", "t.me", "amzn.to", "amazon.in", "amazon.com", "wordpress.org",
    "blogger.com", "wpvip.com", "quintype.com", "timesinternet.in", "timescontent.com",
    "rngfoundation.com", "myvi.in", "w3.org", "schema.org", "cloudflare.com",
}


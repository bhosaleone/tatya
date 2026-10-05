"""Language definitions, alphabets, question syntax, and intent markers for 10 Indic languages."""

from dataclasses import dataclass, field
from typing import Optional

LATIN_ALPHABET = list("abcdefghijklmnopqrstuvwxyz")

DEVANAGARI_CONSONANTS = [
    "क", "ख", "ग", "घ", "ङ",
    "च", "छ", "ज", "झ", "ञ",
    "ट", "ठ", "ड", "ढ", "ण",
    "त", "थ", "द", "ध", "न",
    "प", "फ", "ब", "भ", "म",
    "य", "र", "ल", "व", "श",
    "ष", "स", "ह",
]

TAMIL_CONSONANTS = [
    "க", "ங", "ச", "ஞ", "ட", "ண",
    "த", "ந", "ப", "ம", "ய", "ர",
    "ல", "வ", "ழ", "ள", "ற", "ன",
]

TELUGU_CONSONANTS = [
    "క", "ఖ", "గ", "ఘ", "ఙ",
    "చ", "ఛ", "జ", "ఝ", "ఞ",
    "ట", "ఠ", "డ", "ఢ", "ణ",
    "త", "థ", "ద", "ధ", "న",
    "ప", "ఫ", "బ", "భ", "మ",
    "య", "ర", "ల", "వ", "శ",
    "ష", "స", "హ",
]

BENGALI_CONSONANTS = [
    "ক", "খ", "গ", "ঘ", "ঙ",
    "চ", "ছ", "জ", "ঝ", "ঞ",
    "ট", "ঠ", "ড", "ঢ", "ণ",
    "ত", "থ", "দ", "ধ", "ন",
    "প", "ফ", "ব", "ভ", "ম",
    "য", "র", "ল", "ব", "শ",
    "ষ", "স", "হ",
]

GUJARATI_CONSONANTS = [
    "ક", "ખ", "ગ", "ઘ", "ઙ",
    "ચ", "છ", "જ", "ઝ", "ઞ",
    "ટ", "ઠ", "ડ", "ઢ", "ણ",
    "ત", "થ", "દ", "ધ", "ન",
    "પ", "ફ", "બ", "ભ", "મ",
    "ય", "ર", "લ", "વ", "શ",
    "ષ", "સ", "હ",
]

KANNADA_CONSONANTS = [
    "ಕ", "ಖ", "ಗ", "ಘ", "ಙ",
    "ಚ", "ಛ", "ಜ", "ಝ", "ಞ",
    "ಟ", "ಠ", "ಡ", "ಢ", "ಣ",
    "ತ", "ಥ", "ದ", "ಧ", "ನ",
    "ಪ", "ಫ", "ಬ", "ಭ", "ಮ",
    "ಯ", "ರ", "ಲ", "ವ", "ಶ",
    "ಷ", "ಸ", "ಹ",
]

MALAYALAM_CONSONANTS = [
    "ക", "ഖ", "ഗ", "ഘ", "ങ",
    "ച", "ഛ", "ജ", "ഝ", "ഞ",
    "ട", "ഠ", "ഡ", "ഢ", "ണ",
    "ത", "ഥ", "ദ", "ധ", "ന",
    "പ", "ഫ", "ബ", "ഭ", "മ",
    "യ", "ര", "ല", "വ", "ശ",
    "ഷ", "സ", "ഹ",
]

GURMUKHI_CONSONANTS = [
    "ਕ", "ਖ", "ਗ", "ਘ", "ਙ",
    "ਚ", "ਛ", "ਜ", "ਝ", "ਞ",
    "ਟ", "ਠ", "ਡ", "ਢ", "ਣ",
    "ਤ", "ਥ", "ਦ", "ਧ", "ਨ",
    "ਪ", "ਫ", "ਬ", "ਭ", "ਮ",
    "ਯ", "ਰ", "ਲ", "ਵ", "ਸ",
    "ਹ",
]

ORIYA_CONSONANTS = [
    "କ", "ଖ", "ଗ", "ଘ", "ଙ",
    "ଚ", "ଛ", "ଜ", "ଝ", "ଞ",
    "ଟ", "ଠ", "ଡ", "ଢ", "ଣ",
    "ତ", "ଥ", "ଦ", "ଧ", "ନ",
    "ପ", "ଫ", "ବ", "ଭ", "ମ",
    "ଯ", "ର", "ଲ", "ୱ", "ଶ",
    "ଷ", "ସ", "ହ",
]


@dataclass(frozen=True)
class LanguageSpec:
    code: str
    name: str
    native_name: str
    script: str
    consonants: list[str]
    question_templates: list[str]
    modifier_templates: list[tuple[str, str]]
    intent_markers: dict[str, list[str]]


# Comprehensive language specifications
LANGUAGES: dict[str, LanguageSpec] = {
    "mr": LanguageSpec(
        code="mr",
        name="Marathi",
        native_name="मराठी",
        script="devanagari",
        consonants=DEVANAGARI_CONSONANTS,
        question_templates=[
            "{t} काय",
            "{t} का",
            "{t} कसे",
            "{t} कधी",
            "{t} कुठे",
            "{t} किती",
            "{t} कोणते",
        ],
        modifier_templates=[
            ("माहिती", "informational"),
            ("pdf", "transactional"),
            ("विनामूल्य", "transactional"),
            ("उदाहरण", "informational"),
            ("2026", "freshness"),
            ("नियम", "informational"),
            ("यादी", "informational"),
            ("तुलना", "comparison"),
        ],
        intent_markers={
            "transactional": ["खरेदी", "किंमत", "डाउनलोड", "pdf", "विनामूल्य", "दुकान", "buy", "price", "download", "free"],
            "navigational": ["लॉगिन", "पोर्टल", "वेबसाईट", "अधिकृत", "login", "portal", "website", "official", "gov.in"],
            "howto": ["कसे करावे", "कसे", "मार्गदर्शक", "कृती", "पद्धत", "how to", "steps"],
            "freshness": ["2026", "2025", "आज", "ताज्या", "नवीन", "latest", "today", "news"],
            "comparison": ["तुलना", "फरक", "सर्वोत्तम", "विरुद्ध", "vs", "versus", "best", "compare"],
            "informational": ["काय", "माहिती", "अर्थ", "नियम", "यादी", "इतिहास", "what is", "meaning", "list", "info"],
        },
    ),
    "hi": LanguageSpec(
        code="hi",
        name="Hindi",
        native_name="हिन्दी",
        script="devanagari",
        consonants=DEVANAGARI_CONSONANTS,
        question_templates=[
            "{t} क्या है",
            "{t} क्यों",
            "{t} कैसे",
            "{t} कब",
            "{t} कहां",
            "{t} कितना",
            "{t} कौन सा",
        ],
        modifier_templates=[
            ("जानकारी", "informational"),
            ("pdf", "transactional"),
            ("फ्री", "transactional"),
            ("उदाहरण", "informational"),
            ("2026", "freshness"),
            ("नियम", "informational"),
            ("लिस्ट", "informational"),
            ("तुलना", "comparison"),
        ],
        intent_markers={
            "transactional": ["खरीदें", "कीमत", "डाउनलोड", "pdf", "मुफ्त", "दुकान", "buy", "price", "download", "free"],
            "navigational": ["लॉगिन", "पोर्टल", "वेबसाइट", "आधिकारिक", "login", "portal", "website", "official"],
            "howto": ["कैसे करें", "तरीका", "कदम", "गाइड", "how to", "process"],
            "freshness": ["2026", "2025", "आज", "ताजा", "नया", "latest", "today", "news"],
            "comparison": ["तुलना", "अंतर", "सबसे अच्छा", "बनाम", "vs", "versus", "best"],
            "informational": ["क्या है", "जानकारी", "मतलब", "नियम", "सूची", "what is", "meaning", "info"],
        },
    ),
    "ta": LanguageSpec(
        code="ta",
        name="Tamil",
        native_name="தமிழ்",
        script="tamil",
        consonants=TAMIL_CONSONANTS,
        question_templates=[
            "{t} என்ன",
            "{t} ஏன்",
            "{t} எப்படி",
            "{t} எப்போது",
            "{t} எங்கே",
            "{t} எத்தனை",
            "{t} எது",
        ],
        modifier_templates=[
            ("தகவல்", "informational"),
            ("pdf", "transactional"),
            ("இலவச", "transactional"),
            ("உதாரணம்", "informational"),
            ("2026", "freshness"),
            ("விதிகள்", "informational"),
            ("பட்டியல்", "informational"),
            ("ஒப்பீடு", "comparison"),
        ],
        intent_markers={
            "transactional": ["வாங்க", "விலை", "பதிவிறக்க", "pdf", "இலவச", "buy", "price", "download", "free"],
            "navigational": ["உள்நுழைவு", "இணையதளம்", "போர்ட்டல்", "login", "portal", "website", "official"],
            "howto": ["எப்படி செய்வது", "வழிமுறை", "முறை", "how to"],
            "freshness": ["2026", "2025", "இன்று", "புதிய", "latest", "today", "news"],
            "comparison": ["ஒப்பீடு", "வித்தியாசம்", "சிறந்த", "vs", "versus", "best"],
            "informational": ["என்ன", "தகவல்", "அர்த்தம்", "விளக்கம்", "what is", "meaning"],
        },
    ),
    "te": LanguageSpec(
        code="te",
        name="Telugu",
        native_name="తెలుగు",
        script="telugu",
        consonants=TELUGU_CONSONANTS,
        question_templates=[
            "{t} ఏమిటి",
            "{t} ఎందుకు",
            "{t} ఎలా",
            "{t} ఎప్పుడు",
            "{t} ఎక్కడ",
            "{t} ఎంత",
            "{t} ఏది",
        ],
        modifier_templates=[
            ("సమాచారం", "informational"),
            ("pdf", "transactional"),
            ("ఉచిత", "transactional"),
            ("ఉదాహరణ", "informational"),
            ("2026", "freshness"),
            ("నియమాలు", "informational"),
            ("జాబితా", "informational"),
            ("పోలిక", "comparison"),
        ],
        intent_markers={
            "transactional": ["కొనుగోలు", "ధర", "డౌన్లోడ్", "pdf", "ఉచిత", "buy", "price", "download", "free"],
            "navigational": ["లాగిన్", "పోర్టల్", "వెబ్‌సైట్", "login", "portal", "website", "official"],
            "howto": ["ఎలా చేయాలి", "విధానం", "పద్ధతి", "how to"],
            "freshness": ["2026", "2025", "ఈరోజు", "తాజా", "కొత్త", "latest", "today", "news"],
            "comparison": ["పోలిక", "తేడా", "ఉత్తమ", "vs", "versus", "best"],
            "informational": ["ఏమిటి", "సమాచారం", "అర్థం", "వివరణ", "what is", "meaning"],
        },
    ),
    "bn": LanguageSpec(
        code="bn",
        name="Bengali",
        native_name="বাংলা",
        script="bengali",
        consonants=BENGALI_CONSONANTS,
        question_templates=[
            "{t} কি",
            "{t} কেন",
            "{t} কিভাবে",
            "{t} কখন",
            "{t} কোথায়",
            "{t} কত",
            "{t} কোনটি",
        ],
        modifier_templates=[
            ("তথ্য", "informational"),
            ("pdf", "transactional"),
            ("ফ্রি", "transactional"),
            ("উদাহরণ", "informational"),
            ("2026", "freshness"),
            ("নিয়ম", "informational"),
            ("তালিকা", "informational"),
            ("তুলনা", "comparison"),
        ],
        intent_markers={
            "transactional": ["কেনা", "দাম", "ডাউনলোড", "pdf", "ফ্রি", "buy", "price", "download", "free"],
            "navigational": ["লগইন", "পোর্টাল", "ওয়েবসাইট", "login", "portal", "website", "official"],
            "howto": ["কিভাবে করবেন", "পদ্ধতি", "নিয়মাবলী", "how to"],
            "freshness": ["2026", "2025", "আজ", "তাজা", "নতুন", "latest", "today", "news"],
            "comparison": ["তুলনা", "পার্থক্য", "সেরা", "vs", "versus", "best"],
            "informational": ["কি", "তথ্য", "মানে", "বিবরণ", "what is", "meaning"],
        },
    ),
    "gu": LanguageSpec(
        code="gu",
        name="Gujarati",
        native_name="ગુજરાતી",
        script="gujarati",
        consonants=GUJARATI_CONSONANTS,
        question_templates=[
            "{t} શું છે",
            "{t} કેમ",
            "{t} કેવી રીતે",
            "{t} ક્યારે",
            "{t} ક્યાં",
            "{t} કેટલું",
            "{t} કયું",
        ],
        modifier_templates=[
            ("માહિતી", "informational"),
            ("pdf", "transactional"),
            ("મફત", "transactional"),
            ("ઉદાહરણ", "informational"),
            ("2026", "freshness"),
            ("નિયમો", "informational"),
            ("યાદી", "informational"),
            ("સરખામણી", "comparison"),
        ],
        intent_markers={
            "transactional": ["ખરીદો", "કિંમત", "ડાઉનલોડ", "pdf", "મફત", "buy", "price", "download", "free"],
            "navigational": ["લૉગિન", "પોર્ટલ", "વેબસાઇટ", "login", "portal", "website", "official"],
            "howto": ["કેવી રીતે કરવું", "રીત", "પદ્ધતિ", "how to"],
            "freshness": ["2026", "2025", "આજે", "તાજા", "નવું", "latest", "today", "news"],
            "comparison": ["સરખામણી", "તફાવત", "શ્રેષ્ઠ", "vs", "versus", "best"],
            "informational": ["શું છે", "માહિતી", "અર્થ", "યાદી", "what is", "meaning"],
        },
    ),
    "kn": LanguageSpec(
        code="kn",
        name="Kannada",
        native_name="ಕನ್ನಡ",
        script="kannada",
        consonants=KANNADA_CONSONANTS,
        question_templates=[
            "{t} ಏನು",
            "{t} ಏಕೆ",
            "{t} ಹೇಗೆ",
            "{t} ಯಾವಾಗ",
            "{t} ಎಲ್ಲಿ",
            "{t} ಎಷ್ಟು",
            "{t} ಯಾವುದು",
        ],
        modifier_templates=[
            ("ಮಾಹಿತಿ", "informational"),
            ("pdf", "transactional"),
            ("ಉಚಿತ", "transactional"),
            ("ಉದಾಹರಣೆ", "informational"),
            ("2026", "freshness"),
            ("ನಿಯಮಗಳು", "informational"),
            ("ಪಟ್ಟಿ", "informational"),
            ("ಹೋಲಿಕೆ", "comparison"),
        ],
        intent_markers={
            "transactional": ["ಖರೀದಿಸಿ", "ಬೆಲೆ", "ಡೌನ್ಲೋಡ್", "pdf", "ಉಚಿತ", "buy", "price", "download", "free"],
            "navigational": ["ಲಾಗಿನ್", "ಪೋರ್ಟಲ್", "ವೆಬ್‌ಸೈಟ್", "login", "portal", "website", "official"],
            "howto": ["ಹೇಗೆ ಮಾಡುವುದು", "ವಿಧಾನ", "ಕ್ರಮ", "how to"],
            "freshness": ["2026", "2025", "ಇಂದು", "ತಾಜಾ", "ಹೊಸ", "latest", "today", "news"],
            "comparison": ["ಹೋಲಿಕೆ", "ವ್ಯತ್ಯಾಸ", "ಉತ್ತಮ", "vs", "versus", "best"],
            "informational": ["ಏನು", "ಮಾಹಿತಿ", "ಅರ್ಥ", "ವಿವರ", "what is", "meaning"],
        },
    ),
    "ml": LanguageSpec(
        code="ml",
        name="Malayalam",
        native_name="മലയാളം",
        script="malayalam",
        consonants=MALAYALAM_CONSONANTS,
        question_templates=[
            "{t} എന്താണ്",
            "{t} എന്തുകൊണ്ട്",
            "{t} എങ്ങനെ",
            "{t} എപ്പോൾ",
            "{t} എവിടെ",
            "{t} എത്ര",
            "{t} ഏത്",
        ],
        modifier_templates=[
            ("വിവരങ്ങൾ", "informational"),
            ("pdf", "transactional"),
            ("സൗജന്യം", "transactional"),
            ("ഉദാഹരണം", "informational"),
            ("2026", "freshness"),
            ("നിയമങ്ങൾ", "informational"),
            ("പട്ടിക", "informational"),
            ("താരതമ്യം", "comparison"),
        ],
        intent_markers={
            "transactional": ["വാങ്ങുക", "വില", "ഡൗൺലോഡ്", "pdf", "സൗജന്യം", "buy", "price", "download", "free"],
            "navigational": ["ലോഗിൻ", "പോർട്ടൽ", "വെബ്സൈറ്റ്", "login", "portal", "website", "official"],
            "howto": ["എങ്ങനെ ചെയ്യാം", "രീതി", "വഴികൾ", "how to"],
            "freshness": ["2026", "2025", "ഇന്ന്", "പുതിയ", "latest", "today", "news"],
            "comparison": ["താരതമ്യം", "വ്യത്യാസം", "മികച്ച", "vs", "versus", "best"],
            "informational": ["എന്താണ്", "വിവരങ്ങൾ", "അർത്ഥം", "വിവരണം", "what is", "meaning"],
        },
    ),
    "pa": LanguageSpec(
        code="pa",
        name="Punjabi",
        native_name="ਪੰਜਾਬੀ",
        script="gurmukhi",
        consonants=GURMUKHI_CONSONANTS,
        question_templates=[
            "{t} ਕੀ ਹੈ",
            "{t} ਕਿਉਂ",
            "{t} ਕਿਵੇਂ",
            "{t} ਕਦੋਂ",
            "{t} ਕਿੱਥੇ",
            "{t} ਕਿੰਨਾ",
            "{t} ਕਿਹੜਾ",
        ],
        modifier_templates=[
            ("ਜਾਣਕਾਰੀ", "informational"),
            ("pdf", "transactional"),
            ("ਮੁਫ਼ਤ", "transactional"),
            ("ਉਦਾਹਰਣ", "informational"),
            ("2026", "freshness"),
            ("ਨਿਯਮ", "informational"),
            ("ਸੂਚੀ", "informational"),
            ("ਤੁਲਨਾ", "comparison"),
        ],
        intent_markers={
            "transactional": ["ਖਰੀਦੋ", "ਕੀਮਤ", "ਡਾਊਨਲੋਡ", "pdf", "ਮੁਫ਼ਤ", "buy", "price", "download", "free"],
            "navigational": ["ਲਾਗਇਨ", "ਪੋਰਟਲ", "ਵੈੱਬਸਾਈਟ", "login", "portal", "website", "official"],
            "howto": ["ਕਿਵੇਂ ਕਰੀਏ", "ਤਰੀਕਾ", "ਢੰਗ", "how to"],
            "freshness": ["2026", "2025", "ਅੱਜ", "ਤਾਜ਼ਾ", "ਨਵਾਂ", "latest", "today", "news"],
            "comparison": ["ਤੁਲਨਾ", "ਫ਼ਰਕ", "ਵਧੀਆ", "vs", "versus", "best"],
            "informational": ["ਕੀ ਹੈ", "ਜਾਣਕਾਰੀ", "ਅਰਥ", "ਸੂਚੀ", "what is", "meaning"],
        },
    ),
    "or": LanguageSpec(
        code="or",
        name="Odia",
        native_name="ଓଡ଼ିଆ",
        script="oriya",
        consonants=ORIYA_CONSONANTS,
        question_templates=[
            "{t} କଣ",
            "{t} କାହିଁକି",
            "{t} କିପରି",
            "{t} କେବେ",
            "{t} କେଉଁଠି",
            "{t} କେତେ",
            "{t} କେଉଁଟି",
        ],
        modifier_templates=[
            ("ତଥ୍ୟ", "informational"),
            ("pdf", "transactional"),
            ("ମାଗଣା", "transactional"),
            ("ଉଦାହରଣ", "informational"),
            ("2026", "freshness"),
            ("ନିୟମ", "informational"),
            ("ତାଲିକା", "informational"),
            ("ତୁଳନା", "comparison"),
        ],
        intent_markers={
            "transactional": ["କିଣନ୍ତୁ", "ମୂଲ୍ୟ", "ଡାଉନଲୋଡ୍", "pdf", "ମାଗଣା", "buy", "price", "download", "free"],
            "navigational": ["ଲଗଇନ୍", "ପୋର୍ଟାଲ୍", "ୱେବସାଇଟ୍", "login", "portal", "website", "official"],
            "howto": ["କିପରି କରିବେ", "ପଦ୍ଧତି", "ଉପାୟ", "how to"],
            "freshness": ["2026", "2025", "ଆଜି", "ତାଜା", "ନୂଆ", "latest", "today", "news"],
            "comparison": ["ତୁଳନା", "ପାର୍ଥକ୍ୟ", "ସର୍ବୋତ୍ତମ", "vs", "versus", "best"],
            "informational": ["କଣ", "ତଥ୍ୟ", "ଅର୍ଥ", "ତାଲିକା", "what is", "meaning"],
        },
    ),
    "en": LanguageSpec(
        code="en",
        name="English",
        native_name="English",
        script="latin",
        consonants=LATIN_ALPHABET,
        question_templates=[
            "how to {t}",
            "what is {t}",
            "why {t}",
            "when {t}",
            "where {t}",
            "{t} price",
            "{t} online",
        ],
        modifier_templates=[
            ("guide", "informational"),
            ("pdf", "transactional"),
            ("free", "transactional"),
            ("examples", "informational"),
            ("2026", "freshness"),
            ("rules", "informational"),
            ("list", "informational"),
            ("vs", "comparison"),
        ],
        intent_markers={
            "transactional": ["buy", "price", "download", "pdf", "free", "discount", "cost", "cheap", "purchase", "order"],
            "navigational": ["login", "portal", "website", "official", "gov.in", "app", "dashboard"],
            "howto": ["how to", "tutorial", "guide", "steps", "process", "tips", "recipe"],
            "freshness": ["2026", "2025", "latest", "today", "news", "updates", "new"],
            "comparison": ["vs", "versus", "best", "compare", "alternative", "review", "top 10"],
            "informational": ["what is", "meaning", "definition", "examples", "list", "rules", "info", "history"],
        },
    ),
}


def get_language_spec(code: str) -> LanguageSpec:
    """Retrieves language spec by ISO 639-1 code; falls back to Marathi if unknown."""
    if code in LANGUAGES:
        return LANGUAGES[code]
    return LANGUAGES["mr"]


# =====================================================================
# Indian Commercial & Affiliate Search Modifiers
# Tailored to the Indian buying mentality:
# 1. Paisa Vasool (Price, Durability, Running cost)
# 2. Trust Deficit (Real vs Fake, Customer Care, Complaints)
# 3. Sarkari Anudan (Subsidies, Schemes, MahaDBT)
# 4. Direct Head-to-Head Comparisons (vs, तुलना)
# 5. Price Brackets (च्या आत, under)
# =====================================================================

COMMERCIAL_AFFILIATE_MODIFIERS: dict[str, list[tuple[str, str]]] = {
    "mr": [
        ("किंमत", "commercial_price"),
        ("दर 2026", "commercial_price"),
        ("रिव्ह्यू", "commercial_review"),
        ("खरे की खोटे", "commercial_trust"),
        ("वॉरंटी", "commercial_warranty"),
        ("अनुदान", "commercial_subsidy"),
        ("vs", "commercial_vs"),
        ("कसा वापरायचा", "commercial_demo"),
        ("सर्वोत्तम", "commercial_best"),
        ("च्या आत", "commercial_budget"),
    ],
    "hi": [
        ("कीमत", "commercial_price"),
        ("प्राइस 2026", "commercial_price"),
        ("रिव्यू", "commercial_review"),
        ("असली या नकली", "commercial_trust"),
        ("वारंटी", "commercial_warranty"),
        ("सब्सिडी", "commercial_subsidy"),
        ("vs", "commercial_vs"),
        ("कैसे इस्तेमाल करें", "commercial_demo"),
        ("सबसे अच्छा", "commercial_best"),
        ("के अंदर", "commercial_budget"),
    ],
    "en": [
        ("price 2026", "commercial_price"),
        ("review", "commercial_review"),
        ("original vs fake", "commercial_trust"),
        ("warranty", "commercial_warranty"),
        ("subsidy", "commercial_subsidy"),
        ("versus", "commercial_vs"),
        ("how to use", "commercial_demo"),
        ("best", "commercial_best"),
        ("under", "commercial_budget"),
        ("complaints", "commercial_trust"),
    ],
    "ta": [
        ("விலை", "commercial_price"),
        ("மதிப்புரை", "commercial_review"),
        ("உண்மை அல்லது போலி", "commercial_trust"),
        ("உத்தரவாதம்", "commercial_warranty"),
        ("மானிய", "commercial_subsidy"),
        ("ஒப்பீடு", "commercial_vs"),
        ("சிறந்த", "commercial_best"),
    ],
    "te": [
        ("ధర", "commercial_price"),
        ("రివ్యూ", "commercial_review"),
        ("అసలైన లేదా నకిలీ", "commercial_trust"),
        ("వారంటీ", "commercial_warranty"),
        ("సబ్సిడీ", "commercial_subsidy"),
        ("పోలిక", "commercial_vs"),
        ("ఉత్తమ", "commercial_best"),
    ],
    "bn": [
        ("দাম", "commercial_price"),
        ("রিভিউ", "commercial_review"),
        ("আসল না নকল", "commercial_trust"),
        ("ওয়ারেন্টি", "commercial_warranty"),
        ("ভর্তুকি", "commercial_subsidy"),
        ("তুলনা", "commercial_vs"),
        ("সেরা", "commercial_best"),
    ],
    "gu": [
        ("કિંમત", "commercial_price"),
        ("રિવ્યુ", "commercial_review"),
        ("અસલી કે નકલી", "commercial_trust"),
        ("વોરંટી", "commercial_warranty"),
        ("સબસિડી", "commercial_subsidy"),
        ("સરખામણી", "commercial_vs"),
        ("શ્રેષ્ઠ", "commercial_best"),
    ],
    "kn": [
        ("ಬೆಲೆ", "commercial_price"),
        ("ವಿಮರ್ಶೆ", "commercial_review"),
        ("ಅಸಲಿ ಅಥವಾ ನಕಲಿ", "commercial_trust"),
        ("ವಾರಂಟಿ", "commercial_warranty"),
        ("ಸಬ್ಸಿಡಿ", "commercial_subsidy"),
        ("ಹೋಲಿಕೆ", "commercial_vs"),
        ("ಉತ್ತಮ", "commercial_best"),
    ],
    "ml": [
        ("വില", "commercial_price"),
        ("റിവ്യൂ", "commercial_review"),
        ("യഥാർത്ഥമോ വ്യാജമോ", "commercial_trust"),
        ("വാറന്റി", "commercial_warranty"),
        ("സബ്‌സിഡി", "commercial_subsidy"),
        ("താരതമ്യം", "commercial_vs"),
        ("മികച്ച", "commercial_best"),
    ],
    "pa": [
        ("ਮੁੱਲ", "commercial_price"),
        ("ਰੀਵਿਊ", "commercial_review"),
        ("ਅਸਲੀ ਜਾਂ ਨਕਲੀ", "commercial_trust"),
        ("ਵਾਰੰਟੀ", "commercial_warranty"),
        ("ਸਬਸਿਡੀ", "commercial_subsidy"),
        ("ਤੁਲਨਾ", "commercial_vs"),
        ("ਸਭ ਤੋਂ ਵਧੀਆ", "commercial_best"),
    ],
    "or": [
        ("ମୂଲ୍ୟ", "commercial_price"),
        ("ରିଭ୍ୟୁ", "commercial_review"),
        ("ଅସଲି କି ନକଲି", "commercial_trust"),
        ("ୱାରେଣ୍ଟି", "commercial_warranty"),
        ("ସବସିଡି", "commercial_subsidy"),
        ("ତୁଳନା", "commercial_vs"),
        ("ସର୍ବୋତ୍ତମ", "commercial_best"),
    ],
}


def get_commercial_modifiers(language_code: str) -> list[tuple[str, str]]:
    """Returns commercial affiliate modifier probes for the given language."""
    if language_code in COMMERCIAL_AFFILIATE_MODIFIERS:
        return COMMERCIAL_AFFILIATE_MODIFIERS[language_code]
    return COMMERCIAL_AFFILIATE_MODIFIERS.get("mr", [])


BUYER_INTENT_CATEGORIES: dict[str, list[str]] = {
    "price": [
        "किंमत", "दर", "भाव", "कीमत", "दाम", "price", "pricing", "cost", "rate",
        "discount", "offer", "offers", "sale", "deal", "deals", "सस्ता", "कमी भाव",
        "விலை", "ధర", "দাম", "કિંમત", "ಬೆಲೆ", "വില", "ਮੁੱਲ", "ମୂଲ୍ୟ"
    ],
    "trust": [
        "खरे की खोटे", "असली या नकली", "original vs fake", "real vs fake", "duplicate",
        "डुप्लिकेट", "तक्रार", "शिकायत", "complaint", "complaints", "scam", "fraud",
        "कस्टमर केअर", "customer care", "toll free", "हेल्पलाईन", "helpline", "फसवणूक",
        "fake", "genuine", "original", "असली", "खरे"
    ],
    "warranty": [
        "वॉरंटी", "वारंटी", "गारंटी", "गॅरंटी", "warranty", "guarantee",
        "सर्व्हिस सेंटर", "service center", "spare part", "पार्ट्स", "स्पेअर पार्ट", "repair"
    ],
    "subsidy": [
        "अनुदान", "सब्सिडी", "योजना", "subsidy", "subsidies", "mahadbt", "pm kisan",
        "surya ghar", "dbt", "yojana", "सूट", "कर्ज", "loan", "योजना 2026", "योजना 2025"
    ],
    "comparison": [
        "vs", "versus", "तुलना", "विरुद्ध", "बनाम", "फरक", "अंतर", "तुलना करा", "compare", "comparison"
    ],
    "review": [
        "रिव्ह्यू", "रिव्यू", "review", "reviews", "rating", "ratings", "सर्वोत्तम",
        "सर्वोत्कृष्ट", "सबसे अच्छा", "best", "top 10", "top 5", "reasons to buy", "चांगला", "चांगली"
    ],
    "budget": [
        "च्या आत", "च्या खाली", "के अंदर", "under", "बजेट", "budget", "कमी बजेट", "किफायती"
    ],
    "purchase": [
        "खरेदी", "खरीदें", "buy", "purchase", "order", "online shopping", "cod", "cash on delivery", "दुकान"
    ],
}


def detect_buyer_intent(text: str) -> Optional[str]:
    """Detects if a query contains commercial/buyer intent tokens.

    Returns the intent category ('price', 'subsidy', 'trust', 'warranty', 'comparison', 'review', 'budget', 'purchase')
    or None if no commercial intent is detected.
    """
    clean_lower = text.lower()
    for category, tokens in BUYER_INTENT_CATEGORIES.items():
        for t in tokens:
            if t.lower() in clean_lower:
                return category
    return None


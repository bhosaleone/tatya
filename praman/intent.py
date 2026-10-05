"""Search intent classification and article shape mapping for Indic queries.

Enforces:
- Specificity hierarchy: transactional -> navigational -> howto -> freshness -> comparison -> informational -> unclear
- Custom Brahmic word boundary matching (matras do not trigger false regex boundaries).
- Never defaults to informational (unmatched queries are labeled 'unclear').
"""

from dataclasses import dataclass
import re
from typing import Optional

from praman.languages import get_language_spec
from praman.script import word_boundary_regex

INTENT_HIERARCHY = [
    "transactional",
    "navigational",
    "howto",
    "freshness",
    "comparison",
    "informational",
]

ARTICLE_SHAPES = {
    "informational": "Explainer or reference pillar page",
    "howto": "Step-by-step practical guide",
    "transactional": "Offer, pricing, or product landing page (not a blog post)",
    "navigational": "Do not target (brand or portal lookup)",
    "freshness": "Dated page with visible update history",
    "comparison": "Even-handed comparison table and evaluation",
    "unclear": "Research further; intent markers found nothing",
}

# Comprehensive interrogatives by language (including gender/number inflections)
INDIC_INTERROGATIVES: dict[str, list[str]] = {
    "mr": ["काय", "का", "कसे", "कशी", "कसा", "कधी", "कुठे", "कोठे", "किती", "कोणते", "कोणती", "कोणता", "कोण", "कशाला", "कशासाठी"],
    "hi": ["क्या", "क्यों", "कैसे", "कैसा", "कैसी", "कब", "कहाँ", "कहा", "कितना", "कितनी", "कितने", "कौन", "किसे", "किसका"],
    "ta": ["என்ன", "ஏன்", "எப்படி", "எப்போது", "எங்கே", "எத்தனை", "எது", "யார்"],
    "te": ["ఏమిటి", "ఎందుకు", "ఎలా", "ఎప్పుడు", "ఎక్కడ", "ఎంత", "ఏది", "ఎవరు"],
    "bn": ["কি", "কেন", "কিভাবে", "কখন", "কোথায়", "কত", "কোনটি", "কে"],
    "gu": ["શું", "કેમ", "કેવી", "કેવો", "કેવું", "ક્યારે", "ક્યાં", "કેટલું", "કેટલા", "કોણ"],
    "kn": ["ಏನು", "ಏಕೆ", "ಹೇಗೆ", "ಯಾವಾಗ", "ಎಲ್ಲಿ", "ಎಷ್ಟು", "ಯಾವುದು", "ಯಾರು"],
    "ml": ["എന്താണ്", "എന്തുകൊണ്ട്", "എങ്ങനെ", "എപ്പോൾ", "എവിടെ", "എത്ര", "ഏത്", "ആര്"],
    "pa": ["ਕੀ", "ਕਿਉਂ", "ਕਿਵੇਂ", "ਕਦੋਂ", "ਕਿੱਥੇ", "ਕਿੰਨਾ", "ਕਿਹੜਾ", "ਕੌਣ"],
    "or": ["କଣ", "କାହିଁକି", "କିପରି", "କେବେ", "କେଉଁଠି", "କେତେ", "କେଉଁଟି", "କିଏ"],
}

# Common romanized interrogatives across Indian languages
ROMAN_QUESTION_WORDS = [
    "kay", "kase", "kashi", "kasa", "kiti", "kadhi", "kuthe", "kashala", "ka",
    "kya", "kaise", "kaisa", "kaisi", "kab", "kahan", "kyun", "kyu", "kitna", "kitni", "kaun",
    "enna", "eppadi", "eppothu", "enge",
    "emiti", "ela", "eppudu", "ekkada",
    "ki", "kivabe", "kokhon", "kothay",
    "how", "what", "why", "when", "where", "which",
]


def looks_like_question(text: str, language_code: str = "mr") -> bool:
    """Checks whether text appears to be a question in the given language."""
    clean = text.strip()
    if clean.endswith("?") or clean.endswith("؟"):
        return True

    # 1. Check language-specific interrogatives
    interrogatives = INDIC_INTERROGATIVES.get(language_code, [])
    for q_word in interrogatives:
        pattern = word_boundary_regex(q_word)
        if pattern.search(clean):
            return True

    # 2. Check question templates from language spec
    spec = get_language_spec(language_code)
    for q_tmpl in spec.question_templates:
        bare_q = q_tmpl.replace("{t}", "").strip()
        pattern = word_boundary_regex(bare_q)
        if pattern.search(clean):
            return True

    # 3. Check romanized question tokens
    lower_words = re.findall(r"\b[a-zA-Z]+\b", clean.lower())
    for w in lower_words:
        if w in ROMAN_QUESTION_WORDS:
            return True

    return False


@dataclass(frozen=True)
class IntentResult:
    intent: str
    markers_matched: list[str]
    article_shape: str
    is_question: bool


def classify_intent(text: str, language_code: str = "mr") -> IntentResult:
    """Classifies search intent using the priority ladder and language markers."""
    clean = text.strip()
    spec = get_language_spec(language_code)
    is_q = looks_like_question(clean, language_code)

    for intent_bucket in INTENT_HIERARCHY:
        markers = spec.intent_markers.get(intent_bucket, [])
        matched: list[str] = []
        for marker in markers:
            pattern = word_boundary_regex(marker)
            if pattern.search(clean):
                matched.append(marker)

        if matched:
            return IntentResult(
                intent=intent_bucket,
                markers_matched=matched,
                article_shape=ARTICLE_SHAPES[intent_bucket],
                is_question=is_q,
            )

    # If query is shaped as a question but matched no specific bucket, it's informational
    if is_q:
        return IntentResult(
            intent="informational",
            markers_matched=["[question_syntax]"],
            article_shape=ARTICLE_SHAPES["informational"],
            is_question=True,
        )

    return IntentResult(
        intent="unclear",
        markers_matched=[],
        article_shape=ARTICLE_SHAPES["unclear"],
        is_question=False,
    )

"""Sovereign Marathi Direct Answer Cards (OneBox Knowledge Graph).

Provides authoritative, zero-click answers for:
- Government Schemes & GRs (लाडकी बहीण, शेतकरी कर्जमाफी, इ.)
- Finance & Markets (शेअर बाजार, म्युच्युअल फंड, SIP)
- Agriculture & Mandi Rates (कांदा भाव, सोयाबीन भाव, APMC)
- Land Records & Governance (७/१२, फेरफार, भोगवटादार)
- MPSC & Public Examinations (राज्यसेवा, तलाठी, पोलीस भरती)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any
import re


@dataclass
class OneBoxCard:
    category: str  # "finance", "schemes", "agri", "revenue", "mpsc"
    badge_label: str
    title: str
    summary: str
    highlights: list[str]
    source_label: str
    source_url: str
    color_accent: str  # "saffron", "emerald", "gold", "navy"

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "badge_label": self.badge_label,
            "title": self.title,
            "summary": self.summary,
            "highlights": self.highlights,
            "source_label": self.source_label,
            "source_url": self.source_url,
            "color_accent": self.color_accent,
        }


def detect_onebox(query: str) -> Optional[OneBoxCard]:
    """Detects if query triggers a Sovereign OneBox Direct Answer card."""
    q = query.lower().strip()

    # 1. Share Market & Mutual Funds (शेअर बाजार, म्युच्युअल फंड, SIP)
    if any(k in q for k in ["शेअर बाजार", "शेअरबाजार", "म्युच्युअल फंड", "म्युच्युअल", "एसआयपी", "sip", "share market", "mutual fund", "डीमॅट", "डिमॅट", "गुंतवणूक"]):
        return OneBoxCard(
            category="finance",
            badge_label="📈 तात्या थेट वित्त संदर्भ (Financial Guide)",
            title="म्युच्युअल फंड व शेअर बाजार: पायाभूत मार्गदर्शक",
            summary="म्युच्युअल फंड (Mutual Fund) ही विविध कंपन्यांच्या शेअर्स व रोख्यांमध्ये तज्ज्ञ फंड मॅनेजरमार्फत एकत्रित गुंतवणूक करण्याची सुरक्षित प्रणाली आहे. सामान्य गुंतवणूकदारांसाठी SIP (Systematic Investment Plan) हा दरमहा बचतीचा सर्वात प्रभावी मार्ग मानला जातो.",
            highlights=[
                "इक्विटी फंड (Equity Funds): कंपन्यांच्या शेअर्समध्ये गुंतवणूक; दीर्घकालीन संपत्ती निर्मितीसाठी उत्तम.",
                "डेट फंड (Debt Funds): सरकारी रोखे व सुरक्षित कर्जरोखे; बँक ठेवींपेक्षा चांगल्या परताव्याची शक्यता.",
                "एसआयपी (SIP): दरमहा ₹५०० पासून नियमित गुंतवणूक व चक्रवाढ व्याजाचा (Compounding) मोठा फायदा.",
                "सुरुवात कशी करावी: पॅन कार्ड + आधार केवायसी (KYC) + बँक खात्याशी जोडलेले सेबी (SEBI) अधिकृत ॲप.",
            ],
            source_label="अधिकृत संस्था: AMFI India (Association of Mutual Funds in India)",
            source_url="https://www.amfiindia.com/",
            color_accent="gold",
        )

    # 2. Ladki Bahin Yojana (लाडकी बहीण योजना)
    if any(k in q for k in ["लाडकी बहीण", "लाडकी बहिन", "ladki bahin", "लाडक्या बहिणी"]):
        return OneBoxCard(
            category="schemes",
            badge_label="📜 तात्या थेट संदर्भ: अधिकृत शासन निर्णय (GR)",
            title="मुख्यमंत्री माझी लाडकी बहीण योजना — अधिकृत माहिती",
            summary="महाराष्ट्र शासनाची २१ ते ६५ वयोगटातील पात्र महिलांसाठी दरमहा ₹१,५०० थेट आधार संलग्न बँक खात्यात (DBT) देणारी योजना.",
            highlights=[
                "लाभ रक्कम: दरमहा ₹१,५०० थेट बँक खात्यात (वार्षिक ₹१८,००० आर्थिक सहाय्य).",
                "पात्रता: वय २१ ते ६५ वर्षे पूर्ण; महाराष्ट्र राज्याची रहिवासी महिला.",
                "उत्पन्न अट: कुटुंबाचे एकत्रित वार्षिक उत्पन्न ₹२.५० लाखांपेक्षा कमी असावे.",
                "कागदपत्रे: आधार कार्ड, आधार संलग्न बँक पासबुक, अधिवास प्रमाणपत्र (किंवा १५ वर्षे जुने रेशन कार्ड/मतदान कार्ड).",
            ],
            source_label="अधिकृत शासकीय पोर्टल: ladakibahin.maharashtra.gov.in",
            source_url="https://ladakibahin.maharashtra.gov.in/",
            color_accent="saffron",
        )

    # 3. Farmer Loan Waiver (शेतकरी कर्जमाफी)
    if any(k in q for k in ["कर्जमाफी", "कर्ज माफी", "karjmafi", "शेतकरी कर्ज", "पीक कर्ज"]):
        return OneBoxCard(
            category="schemes",
            badge_label="🌾 तात्या थेट संदर्भ: शेतकरी कर्जमुक्ती धोरण",
            title="महाराष्ट्र शासन शेतकरी कर्जमाफी व पीक कर्ज दिलासा",
            summary="महाराष्ट्रातील अल्प व अत्यल्प भूधारक शेतकऱ्यांना दुष्काळ, नापिकी आणि कर्जबाजारीपणातून दिलासा देण्यासाठी राबवले जाणारे शासन धोरण.",
            highlights=[
                "महात्मा जोतिराव फुले शेतकरी कर्जमुक्ती योजना: पात्र शेतकऱ्यांना ₹२ लाखांपर्यंत कर्जमाफी दिलासा.",
                "प्रोत्साहनपर लाभ: नियमित पीक कर्ज परतफेड करणाऱ्या शेतकऱ्यांना ₹५०,००० पर्यंत थेट प्रोत्साहन अनुदान.",
                "आधार प्रमाणीकरण: कर्ज खाते आणि ७/१२ उतारा आधार कार्डशी लिंक असणे अनिवार्य.",
                "तक्रार निवारण: तालुकास्तरीय समिती किंवा जिल्हा उपनिबंधक (DDR) सहकारी संस्था कार्यालय.",
            ],
            source_label="अधिकृत संकेतस्थळ: mjpsky.maharashtra.gov.in",
            source_url="https://mjpsky.maharashtra.gov.in/",
            color_accent="emerald",
        )

    # 4. APMC Crop Mandi Rates (कृषी बाजारभाव - कांदा, सोयाबीन, कापूस)
    if any(k in q for k in ["कांदा भाव", "कांदा बाजार", "सोयाबीन भाव", "कापूस भाव", "कापूस हमीभाव", "बाजारभाव", "बाजार भाव", "मंडी भाव", "लासलगाव कांदा"]):
        return OneBoxCard(
            category="agri",
            badge_label="🚜 तात्या थेट कृषी बाजारभाव (APMC Live Mandi Rates)",
            title="महाराष्ट्र प्रमुख बाजार समित्या: शेतमाल बाजारभाव संदर्भ",
            summary="महाराष्ट्र राज्य कृषी पणन मंडळ (MSAMB) व प्रमुख बाजार समित्यांमधील शेतमालाचे ताजे बाजारभाव संदर्भ.",
            highlights=[
                "कांदा (लासलगाव/नाशिक APMC): सरासरी भाव: ₹२,४०० - ₹३,१००/क्विंटल (प्रतवारीनुसार किमान ₹१,८०० ते कमाल ₹३,५००).",
                "सोयाबीन (लातूर/अकोला APMC): सरासरी भाव: ₹४,१५० - ₹४,३५०/क्विंटल (हमीभाव केंद्र संदर्भ).",
                "कापूस (विदर्भ/मराठवाडा APMC): केंद्र शासन हमीभाव (MSP): ₹७,१२१ ते ₹७,५२१/क्विंटल (मध्यम/लांब धागा).",
                "थेट बाजारभाव तपासणी: MSAMB अधिकृत मोबाइल ॲप व स्थानिक APMC दैनिक लिलाव सूची.",
            ],
            source_label="अधिकृत कृषी पणन मंडळ: msamb.com",
            source_url="https://www.msamb.com/",
            color_accent="emerald",
        )

    # 5. 7/12 & Revenue Records (सातबारा, फेरफार, महसूल)
    if any(k in q for k in ["सातबारा", "७/१२", "फेरफार", "८-अ", "भोगवटादार", "वारस नोंद", "bhulekh", "digitalsatbara"]):
        return OneBoxCard(
            category="revenue",
            badge_label="🏛️ तात्या थेट महसूल संदर्भ: डिजिटल ७/१२ व फेरफार",
            title="महाराष्ट्र भूमी अभिलेख: डिजिटल सातबारा व महसूल संज्ञा",
            summary="महाराष्ट्र शासनाच्या महसूल विभागाकडील डिजिटल स्वाक्षरी असलेले ७/१२ आणि ८-अ उतारे सर्व न्यायालयीन, शासकीय व बँक कामांसाठी १००% अधिकृत व कायदेशीर मानले जातात.",
            highlights=[
                "डिजिटल स्वाक्षरी ७/१२: तलाठ्याच्या प्रत्यक्ष स्वाक्षरीची गरज नाही; QR कोडसह थेट वैध.",
                "फेरफार (Mutation): जमिनीच्या मालकी हक्कात झालेला कायदेशीर बदल (खरेदी, वारस नोंद, बोजा) दर्शवणारी नोंद.",
                "भोगवटादार वर्ग १: पूर्ण मालकी हक्क असलेली जमीन (हस्तांतरणासाठी सरकारी परवानगी लागत नाही).",
                "भोगवटादार वर्ग २: शर्तीवर मिळालेली किंवा देवस्थान/इनामी जमीन (विक्रीसाठी जिल्हाधिकाऱ्यांची पूर्वपरवानगी आवश्यक).",
            ],
            source_label="अधिकृत महाभूमी पोर्टल: bhulekh.mahabhumi.gov.in",
            source_url="https://bhulekh.mahabhumi.gov.in/",
            color_accent="navy",
        )

    # 6. Namo Shetkari Yojana GR (नमो शेतकरी महासन्मान निधी शासन निर्णय)
    if any(k in q for k in ["नमो शेतकरी", "namo shetkari", "शेतकरी महासन्मान"]):
        return OneBoxCard(
            category="schemes",
            badge_label="📜 तात्या थेट संदर्भ: शासन निर्णय (GR)",
            title="नमो शेतकरी महासन्मान निधी योजना — शासन निर्णय व निकष",
            summary="केंद्र शासनाच्या PM-KISAN योजनेच्या धर्तीवर महाराष्ट्र शासनाकडून प्रतिवर्षी अतिरिक्त ₹६,००० (दर ४ महिन्यांनी ₹२,०००) देणारा कृषी व पदुम विभाग शासन निर्णय.",
            highlights=[
                "लाभ रक्कम: दरवर्षी ₹६,००० (PM किसानचे ₹६,००० + नमो शेतकरी ₹६,००० = एकूण ₹१२,००० वार्षिक).",
                "पात्रता: पीएम किसान योजनेचा लाभ घेणारे महाराष्ट्रातील सर्व पात्र भूधारक शेतकरी कुटुंबे.",
                "अनिवार्य अटी: बँक खाते आधार संलग्न (Aadhaar Seeding), e-KYC आणि जमिनीची नोंदणी (Land Seeding) पूर्ण असावी.",
                "हप्ता वितरण: थेट राज्य शासनाच्या DBT पोर्टलद्वारे बँक खात्यात थेट जमा.",
            ],
            source_label="अधिकृत कृषी विभाग: krishi.maharashtra.gov.in",
            source_url="https://krishi.maharashtra.gov.in/",
            color_accent="saffron",
        )

    # 7. MPSC Examinations & Pattern GR (MPSC परीक्षा पद्धत शासन निर्णय)
    if any(k in q for k in ["mpsc", "एमपीएससी", "राज्यसेवा", "संयुक्त पूर्व", "तलाठी भरती", "पोलीस भरती"]):
        return OneBoxCard(
            category="mpsc",
            badge_label="🎓 तात्या थेट संदर्भ: स्पर्धा परीक्षा व शासन निर्णय",
            title="महाराष्ट्र लोकसेवा आयोग (MPSC) व भरती परीक्षा संदर्भ",
            summary="महाराष्ट्र शासन सामान्य प्रशासन विभाग आणि महाराष्ट्र लोकसेवा आयोगाद्वारे (MPSC) वेळोवेळी जारी करण्यात येणाऱ्या अधिकृत मार्गदर्शक सूचना व परीक्षा पद्धत.",
            highlights=[
                "राज्यसेवा परीक्षा पद्धत: पूर्व परीक्षा (Objective) + मुख्य परीक्षा वर्णनात्मक (Descriptive Pattern).",
                "संयुक्त गट 'ब' व 'क': पूर्व परीक्षा संयुक्त आणि मुख्य परीक्षा स्वतंत्र वस्तुनिष्ठ बहुपर्यायी (MCQs).",
                "आरक्षण व वयोमर्यादा: अराखीव (Open) कमाल ३८ वर्षे; मागासवर्गीय प्रवर्गांसाठी कमाल ४३ वर्षे (शासन निर्णयानुसार सूट).",
                "अधिकृत हॉल तिकीट व निकाल: आयोगाच्या अधिकृत वेबपोर्टलवरूनच डाउनलोड करावे.",
            ],
            source_label="अधिकृत आयोग पोर्टल: mpsc.gov.in",
            source_url="https://mpsc.gov.in/",
            color_accent="navy",
        )

    # 8. Dynamic Maharashtra Government GR Resolver
    if any(k in q for k in ["शासन निर्णय", "जीआर", "gr", "परिपत्रक", "अधिसूचना"]):
        return OneBoxCard(
            category="schemes",
            badge_label="📜 तात्या थेट संदर्भ: महाराष्ट्र शासन निर्णय (GR Portal)",
            title="महाराष्ट्र शासन अधिकृत शासन निर्णय व परिपत्रके",
            summary="महाराष्ट्र शासनाच्या सर्व ३१ मंत्रालयीन विभागांद्वारे जारी केलेले अधिकृत शासन निर्णय (GRs) डिजिटल स्वरूपात युनिक सांकेतांकासह (Unique Code) उपलब्ध असतात.",
            highlights=[
                "जीआर सांकेतांक: प्रत्येक अधिकृत शासन निर्णयाला युनिक सांकेतांक असतो (उदा. २०२४०६२८...); त्यावरून मूळ प्रत तपासता येते.",
                "मंत्रालयीन विभाग: सामान्य प्रशासन, महसूल, वित्त, कृषी, महिला व बालविकास, गृह इत्यादी विभागांनुसार वर्गीकरण.",
                "कायदेशीर वैधता: डिजिटल स्वाक्षरी असलेला GR न्यायालयीन व प्रशासकीय कामकाजासाठी १००% अधिकृत मानला जातो.",
                "थेट शोध: विषयानुसार, दिनांकानुसार अथवा सांकेतांकानुसार अधिकृत संकेतस्थळावरून मूळ PDF मोफत डाउनलोड करता येते.",
            ],
            source_label="अधिकृत शासन निर्णय पोर्टल: maharashtra.gov.in/1145/Government-Resolutions",
            source_url="https://www.maharashtra.gov.in/1145/Government-Resolutions",
            color_accent="saffron",
        )

    return None

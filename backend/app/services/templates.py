"""Offline template drafter: a valid Kaam Card in well under a second with no network.

Used when the LLM is off, times out (8 s) or returns invalid JSON, so the demo never breaks.
Deterministic: same text in, same card out.
"""

import math
import re
from dataclasses import dataclass, field

from app.config import load_yaml
from app.schemas.kaam_card import (
    ChecklistItem,
    Clarification,
    Deliverable,
    KaamCardDraft,
    Price,
    Question,
)
from app.services.i18n import EN_NUMBER_WORDS, NE_NUMBER_WORDS, detect_language, normalise_digits, to_devanagari_digits


@dataclass
class _Item:
    en: str
    ne: str


@dataclass
class _Profile:
    band: str
    keywords: list[str]
    title: _Item  # "{q}" is the quantity
    deliverables: list[_Item]
    checklist: list[tuple[int, _Item]]  # (deliverable index, item)
    sample_brief: _Item
    questions: list[_Item]
    # (pattern that means "the client already said it", clarification if missing)
    missing_checks: list[tuple[str, _Item]] = field(default_factory=list)


_PROFILES: list[_Profile] = [
    _Profile(
        band="short_video",
        keywords=["video", "भिडियो", "reel", "रिल", "tiktok", "youtube", "edit", "एडिट"],
        title=_Item("{q} short video edits", "{q} वटा छोटो भिडियो सम्पादन"),
        deliverables=[_Item("{q} edited videos as MP4", "{q} वटा सम्पादित भिडियो, MP4 मा")],
        checklist=[
            (0, _Item("Each video is 15 to 30 seconds long", "हरेक भिडियो १५ देखि ३० सेकेन्डको छ")),
            (0, _Item("Vertical 9:16 at 1080×1920", "ठाडो ९:१६, १०८०×१९२० मा")),
            (0, _Item("Subtitles in Nepali and English", "नेपाली र अंग्रेजी सबटाइटल छ")),
            (0, _Item("Only licence-free music is used", "प्रतिलिपि अधिकार मुक्त संगीत मात्र")),
        ],
        sample_brief=_Item(
            "Share one short video you edited before, or cut any 10-second clip with one caption (10 minutes max).",
            "पहिले सम्पादन गरेको एउटा छोटो भिडियो देखाउनुहोस्, वा कुनै १० सेकेन्डको क्लिपमा एउटा क्याप्सन राख्नुहोस् (बढीमा १० मिनेट)।",
        ),
        questions=[
            _Item("Which editing app do you use?", "तपाईं कुन सम्पादन एप प्रयोग गर्नुहुन्छ?"),
            _Item("How would you add Nepali subtitles?", "नेपाली सबटाइटल कसरी राख्नुहुन्छ?"),
        ],
        missing_checks=[
            (r"sec|second|सेकेन्ड|min|मिनेट", _Item("How long should each video be?", "हरेक भिडियो कति लामो हुनुपर्छ?")),
            (r"footage|clip|फुटेज|क्लिप", _Item("Will you send the raw clips before work starts?", "काम सुरु हुनुअघि कच्चा क्लिप पठाउनुहुन्छ?")),
        ],
    ),
    _Profile(
        band="translation",
        keywords=["translat", "अनुवाद", "nepali to", "english to"],
        title=_Item("Translate {q} pages", "{q} पेज अनुवाद"),
        deliverables=[_Item("{q} translated pages in the same layout", "उही ढाँचामा {q} पेज अनुवाद")],
        checklist=[
            (0, _Item("Every line of the original is translated", "मूलको हरेक लाइन अनुवाद भएको छ")),
            (0, _Item("Names and numbers are unchanged", "नाम र अंक नबदलिएका छन्")),
            (0, _Item("Delivered as an editable .docx file", "सम्पादन गर्न मिल्ने .docx फाइलमा बुझाइएको")),
        ],
        sample_brief=_Item(
            "Translate these 3 sentences from the card summary (10 minutes max).",
            "कार्डको सारांशका यी ३ वाक्य अनुवाद गर्नुहोस् (बढीमा १० मिनेट)।",
        ),
        questions=[
            _Item("Which language pairs do you translate?", "तपाईं कुन भाषाबाट कुन भाषामा अनुवाद गर्नुहुन्छ?"),
            _Item("How do you check names and numbers?", "नाम र अंक कसरी जाँच्नुहुन्छ?"),
        ],
        missing_checks=[
            (r"nepali|english|नेपाली|अंग्रेजी", _Item("From which language into which?", "कुन भाषाबाट कुन भाषामा?")),
        ],
    ),
    _Profile(
        band="data_entry",
        keywords=["data", "डाटा", "excel", "एक्सेल", "spreadsheet", "typing", "टाइप"],
        title=_Item("Data entry: {q}00 rows", "डाटा इन्ट्री: {q}०० पङ्क्ति"),
        deliverables=[_Item("A spreadsheet with {q}00 rows", "{q}०० पङ्क्ति भएको स्प्रेडसिट")],
        checklist=[
            (0, _Item("Row count matches the source", "पङ्क्ति संख्या स्रोतसँग मिल्छ")),
            (0, _Item("Every column in the agreed template is filled", "तय भएको ढाँचाका सबै स्तम्भ भरिएका")),
            (0, _Item("Delivered as .xlsx", ".xlsx मा बुझाइएको")),
        ],
        sample_brief=_Item(
            "Type these 5 sample rows into a spreadsheet (10 minutes max).",
            "यी ५ नमुना पङ्क्ति स्प्रेडसिटमा टाइप गर्नुहोस् (बढीमा १० मिनेट)।",
        ),
        questions=[
            _Item("Which spreadsheet app do you use?", "कुन स्प्रेडसिट एप प्रयोग गर्नुहुन्छ?"),
            _Item("How do you check for typing mistakes?", "टाइपिङ गल्ती कसरी जाँच्नुहुन्छ?"),
        ],
    ),
    _Profile(
        band="writing",
        keywords=["write", "writing", "लेख", "caption", "क्याप्सन", "blog", "article", "description", "विवरण"],
        title=_Item("{q} written pieces", "{q} वटा लेख"),
        deliverables=[_Item("{q} pieces of about 500 words in a shared doc", "करिब ५०० शब्दका {q} वटा लेख, साझा डकमा")],
        checklist=[
            (0, _Item("Each piece is 450 to 550 words", "हरेक लेख ४५० देखि ५५० शब्दको")),
            (0, _Item("Passes a plagiarism check", "नक्कल जाँचमा पास")),
            (0, _Item("Uses the 3 keywords the client provides", "ग्राहकले दिएका ३ मुख्य शब्द प्रयोग गरिएको")),
        ],
        sample_brief=_Item(
            "Share one piece you wrote before, or write a 60-word intro for this topic (10 minutes max).",
            "पहिले लेखेको एउटा लेख देखाउनुहोस्, वा यस विषयमा ६० शब्दको परिचय लेख्नुहोस् (बढीमा १० मिनेट)।",
        ),
        questions=[
            _Item("Which languages do you write in?", "तपाईं कुन भाषामा लेख्नुहुन्छ?"),
            _Item("How do you research a new topic?", "नयाँ विषय कसरी खोज्नुहुन्छ?"),
        ],
        missing_checks=[
            (r"word|शब्द", _Item("How many words should each piece be?", "हरेक लेख कति शब्दको हुनुपर्छ?")),
        ],
    ),
    # Default profile: social media posts / graphics (the seed scenario).
    _Profile(
        band="social_post",
        keywords=["post", "पोस्ट", "poster", "पोस्टर", "design", "डिजाइन", "banner", "ब्यानर", "flyer", "graphic"],
        title=_Item("{q} {festival}social media posts", "{q} वटा {festival_ne}सोसल मिडिया पोस्ट"),
        deliverables=[
            _Item("{q} finished post designs as PNG", "{q} वटा तयार पोस्ट डिजाइन, PNG मा"),
        ],
        checklist=[
            (0, _Item("{q} PNG files, each 1080×1080 px", "{q} वटा PNG फाइल, हरेक १०८०×१०८० px")),
            (0, _Item("Shop logo appears on every post", "हरेक पोस्टमा पसलको लोगो छ")),
            (0, _Item("Text is in both Nepali and English", "लेख नेपाली र अंग्रेजी दुवैमा छ")),
            (0, _Item("{festival_req}", "{festival_req_ne}")),
        ],
        sample_brief=_Item(
            "Share one post you designed before, or make a quick 1080×1080 greeting with one line of Nepali text (10 minutes max). This is not one of the paid posts.",
            "पहिले बनाएको एउटा पोस्ट देखाउनुहोस्, वा एक लाइन नेपाली लेखसहित १०८०×१०८० को छिटो शुभकामना बनाउनुहोस् (बढीमा १० मिनेट)। यो पैसा पाउने पोस्टमध्ये एक होइन।",
        ),
        questions=[
            _Item("Which design app do you use?", "तपाईं कुन डिजाइन एप प्रयोग गर्नुहुन्छ?"),
            _Item("How would you fit Nepali and English text on one post?", "एउटै पोस्टमा नेपाली र अंग्रेजी लेख कसरी मिलाउनुहुन्छ?"),
        ],
        missing_checks=[
            (r"logo|लोगो", _Item("Will you send your logo file?", "तपाईं आफ्नो लोगो फाइल पठाउनुहुन्छ?")),
            (r"\d{3,4}\s*[x×]\s*\d{3,4}|size|साइज", _Item("Is 1080×1080 (Facebook/Instagram square) the right size?", "१०८०×१०८० (फेसबुक/इन्स्टाग्राम वर्ग) साइज ठीक हो?")),
            (r"nepali|english|नेपाली|अंग्रेजी", _Item("Should the text be in Nepali, English or both?", "लेख नेपाली, अंग्रेजी वा दुवैमा हुनुपर्छ?")),
        ],
    ),
]

_FESTIVALS = {
    "dashain": ("Dashain ", "दसैं ", "Each post includes a Dashain greeting", "हरेक पोस्टमा दसैंको शुभकामना छ"),
    "दसैं": ("Dashain ", "दसैं ", "Each post includes a Dashain greeting", "हरेक पोस्टमा दसैंको शुभकामना छ"),
    "दशैं": ("Dashain ", "दसैं ", "Each post includes a Dashain greeting", "हरेक पोस्टमा दसैंको शुभकामना छ"),
    "tihar": ("Tihar ", "तिहार ", "Each post includes a Tihar greeting", "हरेक पोस्टमा तिहारको शुभकामना छ"),
    "तिहार": ("Tihar ", "तिहार ", "Each post includes a Tihar greeting", "हरेक पोस्टमा तिहारको शुभकामना छ"),
}
_NO_FESTIVAL = ("", "", "Shop brand colours are used", "पसलको ब्रान्ड रङ प्रयोग गरिएको")

def glossary(target: str) -> dict[str, str]:
    """Exact-match phrase pairs from the templates, for offline translation fallback."""
    pairs: list[_Item] = []
    for p in _PROFILES:
        pairs += [*p.deliverables, *(c for _, c in p.checklist), p.sample_brief, *p.questions]
        pairs += [q for _, q in p.missing_checks]
    out: dict[str, str] = {}
    for item in pairs:
        if "{" in item.en:
            continue
        src, dst = (item.en, item.ne) if target == "ne" else (item.ne, item.en)
        out[src] = dst
    return out


_BLOCKED_HINT = re.compile(r"fake review|नक्कली समीक्षा|exam|परीक्षा|homework|होमवर्क|adult|nsfw|lottery|लटरी")


def _quantity(text: str) -> int | None:
    norm = normalise_digits(text).lower()
    m = re.search(r"(\d{1,3})\s*(?:वटा|ota|wota|x\b|pcs|posts?|videos?|pages?|पोस्ट|भिडियो|पेज|लेख)", norm)
    if not m:
        m = re.search(r"\b(\d{1,3})\b(?!\s*(?:\$|usd|dollar|डलर|days?|दिन))", norm)
        if m and re.search(rf"\$\s*{m.group(1)}\b", norm):
            m = None
    if m:
        return max(1, min(50, int(m.group(1))))
    for word, n in {**NE_NUMBER_WORDS, **EN_NUMBER_WORDS}.items():
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", norm):
            return n
    return None


def _price_minor(text: str) -> int | None:
    norm = normalise_digits(text).lower()
    m = re.search(r"(?:\$|usd\s*)(\d{1,5})", norm) or re.search(r"(\d{1,5})\s*(?:usd|dollars?|डलर)", norm)
    return int(m.group(1)) * 100 if m else None


def _days(text: str) -> int | None:
    norm = normalise_digits(text).lower()
    m = re.search(r"(\d{1,2})\s*(?:days?|दिन)", norm)
    return max(1, min(60, int(m.group(1)))) if m else None


def _profile_for(text: str) -> _Profile:
    low = text.lower()
    for p in _PROFILES[:-1]:
        if any(k in low for k in p.keywords):
            return p
    return _PROFILES[-1]


def _fmt(item: _Item, lang: str, q: int, fest: tuple[str, str, str, str]) -> str:
    q_text = to_devanagari_digits(str(q)) if lang == "ne" else str(q)
    raw = item.ne if lang == "ne" else item.en
    return raw.format(q=q_text, festival=fest[0], festival_ne=fest[1], festival_req=fest[2], festival_req_ne=fest[3])


def draft_from_template(text: str) -> KaamCardDraft:
    ref = detect_language(text)
    low = normalise_digits(text).lower()

    if _BLOCKED_HINT.search(low):
        return KaamCardDraft(
            title_ne="यो काम साझा काममा राख्न मिल्दैन", title_en="This work is not allowed on Sajha Kaam",
            summary_ne="", summary_en="", deliverables=[], checklist=[], deadline_days=1,
            price=Price(amount_minor=0, is_suggestion=True), revisions_included=0, reference_language=ref,
            sample_brief_ne="", sample_brief_en="",
            questions=[Question(ne="", en=""), Question(ne="", en="")],
            needs_clarification=[], warnings=["blocked_work"],
        )

    profile = _profile_for(text)
    band = load_yaml("task_bands.yaml")["bands"][profile.band]
    fest = next((v for k, v in _FESTIVALS.items() if k in low), _NO_FESTIVAL)

    clar: list[Clarification] = []
    qty = _quantity(text)
    if qty is None:
        qty = 5
        clar.append(Clarification(question_en="How many do you need? We assumed 5.", question_ne="कति वटा चाहिन्छ? ५ वटा मानिएको छ।"))

    days = _days(text)
    if days is None:
        days = max(band["min_days"], 2 + math.ceil(qty / 2))
        clar.append(Clarification(question_en=f"When do you need it? We suggested {days} days.",
                                  question_ne=f"कहिलेसम्म चाहिन्छ? {to_devanagari_digits(str(days))} दिन सुझाइएको छ।"))

    price = _price_minor(text)
    is_suggestion = price is None
    if price is None:
        price = qty * band["typical_per_unit_minor"]

    for pattern, question in profile.missing_checks:
        if not re.search(pattern, low):
            clar.append(Clarification(question_en=question.en, question_ne=question.ne))

    deliverables = [
        Deliverable(id=f"d{i + 1}", text_en=_fmt(d, "en", qty, fest), text_ne=_fmt(d, "ne", qty, fest))
        for i, d in enumerate(profile.deliverables)
    ]
    checklist = [
        ChecklistItem(id=f"c{i + 1}", deliverable_id=f"d{d_idx + 1}",
                      text_en=_fmt(c, "en", qty, fest), text_ne=_fmt(c, "ne", qty, fest), testable=True)
        for i, (d_idx, c) in enumerate(profile.checklist)
    ]
    title_en = _fmt(profile.title, "en", qty, fest)
    title_ne = _fmt(profile.title, "ne", qty, fest)
    return KaamCardDraft(
        title_en=title_en,
        title_ne=title_ne,
        summary_en=f"{title_en}, delivered in {days} days. Fixed price, {1} revision included.",
        summary_ne=f"{title_ne}, {to_devanagari_digits(str(days))} दिनमा बुझाउने। तोकिएको मूल्य, १ पटक सुधार समावेश।",
        deliverables=deliverables,
        checklist=checklist,
        deadline_days=days,
        price=Price(amount_minor=price, is_suggestion=is_suggestion),
        revisions_included=1,
        reference_language=ref,
        sample_brief_en=profile.sample_brief.en,
        sample_brief_ne=profile.sample_brief.ne,
        questions=[Question(en=q.en, ne=q.ne) for q in profile.questions],
        needs_clarification=clar,
        warnings=[],
    )

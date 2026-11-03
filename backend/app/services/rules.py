"""Card rule checks on "Save & post" (deterministic, no AI). Thresholds live in config/*.yaml.

Every issue carries a plain-language fix in both languages. Errors block posting;
warnings flag the card for the admin queue but do not block.
"""

import re
from dataclasses import asdict, dataclass

from app.config import load_yaml
from app.schemas.kaam_card import KaamCardDraft
from app.services.i18n import normalise_digits

NE_SUFFIXES = ("", "को", "का", "की", "मा", "ले", "लाई", "हरू", "बाट")


@dataclass
class Issue:
    code: str
    severity: str  # error | warning
    message_en: str
    message_ne: str
    item_id: str | None = None


def _texts(card: KaamCardDraft) -> list[tuple[str | None, str]]:
    out: list[tuple[str | None, str]] = [(None, card.title_en), (None, card.title_ne), (None, card.summary_en),
                                         (None, card.summary_ne), ("sample_brief", card.sample_brief_en),
                                         ("sample_brief", card.sample_brief_ne)]
    out += [(d.id, d.text_en) for d in card.deliverables] + [(d.id, d.text_ne) for d in card.deliverables]
    out += [(c.id, c.text_en) for c in card.checklist] + [(c.id, c.text_ne) for c in card.checklist]
    out += [(f"q{i + 1}", q.en) for i, q in enumerate(card.questions)]
    out += [(f"q{i + 1}", q.ne) for i, q in enumerate(card.questions)]
    return out


def find_terms(text: str, en_terms: list[str], ne_terms: list[str]) -> list[str]:
    """Whole-word match: 'age' does not hit 'page', 'थर' does not hit 'पत्थर'."""
    norm = normalise_digits(text).lower()
    hits = [t for t in en_terms if re.search(rf"(?<![a-z]){re.escape(t.lower())}(?![a-z])", norm)]
    tokens = re.findall(r"[ऀ-ॿ]+", norm)
    for term in ne_terms:
        if " " in term:
            if term in norm:
                hits.append(term)
        elif any(tok == term + suf for tok in tokens for suf in NE_SUFFIXES):
            hits.append(term)
    return hits


def price_floor_minor(skill: str, card: KaamCardDraft) -> int:
    bands = [b for b in load_yaml("task_bands.yaml")["bands"].values() if b["skill"] == skill]
    per_unit = min((b["floor_per_unit_minor"] for b in bands), default=500)
    m = re.search(r"\d+", normalise_digits(card.title_en))
    qty = int(m.group()) if m and int(m.group()) <= 50 else 1
    return per_unit * max(1, qty)


def check_card(card: KaamCardDraft, skill: str) -> list[Issue]:
    rules = load_yaml("rules.yaml")
    issues: list[Issue] = []

    if "blocked_work" in card.warnings or any(
        find_terms(text, rules["blocked_work"]["en"], rules["blocked_work"]["ne"]) for _, text in _texts(card)
    ):
        issues.append(Issue("blocked_work", "error", "This kind of work is not allowed on Sajha Kaam.",
                            "यस्तो काम साझा काममा राख्न मिल्दैन।"))

    for item_id, text in _texts(card):
        hits = find_terms(text, rules["forbidden_asks"]["en"], rules["forbidden_asks"]["ne"])
        if hits:
            issues.append(Issue("forbidden_ask", "error",
                                f"Remove the request for personal details ({', '.join(hits)}). Applicants are judged on work only.",
                                f"व्यक्तिगत विवरण ({', '.join(hits)}) माग्ने कुरा हटाउनुहोस्। आवेदकलाई कामले मात्र जाँचिन्छ।",
                                item_id))

    if not card.deliverables:
        issues.append(Issue("no_deliverables", "error", "Add at least one deliverable.", "कम्तीमा एउटा बुझाउने कुरा थप्नुहोस्।"))
    covered = {c.deliverable_id for c in card.checklist}
    for d in card.deliverables:
        if d.id not in covered:
            issues.append(Issue("deliverable_without_check", "error",
                                "Add a 'Done when' item for this deliverable.",
                                "यो बुझाउने कुराका लागि 'पूरा भएको मानिने' बुँदा थप्नुहोस्।", d.id))

    for c in card.checklist:
        vague = find_terms(c.text_en, rules["untestable_words"]["en"], []) + \
            find_terms(c.text_ne, [], rules["untestable_words"]["ne"])
        if vague or not c.testable or not (c.text_en.strip() and c.text_ne.strip()):
            issues.append(Issue("untestable_item", "error",
                                "Make this checkable by a stranger: use a count, size, format or language instead of "
                                f"words like '{vague[0] if vague else 'good'}'.",
                                "अपरिचितले जाँच्न सक्ने बनाउनुहोस्: 'राम्रो' जस्ता शब्दको सट्टा संख्या, साइज, ढाँचा वा भाषा लेख्नुहोस्।",
                                c.id))

    floor = price_floor_minor(skill, card)
    if card.price.amount_minor < floor:
        issues.append(Issue("price_below_floor", "error",
                            f"The price is below the fair minimum for this task (${floor // 100}). Raise it so beginners are not underpaid.",
                            f"यो कामका लागि उचित न्यूनतम (${floor // 100}) भन्दा मूल्य कम छ। नयाँ कामदारलाई कम पैसा नहोस् भनेर बढाउनुहोस्।"))

    c_rules = rules["card"]
    if not c_rules["min_deadline_days"] <= card.deadline_days <= c_rules["max_deadline_days"]:
        issues.append(Issue("deadline", "error", "Choose a deadline between 1 and 60 days.", "म्याद १ देखि ६० दिनभित्र राख्नुहोस्।"))
    if card.revisions_included > c_rules["max_revisions"]:
        issues.append(Issue("revisions", "error", "At most 3 revisions.", "बढीमा ३ पटक सुधार।"))

    brief = normalise_digits(f"{card.sample_brief_en} {card.sample_brief_ne}").lower()
    minutes = [int(m) for m in re.findall(r"(\d+)\s*(?:-|\s)?(?:min|minute|मिनेट)", brief)]
    past = re.search(r"before|past|previous|already|पहिले|पुरानो", brief)
    if not brief.strip():
        issues.append(Issue("sample_missing", "error", "Say what applicants should send as a sample.",
                            "आवेदकले नमुनामा के पठाउने भन्नुहोस्।", "sample_brief"))
    elif any(m > c_rules["micro_sample_max_minutes"] for m in minutes) or (not minutes and not past):
        issues.append(Issue("free_labour", "error",
                            "Ask for past work or a sample of 10 minutes or less. Never ask for the real job for free.",
                            "पहिलेको काम वा बढीमा १० मिनेटको नमुना मात्र माग्नुहोस्। असली काम सित्तैमा नमाग्नुहोस्।",
                            "sample_brief"))

    if len(card.questions) != 2 or any(not (q.en.strip() or q.ne.strip()) for q in card.questions):
        issues.append(Issue("questions", "error", "Write exactly two short questions.", "ठ्याक्कै दुई छोटा प्रश्न लेख्नुहोस्।"))

    if card.price.is_suggestion:
        issues.append(Issue("price_is_suggestion", "warning", "You kept the suggested price. Check it is what you want to pay.",
                            "तपाईंले सुझाइएको मूल्य राख्नुभयो। तिर्न चाहेको मूल्य यही हो कि जाँच्नुहोस्।"))
    return issues


def to_json(issues: list[Issue]) -> list[dict]:
    return [asdict(i) for i in issues]


def passed(issues: list[Issue]) -> bool:
    return not any(i.severity == "error" for i in issues)

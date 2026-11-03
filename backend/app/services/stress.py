"""Kaam Card Stress Test ("Dispute Simulator"): finds checklist items two worried readers could argue about.

AI when configured; otherwise a rule-based fallback labelled as such. It never changes price,
deadline or revisions, never adds deliverables, and never blocks posting.
"""

import logging
import re

from pydantic import BaseModel, Field

from app.config import load_yaml
from app.schemas.kaam_card import KaamCardDraft
from app.services.i18n import normalise_digits
from app.services.rules import find_terms

log = logging.getLogger("sajha.stress")
MAX_ISSUES = 5

STRESS_SYSTEM = """Act as two skeptical readers of this Kaam Card. READER 1 is a worker afraid of being blamed \
unfairly: find places where the client could say "not done" even if the work was done. READER 2 is a client afraid \
of receiving something unusable that is technically "done". Return ONLY JSON with at most 5 issues. Each issue names \
the checklist item id (or deliverable id) it is about, the problem and why it is a dispute risk in plain English and in \
natural, simple Nepali (Devanagari, not Hindi), and a suggested rewrite in both languages that a stranger could check \
yes/no (count, size, format, language, presence). Do not change price, deadline or revisions. Do not add deliverables. \
Set testable_before to how many checklist items are already checkable, and testable_after_if_all_applied."""


class StressIssue(BaseModel):
    item_id: str
    problem_en: str
    problem_ne: str
    why_dispute_risk_en: str
    why_dispute_risk_ne: str
    suggested_rewrite_en: str  # empty: no one-tap rewrite, the client writes the fix
    suggested_rewrite_ne: str
    severity: str = Field(pattern="^(low|medium|high)$")


class StressBody(BaseModel):
    issues: list[StressIssue]
    testable_before: int
    testable_after_if_all_applied: int


class StressResult(StressBody):
    source: str  # "ai" -> "Made with AI"; "rules" -> "Checked by rules (offline)"
    total_items: int


# Something a stranger can check: a number, a size, a file type, a language, a "every/each" presence rule.
OBSERVABLE = re.compile(
    r"\d|px|png|jpe?g|mp4|pdf|docx?|xlsx|svg|nepali|english|नेपाली|अंग्रेजी|logo|लोगो|every|each|all |हरेक|सबै|"
    r"second|minute|सेकेन्ड|मिनेट|word|शब्द|page|पेज|row|पङ्क्ति|size|साइज|colour|color|रङ",
    re.I,
)


def _vague(item_en: str, item_ne: str) -> list[str]:
    words = load_yaml("rules.yaml")["untestable_words"]
    return find_terms(item_en, words["en"], []) + find_terms(item_ne, [], words["ne"])


def testable(text_en: str, text_ne: str) -> bool:
    both = normalise_digits(f"{text_en} {text_ne}")
    return not _vague(text_en, text_ne) and bool(OBSERVABLE.search(both))


def rule_based(card: KaamCardDraft) -> StressResult:
    issues: list[StressIssue] = []
    covered = {c.deliverable_id for c in card.checklist}
    for d in card.deliverables:
        if d.id not in covered:
            issues.append(StressIssue(
                item_id=d.id, severity="high",
                problem_en="This deliverable has no 'Done when' item.", problem_ne="यो बुझाउने कुराको 'पूरा भएको मानिने' बुँदा छैन।",
                why_dispute_risk_en="Nobody can say when it is finished, so either side can claim it is not.",
                why_dispute_risk_ne="कहिले सकियो भन्न सकिँदैन, त्यसैले जसले पनि 'सकिएन' भन्न सक्छ।",
                suggested_rewrite_en=f"{d.text_en} is delivered", suggested_rewrite_ne=f"{d.text_ne} बुझाइएको छ"))
    for c in card.checklist:
        vague = _vague(c.text_en, c.text_ne)
        if vague:
            word = vague[0]
            issues.append(StressIssue(
                item_id=c.id, severity="high",
                problem_en=f"'{word}' means different things to different people.",
                problem_ne=f"'{word}' को अर्थ मानिसअनुसार फरक हुन्छ।",
                why_dispute_risk_en="The worker can't prove it is met, and the client can't prove it isn't.",
                why_dispute_risk_ne="कामदारले पूरा भयो भनी प्रमाणित गर्न सक्दैनन्, ग्राहकले पनि नभएको प्रमाणित गर्न सक्दैनन्।",
                # Replace the wording entirely: keeping the vague word would keep the item vague.
                suggested_rewrite_en="Matches the reference image the client sends: same layout, logo and colours",
                suggested_rewrite_ne="ग्राहकले पठाउने नमुना तस्बिरसँग मिल्छ: उही ढाँचा, लोगो र रङ"))
        elif not testable(c.text_en, c.text_ne):
            # No one-tap rewrite offline: a guessed fix would be worse than none. The client writes it.
            issues.append(StressIssue(
                item_id=c.id, severity="medium",
                problem_en="A stranger could not check this yes or no.",
                problem_ne="अपरिचितले यसलाई हो वा होइन भनेर जाँच्न सक्दैन।",
                why_dispute_risk_en="Add a number, size, file type or language so 'done' is clear to both sides.",
                why_dispute_risk_ne="दुवैलाई 'पूरा भयो' स्पष्ट होस् भनेर संख्या, साइज, फाइल प्रकार वा भाषा थप्नुहोस्।",
                suggested_rewrite_en="", suggested_rewrite_ne=""))
    issues = issues[:MAX_ISSUES]
    before = sum(testable(c.text_en, c.text_ne) for c in card.checklist)
    fixed = {i.item_id for i in issues if i.suggested_rewrite_en and testable(i.suggested_rewrite_en, i.suggested_rewrite_ne)}
    after = sum(testable(c.text_en, c.text_ne) or c.id in fixed for c in card.checklist)
    return StressResult(issues=issues, testable_before=before, testable_after_if_all_applied=after,
                        source="rules", total_items=len(card.checklist))


def stress_test(card: KaamCardDraft, llm=None) -> StressResult:
    from app.services.llm import get_llm  # local import: llm imports templates, avoid a cycle

    llm = llm if llm is not None else get_llm()
    if llm is not None:
        try:
            body = llm.stress_test(card)
            ids = {c.id for c in card.checklist} | {d.id for d in card.deliverables}
            issues = [i for i in body.issues if i.item_id in ids][:MAX_ISSUES]
            total = len(card.checklist)
            return StressResult(issues=issues, testable_before=min(body.testable_before, total),
                                testable_after_if_all_applied=min(body.testable_after_if_all_applied, total),
                                source="ai", total_items=total)
        except Exception as e:  # timeout, refusal, bad JSON: the rules still help
            log.warning("stress_test failed, using rules: %s", type(e).__name__)
    return rule_based(card)

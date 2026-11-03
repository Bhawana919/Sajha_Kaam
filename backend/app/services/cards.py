"""Card persistence and lifecycle helpers shared by the routers.

Every state change goes through move(): the shared state machine checks the actor and the
transition, and the hash-chained audit log records it under a pseudonym.
"""

import json
from datetime import timedelta

from fastapi import HTTPException
from sqlmodel import Session, func, select

from app.config import load_yaml
from app.models import (
    Application,
    Card,
    ChecklistItemRow,
    ClientProfile,
    DeliverableRow,
    Engagement,
    PassportClaim,
    Review,
    User,
    utcnow,
)
from app.schemas.api import ApplicantRow, EngagementSummary, Feedback, FeedbackItem, MyCardItem, OwnerCard, RuleIssue
from app.schemas.board import CardDetail
from app.schemas.kaam_card import ChecklistItem, Deliverable, KaamCardDraft, Price, Question
from app.seed import demo_order_for
from app.services import audit, notify, passport, signing
from app.services.fairpick import ordered_for_reviewer
from app.services.levels import record
from app.services.state_machine import TransitionError, find

GROUPS = {
    "draft": {"draft", "ai_drafted", "client_edited", "rules_failed", "rules_passed", "pending_review", "approved"},
    "open": {"open", "expired"},
    "in_review": {"closed_for_applications", "in_review", "picked", "revealed", "worker_declined"},
    "in_progress": {"worker_accepted", "in_progress", "delivered", "revision_requested", "client_confirmed",
                    "payment_handoff", "disputed"},
    "completed": {"completed", "passport_issued", "cancelled"},
}


def application_ref(application_id: str) -> str:
    """Short, readable application id for people (SK-3F2A9C). Derived from the opaque id, never a name."""
    import hashlib

    return "SK-" + hashlib.sha256(application_id.encode()).hexdigest()[:6].upper()


def group_for(state: str) -> str:
    return next(g for g, states in GROUPS.items() if state in states)


def get_card(session: Session, card_id: str) -> Card:
    card = session.get(Card, card_id)
    if card is None:
        raise HTTPException(404, "card not found")
    return card


def own_card(session: Session, card_id: str, user: User) -> Card:
    card = get_card(session, card_id)
    if card.client_id != user.id:
        raise HTTPException(403, "not your card")
    return card


def move(session: Session, card: Card, action: str, actor_role: str, pseudonym: str,
         payload: dict | None = None, to_state: str | None = None) -> None:
    try:
        t = find("card", card.state, action, actor_role, to_state)
    except TransitionError as e:
        raise HTTPException(409, str(e)) from e
    to_state = t.to_state
    if to_state == "*previous":
        to_state = (payload or {}).get("restore_to") or card.state
    audit.append(session, card.id, pseudonym, action, {"from": card.state, "to": to_state, **(payload or {})})
    card.state = to_state
    session.add(card)


def rows(session: Session, card_id: str) -> tuple[list[DeliverableRow], list[ChecklistItemRow]]:
    dels = session.exec(select(DeliverableRow).where(DeliverableRow.card_id == card_id)
                        .order_by(DeliverableRow.position)).all()
    items = session.exec(select(ChecklistItemRow).where(ChecklistItemRow.card_id == card_id)
                         .order_by(ChecklistItemRow.position)).all()
    return list(dels), list(items)


def to_draft(session: Session, card: Card) -> KaamCardDraft:
    dels, items = rows(session, card.id)
    return KaamCardDraft(
        title_ne=card.title_ne, title_en=card.title_en, summary_ne=card.summary_ne, summary_en=card.summary_en,
        deliverables=[Deliverable(id=d.id, text_ne=d.text_ne, text_en=d.text_en) for d in dels],
        checklist=[ChecklistItem(id=c.id, deliverable_id=c.deliverable_id, text_ne=c.text_ne, text_en=c.text_en,
                                 testable=c.testable) for c in items],
        deadline_days=card.deadline_days,
        price=Price(amount_minor=card.price_minor, currency="USD", is_suggestion=False),
        revisions_included=card.revisions_included, reference_language=card.reference_language,
        sample_brief_ne=card.sample_brief_ne, sample_brief_en=card.sample_brief_en,
        questions=[Question(**q) for q in json.loads(card.questions_json)],
        needs_clarification=[], warnings=[],
    )


def save_draft(session: Session, card: Card, draft: KaamCardDraft) -> None:
    for name in ("title_ne", "title_en", "summary_ne", "summary_en", "deadline_days", "revisions_included",
                 "reference_language", "sample_brief_ne", "sample_brief_en"):
        setattr(card, name, getattr(draft, name))
    card.price_minor = draft.price.amount_minor
    card.currency = draft.price.currency
    card.questions_json = json.dumps([q.model_dump() for q in draft.questions], ensure_ascii=False)
    old_dels, old_items = rows(session, card.id)
    for r in [*old_dels, *old_items]:
        session.delete(r)
    session.flush()
    for i, d in enumerate(draft.deliverables):
        session.add(DeliverableRow(card_id=card.id, id=d.id, position=i, text_ne=d.text_ne, text_en=d.text_en))
    for i, c in enumerate(draft.checklist):
        session.add(ChecklistItemRow(card_id=card.id, id=c.id, deliverable_id=c.deliverable_id, position=i,
                                     text_ne=c.text_ne, text_en=c.text_en, testable=c.testable))


def active_apps(session: Session, card_id: str) -> list[Application]:
    return list(session.exec(select(Application).where(Application.card_id == card_id,
                                                       Application.state != "withdrawn")).all())


def applicant_count(session: Session, card_id: str) -> int:
    return session.exec(select(func.count()).select_from(Application)
                        .where(Application.card_id == card_id, Application.state != "withdrawn")).one()


def refresh_window(session: Session, card: Card) -> None:
    """Close (or expire) an open card whose 48 h window has passed. Idempotent."""
    if card.state != "open" or card.window_closes_at is None:
        return
    closes = card.window_closes_at.replace(tzinfo=None)
    if utcnow().replace(tzinfo=None) < closes:
        return
    if applicant_count(session, card.id):
        move(session, card, "close_window", "system", "System")
        notify.send(session, card.client_id, "window_closed", card_id=card.id, title_ne=card.title_ne,
                    title_en=card.title_en, applicants=applicant_count(session, card.id))
    else:
        move(session, card, "expire", "system", "System")
    session.commit()


def open_window(card: Card) -> None:
    hours = load_yaml("rules.yaml")["board"]["window_hours"]
    card.window_opens_at = utcnow()
    card.window_closes_at = card.window_opens_at + timedelta(hours=hours)


def letters(session: Session, card: Card) -> dict[str, str]:
    """application_id -> letter, as the card's client sees them (server-side only).

    Withdrawn applications keep their letter, so nobody else's letter shifts."""
    every = list(session.exec(select(Application).where(Application.card_id == card.id)).all())
    pairs = ordered_for_reviewer(every, card.client_id, card.id, demo_order_for(card.id))
    return {app.id: letter for letter, app in pairs}


def reviews_by_app(session: Session, card: Card) -> dict[str, Review]:
    return {r.application_id: r for r in session.exec(
        select(Review).where(Review.card_id == card.id, Review.reviewer_id == card.client_id)).all()}


def feedback_for(session: Session, card: Card, review: Review | None) -> Feedback:
    """Template feedback from the client's stars (3 stars = met). Not AI judgement."""
    _, items = rows(session, card.id)
    stars = json.loads(review.star_scores_json) if review else {}
    missing = [FeedbackItem(id=i.id, text_ne=i.text_ne, text_en=i.text_en) for i in items if stars.get(i.id, 0) < 3]
    return Feedback(met=len(items) - len(missing), total=len(items), missing=missing)


def current_engagement(session: Session, card_id: str) -> Engagement | None:
    return session.exec(select(Engagement).where(Engagement.card_id == card_id, Engagement.state != "declined")
                        .order_by(Engagement.created_at.desc())).first()


def detail(session: Session, card: Card) -> CardDetail:
    profile = session.get(ClientProfile, card.client_id)
    draft = to_draft(session, card)
    return CardDetail(
        id=card.id, title_ne=card.title_ne, title_en=card.title_en, skill=card.skill,
        price=Price(amount_minor=card.price_minor, currency="USD", is_suggestion=False),
        deadline_days=card.deadline_days, revisions_included=card.revisions_included, pahilo_kaam=card.pahilo_kaam,
        client_country=profile.country if profile else "", applicant_count=applicant_count(session, card.id),
        max_applicants=load_yaml("rules.yaml")["board"]["max_applicants"], window_closes_at=card.window_closes_at,
        state=card.state, summary_ne=card.summary_ne, summary_en=card.summary_en,
        reference_language=card.reference_language, deliverables=draft.deliverables, checklist=draft.checklist,
        sample_brief_ne=card.sample_brief_ne, sample_brief_en=card.sample_brief_en, questions=draft.questions,
        reviewed_by_sajha=card.reviewed_by_sajha,
    )


def owner_view(session: Session, card: Card) -> OwnerCard:
    eng = current_engagement(session, card.id)
    summary = None
    if eng:
        revealed = card.state not in ("picked",)
        worker = session.get(User, eng.worker_id) if revealed else None
        summary = EngagementSummary(id=eng.id, state=eng.state, worker_display_name=worker.display_name if worker else None)
    letter_of = letters(session, card)
    picked_letter = letter_of.get(card.picked_application_id) if card.picked_application_id else None
    # Letters are fixed only once the window closes (new applicants would shift them before that).
    show_letters = card.state not in ("open", "expired") and card.state not in GROUPS["draft"]
    apps = sorted(active_apps(session, card.id), key=lambda a: (letter_of.get(a.id, ""), a.created_at))
    applicants = [ApplicantRow(application_id=a.id, application_ref=application_ref(a.id),
                               letter=letter_of.get(a.id) if show_letters else None, state=a.state) for a in apps]
    return OwnerCard(
        **detail(session, card).model_dump(), version=card.version, draft_source=card.draft_source,
        rules=[RuleIssue(**r) for r in json.loads(card.rules_result_json or "[]")],
        picked_letter=picked_letter, engagement=summary, applicants=applicants,
    )


def my_card_item(session: Session, card: Card) -> MyCardItem:
    eng = current_engagement(session, card.id)
    return MyCardItem(id=card.id, title_ne=card.title_ne, title_en=card.title_en, state=card.state,
                      group=group_for(card.state), applicant_count=applicant_count(session, card.id),
                      window_closes_at=card.window_closes_at, engagement_id=eng.id if eng else None)


def issue_claim(session: Session, card: Card, eng: Engagement, type_: str, source_label: str) -> PassportClaim:
    """One claim per (engagement, type). Calling twice returns the existing claim."""
    existing = session.exec(select(PassportClaim).where(PassportClaim.engagement_id == eng.id,
                                                        PassportClaim.type == type_)).first()
    if existing:
        return existing
    on_time = eng.due_at is None or eng.delivered_at is None or \
        eng.delivered_at.replace(tzinfo=None) <= eng.due_at.replace(tzinfo=None)
    claim = PassportClaim(
        user_id=eng.worker_id, engagement_id=eng.id, type=type_, skill=card.skill,
        summary_en=card.title_en, summary_ne=card.title_ne, level_at_time=record(session, eng.worker_id).level["id"],
        source_label=source_label, on_time=on_time,
    )
    session.add(claim)
    session.flush()
    # Sign it now: the record is checkable by anyone, on their own device, from this moment.
    worker = session.get(User, eng.worker_id)
    credential = signing.credential_for(claim, worker.display_name, passport.get_or_create(session, worker.id).slug)
    claim.credential_json = audit.canonical(credential)
    claim.signature_b64, claim.key_id = signing.sign(credential)
    session.add(claim)
    session.flush()
    return claim

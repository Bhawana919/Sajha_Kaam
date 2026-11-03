"""Client card endpoints: draft, save, post (rule checks), blind review, score, pick, reveal."""

import json

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import require_role
from app.db import get_session
from app.models import AcquaintanceAttestation, Application, Card, Engagement, Review, User, utcnow
from app.schemas.api import (
    CardWrite,
    MyCardItem,
    OwnerCard,
    PickOut,
    PickRequest,
    PostResult,
    RevealOut,
    RuleIssue,
    ScoreOut,
    ScoreRequest,
)
from app.schemas.blind import BlindAnswer, BlindApplicant, BlindReview
from app.schemas.kaam_card import DraftRequest, DraftResponse, KaamCardDraft
from app.services import audit, idempotency, llm, notify, rules
from app.services.cards import (
    GROUPS,
    active_apps,
    current_engagement,
    letters,
    move,
    my_card_item,
    open_window,
    own_card,
    owner_view,
    refresh_window,
    reviews_by_app,
    rows,
    save_draft,
    to_draft,
)
from app.services.levels import record
from app.services.skills import skills
from app.services.stress import StressResult, stress_test

router = APIRouter(prefix="/v1", tags=["cards"])
client_only = require_role("client")
EDITABLE = {"ai_drafted", "client_edited", "rules_failed", "rules_passed"}
REVIEWABLE = GROUPS["in_review"] | GROUPS["in_progress"] | GROUPS["completed"]


@router.post("/cards/draft", response_model=DraftResponse)
def draft(body: DraftRequest) -> DraftResponse:
    """Nothing is saved or posted here; the client edits, then saves and posts."""
    return llm.draft_card(body.text)


class StressRequest(BaseModel):
    card: KaamCardDraft


@router.post("/cards/stress-test", response_model=StressResult)
def stress(body: StressRequest, _: User = Depends(client_only)) -> StressResult:
    """Advice only: it never changes price, deadline or revisions and never blocks posting."""
    return stress_test(body.card)


@router.post("/cards", response_model=OwnerCard)
def create_card(body: CardWrite, user: User = Depends(client_only), session: Session = Depends(get_session),
                idempotency_key: str | None = Header(None)) -> dict:
    if body.skill not in {s["id"] for s in skills()}:
        raise HTTPException(422, "unknown skill")

    def compute() -> dict:
        card = Card(client_id=user.id, state="draft", skill=body.skill, pahilo_kaam=body.pahilo_kaam,
                    draft_source=body.source)
        session.add(card)
        session.flush()
        save_draft(session, card, body.card)
        move(session, card, "draft_with_ai" if body.source in ("ai", "template") else "edit", "client", "Client",
             {"source": body.source})
        session.commit()
        return owner_view(session, card).model_dump(mode="json")

    return idempotency.run(session, user.id, "create_card", idempotency_key, compute)


@router.patch("/cards/{card_id}", response_model=OwnerCard)
def edit_card(card_id: str, body: CardWrite, user: User = Depends(client_only),
              session: Session = Depends(get_session)) -> OwnerCard:
    card = own_card(session, card_id, user)
    if card.state not in EDITABLE:
        raise HTTPException(409, "this card can no longer be edited")
    card.skill, card.pahilo_kaam, card.version = body.skill, body.pahilo_kaam, card.version + 1
    save_draft(session, card, body.card)
    move(session, card, "edit", "client", "Client", {"version": card.version})
    session.commit()
    return owner_view(session, card)


@router.post("/cards/{card_id}/post", response_model=PostResult)
def post_card(card_id: str, user: User = Depends(client_only), session: Session = Depends(get_session),
              idempotency_key: str | None = Header(None)) -> dict:
    card = own_card(session, card_id, user)

    def compute() -> dict:
        if card.state == "rules_failed":
            raise HTTPException(409, "fix the card first")
        if card.state in ("ai_drafted", "client_edited"):
            issues = rules.check_card(to_draft(session, card), card.skill)
            card.rules_result_json = json.dumps(rules.to_json(issues), ensure_ascii=False)
            card.reviewed_by_sajha = True  # the checks ran; "approved" is separate (admin)
            ok = rules.passed(issues)
            move(session, card, "check_rules", "system", "System", {"passed": ok},
                 to_state="rules_passed" if ok else "rules_failed")
            if not ok:
                session.commit()
                return PostResult(state=card.state, posted=False, rules=[RuleIssue(**i) for i in rules.to_json(issues)]
                                  ).model_dump(mode="json")
            card.flagged = any(i.severity == "warning" and i.code != "price_is_suggestion" for i in issues)
        if card.state != "rules_passed":
            raise HTTPException(409, f"cannot post a card in state {card.state}")
        first_card = session.exec(select(Card).where(Card.client_id == user.id, Card.id != card.id,
                                                     Card.state.not_in(GROUPS["draft"]))).first() is None
        to_queue = first_card or card.flagged
        move(session, card, "post", "client", "Client", {"first_card": first_card, "flagged": card.flagged},
             to_state="pending_review" if to_queue else "open")
        if to_queue:
            notify.send(session, user.id, "card_pending_review", card_id=card.id,
                        title_ne=card.title_ne, title_en=card.title_en)
        else:
            open_window(card)
            notify.send(session, user.id, "card_posted", card_id=card.id, title_ne=card.title_ne, title_en=card.title_en)
        session.add(card)
        session.commit()
        return PostResult(state=card.state, posted=True,
                          rules=[RuleIssue(**i) for i in json.loads(card.rules_result_json or "[]")]).model_dump(mode="json")

    return idempotency.run(session, user.id, f"post:{card_id}", idempotency_key, compute)


@router.post("/cards/{card_id}/extend", response_model=OwnerCard)
def extend(card_id: str, user: User = Depends(client_only), session: Session = Depends(get_session)) -> OwnerCard:
    card = own_card(session, card_id, user)
    refresh_window(session, card)
    if card.state != "expired" or card.extended_once:
        raise HTTPException(409, "only an expired card can be extended, once")
    move(session, card, "extend", "client", "Client")
    card.extended_once = True
    open_window(card)
    session.commit()
    return owner_view(session, card)


@router.get("/me/cards", response_model=list[MyCardItem])
def my_cards(user: User = Depends(client_only), session: Session = Depends(get_session)) -> list[MyCardItem]:
    cards = session.exec(select(Card).where(Card.client_id == user.id).order_by(Card.created_at.desc())).all()
    for c in cards:
        refresh_window(session, c)
    return [my_card_item(session, c) for c in cards]


@router.get("/cards/{card_id}/manage", response_model=OwnerCard)
def manage(card_id: str, user: User = Depends(client_only), session: Session = Depends(get_session)) -> OwnerCard:
    card = own_card(session, card_id, user)
    refresh_window(session, card)
    return owner_view(session, card)


# ---------- Fair Pick ----------

def build_blind_review(session: Session, card: Card) -> BlindReview:
    letter_of = letters(session, card)
    reviews = reviews_by_app(session, card)
    _, items = rows(session, card.id)
    apps = sorted(active_apps(session, card.id), key=lambda a: letter_of[a.id])
    blind = [
        BlindApplicant(
            application_id=a.id, letter=letter_of[a.id], sample_text=a.scrubbed_text, sample_lang=a.sample_lang,
            answers=[BlindAnswer(**x) for x in json.loads(a.answers_json)],
            confirmed_jobs=record(session, a.worker_id).confirmed_jobs, on_time_pct=record(session, a.worker_id).on_time_pct,
        )
        for a in apps
    ]
    attested = session.exec(select(AcquaintanceAttestation).where(AcquaintanceAttestation.card_id == card.id)).first()
    return BlindReview(
        card_id=card.id, state=card.state, applicant_count=len(blind), checklist_ids=[i.id for i in items],
        applicants=blind, scores={app_id: json.loads(r.star_scores_json) for app_id, r in reviews.items()},
        attested_unacquainted=attested is not None,
    )


@router.get("/cards/{card_id}/review", response_model=BlindReview)
def review(card_id: str, user: User = Depends(client_only), session: Session = Depends(get_session)) -> BlindReview:
    card = own_card(session, card_id, user)
    refresh_window(session, card)
    if card.state not in REVIEWABLE:
        raise HTTPException(409, "review opens when the application window closes")
    return build_blind_review(session, card)


@router.put("/reviews/{application_id}", response_model=ScoreOut)
def score(application_id: str, body: ScoreRequest, user: User = Depends(client_only),
          session: Session = Depends(get_session)) -> ScoreOut:
    app = session.get(Application, application_id)
    if app is None or app.state == "withdrawn":
        raise HTTPException(404, "application not found")
    card = own_card(session, app.card_id, user)
    if card.state == "closed_for_applications":
        move(session, card, "start_review", "client", "Client")
    if card.state != "in_review":
        raise HTTPException(409, "scoring is only open during review")
    _, items = rows(session, card.id)
    if set(body.stars) != {i.id for i in items}:
        raise HTTPException(422, "give stars for every checklist item, and only those")
    letter = letters(session, card)[app.id]
    review_row = reviews_by_app(session, card).get(app.id) or Review(
        card_id=card.id, reviewer_id=user.id, application_id=app.id, letter=letter)
    review_row.star_scores_json = json.dumps(body.stars, sort_keys=True)
    review_row.total = sum(body.stars.values())
    app.state = "scored"
    session.add_all([review_row, app])
    audit.append(session, card.id, "Client", "score", {"applicant": letter, "stars": body.stars, "total": review_row.total})
    session.commit()
    return ScoreOut(application_id=app.id, letter=letter, stars=body.stars, total=review_row.total)


@router.post("/cards/{card_id}/attest-unacquainted", response_model=BlindReview)
def attest(card_id: str, user: User = Depends(client_only), session: Session = Depends(get_session)) -> BlindReview:
    card = own_card(session, card_id, user)
    if card.state not in ("closed_for_applications", "in_review"):
        raise HTTPException(409, "attest during review")
    if not session.exec(select(AcquaintanceAttestation).where(AcquaintanceAttestation.card_id == card.id)).first():
        session.add(AcquaintanceAttestation(card_id=card.id, client_id=user.id))
        audit.append(session, card.id, "Client", "attest_unacquainted", {})
        session.commit()
    return build_blind_review(session, card)


def ranked(session: Session, card: Card) -> list[tuple[Application, int]]:
    """Scored applications by total, excluding any whose offer was declined."""
    declined = {e.application_id for e in session.exec(
        select(Engagement).where(Engagement.card_id == card.id, Engagement.state == "declined")).all()}
    reviews = reviews_by_app(session, card)
    apps = [a for a in active_apps(session, card.id) if a.id not in declined]
    return sorted(((a, reviews[a.id].total if a.id in reviews else -1) for a in apps), key=lambda x: -x[1])


@router.post("/cards/{card_id}/pick", response_model=PickOut)
def pick(card_id: str, body: PickRequest, user: User = Depends(client_only), session: Session = Depends(get_session),
         idempotency_key: str | None = Header(None)) -> dict:
    card = own_card(session, card_id, user)

    def compute() -> dict:
        if card.state != "in_review":
            raise HTTPException(409, "score the applicants first")
        if not session.exec(select(AcquaintanceAttestation).where(AcquaintanceAttestation.card_id == card.id)).first():
            raise HTTPException(409, "confirm you don't personally know any applicant")
        order = ranked(session, card)
        if any(total < 0 for _, total in order):
            raise HTTPException(409, "score every applicant before picking")
        top = order[0][1]
        tied = [a for a, total in order if total == top]
        if len(tied) == 1:
            chosen = tied[0]
        else:
            chosen = next((a for a in tied if a.id == body.application_id), None)
            if chosen is None or not (body.tie_note or "").strip():
                raise HTTPException(409, "tie: choose one of the tied applicants and give a reason")
            card.tie_note = body.tie_note
        letter = letters(session, card)[chosen.id]
        card.picked_application_id = chosen.id
        chosen.state = "picked"
        move(session, card, "pick", "client", "Client",
             {"applicant": letter, "total": top, "tied": len(tied) > 1, "tie_note": card.tie_note})
        session.add(chosen)
        session.commit()
        return PickOut(letter=letter, total=top, state=card.state).model_dump(mode="json")

    return idempotency.run(session, user.id, f"pick:{card_id}", idempotency_key, compute)


@router.post("/cards/{card_id}/reveal", response_model=RevealOut)
def reveal(card_id: str, user: User = Depends(client_only), session: Session = Depends(get_session),
           idempotency_key: str | None = Header(None)) -> dict:
    card = own_card(session, card_id, user)

    def compute() -> dict:
        if card.state != "picked" or not card.picked_application_id:
            raise HTTPException(409, "pick an applicant first")
        app = session.get(Application, card.picked_application_id)
        worker = session.get(User, app.worker_id)
        eng = Engagement(card_id=card.id, application_id=app.id, worker_id=worker.id)
        session.add(eng)
        move(session, card, "reveal", "client", "Client", {"applicant": letters(session, card)[app.id],
                                                         "revealed_at": utcnow().isoformat()})
        notify.send(session, worker.id, "offer", card_id=card.id, engagement_id=eng.id,
                    title_ne=card.title_ne, title_en=card.title_en)
        session.commit()
        return RevealOut(worker_display_name=worker.display_name, engagement_id=eng.id).model_dump(mode="json")

    return idempotency.run(session, user.id, f"reveal:{card_id}", idempotency_key, compute)


def offer_next(session: Session, card: Card) -> bool:
    """After a decline: offer the card to the next-highest applicant (the client reveals again)."""
    order = [a for a, total in ranked(session, card) if total >= 0]
    if not order:
        return False
    nxt = order[0]
    card.picked_application_id = nxt.id
    nxt.state = "picked"
    session.add(nxt)
    move(session, card, "offer_next", "system", "System", {"applicant": letters(session, card)[nxt.id]})
    notify.send(session, card.client_id, "declined", card_id=card.id, title_ne=card.title_ne, title_en=card.title_en,
                next_letter=letters(session, card)[nxt.id])
    return True


__all__ = ["router", "offer_next", "current_engagement"]

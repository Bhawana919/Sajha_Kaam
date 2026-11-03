"""Public board and card detail (guests can browse)."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

from app.config import load_yaml
from app.db import get_session
from app.models import Application, Card, ChecklistItemRow, ClientProfile, DeliverableRow
from app.schemas.board import BoardCard, BoardPage, CardDetail
from app.schemas.kaam_card import ChecklistItem, Deliverable, Price, Question
from app.services.cards import refresh_window
from app.services.skills import match_skill_ids, skills

router = APIRouter(prefix="/v1", tags=["board"])
PUBLIC_STATES = ("open",)


def _board_card(session: Session, card: Card) -> BoardCard:
    profile = session.get(ClientProfile, card.client_id)
    count = session.exec(select(func.count()).select_from(Application)
                         .where(Application.card_id == card.id, Application.state != "withdrawn")).one()
    return BoardCard(
        id=card.id, title_ne=card.title_ne, title_en=card.title_en, skill=card.skill,
        price=Price(amount_minor=card.price_minor, currency=card.currency, is_suggestion=False),
        deadline_days=card.deadline_days, revisions_included=card.revisions_included,
        pahilo_kaam=card.pahilo_kaam, client_country=profile.country if profile else "",
        applicant_count=count, max_applicants=load_yaml("rules.yaml")["board"]["max_applicants"],
        window_closes_at=card.window_closes_at, state=card.state,
    )


@router.get("/skills")
def list_skills() -> list[dict]:
    return [{"id": s["id"], "en": s["en"], "ne": s["ne"]} for s in skills()]


@router.get("/board", response_model=BoardPage)
def board(pahilo: bool = False, skill: str | None = None, q: str | None = None,
          min_price_minor: int | None = Query(None, ge=0), max_price_minor: int | None = Query(None, ge=0),
          session: Session = Depends(get_session)) -> BoardPage:
    stmt = select(Card).where(Card.state.in_(PUBLIC_STATES)).order_by(Card.window_closes_at)
    if pahilo:
        stmt = stmt.where(Card.pahilo_kaam)
    if skill:
        stmt = stmt.where(Card.skill == skill)
    if min_price_minor is not None:
        stmt = stmt.where(Card.price_minor >= min_price_minor)
    if max_price_minor is not None:
        stmt = stmt.where(Card.price_minor <= max_price_minor)
    cards = list(session.exec(stmt).all())
    for c in cards:
        refresh_window(session, c)
    cards = [c for c in cards if c.state == "open"]
    if q:
        ids = match_skill_ids(q)
        ql = q.lower()
        cards = [c for c in cards if c.skill in ids or ql in c.title_en.lower() or q in c.title_ne]
    return BoardPage(items=[_board_card(session, c) for c in cards])


@router.get("/cards/{card_id}", response_model=CardDetail)
def card_detail(card_id: str, session: Session = Depends(get_session)) -> CardDetail:
    card = session.get(Card, card_id)
    if card is not None:
        refresh_window(session, card)
    if card is None or card.state not in PUBLIC_STATES:
        raise HTTPException(404, "card not found")
    dels = session.exec(select(DeliverableRow).where(DeliverableRow.card_id == card_id)
                        .order_by(DeliverableRow.position)).all()
    items = session.exec(select(ChecklistItemRow).where(ChecklistItemRow.card_id == card_id)
                         .order_by(ChecklistItemRow.position)).all()
    base = _board_card(session, card)
    return CardDetail(
        **base.model_dump(),
        summary_ne=card.summary_ne, summary_en=card.summary_en, reference_language=card.reference_language,
        deliverables=[Deliverable(id=d.id, text_ne=d.text_ne, text_en=d.text_en) for d in dels],
        checklist=[ChecklistItem(id=c.id, deliverable_id=c.deliverable_id, text_ne=c.text_ne, text_en=c.text_en,
                                 testable=c.testable) for c in items],
        sample_brief_ne=card.sample_brief_ne, sample_brief_en=card.sample_brief_en,
        questions=[Question(**q) for q in json.loads(card.questions_json)],
        reviewed_by_sajha=card.reviewed_by_sajha,
    )

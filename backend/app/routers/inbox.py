"""Notifications, the worker's Passport and Kaam Path, translation and cases."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.auth import current_user, require_role
from app.db import get_session
from app.models import Card, Case, Engagement, Notification, User, utcnow
from app.schemas.api import CaseIn, NotificationOut
from app.schemas.kaam_card import TranslateRequest, TranslateResponse
from app.services import audit, llm, notify
from app.services.cards import get_card, move
from app.services.state_machine import locked_states

router = APIRouter(prefix="/v1", tags=["inbox"])


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(user: User = Depends(current_user), session: Session = Depends(get_session)) -> list[NotificationOut]:
    rows = session.exec(select(Notification).where(Notification.user_id == user.id)
                        .order_by(Notification.created_at.desc()).limit(100)).all()
    return [NotificationOut(id=n.id, type=n.type, params=json.loads(n.payload_json), read=n.read_at is not None,
                            created_at=n.created_at) for n in rows]


@router.post("/notifications/read-all", response_model=int)
def read_all(user: User = Depends(current_user), session: Session = Depends(get_session)) -> int:
    unread = session.exec(select(Notification).where(Notification.user_id == user.id,
                                                     Notification.read_at.is_(None))).all()
    for n in unread:
        n.read_at = utcnow()
        session.add(n)
    session.commit()
    return len(unread)


@router.post("/translate", response_model=TranslateResponse)
def translate(body: TranslateRequest, _: User = Depends(current_user)) -> TranslateResponse:
    """Labelled "Translated by AI" in the app; 'original' means no offline translation was possible."""
    return llm.translate(body.text, body.target)


@router.post("/cases", response_model=dict)
def open_case(body: CaseIn, user: User = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    card = get_card(session, body.card_id)
    eng = session.exec(select(Engagement).where(Engagement.card_id == card.id, Engagement.state == "accepted")).first()
    if user.id not in (card.client_id, eng.worker_id if eng else None):
        raise HTTPException(404, "card not found")
    if card.state not in locked_states():
        raise HTTPException(409, "a case can be opened once the job has started")
    role = "client" if user.id == card.client_id else "worker"
    case = Case(card_id=card.id, opened_by=user.id, reason=body.reason, state_before=card.state)
    session.add(case)
    move(session, card, "open_case", role, "Client" if role == "client" else "Worker", {"case_id": case.id})
    for uid in {card.client_id, eng.worker_id}:
        notify.send(session, uid, "case_opened", card_id=card.id, title_ne=card.title_ne, title_en=card.title_en)
    session.commit()
    return {"case_id": case.id, "status": case.status}


# ---------- admin ----------

admin_router = APIRouter(prefix="/v1/admin", tags=["admin"])


@admin_router.get("/queue", response_model=list[dict])
def queue(_: User = Depends(require_role("admin")), session: Session = Depends(get_session)) -> list[dict]:
    cards = session.exec(select(Card).where(Card.state == "pending_review").order_by(Card.created_at)).all()
    return [{"card_id": c.id, "title_en": c.title_en, "title_ne": c.title_ne, "flagged": c.flagged,
             "rules": json.loads(c.rules_result_json or "[]")} for c in cards]


@admin_router.post("/cards/{card_id}/decision", response_model=dict)
def decide(card_id: str, body: dict, _: User = Depends(require_role("admin")),
           session: Session = Depends(get_session)) -> dict:
    from app.schemas.api import AdminDecision
    from app.services.cards import open_window

    d = AdminDecision.model_validate(body)
    card = get_card(session, card_id)
    if d.decision == "approve":
        move(session, card, "approve", "admin", "Sajha reviewer", {"reason": d.reason})
        card.admin_approved = True
        open_window(card)
        move(session, card, "open_window", "system", "System")
        notify.send(session, card.client_id, "card_approved", card_id=card.id, title_ne=card.title_ne,
                    title_en=card.title_en)
    elif d.decision == "request_change":
        move(session, card, "request_change", "admin", "Sajha reviewer", {"reason": d.reason})
        notify.send(session, card.client_id, "card_changes_requested", card_id=card.id, title_ne=card.title_ne,
                    title_en=card.title_en, reason=d.reason)
    else:
        move(session, card, "reject", "admin", "Sajha reviewer", {"reason": d.reason})
    session.commit()
    return {"card_id": card.id, "state": card.state}


@admin_router.get("/cards/{card_id}/audit", response_model=dict)
def audit_trail(card_id: str, _: User = Depends(require_role("admin")), session: Session = Depends(get_session)) -> dict:
    chain = audit.events(session, card_id)
    return {"broken_at": audit.verify(chain),
            "events": [{**audit.event_body(e), "prev_hash": e.prev_hash, "hash": e.hash} for e in chain]}

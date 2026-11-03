"""After the reveal: accept/decline, lock, workroom, deliver, confirm, payment handoff, messages.

Payment never moves through Sajha Kaam. The client pays the worker's own Khalti payment
request outside the app; "paid" appears only when BOTH sides have confirmed.
"""

import json
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session, select

from app.auth import current_user
from app.db import get_session
from app.models import (
    Application,
    Card,
    ClientProfile,
    Delivery,
    Engagement,
    Message,
    PaymentConfirmation,
    User,
    utcnow,
)
from app.routers.cards import offer_next
from app.schemas.api import (
    AcceptRequest,
    ConfirmRequest,
    DeliverRequest,
    DeliveryOut,
    EngagementOut,
    FeedbackItem,
    MessageIn,
    MessageOut,
    PaymentOut,
    RevisionRequest,
)
from app.services import idempotency, leakguard, notify
from app.services.cards import feedback_for, issue_claim, letters, move, reviews_by_app, rows, to_draft

router = APIRouter(prefix="/v1/engagements", tags=["engagements"])
REVEALED_STATES = {"revealed", "worker_accepted", "in_progress", "delivered", "revision_requested",
                   "client_confirmed", "payment_handoff", "completed", "passport_issued", "disputed"}


def _load(session: Session, engagement_id: str, user: User) -> tuple[Engagement, Card, str]:
    eng = session.get(Engagement, engagement_id)
    if eng is None:
        raise HTTPException(404, "not found")
    card = session.get(Card, eng.card_id)
    if user.id == card.client_id:
        return eng, card, "client"
    if user.id == eng.worker_id:
        return eng, card, "worker"
    raise HTTPException(404, "not found")


def _need(role: str, wanted: str) -> None:
    if role != wanted:
        raise HTTPException(403, f"only the {wanted} can do this")


def _worker_alias(session: Session, card: Card, eng: Engagement) -> str:
    return f"Applicant {letters(session, card).get(eng.application_id, '?')}"


def view(session: Session, eng: Engagement, card: Card, role: str) -> EngagementOut:
    worker = session.get(User, eng.worker_id)
    profile = session.get(ClientProfile, card.client_id)
    deliveries = session.exec(select(Delivery).where(Delivery.engagement_id == eng.id).order_by(Delivery.created_at)).all()
    payment = session.get(PaymentConfirmation, eng.id)
    _, items = rows(session, card.id)
    show_link = role == "worker" or card.state in ("client_confirmed", "payment_handoff", "completed", "passport_issued")
    return EngagementOut(
        id=eng.id, card_id=card.id, title_ne=card.title_ne, title_en=card.title_en, state=eng.state,
        card_state=card.state, my_role=role,
        worker_display_name=worker.display_name if card.state in REVEALED_STATES or role == "worker" else None,
        client_country=profile.country if profile else "", price_minor=card.price_minor, currency=card.currency,
        revisions_used=eng.revisions_used, revisions_included=card.revisions_included, due_at=eng.due_at,
        khalti_payment_link=eng.khalti_payment_link if show_link else None,
        deliveries=[DeliveryOut(id=d.id, note=d.note, link=d.link, created_at=d.created_at,
                                revision_notes=json.loads(d.revision_notes_json) if d.revision_notes_json else None)
                    for d in deliveries],
        payment=PaymentOut(client_marked_paid_at=payment.client_marked_paid_at,
                           worker_confirmed_received_at=payment.worker_confirmed_received_at,
                           simulated=payment.simulated) if payment else None,
        checklist=[FeedbackItem(id=i.id, text_ne=i.text_ne, text_en=i.text_en) for i in items],
    )


@router.get("/me", response_model=list[EngagementOut])
def my_engagements(user: User = Depends(current_user), session: Session = Depends(get_session)) -> list[EngagementOut]:
    if user.role == "worker":
        engs = session.exec(select(Engagement).where(Engagement.worker_id == user.id)).all()
    else:
        engs = session.exec(select(Engagement).join(Card).where(Card.client_id == user.id,
                                                                 Engagement.state != "declined")).all()
    out = []
    for e in engs:
        _, card, role = _load(session, e.id, user)
        out.append(view(session, e, card, role))
    return sorted(out, key=lambda v: v.title_en)


@router.get("/{engagement_id}", response_model=EngagementOut)
def get_engagement(engagement_id: str, user: User = Depends(current_user),
                   session: Session = Depends(get_session)) -> EngagementOut:
    eng, card, role = _load(session, engagement_id, user)
    return view(session, eng, card, role)


@router.post("/{engagement_id}/accept", response_model=EngagementOut)
def accept(engagement_id: str, body: AcceptRequest, user: User = Depends(current_user),
           session: Session = Depends(get_session), idempotency_key: str | None = Header(None)) -> dict:
    eng, card, role = _load(session, engagement_id, user)
    _need(role, "worker")

    def compute() -> dict:
        link = body.khalti_payment_link.strip()
        if not link.startswith("https://"):
            raise HTTPException(422, "paste the https:// payment-request link from your Khalti app")
        if eng.state != "offered" or card.state != "revealed":
            raise HTTPException(409, "this offer is no longer open")
        alias = _worker_alias(session, card, eng)
        move(session, card, "accept", "worker", alias)
        now = utcnow()
        card.terms_snapshot_json = to_draft(session, card).model_dump_json()
        card.locked_at = now
        eng.state, eng.accepted_at, eng.khalti_payment_link = "accepted", now, link
        eng.due_at = now + timedelta(days=card.deadline_days)
        move(session, card, "start_work", "system", "System", {"locked_version": card.version})
        # Everyone else gets checklist feedback from the client's stars (a template, not AI).
        reviews = reviews_by_app(session, card)
        for app in session.exec(select(Application).where(Application.card_id == card.id,
                                                          Application.id != eng.application_id,
                                                          Application.state.in_(("submitted", "scored")))).all():
            fb = feedback_for(session, card, reviews.get(app.id))
            app.state, app.feedback_json = "not_picked_feedback_sent", fb.model_dump_json()
            session.add(app)
            notify.send(session, app.worker_id, "feedback", card_id=card.id, title_ne=card.title_ne,
                        title_en=card.title_en, met=fb.met, total=fb.total)
        notify.send(session, card.client_id, "accepted", card_id=card.id, engagement_id=eng.id,
                    title_ne=card.title_ne, title_en=card.title_en)
        session.add_all([eng, card])
        session.commit()
        return view(session, eng, card, role).model_dump(mode="json")

    return idempotency.run(session, user.id, f"accept:{engagement_id}", idempotency_key, compute)


@router.post("/{engagement_id}/decline", response_model=EngagementOut)
def decline(engagement_id: str, user: User = Depends(current_user), session: Session = Depends(get_session)) -> EngagementOut:
    """No penalty. The next-highest applicant is offered the job."""
    eng, card, role = _load(session, engagement_id, user)
    _need(role, "worker")
    if eng.state != "offered" or card.state != "revealed":
        raise HTTPException(409, "this offer is no longer open")
    move(session, card, "decline", "worker", _worker_alias(session, card, eng))
    eng.state = "declined"
    session.add(eng)
    session.flush()
    offer_next(session, card)
    session.commit()
    return view(session, eng, card, role)


@router.post("/{engagement_id}/deliveries", response_model=EngagementOut)
def deliver(engagement_id: str, body: DeliverRequest, user: User = Depends(current_user),
            session: Session = Depends(get_session), idempotency_key: str | None = Header(None)) -> dict:
    eng, card, role = _load(session, engagement_id, user)
    _need(role, "worker")

    def compute() -> dict:
        move(session, card, "deliver", "worker", _worker_alias(session, card, eng))
        eng.delivered_at = utcnow()
        session.add_all([Delivery(engagement_id=eng.id, note=body.note, link=body.link), eng])
        notify.send(session, card.client_id, "delivered", card_id=card.id, engagement_id=eng.id,
                    title_ne=card.title_ne, title_en=card.title_en)
        session.commit()
        return view(session, eng, card, role).model_dump(mode="json")

    return idempotency.run(session, user.id, f"deliver:{engagement_id}:{eng.revisions_used}", idempotency_key, compute)


def _latest_delivery(session: Session, eng: Engagement) -> Delivery:
    d = session.exec(select(Delivery).where(Delivery.engagement_id == eng.id).order_by(Delivery.created_at.desc())).first()
    if d is None:
        raise HTTPException(409, "nothing delivered yet")
    return d


@router.post("/{engagement_id}/request-revision", response_model=EngagementOut)
def request_revision(engagement_id: str, body: RevisionRequest, user: User = Depends(current_user),
                     session: Session = Depends(get_session)) -> EngagementOut:
    eng, card, role = _load(session, engagement_id, user)
    _need(role, "client")
    if eng.revisions_used >= card.revisions_included:
        raise HTTPException(409, "all agreed revisions are used")
    _, items = rows(session, card.id)
    if not body.notes or not set(body.notes) <= {i.id for i in items}:
        raise HTTPException(422, "say which checklist items are missing")
    move(session, card, "request_revision", "client", "Client", {"items": sorted(body.notes)})
    d = _latest_delivery(session, eng)
    d.revision_notes_json = json.dumps(body.notes, ensure_ascii=False)
    eng.revisions_used += 1
    session.add_all([d, eng])
    notify.send(session, eng.worker_id, "revision_requested", card_id=card.id, engagement_id=eng.id,
                title_ne=card.title_ne, title_en=card.title_en)
    session.commit()
    return view(session, eng, card, role)


@router.post("/{engagement_id}/confirm", response_model=EngagementOut)
def confirm(engagement_id: str, body: ConfirmRequest, user: User = Depends(current_user),
            session: Session = Depends(get_session), idempotency_key: str | None = Header(None)) -> dict:
    eng, card, role = _load(session, engagement_id, user)
    _need(role, "client")

    def compute() -> dict:
        _, items = rows(session, card.id)
        if set(body.checklist) != {i.id for i in items} or not all(body.checklist.values()):
            raise HTTPException(422, "tick every checklist item to confirm, or request a revision")
        move(session, card, "confirm", "client", "Client")
        d = _latest_delivery(session, eng)
        d.checklist_result_json = json.dumps(body.checklist)
        session.add(d)
        issue_claim(session, card, eng, "client_confirmed_delivery", "Client confirmed delivery on Sajha Kaam")
        notify.send(session, eng.worker_id, "confirmed", card_id=card.id, engagement_id=eng.id,
                    title_ne=card.title_ne, title_en=card.title_en)
        session.commit()
        return view(session, eng, card, role).model_dump(mode="json")

    return idempotency.run(session, user.id, f"confirm:{engagement_id}", idempotency_key, compute)


@router.post("/{engagement_id}/payment/client-paid", response_model=EngagementOut)
def client_paid(engagement_id: str, user: User = Depends(current_user), session: Session = Depends(get_session),
                idempotency_key: str | None = Header(None)) -> dict:
    eng, card, role = _load(session, engagement_id, user)
    _need(role, "client")

    def compute() -> dict:
        move(session, card, "client_paid", "client", "Client")
        pay = session.get(PaymentConfirmation, eng.id) or PaymentConfirmation(engagement_id=eng.id)
        pay.client_marked_paid_at = utcnow()
        session.add(pay)
        notify.send(session, eng.worker_id, "payment_marked", card_id=card.id, engagement_id=eng.id,
                    title_ne=card.title_ne, title_en=card.title_en)
        session.commit()
        return view(session, eng, card, role).model_dump(mode="json")

    return idempotency.run(session, user.id, f"client_paid:{engagement_id}", idempotency_key, compute)


@router.post("/{engagement_id}/payment/worker-received", response_model=EngagementOut)
def worker_received(engagement_id: str, user: User = Depends(current_user), session: Session = Depends(get_session),
                    idempotency_key: str | None = Header(None)) -> dict:
    eng, card, role = _load(session, engagement_id, user)
    _need(role, "worker")

    def compute() -> dict:
        move(session, card, "worker_received", "worker", _worker_alias(session, card, eng))
        pay = session.get(PaymentConfirmation, eng.id)
        pay.worker_confirmed_received_at = utcnow()
        session.add(pay)
        issue_claim(session, card, eng, "both_confirmed_payment", "Client and worker both confirmed payment")
        move(session, card, "issue_passport", "system", "System")
        notify.send(session, card.client_id, "payment_received", card_id=card.id, engagement_id=eng.id,
                    title_ne=card.title_ne, title_en=card.title_en)
        notify.send(session, eng.worker_id, "passport_issued", card_id=card.id, title_ne=card.title_ne,
                    title_en=card.title_en)
        session.commit()
        return view(session, eng, card, role).model_dump(mode="json")

    return idempotency.run(session, user.id, f"worker_received:{engagement_id}", idempotency_key, compute)


@router.get("/{engagement_id}/messages", response_model=list[MessageOut])
def messages(engagement_id: str, user: User = Depends(current_user), session: Session = Depends(get_session)) -> list[MessageOut]:
    eng, _, _ = _load(session, engagement_id, user)
    rows_ = session.exec(select(Message).where(Message.engagement_id == eng.id).order_by(Message.created_at)).all()
    return [MessageOut(id=m.id, mine=m.sender_id == user.id, text=m.text, lang=m.lang,
                       warnings=json.loads(m.warnings_json), created_at=m.created_at) for m in rows_]


@router.post("/{engagement_id}/messages", response_model=MessageOut)
def send_message(engagement_id: str, body: MessageIn, user: User = Depends(current_user),
                 session: Session = Depends(get_session)) -> MessageOut:
    eng, card, _ = _load(session, engagement_id, user)
    if eng.state != "accepted":
        raise HTTPException(409, "messages open once the card is locked")
    warnings = leakguard.scan_message(body.text)
    m = Message(engagement_id=eng.id, sender_id=user.id, text=body.text, lang=body.lang,
                warnings_json=json.dumps(warnings))
    session.add(m)
    session.commit()
    return MessageOut(id=m.id, mine=True, text=m.text, lang=m.lang, warnings=warnings, created_at=m.created_at)

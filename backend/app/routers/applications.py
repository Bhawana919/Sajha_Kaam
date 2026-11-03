"""Worker side: Leak Guard scan, apply, withdraw, my applications."""

import json

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session, select

from app.auth import current_user, require_role
from app.config import load_yaml
from app.db import get_session
from app.models import Application, Card, Engagement, User, WorkerProfile, utcnow
from app.schemas.api import ApplicationCreate, Feedback, LeakFinding, LeakScanOut, LeakScanRequest, MyApplication
from app.services import audit, idempotency, leakguard, notify
from app.services.cards import GROUPS, applicant_count, application_ref, get_card, move, refresh_window
from app.services.levels import record

router = APIRouter(prefix="/v1", tags=["applications"])
worker_only = require_role("worker")
LIVE_APP_STATES = ("submitted", "scored", "picked")


def _name_tokens(session: Session, user: User) -> list[str]:
    profile = session.get(WorkerProfile, user.id)
    tokens = json.loads(profile.name_tokens_json) if profile else []
    return tokens or [t for t in user.display_name.replace(".", " ").split() if len(t) > 1]


@router.post("/leakguard/scan", response_model=LeakScanOut)
def scan(body: LeakScanRequest, user: User = Depends(current_user), session: Session = Depends(get_session)) -> LeakScanOut:
    tokens = _name_tokens(session, user) if user.role == "worker" else []
    findings = leakguard.scan(body.text, tokens)
    return LeakScanOut(findings=[LeakFinding(**f) for f in leakguard.to_json(findings)],
                       redacted=leakguard.redact(body.text, findings))


@router.post("/leakguard/message-check", response_model=list[str])
def message_check(body: LeakScanRequest, _: User = Depends(current_user)) -> list[str]:
    """Warn the sender before a message shares a phone/email or moves to personal chat."""
    return leakguard.scan_message(body.text)


def eligibility_error(session: Session, worker: User, card: Card) -> str | None:
    rec = record(session, worker.id)
    board = load_yaml("rules.yaml")["board"]
    if card.pahilo_kaam and rec.confirmed_jobs > board["pahilo_kaam_max_confirmed_jobs"]:
        return "pahilo_kaam_only_beginners"
    if card.price_minor > rec.level["price_cap_minor"]:
        return "above_level_cap"
    live = session.exec(select(Application).join(Card).where(
        Application.worker_id == worker.id, Application.state.in_(LIVE_APP_STATES),
        Card.state.not_in(GROUPS["completed"]))).all()
    if len(live) >= board["max_active_applications_per_worker"]:
        return "too_many_active_applications"
    return None


@router.post("/cards/{card_id}/applications", response_model=MyApplication)
def apply(card_id: str, body: ApplicationCreate, user: User = Depends(worker_only),
          session: Session = Depends(get_session), idempotency_key: str | None = Header(None)) -> dict:
    card = get_card(session, card_id)

    def compute() -> dict:
        refresh_window(session, card)
        if card.state != "open":
            raise HTTPException(409, "applications are closed")
        if not (body.consent and body.no_identifying_details):
            raise HTTPException(422, "tick both boxes to apply")
        if session.exec(select(Application).where(Application.card_id == card.id, Application.worker_id == user.id,
                                                  Application.state != "withdrawn")).first():
            raise HTTPException(409, "you already applied")
        reason = eligibility_error(session, user, card)
        if reason:
            raise HTTPException(403, reason)
        tokens = _name_tokens(session, user)
        findings = leakguard.scan(body.sample_text, tokens) + [f for a in body.answers for f in leakguard.scan(a, tokens)]
        if findings:
            raise HTTPException(422, {"code": "leak_guard", "findings": leakguard.to_json(findings)})
        app = Application(
            card_id=card.id, worker_id=user.id, sample_text=body.sample_text, scrubbed_text=body.sample_text,
            sample_lang=body.sample_lang, consent_at=utcnow(),
            answers_json=json.dumps([{"question_index": i, "text": a, "lang": body.sample_lang}
                                     for i, a in enumerate(body.answers)], ensure_ascii=False),
        )
        session.add(app)
        session.flush()
        count = applicant_count(session, card.id)
        audit.append(session, card.id, "Worker", "apply", {"applicant_count": count})
        notify.send(session, card.client_id, "new_applicant", card_id=card.id, title_ne=card.title_ne,
                    title_en=card.title_en, applicants=count)
        if count >= load_yaml("rules.yaml")["board"]["max_applicants"]:
            move(session, card, "close_window", "system", "System", {"reason": "max_applicants"})
            notify.send(session, card.client_id, "window_closed", card_id=card.id, title_ne=card.title_ne,
                        title_en=card.title_en, applicants=count)
        session.commit()
        return my_application(session, app).model_dump(mode="json")

    return idempotency.run(session, user.id, f"apply:{card_id}", idempotency_key, compute)


@router.delete("/applications/{application_id}", response_model=MyApplication)
def withdraw(application_id: str, user: User = Depends(worker_only), session: Session = Depends(get_session)) -> MyApplication:
    app = session.get(Application, application_id)
    if app is None or app.worker_id != user.id:
        raise HTTPException(404, "application not found")
    if app.state not in ("submitted", "scored") or get_card(session, app.card_id).picked_application_id:
        raise HTTPException(409, "you can only withdraw before the pick")
    app.state = "withdrawn"
    session.add(app)
    audit.append(session, app.card_id, "Worker", "withdraw", {})
    session.commit()
    return my_application(session, app)


def my_application(session: Session, app: Application) -> MyApplication:
    card = session.get(Card, app.card_id)
    eng = session.exec(select(Engagement).where(Engagement.application_id == app.id)
                       .order_by(Engagement.created_at.desc())).first()
    worker = session.get(User, app.worker_id)
    return MyApplication(
        id=app.id, application_ref=application_ref(app.id), applicant_name=worker.display_name, role="worker",
        card_id=card.id, title_ne=card.title_ne, title_en=card.title_en, state=app.state,
        card_state=card.state, created_at=app.created_at,
        feedback=Feedback(**json.loads(app.feedback_json)) if app.feedback_json else None,
        engagement_id=eng.id if eng else None,
    )


@router.get("/me/applications", response_model=list[MyApplication])
def my_applications(user: User = Depends(worker_only), session: Session = Depends(get_session)) -> list[MyApplication]:
    apps = session.exec(select(Application).where(Application.worker_id == user.id)
                        .order_by(Application.created_at.desc())).all()
    for a in apps:
        refresh_window(session, session.get(Card, a.card_id))
    return [my_application(session, a) for a in apps]

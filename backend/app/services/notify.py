"""In-app notifications, stored as type + params. The app renders the text from its locale
files, so every notice exists in both languages. No streaks, no "come back" nudges."""

import json

from sqlmodel import Session

from app.models import Notification

TYPES = {
    "new_applicant", "window_closed", "picked", "revealed", "offer", "accepted", "declined", "delivered",
    "revision_requested", "confirmed", "payment_marked", "payment_received", "passport_issued",
    "feedback", "card_posted", "card_pending_review", "card_approved", "card_changes_requested", "case_opened",
}


def send(session: Session, user_id: str, type_: str, **params) -> Notification:
    assert type_ in TYPES, type_
    n = Notification(user_id=user_id, type=type_, payload_json=json.dumps(params, ensure_ascii=False))
    session.add(n)
    return n

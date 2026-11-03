"""Work Passport: public address, share links, export and deletion. Private by default."""

import hashlib
import json
import secrets
from datetime import timedelta

from sqlmodel import Session, select

from app.config import settings
from app.models import Notification, Passport, PassportClaim, ShareLink, User, WorkerProfile, utcnow


def get_or_create(session: Session, user_id: str) -> Passport:
    p = session.get(Passport, user_id)
    if p is None:
        p = Passport(user_id=user_id, slug=secrets.token_urlsafe(8).replace("-", "x").replace("_", "y"))
        session.add(p)
        session.flush()  # the caller's route commits, so issuing a claim stays one transaction
    return p


def base_url(request_base: str) -> str:
    return (settings().public_base_url or request_base).rstrip("/")


def public_url(slug: str, request_base: str) -> str:
    return f"{base_url(request_base)}/p/{slug}"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_share(session: Session, user_id: str, claim_ids: list[str], days: int) -> tuple[ShareLink, str]:
    token = secrets.token_urlsafe(16)
    link = ShareLink(user_id=user_id, token_hash=_hash(token), claim_ids_json=json.dumps(sorted(claim_ids)),
                     expires_at=utcnow() + timedelta(days=days))
    session.add(link)
    session.commit()
    return link, token


def share_url(token: str, request_base: str) -> str:
    return f"{base_url(request_base)}/s/{token}"


def active_share(session: Session, token: str) -> ShareLink | None:
    link = session.exec(select(ShareLink).where(ShareLink.token_hash == _hash(token))).first()
    if link is None or link.revoked_at is not None:
        return None
    if utcnow().replace(tzinfo=None) >= link.expires_at.replace(tzinfo=None):
        return None
    return link


def claims_for(session: Session, user_id: str, ids: list[str] | None = None, public_only: bool = False) -> list[PassportClaim]:
    stmt = select(PassportClaim).where(PassportClaim.user_id == user_id).order_by(PassportClaim.issued_at.desc())
    rows = list(session.exec(stmt).all())
    if ids is not None:
        rows = [c for c in rows if c.id in set(ids)]
    if public_only:
        rows = [c for c in rows if c.visibility == "public"]
    return rows


def export(session: Session, user: User) -> dict:
    """Everything Sajha Kaam holds in the worker's Passport, as plain JSON."""
    return {
        "exported_at": utcnow().isoformat(),
        "display_name": user.display_name,
        "note_en": "A record of work done on Sajha Kaam. Not a government ID, work permit, tax document or legal identity.",
        "note_ne": "साझा काममा गरिएको कामको अभिलेख। यो सरकारी परिचयपत्र, श्रम स्वीकृति, कर कागजात वा कानुनी पहिचान होइन।",
        "claims": [c.model_dump(mode="json", exclude={"credential_json", "signature_b64", "key_id"})
                   for c in claims_for(session, user.id)],
    }


def delete_everything(session: Session, user: User) -> None:
    """Delete the Passport and personal data. Pseudonymous audit events stay so other people's records hold."""
    for model in (PassportClaim, ShareLink, Notification):
        for row in session.exec(select(model).where(model.user_id == user.id)).all():
            session.delete(row)
    p = session.get(Passport, user.id)
    if p:
        session.delete(p)
    profile = session.get(WorkerProfile, user.id)
    if profile:
        profile.name_tokens_json, profile.district, profile.khalti_payment_link = "[]", None, None
        session.add(profile)
    user.display_name = "Deleted account"
    user.email = f"deleted-{user.id}@deleted.invalid"
    user.password_hash = "!"  # can never sign in again
    session.add(user)
    session.commit()

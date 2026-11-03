"""Append-only, hash-chained audit log per card.

hash = SHA-256(prev_hash || canonical_json(event)), canonical = sorted keys, no whitespace.
Actors are pseudonyms ("Client", "Applicant C", "System"); never names.
The public Receipt (P1) recomputes the chain on-device with the same rule.
"""

import hashlib
import json

from sqlmodel import Session, select

from app.models import AuditEvent, utcnow

GENESIS = "0" * 64


def canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def event_body(e: AuditEvent) -> dict:
    return {"card_id": e.card_id, "seq": e.seq, "actor": e.actor_pseudonym, "action": e.action,
            "payload": json.loads(e.payload_json),
            "at": e.created_at_utc.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"}


def compute_hash(prev_hash: str, body: dict) -> str:
    return hashlib.sha256((prev_hash + canonical(body)).encode()).hexdigest()


def events(session: Session, card_id: str) -> list[AuditEvent]:
    return list(session.exec(select(AuditEvent).where(AuditEvent.card_id == card_id).order_by(AuditEvent.seq)).all())


def append(session: Session, card_id: str, actor: str, action: str, payload: dict | None = None) -> AuditEvent:
    chain = events(session, card_id)
    prev = chain[-1].hash if chain else GENESIS
    e = AuditEvent(card_id=card_id, seq=len(chain) + 1, actor_pseudonym=actor, action=action,
                   payload_json=canonical(payload or {}), created_at_utc=utcnow().replace(microsecond=0),
                   prev_hash=prev, hash="")
    e.hash = compute_hash(prev, event_body(e))
    session.add(e)
    session.flush()
    return e


def verify(chain: list[AuditEvent]) -> int | None:
    """Return the seq of the first broken event, or None if the whole chain is intact."""
    prev = GENESIS
    for e in chain:
        if e.prev_hash != prev or compute_hash(prev, event_body(e)) != e.hash:
            return e.seq
        prev = e.hash
    return None

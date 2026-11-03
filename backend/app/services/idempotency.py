"""Idempotency for mutations: the same Idempotency-Key from the same user replays the first response."""

import json
from collections.abc import Callable

from sqlmodel import Session

from app.models import IdempotencyRecord


def run(session: Session, user_id: str, scope: str, key: str | None, compute: Callable[[], dict]) -> dict:
    if not key:
        return compute()
    record_key = f"{user_id}|{scope}|{key}"
    existing = session.get(IdempotencyRecord, record_key)
    if existing:
        return json.loads(existing.response_json)
    result = compute()
    session.add(IdempotencyRecord(key=record_key, response_json=json.dumps(result, ensure_ascii=False, default=str)))
    session.commit()
    return result

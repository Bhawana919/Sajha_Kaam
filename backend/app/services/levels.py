"""Kaam Path levels, from client-confirmed jobs only (config/levels.yaml)."""

from dataclasses import dataclass

from sqlmodel import Session, select

from app.config import load_yaml
from app.models import PassportClaim


@dataclass
class WorkerRecord:
    confirmed_jobs: int
    on_time_pct: int | None
    level: dict
    next_level: dict | None


def record(session: Session, worker_id: str) -> WorkerRecord:
    claims = session.exec(select(PassportClaim).where(PassportClaim.user_id == worker_id,
                                                      PassportClaim.type == "client_confirmed_delivery")).all()
    n = len(claims)
    pct = round(100 * sum(c.on_time for c in claims) / n) if n else None
    levels = load_yaml("levels.yaml")["levels"]
    current = levels[0]
    for lv in levels:
        if n >= lv["min_confirmed_jobs"] and (pct or 0) >= lv["min_on_time_pct"]:
            current = lv
    idx = levels.index(current)
    return WorkerRecord(n, pct, current, levels[idx + 1] if idx + 1 < len(levels) else None)

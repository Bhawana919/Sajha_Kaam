"""Fair Pick: blind letters in a random order that is stable per reviewer."""

import hashlib
import string

from app.config import settings
from app.models import Application

LETTERS = string.ascii_uppercase


def ordered_for_reviewer(apps: list[Application], reviewer_id: str, card_id: str,
                         demo_order: list[str] | None = None) -> list[tuple[str, Application]]:
    """Return (letter, application) pairs.

    Pass every application, withdrawn ones included, so letters never shift mid-review.

    Real mode: order by SHA-256(reviewer|card|application) - random-looking, stable for this
    reviewer, different for other reviewers and other jobs. Demo mode may pin a fixed order
    so the pitch can say "Applicant F" every time.
    """
    if settings().demo_mode and demo_order:
        rank = {app_id: i for i, app_id in enumerate(demo_order)}
        ordered = sorted(apps, key=lambda a: rank.get(a.id, len(rank)))
    else:
        ordered = sorted(apps, key=lambda a: hashlib.sha256(f"{reviewer_id}|{card_id}|{a.id}".encode()).hexdigest())
    return [(LETTERS[i], a) for i, a in enumerate(ordered)]

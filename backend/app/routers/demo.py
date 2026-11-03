"""Demo controls (DEMO_MODE=1 only). Every screen that uses them is labelled DEMO in the app."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.config import settings
from app.db import engine, get_session, init_db
from app.models import utcnow
from app.schemas.api import MyCardItem
from app.seed import seed
from app.services.cards import get_card, my_card_item, refresh_window


def demo_only() -> None:
    if not settings().demo_mode:
        raise HTTPException(404, "not found")


router = APIRouter(prefix="/demo", tags=["demo"], dependencies=[Depends(demo_only)])


@router.post("/reset", response_model=dict)
def reset() -> dict:
    init_db(reset=True)
    with Session(engine) as session:
        seed(session)
    return {"ok": True}


@router.post("/cards/{card_id}/fast-forward", response_model=MyCardItem)
def fast_forward(card_id: str, session: Session = Depends(get_session)) -> MyCardItem:
    """Skip the rest of the 48 h window so review can start now."""
    card = get_card(session, card_id)
    if card.state != "open":
        raise HTTPException(409, "only an open card can be fast-forwarded")
    card.window_closes_at = utcnow() - timedelta(seconds=1)
    session.add(card)
    session.commit()
    refresh_window(session, card)
    return my_card_item(session, card)

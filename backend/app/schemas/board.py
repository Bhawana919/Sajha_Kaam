"""Public board and card detail. Clients are shown by country only."""

from datetime import UTC, datetime

from pydantic import BaseModel, field_validator

from app.schemas.kaam_card import ChecklistItem, Deliverable, Lang, Price, Question


class BoardCard(BaseModel):
    id: str
    title_ne: str
    title_en: str
    skill: str
    price: Price
    deadline_days: int
    revisions_included: int
    pahilo_kaam: bool
    client_country: str
    applicant_count: int
    max_applicants: int
    window_closes_at: datetime | None
    state: str

    @field_validator("window_closes_at")
    @classmethod
    def _utc(cls, v: datetime | None) -> datetime | None:
        # SQLite drops tzinfo; every stored time is UTC, so say so on the wire.
        return v.replace(tzinfo=UTC) if v is not None and v.tzinfo is None else v


class CardDetail(BoardCard):
    summary_ne: str
    summary_en: str
    reference_language: Lang
    deliverables: list[Deliverable]
    checklist: list[ChecklistItem]
    sample_brief_ne: str
    sample_brief_en: str
    questions: list[Question]
    reviewed_by_sajha: bool


class BoardPage(BaseModel):
    items: list[BoardCard]
    next_cursor: str | None = None

"""Kaam Card contract. Mirrors shared/kaam_card.schema.json; money is integer minor units."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Lang = Literal["ne", "en"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Deliverable(_Strict):
    id: str
    text_ne: str
    text_en: str


class ChecklistItem(_Strict):
    id: str
    deliverable_id: str
    text_ne: str
    text_en: str
    testable: bool


class Price(_Strict):
    amount_minor: int = Field(ge=0)
    currency: Literal["USD"] = "USD"
    is_suggestion: bool


class Question(_Strict):
    ne: str
    en: str


class Clarification(_Strict):
    question_ne: str
    question_en: str


class KaamCardDraft(_Strict):
    title_ne: str
    title_en: str
    summary_ne: str
    summary_en: str
    deliverables: list[Deliverable]
    checklist: list[ChecklistItem]
    deadline_days: int = Field(ge=1, le=60)
    price: Price
    revisions_included: int = Field(ge=0, le=3)
    reference_language: Lang
    sample_brief_ne: str
    sample_brief_en: str
    questions: list[Question] = Field(min_length=2, max_length=2)
    needs_clarification: list[Clarification]
    warnings: list[str]


DraftSource = Literal["ai", "template"]


class DraftRequest(_Strict):
    text: str = Field(min_length=3, max_length=2000)


class DraftResponse(_Strict):
    source: DraftSource
    """'ai' -> label "Made with AI"; 'template' -> label "From template"."""
    card: KaamCardDraft


class TranslateRequest(_Strict):
    text: str = Field(min_length=1, max_length=4000)
    target: Lang


class TranslateResponse(_Strict):
    text: str
    source: Literal["ai", "glossary", "original"]
    """'ai' -> label "Translated by AI"; 'original' -> no translation was possible offline."""

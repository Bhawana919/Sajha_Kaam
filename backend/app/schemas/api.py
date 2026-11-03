"""Request/response models for auth, cards, applications, engagements, passport and inbox."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.board import CardDetail
from app.schemas.kaam_card import KaamCardDraft, Lang

UtcDatetime = datetime
EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- auth / me ----------

class RegisterRequest(_In):
    role: Literal["client", "worker"]
    email: str = Field(pattern=EMAIL, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=60)
    locale: Lang = "ne"
    country: str | None = Field(default=None, max_length=60)
    org_label: str | None = Field(default=None, max_length=80)
    skills: list[str] = Field(default_factory=list, max_length=5)
    age_attested: bool = False
    consent: bool


class LoginRequest(_In):
    email: str = Field(pattern=EMAIL, max_length=254)
    password: str


class RefreshRequest(_In):
    refresh_token: str


class SampleLoginRequest(_In):
    user_id: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LevelOut(BaseModel):
    id: str
    en: str
    ne: str
    price_cap_minor: int


class Me(BaseModel):
    id: str
    role: str
    display_name: str
    locale: Lang
    numerals_pref: Literal["devanagari", "latin"]
    is_sample_identity: bool
    country: str | None = None
    skills: list[str] = []
    confirmed_jobs: int | None = None
    level: LevelOut | None = None


class MePatch(_In):
    locale: Lang | None = None
    numerals_pref: Literal["devanagari", "latin"] | None = None
    skills: list[str] | None = Field(default=None, min_length=1, max_length=5)


class SampleIdentity(BaseModel):
    user_id: str
    role: str
    display_name: str
    note_en: str
    note_ne: str


# ---------- cards ----------

class CardWrite(_In):
    card: KaamCardDraft
    skill: str
    pahilo_kaam: bool = True
    source: Literal["ai", "template", "manual"] = "manual"


class RuleIssue(BaseModel):
    code: str
    severity: Literal["error", "warning"]
    message_en: str
    message_ne: str
    item_id: str | None = None


class PostResult(BaseModel):
    state: str
    posted: bool
    rules: list[RuleIssue]


class EngagementSummary(BaseModel):
    id: str
    state: str
    worker_display_name: str | None  # client sees it only after the reveal


class ApplicantRow(BaseModel):
    """One applicant as the client sees them. Deliberately no name field: the hired worker's
    name arrives only through `engagement` after "Reveal & hire" (Fair Pick)."""

    application_id: str
    application_ref: str  # short, readable id, e.g. SK-3F2A9C
    letter: str | None  # A, B, C... once the application window has closed
    role: str = "worker"
    state: str


class OwnerCard(CardDetail):
    """The client's own view of a card in any state."""

    applicants: list[ApplicantRow] = []
    version: int
    draft_source: str | None
    rules: list[RuleIssue]
    picked_letter: str | None = None
    engagement: EngagementSummary | None = None


class MyCardItem(BaseModel):
    id: str
    title_ne: str
    title_en: str
    state: str
    group: Literal["draft", "open", "in_review", "in_progress", "completed"]
    applicant_count: int
    window_closes_at: UtcDatetime | None
    engagement_id: str | None = None


class ScoreRequest(_In):
    stars: dict[str, int]

    @field_validator("stars")
    @classmethod
    def _range(cls, v: dict[str, int]) -> dict[str, int]:
        if any(s not in (1, 2, 3) for s in v.values()):
            raise ValueError("each item gets 1, 2 or 3 stars")
        return v


class ScoreOut(BaseModel):
    application_id: str
    letter: str
    stars: dict[str, int]
    total: int


class PickRequest(_In):
    application_id: str | None = None  # needed only to break a tie
    tie_note: str | None = Field(default=None, max_length=280)


class PickOut(BaseModel):
    letter: str
    total: int
    state: str


class RevealOut(BaseModel):
    worker_display_name: str
    engagement_id: str


# ---------- applications ----------

class ApplicationCreate(_In):
    sample_text: str = Field(min_length=10, max_length=2000)
    sample_lang: Lang
    answers: list[str] = Field(min_length=2, max_length=2)
    consent: bool
    no_identifying_details: bool

    @field_validator("answers")
    @classmethod
    def _short(cls, v: list[str]) -> list[str]:
        if any(not a.strip() or len(a) > 280 for a in v):
            raise ValueError("each answer is 1 to 280 characters")
        return v


class FeedbackItem(BaseModel):
    id: str
    text_ne: str
    text_en: str


class Feedback(BaseModel):
    met: int
    total: int
    missing: list[FeedbackItem]


class MyApplication(BaseModel):
    id: str
    application_ref: str
    applicant_name: str  # the worker's own name, on their own application
    role: str = "worker"
    card_id: str
    title_ne: str
    title_en: str
    state: str
    card_state: str
    created_at: UtcDatetime
    feedback: Feedback | None = None
    engagement_id: str | None = None


class LeakScanRequest(_In):
    text: str = Field(max_length=4000)


class LeakFinding(BaseModel):
    kind: str
    start: int
    end: int
    text: str


class LeakScanOut(BaseModel):
    findings: list[LeakFinding]
    redacted: str


# ---------- engagements ----------

class AcceptRequest(_In):
    khalti_payment_link: str = Field(min_length=8, max_length=300)


class DeliverRequest(_In):
    note: str = Field(min_length=1, max_length=2000)
    link: str | None = Field(default=None, max_length=500)


class RevisionRequest(_In):
    notes: dict[str, str]  # checklist item id -> what is missing


class ConfirmRequest(_In):
    checklist: dict[str, bool]


class DeliveryOut(BaseModel):
    id: str
    note: str
    link: str | None
    created_at: UtcDatetime
    revision_notes: dict[str, str] | None = None


class PaymentOut(BaseModel):
    client_marked_paid_at: UtcDatetime | None
    worker_confirmed_received_at: UtcDatetime | None
    simulated: bool


class EngagementOut(BaseModel):
    id: str
    card_id: str
    title_ne: str
    title_en: str
    state: str
    card_state: str
    my_role: Literal["client", "worker"]
    worker_display_name: str | None
    client_country: str
    price_minor: int
    currency: str
    revisions_used: int
    revisions_included: int
    due_at: UtcDatetime | None
    khalti_payment_link: str | None  # client sees it after confirming the work
    deliveries: list[DeliveryOut]
    payment: PaymentOut | None
    checklist: list[FeedbackItem]


class MessageIn(_In):
    text: str = Field(min_length=1, max_length=2000)
    lang: Lang


class MessageOut(BaseModel):
    id: str
    mine: bool
    text: str
    lang: str
    warnings: list[str]
    created_at: UtcDatetime


class CaseIn(_In):
    card_id: str
    reason: str = Field(min_length=3, max_length=1000)


# ---------- passport / inbox ----------

class ClaimOut(BaseModel):
    id: str
    type: str
    skill: str
    summary_en: str
    summary_ne: str
    level_at_time: str
    source_label: str
    on_time: bool
    issued_at: UtcDatetime
    visibility: str
    signed: bool = False
    # The signed body and signature, so the owner's app can check it on the phone.
    credential: dict | None = None
    signature_b64: str | None = None
    key_id: str | None = None


class PassportOut(BaseModel):
    confirmed_jobs: int
    on_time_pct: int | None
    level: LevelOut
    next_level: LevelOut | None
    jobs_to_next: int | None
    claims: list[ClaimOut]
    slug: str
    public_url: str


class NotificationOut(BaseModel):
    id: str
    type: str
    params: dict
    read: bool
    created_at: UtcDatetime


class AdminDecision(_In):
    decision: Literal["approve", "request_change", "reject"]
    reason: str = Field(min_length=3, max_length=500)

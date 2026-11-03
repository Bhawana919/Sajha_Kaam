"""SQLite tables (UUID keys, UTC times, money as integer minor units).

Identity lives only in users / worker_profiles. Everything a reviewer sees during
Fair Pick is built from applications.scrubbed_text, never from these tables.
"""

import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(default_factory=new_id, primary_key=True)
    role: str = Field(index=True)  # client | worker | admin
    email: str = Field(index=True, unique=True)  # login and notices only, never shown to the other party
    password_hash: str
    display_name: str
    locale: str = "ne"
    numerals_pref: str = "devanagari"  # devanagari | latin (Nepali locale only)
    consent_version: str | None = None
    age_attested_at: datetime | None = None
    is_sample_identity: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class WorkerProfile(SQLModel, table=True):
    __tablename__ = "worker_profiles"
    user_id: str = Field(foreign_key="users.id", primary_key=True)
    skills_json: str = "[]"
    # Name tokens (Latin + Devanagari) Leak Guard looks for in this worker's samples.
    name_tokens_json: str = "[]"
    # Private: never in any client-facing or blind response before the reveal.
    district: str | None = None
    khalti_payment_link: str | None = None


class ClientProfile(SQLModel, table=True):
    __tablename__ = "client_profiles"
    user_id: str = Field(foreign_key="users.id", primary_key=True)
    country: str
    org_label: str | None = None


class Card(SQLModel, table=True):
    __tablename__ = "cards"
    id: str = Field(default_factory=new_id, primary_key=True)
    client_id: str = Field(foreign_key="users.id", index=True)
    state: str = Field(default="draft", index=True)
    version: int = 1
    skill: str = "graphic_design"
    reference_language: str = "ne"
    title_ne: str = ""
    title_en: str = ""
    summary_ne: str = ""
    summary_en: str = ""
    price_minor: int = 0
    currency: str = "USD"
    deadline_days: int = 5
    revisions_included: int = 1
    pahilo_kaam: bool = False
    sample_brief_ne: str = ""
    sample_brief_en: str = ""
    questions_json: str = "[]"
    draft_source: str | None = None  # ai | template
    window_opens_at: datetime | None = None
    window_closes_at: datetime | None = None
    rules_result_json: str | None = None
    flagged: bool = False  # rule warnings or reports: goes to the admin queue
    reviewed_by_sajha: bool = False  # True only when rule checks ran
    admin_approved: bool = False
    extended_once: bool = False
    picked_application_id: str | None = None
    tie_note: str | None = None
    terms_snapshot_json: str | None = None
    locked_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)


class DeliverableRow(SQLModel, table=True):
    __tablename__ = "deliverables"
    pk: str = Field(default_factory=new_id, primary_key=True)
    card_id: str = Field(foreign_key="cards.id", index=True)
    id: str  # d1, d2... within the card
    position: int
    text_ne: str
    text_en: str


class ChecklistItemRow(SQLModel, table=True):
    __tablename__ = "checklist_items"
    pk: str = Field(default_factory=new_id, primary_key=True)
    card_id: str = Field(foreign_key="cards.id", index=True)
    id: str  # c1, c2... within the card
    deliverable_id: str
    position: int
    text_ne: str
    text_en: str
    testable: bool = True


class Application(SQLModel, table=True):
    __tablename__ = "applications"
    id: str = Field(default_factory=new_id, primary_key=True)
    card_id: str = Field(foreign_key="cards.id", index=True)
    worker_id: str = Field(foreign_key="users.id", index=True)
    state: str = "submitted"
    sample_text: str = ""
    sample_lang: str = "ne"
    scrubbed_text: str = ""  # after Leak Guard; the only text a reviewer or AI ever sees
    answers_json: str = "[]"  # [{"question_index":0,"text":"...","lang":"ne"}]
    consent_at: datetime | None = None
    feedback_json: str | None = None  # template note for unpicked applicants
    created_at: datetime = Field(default_factory=utcnow)


class Review(SQLModel, table=True):
    __tablename__ = "reviews"
    id: str = Field(default_factory=new_id, primary_key=True)
    card_id: str = Field(foreign_key="cards.id", index=True)
    reviewer_id: str = Field(foreign_key="users.id")
    application_id: str = Field(foreign_key="applications.id")
    letter: str  # server-side mapping only
    star_scores_json: str = "{}"
    total: int = 0


class AuditEvent(SQLModel, table=True):
    """Append-only, hash-chained: hash = SHA-256(prev_hash || canonical_json(event))."""

    __tablename__ = "audit_events"
    id: str = Field(default_factory=new_id, primary_key=True)
    card_id: str = Field(foreign_key="cards.id", index=True)
    seq: int
    actor_pseudonym: str
    action: str
    payload_json: str = "{}"
    created_at_utc: datetime = Field(default_factory=utcnow)
    prev_hash: str
    hash: str


class AcquaintanceAttestation(SQLModel, table=True):
    """The client ticked "I don't personally know any applicant" before picking."""

    __tablename__ = "acquaintance_attestations"
    id: str = Field(default_factory=new_id, primary_key=True)
    card_id: str = Field(foreign_key="cards.id", index=True)
    client_id: str = Field(foreign_key="users.id")
    attested_at: datetime = Field(default_factory=utcnow)


class Engagement(SQLModel, table=True):
    """One offer to one worker for one card. A declined offer stays as history."""

    __tablename__ = "engagements"
    id: str = Field(default_factory=new_id, primary_key=True)
    card_id: str = Field(foreign_key="cards.id", index=True)
    application_id: str = Field(foreign_key="applications.id")
    worker_id: str = Field(foreign_key="users.id", index=True)
    state: str = "offered"  # offered | accepted | declined
    version: int = 1
    khalti_payment_link: str | None = None
    revisions_used: int = 0
    due_at: datetime | None = None
    accepted_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Message(SQLModel, table=True):
    __tablename__ = "messages"
    id: str = Field(default_factory=new_id, primary_key=True)
    engagement_id: str = Field(foreign_key="engagements.id", index=True)
    sender_id: str = Field(foreign_key="users.id")
    text: str
    lang: str = "ne"
    warnings_json: str = "[]"
    created_at: datetime = Field(default_factory=utcnow)


class Delivery(SQLModel, table=True):
    __tablename__ = "deliveries"
    id: str = Field(default_factory=new_id, primary_key=True)
    engagement_id: str = Field(foreign_key="engagements.id", index=True)
    note: str = ""
    link: str | None = None
    checklist_result_json: str | None = None  # client's per-item result {c1: true, ...}
    revision_notes_json: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class PaymentConfirmation(SQLModel, table=True):
    __tablename__ = "payment_confirmations"
    engagement_id: str = Field(foreign_key="engagements.id", primary_key=True)
    client_marked_paid_at: datetime | None = None
    worker_confirmed_received_at: datetime | None = None
    simulated: bool = True


class PassportClaim(SQLModel, table=True):
    """A source-labelled record. One per (engagement, type): never duplicated."""

    __tablename__ = "passport_claims"
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    engagement_id: str = Field(foreign_key="engagements.id", index=True)
    type: str  # client_confirmed_delivery | both_confirmed_payment | practice_badge
    skill: str
    summary_en: str
    summary_ne: str
    client_note: str | None = None
    level_at_time: str
    source_label: str
    on_time: bool
    issued_at: datetime = Field(default_factory=utcnow)
    visibility: str = "private"  # private | public
    credential_json: str | None = None  # signed in P1
    signature_b64: str | None = None
    key_id: str | None = None


class Notification(SQLModel, table=True):
    """Stored as a type + params; the app renders the text from its locale files."""

    __tablename__ = "notifications"
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    type: str
    payload_json: str = "{}"
    read_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)


class IdempotencyRecord(SQLModel, table=True):
    __tablename__ = "idempotency_records"
    key: str = Field(primary_key=True)  # user_id|scope|client key
    response_json: str
    created_at: datetime = Field(default_factory=utcnow)


class Case(SQLModel, table=True):
    __tablename__ = "cases"
    id: str = Field(default_factory=new_id, primary_key=True)
    card_id: str = Field(foreign_key="cards.id", index=True)
    opened_by: str = Field(foreign_key="users.id")
    reason: str
    state_before: str
    status: str = "open"  # open | resolved
    created_at: datetime = Field(default_factory=utcnow)


class Passport(SQLModel, table=True):
    """The worker's public Passport address. Claims stay private until the worker makes them public."""

    __tablename__ = "passports"
    user_id: str = Field(foreign_key="users.id", primary_key=True)
    slug: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=utcnow)


class ShareLink(SQLModel, table=True):
    """A revocable, expiring link to a chosen subset of claims. Only the token's hash is stored."""

    __tablename__ = "share_links"
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(index=True, unique=True)
    claim_ids_json: str
    expires_at: datetime
    revoked_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)

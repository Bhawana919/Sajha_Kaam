"""What a client sees during Fair Pick blind review.

This model is deliberately separate from every other applicant/user model.
It must NEVER gain a field that can identify a person. tests/test_blindness.py
fails if a forbidden token appears in any field name.
"""

from pydantic import BaseModel, ConfigDict, Field

# Tokens matched against snake_case field-name parts (and a few whole substrings).
FORBIDDEN_IDENTITY_TOKENS = frozenset(
    {"name", "surname", "firstname", "lastname", "photo", "avatar", "picture", "gender", "sex", "age", "dob",
     "birth", "district", "province", "city", "address", "location", "phone", "mobile", "email", "khalti",
     "account", "user", "worker", "caste", "religion", "ethnicity", "citizenship"}
)
FORBIDDEN_SUBSTRINGS = ("surname", "khalti", "phone", "email", "gender", "district", "photo")


def identity_violations(keys: list[str]) -> list[str]:
    bad = []
    for key in keys:
        low = key.lower()
        parts = set(low.replace("-", "_").split("_"))
        if parts & FORBIDDEN_IDENTITY_TOKENS or any(s in low for s in FORBIDDEN_SUBSTRINGS):
            bad.append(key)
    return bad


class BlindAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_index: int
    text: str
    lang: str


class BlindApplicant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: str
    letter: str = Field(description="A, B, C... stable per reviewer")
    sample_text: str
    sample_lang: str
    sample_image_urls: list[str] = Field(default_factory=list, description="EXIF-stripped re-encodes")
    answers: list[BlindAnswer]
    confirmed_jobs: int = Field(description="context only, not scored")
    on_time_pct: int | None = Field(default=None, description="context only, not scored")


class BlindReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: str
    state: str
    applicant_count: int
    checklist_ids: list[str]
    applicants: list[BlindApplicant]
    scores: dict[str, dict[str, int]] = Field(default_factory=dict, description="application_id -> stars")
    attested_unacquainted: bool = False

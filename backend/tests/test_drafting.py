"""draft_card: template fallback always yields a valid card, offline and fast."""

import time

from app.schemas.kaam_card import KaamCardDraft
from app.services import llm
from app.services.i18n import detect_language, normalise_digits, to_devanagari_digits
from app.services.templates import draft_from_template


def test_seed_request_gives_the_demo_card():
    card = draft_from_template("५ वटा दसैं पोस्ट चाहियो")
    assert card.price.amount_minor == 4000 and card.price.currency == "USD" and card.price.is_suggestion
    assert card.deadline_days == 5
    assert card.revisions_included == 1
    assert len(card.checklist) == 4
    assert card.reference_language == "ne"
    assert "दसैं" in card.title_ne and "Dashain" in card.title_en
    assert all(c.testable for c in card.checklist)
    assert {c.deliverable_id for c in card.checklist} <= {d.id for d in card.deliverables}


def test_explicit_price_and_days_are_kept():
    card = draft_from_template("I need 3 reels for my momo truck, $75, 4 days")
    assert card.price.amount_minor == 7500 and not card.price.is_suggestion
    assert card.deadline_days == 4
    assert card.reference_language == "en"


def test_devanagari_numbers_are_understood():
    card = draft_from_template("१० वटा पोस्ट, ७ दिन")
    assert card.deadline_days == 7
    assert "१०" in card.title_ne and "10" in card.title_en


def test_blocked_work_returns_warning_and_no_deliverables():
    card = draft_from_template("write 20 fake reviews for my restaurant")
    assert card.deliverables == [] and "blocked_work" in card.warnings


def test_fallback_is_fast():
    start = time.perf_counter()
    draft_from_template("५ वटा दसैं पोस्ट चाहियो")
    assert time.perf_counter() - start < 1.0


class _Broken:
    def __init__(self, exc):
        self.exc = exc

    def draft_card(self, text):
        raise self.exc


class _Invalid:
    def draft_card(self, text):
        return KaamCardDraft.model_validate({"title_en": "missing everything"})


def test_llm_timeout_falls_back_to_template():
    out = llm.draft_card("५ वटा दसैं पोस्ट चाहियो", llm=_Broken(TimeoutError()))
    assert out.source == "template" and len(out.card.checklist) == 4


def test_llm_invalid_json_falls_back_to_template():
    out = llm.draft_card("५ वटा दसैं पोस्ट चाहियो", llm=_Invalid())
    assert out.source == "template"


def test_draft_endpoint_works_without_llm(client):
    r = client.post("/v1/cards/draft", json={"text": "५ वटा दसैं पोस्ट चाहियो"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "template"
    assert body["card"]["price"] == {"amount_minor": 4000, "currency": "USD", "is_suggestion": True}


def test_digit_helpers():
    assert normalise_digits("९८१२३४५६७८") == "9812345678"
    assert to_devanagari_digits("40") == "४०"
    assert detect_language("५ वटा दसैं पोस्ट चाहियो") == "ne"
    assert detect_language("need 5 posts") == "en"


def test_structured_schema_is_closed_and_inlined():
    schema = llm._structured_schema(KaamCardDraft)
    assert "$ref" not in str(schema) and schema["additionalProperties"] is False

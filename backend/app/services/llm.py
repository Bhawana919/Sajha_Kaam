"""One LLM interface for every AI feature, chosen by env vars.

AI only drafts, stress-tests, translates and writes practice briefs. It never ranks,
scores, rejects or selects people (docs/RULES.md, rule 3). Every output is JSON validated
against a schema; on any failure draft_card falls back to the offline template.

Data note: personal data is stripped before any call (Leak Guard runs first for applicant
text). Anthropic's commercial API terms say customer inputs/outputs are not used to train
models by default; confirm your account's retention settings before launch (see README).
"""

import json
import logging
from typing import Protocol

from pydantic import ValidationError

from app.config import settings
from app.schemas.kaam_card import DraftResponse, KaamCardDraft, TranslateResponse
from app.services.templates import draft_from_template, glossary

log = logging.getLogger("sajha.llm")
PROMPT_VERSION = "draft_card@1"

DRAFT_CARD_SYSTEM = """You draft Kaam Cards for Sajha Kaam, where young Nepali beginners win a fair first paid job. \
Convert the client's request (Nepali, English or mixed) into a Kaam Card. You only DRAFT; a human edits and approves. \
Output ONLY valid JSON matching the schema - no prose, no markdown. Write every text field in both natural, simple \
Nepali (Devanagari, not Hindi) and plain English; set reference_language to the language the client wrote in. \
Every deliverable needs at least one checklist item a stranger can verify yes/no (count, format, language, size, \
presence) - never subjective words like "good" or "professional". Use the client's price and deadline if given, \
otherwise suggest and set is_suggestion true. Price is in USD minor units (cents). If quantity, language, format or \
deadline is missing, add a plain question to needs_clarification instead of guessing. revisions_included is 1 unless \
stated. The application sample must be existing past work or a 10-minute-or-less micro-sample that is NOT the real \
deliverable. Give exactly 2 short application questions. Never request or mention photos, caste, ethnicity, religion, \
age, gender, citizenship/ID numbers or phone numbers. If the request involves fake reviews, exam cheating, adult \
content or scams, return empty deliverables and a warning."""


def _structured_schema(model: type) -> dict:
    """Pydantic JSON schema, inlined and stripped of keywords structured outputs may not accept."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(defs[node["$ref"].split("/")[-1]])
            out = {k: walk(v) for k, v in node.items()
                   if k not in {"title", "description", "minimum", "maximum", "minItems", "maxItems", "minLength", "maxLength", "default"}}
            if out.get("type") == "object":
                out["additionalProperties"] = False
                out["required"] = list(out.get("properties", {}).keys())
            return out
        if isinstance(node, list):
            return [walk(n) for n in node]
        return node

    return walk(schema)


TRANSLATE_SYSTEM = """Translate the user's text between Nepali and English. Keep every number, unit, size and format exactly. Keep checklist items observable (counts, sizes, formats). Write natural, simple Nepali in Devanagari, not Hindi, and plain English. Output ONLY JSON {"text": "..."}."""


class LLMClient(Protocol):
    def draft_card(self, text: str) -> KaamCardDraft: ...

    def translate(self, text: str, target: str) -> str: ...

    def stress_test(self, card: KaamCardDraft): ...


class AnthropicLLM:
    def __init__(self) -> None:
        import anthropic

        s = settings()
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=s.llm_api_key) if s.llm_api_key else anthropic.Anthropic()
        self._model = s.llm_model
        self._timeout = s.llm_timeout_s

    def _json_call(self, system: str, user: str, schema: dict) -> dict:
        response = self._client.with_options(timeout=self._timeout, max_retries=0).messages.create(
            model=self._model,
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
        )
        if response.stop_reason == "refusal":
            raise ValueError("model declined")
        text = next(b.text for b in response.content if b.type == "text")
        return json.loads(text)

    def draft_card(self, text: str) -> KaamCardDraft:
        data = self._json_call(DRAFT_CARD_SYSTEM, f"Client request:\n{text}", _structured_schema(KaamCardDraft))
        return KaamCardDraft.model_validate(data)


def get_llm() -> LLMClient | None:
    s = settings()
    if s.llm_provider == "anthropic":
        return AnthropicLLM()
    return None


def draft_card(text: str, llm: LLMClient | None = None) -> DraftResponse:
    """AI draft when configured; offline template on any error, timeout or invalid output."""
    llm = llm if llm is not None else get_llm()
    if llm is not None:
        try:
            return DraftResponse(source="ai", card=llm.draft_card(text))
        except (ValidationError, ValueError, KeyError, StopIteration) as e:
            log.warning("draft_card invalid output, using template: %s", type(e).__name__)
        except Exception as e:  # network, timeout, auth: the demo must never break
            log.warning("draft_card failed, using template: %s", type(e).__name__)
    return DraftResponse(source="template", card=draft_from_template(text))


def translate(text: str, target: str, llm: LLMClient | None = None) -> TranslateResponse:
    """AI translation, else an exact glossary hit, else the original text (labelled, never faked)."""
    llm = llm if llm is not None else get_llm()
    if llm is not None:
        try:
            return TranslateResponse(text=llm.translate(text, target), source="ai")
        except Exception as e:  # timeout, refusal, bad JSON: fall back offline
            log.warning("translate failed, using offline fallback: %s", type(e).__name__)
    hit = glossary(target).get(text.strip())
    if hit:
        return TranslateResponse(text=hit, source="glossary")
    return TranslateResponse(text=text, source="original")

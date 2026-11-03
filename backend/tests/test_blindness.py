"""Blindness is structural: the review API cannot return identity fields or values."""

import json
import re

from pydantic import create_model

from app.models import Application
from app.schemas.blind import BlindAnswer, BlindApplicant, BlindReview, identity_violations
from app.seed import _WORKERS, ANJALI_ID, LONDON_ID, RAMESH_ID
from app.services.fairpick import ordered_for_reviewer
from tests.conftest import ANJALI_APP, BIKASH_APP, DASHAIN, auth, review_to_pick


def _all_keys(node) -> list[str]:
    keys = []
    if isinstance(node, dict):
        for k, v in node.items():
            keys.append(k)
            keys.extend(_all_keys(v))
    elif isinstance(node, list):
        for v in node:
            keys.extend(_all_keys(v))
    return keys


def _assert_no_identity(body) -> None:
    assert identity_violations(_all_keys(body)) == []
    # Case-insensitive, whole words: an id like "app-anjali" leaks a name just as much as "Anjali"
    # does, but "asha" inside "Dashain" is not a leak.
    text = json.dumps(body, ensure_ascii=False).lower()

    def word(w: str) -> bool:
        return re.search(rf"(?<![a-zऀ-ॿ]){re.escape(w.lower())}(?![a-zऀ-ॿ])", text) is not None

    for uid, name, tokens, district, *_ in _WORKERS:
        assert uid.lower() not in text
        assert not word(name) and not word(district), name
        for token in tokens:
            assert not word(token), f"{token} leaked"


def test_blind_models_have_no_identity_fields():
    for model in (BlindApplicant, BlindAnswer, BlindReview):
        assert identity_violations(list(model.model_fields)) == [], model.__name__


def test_adding_an_identity_field_is_caught():
    for bad in ("display_name", "surname", "photo_url", "gender", "age", "district", "phone",
                "email", "khalti_link", "worker_id", "user_id"):
        leaky = create_model("Leaky", __base__=BlindApplicant, **{bad: (str, "")})
        assert identity_violations(list(leaky.model_fields)) == [bad], bad


def test_benign_fields_are_not_flagged():
    assert identity_violations(["sample_image_urls", "stage", "page", "message", "letter", "application_id"]) == []


def test_review_needs_the_cards_own_client(client):
    assert client.get(f"/v1/cards/{DASHAIN}/review").status_code == 401
    assert client.get(f"/v1/cards/{DASHAIN}/review", headers=auth(client, LONDON_ID)).status_code == 403
    assert client.get(f"/v1/cards/{DASHAIN}/review", headers=auth(client, ANJALI_ID)).status_code == 403
    # Still open: review has not started.
    assert client.get(f"/v1/cards/{DASHAIN}/review", headers=auth(client, RAMESH_ID)).status_code == 409


def test_review_and_owner_views_have_no_identity_before_reveal(client):
    ramesh = auth(client, RAMESH_ID)
    review = review_to_pick(client, ramesh)
    assert review["applicant_count"] == 12
    _assert_no_identity(review)
    _assert_no_identity(client.get(f"/v1/cards/{DASHAIN}/review", headers=ramesh).json())
    assert client.post(f"/v1/cards/{DASHAIN}/pick", json={}, headers=ramesh).status_code == 200
    owner = client.get(f"/v1/cards/{DASHAIN}/manage", headers=ramesh).json()
    _assert_no_identity(owner)  # picked, not revealed: still blind
    assert owner["picked_letter"] == "F"
    revealed = client.post(f"/v1/cards/{DASHAIN}/reveal", headers=ramesh).json()
    assert revealed["worker_display_name"] == "Anjali Thapa"


def test_demo_mode_pins_anjali_as_applicant_f(client):
    review = review_to_pick(client, auth(client, RAMESH_ID))
    letters = {a["letter"]: a["application_id"] for a in review["applicants"]}
    assert letters["F"] == ANJALI_APP


def _apps(n: int) -> list[Application]:
    return [Application(id=f"a{i}", card_id="c", worker_id=f"w{i}") for i in range(n)]


def test_order_is_stable_per_reviewer_and_differs_across_reviewers_and_jobs():
    apps = _apps(12)
    first = [a.id for _, a in ordered_for_reviewer(apps, "rev1", "card1")]
    again = [a.id for _, a in ordered_for_reviewer(list(reversed(apps)), "rev1", "card1")]
    other_reviewer = [a.id for _, a in ordered_for_reviewer(apps, "rev2", "card1")]
    other_job = [a.id for _, a in ordered_for_reviewer(apps, "rev1", "card2")]
    assert first == again
    assert first != other_reviewer
    assert first != other_job
    assert first != [a.id for a in apps]  # not submission order


def test_withdrawal_does_not_shift_other_letters(client):
    ramesh = auth(client, RAMESH_ID)
    from app.seed import BIKASH_ID

    bikash = auth(client, BIKASH_ID)
    assert client.delete(f"/v1/applications/{BIKASH_APP}", headers=bikash).status_code == 200
    review = review_to_pick(client, ramesh)
    letters = {a["letter"]: a["application_id"] for a in review["applicants"]}
    assert letters["F"] == ANJALI_APP and "K" not in letters and review["applicant_count"] == 11


def test_conftest_ids_match_the_seed():
    from app.seed import ANJALI_ID, BIKASH_ID, application_id_for
    from tests.conftest import ANJALI_APP, BIKASH_APP

    assert (application_id_for(ANJALI_ID), application_id_for(BIKASH_ID)) == (ANJALI_APP, BIKASH_APP)


def test_worker_sees_their_application_card(client):
    from app.seed import ANJALI_ID

    mine = client.get("/v1/me/applications", headers=auth(client, ANJALI_ID)).json()
    dashain = next(a for a in mine if a["card_id"] == DASHAIN)
    assert dashain["applicant_name"] == "Anjali Thapa" and dashain["role"] == "worker"
    assert dashain["application_ref"].startswith("SK-") and len(dashain["application_ref"]) == 9


def test_client_applicant_list_has_ids_and_roles_but_no_names(client):
    ramesh = auth(client, RAMESH_ID)
    open_view = client.get(f"/v1/cards/{DASHAIN}/manage", headers=ramesh).json()
    rows = open_view["applicants"]
    assert len(rows) == 12 and all(r["role"] == "worker" and r["application_ref"].startswith("SK-") for r in rows)
    assert all(r["letter"] is None for r in rows)  # letters only once the window has closed
    _assert_no_identity(open_view)
    review_to_pick(client, ramesh)
    closed = client.get(f"/v1/cards/{DASHAIN}/manage", headers=ramesh).json()
    assert sorted(r["letter"] for r in closed["applicants"]) == list("ABCDEFGHIJKL")
    _assert_no_identity(closed)

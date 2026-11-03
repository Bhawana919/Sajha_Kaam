"""The P0 loop through the API: post -> apply -> blind review -> pick -> reveal -> accept ->
deliver -> confirm -> payment handoff -> Passport. Plus ownership, invalid order and idempotency."""

from sqlmodel import Session, select

from app.db import engine
from app.models import Application, PassportClaim
from app.seed import ANJALI_ID, BIKASH_ID, LONDON_ID, RAMESH_ID
from app.services import audit
from tests.conftest import ANJALI_APP, DASHAIN, auth, register, review_to_pick

LINK = "https://pay.khalti.com/demo/anjali"


def _to_revealed(client, ramesh) -> str:
    review_to_pick(client, ramesh)
    assert client.post(f"/v1/cards/{DASHAIN}/pick", json={}, headers=ramesh).json()["letter"] == "F"
    return client.post(f"/v1/cards/{DASHAIN}/reveal", headers=ramesh).json()["engagement_id"]


def test_full_loop_issues_passport_and_feedback(client):
    ramesh, anjali, bikash = auth(client, RAMESH_ID), auth(client, ANJALI_ID), auth(client, BIKASH_ID)
    eng_id = _to_revealed(client, ramesh)

    offer = client.get(f"/v1/engagements/{eng_id}", headers=anjali).json()
    assert offer["state"] == "offered" and offer["card_state"] == "revealed"

    r = client.post(f"/v1/engagements/{eng_id}/accept", json={"khalti_payment_link": LINK}, headers=anjali)
    assert r.status_code == 200, r.text
    assert r.json()["card_state"] == "in_progress"
    # Client does not see the payment link until the work is confirmed.
    assert client.get(f"/v1/engagements/{eng_id}", headers=ramesh).json()["khalti_payment_link"] is None

    # Bikash got template feedback: his sample missed the Nepali-text item.
    bik_app = next(a for a in client.get("/v1/me/applications", headers=bikash).json() if a["card_id"] == DASHAIN)
    assert bik_app["state"] == "not_picked_feedback_sent"
    assert bik_app["feedback"]["met"] == 3 and bik_app["feedback"]["total"] == 4
    assert bik_app["feedback"]["missing"][0]["text_en"] == "Text is in both Nepali and English"

    assert client.post(f"/v1/engagements/{eng_id}/deliveries", json={"note": "5 PNGs attached", "link": "https://drive.example/x"},
                       headers=anjali).status_code == 200
    assert client.post(f"/v1/engagements/{eng_id}/confirm", json={"checklist": {"c1": True, "c2": True, "c3": True, "c4": True}},
                       headers=ramesh).status_code == 200
    seen = client.get(f"/v1/engagements/{eng_id}", headers=ramesh).json()
    assert seen["khalti_payment_link"] == LINK and seen["card_state"] == "client_confirmed"

    passport = client.get("/v1/me/passport", headers=anjali).json()
    assert [c["type"] for c in passport["claims"]] == ["client_confirmed_delivery"]  # not "paid" yet
    assert passport["level"]["id"] == "first_kaam"

    assert client.post(f"/v1/engagements/{eng_id}/payment/client-paid", headers=ramesh).status_code == 200
    done = client.post(f"/v1/engagements/{eng_id}/payment/worker-received", headers=anjali).json()
    assert done["card_state"] == "passport_issued"
    assert done["payment"]["client_marked_paid_at"] and done["payment"]["worker_confirmed_received_at"]

    types = sorted(c["type"] for c in client.get("/v1/me/passport", headers=anjali).json()["claims"])
    assert types == ["both_confirmed_payment", "client_confirmed_delivery"]
    inbox = [n["type"] for n in client.get("/v1/notifications", headers=anjali).json()]
    assert {"offer", "confirmed", "payment_marked", "passport_issued"} <= set(inbox)

    with Session(engine) as s:
        chain = audit.events(s, DASHAIN)
        assert audit.verify(chain) is None
        actors = {e.actor_pseudonym for e in chain}
        assert "Anjali Thapa" not in actors and "Applicant F" in actors


def test_ownership_is_enforced(client):
    ramesh, london, anjali, bikash = (auth(client, u) for u in (RAMESH_ID, LONDON_ID, ANJALI_ID, BIKASH_ID))
    stars = {"c1": 3, "c2": 3, "c3": 3, "c4": 3}
    assert client.put(f"/v1/reviews/{ANJALI_APP}", json={"stars": stars}, headers=london).status_code == 403
    assert client.put(f"/v1/reviews/{ANJALI_APP}", json={"stars": stars}, headers=anjali).status_code == 403
    assert client.post(f"/v1/cards/{DASHAIN}/pick", json={}, headers=anjali).status_code == 403
    eng_id = _to_revealed(client, ramesh)
    assert client.get(f"/v1/engagements/{eng_id}", headers=bikash).status_code == 404
    assert client.post(f"/v1/engagements/{eng_id}/accept", json={"khalti_payment_link": LINK}, headers=bikash).status_code == 404
    assert client.post(f"/v1/engagements/{eng_id}/accept", json={"khalti_payment_link": LINK}, headers=ramesh).status_code == 403
    assert client.get("/v1/me/passport", headers=ramesh).status_code == 403


def test_steps_cannot_be_skipped(client):
    ramesh, anjali = auth(client, RAMESH_ID), auth(client, ANJALI_ID)
    assert client.post(f"/demo/cards/{DASHAIN}/fast-forward").status_code == 200
    assert client.post(f"/v1/cards/{DASHAIN}/pick", json={}, headers=ramesh).status_code == 409  # not scored
    client.put(f"/v1/reviews/{ANJALI_APP}", json={"stars": {"c1": 3, "c2": 3, "c3": 3, "c4": 3}}, headers=ramesh)
    assert client.post(f"/v1/cards/{DASHAIN}/pick", json={}, headers=ramesh).status_code == 409  # no attestation
    client.post(f"/v1/cards/{DASHAIN}/attest-unacquainted", headers=ramesh)
    assert client.post(f"/v1/cards/{DASHAIN}/pick", json={}, headers=ramesh).status_code == 409  # others unscored

    eng_id = _to_revealed(client, ramesh)
    assert client.post(f"/v1/engagements/{eng_id}/deliveries", json={"note": "x"}, headers=anjali).status_code == 409
    client.post(f"/v1/engagements/{eng_id}/accept", json={"khalti_payment_link": LINK}, headers=anjali)
    all_met = {"checklist": {"c1": True, "c2": True, "c3": True, "c4": True}}
    assert client.post(f"/v1/engagements/{eng_id}/confirm", json=all_met, headers=ramesh).status_code == 409
    assert client.post(f"/v1/engagements/{eng_id}/payment/worker-received", headers=anjali).status_code == 409
    client.post(f"/v1/engagements/{eng_id}/deliveries", json={"note": "done"}, headers=anjali)
    partly = {"checklist": {"c1": True, "c2": True, "c3": False, "c4": True}}
    assert client.post(f"/v1/engagements/{eng_id}/confirm", json=partly, headers=ramesh).status_code == 422
    assert client.post(f"/v1/engagements/{eng_id}/payment/client-paid", headers=ramesh).status_code == 409
    with Session(engine) as s:  # no claim before the client confirms
        assert s.exec(select(PassportClaim).where(PassportClaim.user_id == ANJALI_ID)).all() == []


def test_revision_limit(client):
    ramesh, anjali = auth(client, RAMESH_ID), auth(client, ANJALI_ID)
    eng_id = _to_revealed(client, ramesh)
    client.post(f"/v1/engagements/{eng_id}/accept", json={"khalti_payment_link": LINK}, headers=anjali)
    client.post(f"/v1/engagements/{eng_id}/deliveries", json={"note": "v1"}, headers=anjali)
    r = client.post(f"/v1/engagements/{eng_id}/request-revision", json={"notes": {"c2": "logo missing on post 3"}}, headers=ramesh)
    assert r.status_code == 200 and r.json()["revisions_used"] == 1
    assert client.post(f"/v1/engagements/{eng_id}/deliveries", json={"note": "v2"}, headers=anjali).status_code == 200
    r = client.post(f"/v1/engagements/{eng_id}/request-revision", json={"notes": {"c2": "again"}}, headers=ramesh)
    assert r.status_code == 409  # only 1 revision was agreed


def test_decline_offers_next_highest(client):
    ramesh, anjali = auth(client, RAMESH_ID), auth(client, ANJALI_ID)
    eng_id = _to_revealed(client, ramesh)
    assert client.post(f"/v1/engagements/{eng_id}/decline", headers=anjali).status_code == 200
    owner = client.get(f"/v1/cards/{DASHAIN}/manage", headers=ramesh).json()
    assert owner["state"] == "picked" and owner["picked_letter"] == "K"  # Bikash: next-highest total (10)
    nxt = client.post(f"/v1/cards/{DASHAIN}/reveal", headers=ramesh).json()
    assert nxt["worker_display_name"] == "Bikash"


def test_tie_needs_a_choice_and_reason(client):
    ramesh = auth(client, RAMESH_ID)
    review = review_to_pick(client, ramesh)
    a_id = next(a["application_id"] for a in review["applicants"] if a["letter"] == "A")
    client.put(f"/v1/reviews/{a_id}", json={"stars": {"c1": 3, "c2": 3, "c3": 3, "c4": 3}}, headers=ramesh)
    assert client.post(f"/v1/cards/{DASHAIN}/pick", json={}, headers=ramesh).status_code == 409
    r = client.post(f"/v1/cards/{DASHAIN}/pick", json={"application_id": a_id, "tie_note": "Closer to our brand colours"},
                    headers=ramesh)
    assert r.status_code == 200 and r.json()["letter"] == "A"


def test_idempotent_apply_and_confirm(client):
    worker = register(client, "worker", "new.worker@example.org", name="Sita K", skills=["social_media_posts"])
    body = {"sample_text": "A square festival post with Nepali and English text and a shop logo.",
            "sample_lang": "en", "answers": ["Canva", "Two lines, one per language."],
            "consent": True, "no_identifying_details": True}
    key = {"Idempotency-Key": "apply-1", **worker}
    first = client.post(f"/v1/cards/{DASHAIN}/applications", json=body, headers=key).json()
    again = client.post(f"/v1/cards/{DASHAIN}/applications", json=body, headers=key).json()
    assert first == again
    with Session(engine) as s:
        assert len(s.exec(select(Application).where(Application.id == first["id"])).all()) == 1
    # A second application without the key is a real duplicate and is refused.
    assert client.post(f"/v1/cards/{DASHAIN}/applications", json=body, headers=worker).status_code == 409


def test_confirm_twice_gives_one_claim(client):
    ramesh, anjali = auth(client, RAMESH_ID), auth(client, ANJALI_ID)
    eng_id = _to_revealed(client, ramesh)
    client.post(f"/v1/engagements/{eng_id}/accept", json={"khalti_payment_link": LINK}, headers=anjali)
    client.post(f"/v1/engagements/{eng_id}/deliveries", json={"note": "done"}, headers=anjali)
    all_met = {"checklist": {"c1": True, "c2": True, "c3": True, "c4": True}}
    h = {"Idempotency-Key": "confirm-1", **ramesh}
    assert client.post(f"/v1/engagements/{eng_id}/confirm", json=all_met, headers=h).status_code == 200
    assert client.post(f"/v1/engagements/{eng_id}/confirm", json=all_met, headers=h).status_code == 200
    assert client.post(f"/v1/engagements/{eng_id}/confirm", json=all_met, headers=ramesh).status_code == 409
    with Session(engine) as s:
        assert len(s.exec(select(PassportClaim).where(PassportClaim.user_id == ANJALI_ID)).all()) == 1


def test_window_closes_early_at_15_applicants(client):
    body = {"sample_text": "Past work: a 1080x1080 greeting post with Nepali text.", "sample_lang": "en",
            "answers": ["Figma", "Nepali on top."], "consent": True, "no_identifying_details": True}
    for i in range(3):
        w = register(client, "worker", f"extra{i}@example.org", name=f"Extra Worker{i}")
        assert client.post(f"/v1/cards/{DASHAIN}/applications", json=body, headers=w).status_code == 200
    ramesh = auth(client, RAMESH_ID)
    assert client.get(f"/v1/cards/{DASHAIN}/manage", headers=ramesh).json()["state"] == "closed_for_applications"
    late = register(client, "worker", "late@example.org", name="Late Comer")
    assert client.post(f"/v1/cards/{DASHAIN}/applications", json=body, headers=late).status_code == 409

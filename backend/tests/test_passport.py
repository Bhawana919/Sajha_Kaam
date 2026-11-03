"""Work Passport: private by default, public page, share links (expiry, revoke), export, delete."""

from datetime import timedelta

from sqlmodel import Session

from app.db import engine
from app.models import ShareLink
from app.seed import ANJALI_ID, BIKASH_ID, RAMESH_ID
from tests.conftest import DASHAIN, auth, review_to_pick

LINK = "https://pay.khalti.com/demo/anjali"


def _complete_job(client) -> dict:
    ramesh, anjali = auth(client, RAMESH_ID), auth(client, ANJALI_ID)
    review_to_pick(client, ramesh)
    client.post(f"/v1/cards/{DASHAIN}/pick", json={}, headers=ramesh)
    eng = client.post(f"/v1/cards/{DASHAIN}/reveal", headers=ramesh).json()["engagement_id"]
    client.post(f"/v1/engagements/{eng}/accept", json={"khalti_payment_link": LINK}, headers=anjali)
    client.post(f"/v1/engagements/{eng}/deliveries", json={"note": "done"}, headers=anjali)
    client.post(f"/v1/engagements/{eng}/confirm", json={"checklist": {f"c{i}": True for i in range(1, 5)}}, headers=ramesh)
    client.post(f"/v1/engagements/{eng}/payment/client-paid", headers=ramesh)
    client.post(f"/v1/engagements/{eng}/payment/worker-received", headers=anjali)
    return anjali


def _path(url: str) -> str:
    """'http://host:8000/p/abc' -> '/p/abc' (the test client talks to the app directly)."""
    return "/" + url.split("://", 1)[1].split("/", 1)[1]


def test_public_page_is_private_until_the_worker_chooses(client):
    anjali = _complete_job(client)
    passport = client.get("/v1/me/passport", headers=anjali).json()
    assert len(passport["claims"]) == 2 and all(c["visibility"] == "private" for c in passport["claims"])
    page = client.get(_path(passport["public_url"]))
    assert page.status_code == 200 and "Anjali Thapa" in page.text
    assert "Dashain" not in page.text and "Not a government ID" in page.text and "सरकारी परिचयपत्र" in page.text

    paid = next(c for c in passport["claims"] if c["type"] == "both_confirmed_payment")
    assert client.patch(f"/v1/passport/claims/{paid['id']}", json={"visibility": "public"}, headers=anjali).status_code == 200
    page = client.get(_path(passport["public_url"])).text
    assert "Payment confirmed by both" in page and "Client confirmed delivery" not in page
    assert "Surkhet" not in page and "khalti" not in page.lower()


def test_others_cannot_change_or_share_my_claims(client):
    anjali = _complete_job(client)
    claim = client.get("/v1/me/passport", headers=anjali).json()["claims"][0]
    bikash = auth(client, BIKASH_ID)
    assert client.patch(f"/v1/passport/claims/{claim['id']}", json={"visibility": "public"}, headers=bikash).status_code == 404
    assert client.post("/v1/passport/shares", json={"claim_ids": [claim["id"]]}, headers=bikash).status_code == 404


def test_share_links_show_only_chosen_claims_and_can_be_revoked(client):
    anjali = _complete_job(client)
    claims = client.get("/v1/me/passport", headers=anjali).json()["claims"]
    delivery = next(c for c in claims if c["type"] == "client_confirmed_delivery")
    share = client.post("/v1/passport/shares", json={"claim_ids": [delivery["id"]], "days": 7}, headers=anjali).json()
    page = client.get(_path(share["url"])).text
    assert "Client confirmed delivery" in page and "Payment confirmed by both" not in page
    assert client.get("/v1/passport/shares", headers=anjali).json()[0]["url"] is None  # token shown once only
    client.delete(f"/v1/passport/shares/{share['id']}", headers=anjali)
    assert client.get(_path(share["url"])).status_code == 404


def test_share_links_expire(client):
    anjali = _complete_job(client)
    claim = client.get("/v1/me/passport", headers=anjali).json()["claims"][0]
    share = client.post("/v1/passport/shares", json={"claim_ids": [claim["id"]], "days": 1}, headers=anjali).json()
    with Session(engine) as s:
        link = s.get(ShareLink, share["id"])
        link.expires_at = link.expires_at - timedelta(days=2)
        s.add(link)
        s.commit()
    assert client.get(_path(share["url"])).status_code == 404


def test_export_and_delete_everything(client):
    anjali = _complete_job(client)
    exported = client.get("/v1/passport/export", headers=anjali).json()
    assert len(exported["claims"]) == 2 and "legal identity" in exported["note_en"]
    url = client.get("/v1/me/passport", headers=anjali).json()["public_url"]
    assert client.delete("/v1/me/data", headers=anjali).json() == {"deleted": True}
    assert client.get(_path(url)).status_code == 404
    assert client.post("/v1/auth/login", json={"email": "anjali@sample.sajhakaam.test", "password": "sajha-demo"}).status_code == 401
    # The client's record of the job still holds (pseudonymous audit, card state).
    assert client.get(f"/v1/cards/{DASHAIN}/manage", headers=auth(client, RAMESH_ID)).json()["state"] == "passport_issued"


def test_unknown_public_links_are_404_in_both_languages(client):
    page = client.get("/p/nope")
    assert page.status_code == 404 and "भेटिएन" in page.text and "Not found" in page.text

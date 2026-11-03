"""Signed Passport claims, the Verify page and the Fair Pick Receipt."""

import copy
import hashlib
import json

from app.seed import _WORKERS
from app.services import signing
from app.services.audit import GENESIS, canonical
from tests.conftest import DASHAIN
from tests.test_passport import _complete_job


def _claims(client, headers):
    return client.get("/v1/me/passport", headers=headers).json()["claims"]


def test_claims_are_signed_and_any_change_breaks_the_signature(client):
    anjali = _complete_job(client)
    claims = _claims(client, anjali)
    assert claims and all(c["signed"] for c in claims)
    claim = claims[0]
    client.patch(f"/v1/passport/claims/{claim['id']}", json={"visibility": "public"}, headers=anjali)
    proof = client.get(f"/v1/public/claims/{claim['id']}").json()
    cred, sig = proof["credential"], proof["signature_b64"]
    key = client.get("/.well-known/sajha-kaam-keys.json").json()["keys"][0]
    assert key["key_id"] == proof["key_id"] and key["alg"] == "Ed25519"
    assert signing.verify(cred, sig, key["public_key_b64"])
    assert cred["@context"] == ["https://www.w3.org/ns/credentials/v2"]
    assert cred["credentialSubject"]["displayName"] == "Anjali Thapa"
    for path in (("credentialSubject", "onTime"), ("credentialSubject", "skill"), ("validFrom",)):
        bad = copy.deepcopy(cred)
        target = bad
        for k in path[:-1]:
            target = target[k]
        target[path[-1]] = "changed" if not isinstance(target[path[-1]], bool) else not target[path[-1]]
        assert not signing.verify(bad, sig, key["public_key_b64"]), path


def test_credential_holds_no_private_details(client):
    anjali = _complete_job(client)
    claim = _claims(client, anjali)[0]
    client.patch(f"/v1/passport/claims/{claim['id']}", json={"visibility": "public"}, headers=anjali)
    text = json.dumps(client.get(f"/v1/public/claims/{claim['id']}").json(), ensure_ascii=False).lower()
    for secret in ("surkhet", "khalti", "@sample", "ramesh", "himalayan"):
        assert secret not in text, secret


def test_private_claims_need_public_or_a_share_link(client):
    anjali = _complete_job(client)
    claim = _claims(client, anjali)[0]
    assert client.get(f"/v1/public/claims/{claim['id']}").status_code == 404
    assert client.get(f"/verify/{claim['id']}").status_code == 404
    share = client.post("/v1/passport/shares", json={"claim_ids": [claim["id"]]}, headers=anjali).json()
    token = share["url"].rsplit("/", 1)[1]
    assert client.get(f"/v1/public/claims/{claim['id']}", params={"s": token}).status_code == 200
    page = client.get(f"/verify/{claim['id']}", params={"s": token})
    assert page.status_code == 200 and "nacl-fast.min.js" in page.text and "सरकारी परिचयपत्र" in page.text
    assert client.get(f"/v1/public/claims/{claim['id']}", params={"s": "not-a-token"}).status_code == 404


def test_static_verifier_is_served(client):
    assert "SajhaVerify" in client.get("/static/verify.js").text
    assert client.get("/static/vendor/nacl-fast.min.js").status_code == 200


def test_receipt_only_after_the_pick(client):
    assert client.get(f"/receipt/{DASHAIN}").status_code == 404
    assert client.get(f"/v1/public/receipts/{DASHAIN}").status_code == 404


def test_receipt_shows_letters_scores_and_a_chain_anyone_can_recompute(client):
    _complete_job(client)
    data = client.get(f"/v1/public/receipts/{DASHAIN}").json()
    assert data["applicant_count"] == 12 and data["picked"] == "F"
    assert [r["id"] for r in data["rubric"]] == ["c1", "c2", "c3", "c4"]
    assert {s["applicant"] for s in data["scores"]} == set("ABCDEFGHIJKL")
    assert data["attested_unacquainted_at"] and data["revealed_at"]
    prev = GENESIS  # recompute exactly as the browser does, from the published JSON only
    for e in data["events"]:
        assert e["prev_hash"] == prev
        assert hashlib.sha256((prev + canonical(e["body"])).encode()).hexdigest() == e["hash"]
        prev = e["hash"]
    assert data["final_hash"] == prev

    page = client.get(f"/receipt/{DASHAIN}").text
    for uid, name, tokens, district, *_ in _WORKERS:
        assert name not in page and district not in page and uid not in page
        assert not any(token in page for token in tokens), name
    assert "Ramesh" not in page and "verify.js" in page


def test_receipt_json_never_has_identity_fields(client):
    from app.schemas.blind import identity_violations

    _complete_job(client)
    data = client.get(f"/v1/public/receipts/{DASHAIN}").json()

    def keys(node):
        if isinstance(node, dict):
            for k, v in node.items():
                yield k
                yield from keys(v)
        elif isinstance(node, list):
            for v in node:
                yield from keys(v)

    assert identity_violations(list(keys(data))) == []

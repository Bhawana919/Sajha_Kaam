import os
import tempfile

# Settings are read at import time, so point at a throwaway DB before importing the app.
_tmp = tempfile.mkdtemp(prefix="sajha-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp, 'test.db')}"
os.environ["DEMO_MODE"] = "1"
os.environ["LLM_PROVIDER"] = "none"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

DASHAIN = "card-dashain-posts"
ANJALI_APP = "app-" + __import__("hashlib").sha256(b"sajha-demo|u-worker-anjali").hexdigest()[:12]
BIKASH_APP = "app-" + __import__("hashlib").sha256(b"sajha-demo|u-worker-bikash").hexdigest()[:12]


@pytest.fixture(scope="session")
def _app_client():
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(_app_client):
    """A freshly reseeded demo world for every test."""
    assert _app_client.post("/demo/reset").status_code == 200
    return _app_client


def auth(client, user_id: str) -> dict:
    r = client.post("/v1/auth/sample-login", json={"user_id": user_id})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def register(client, role: str, email: str, **extra) -> dict:
    body = {"role": role, "email": email, "password": "long-enough-pw", "display_name": extra.pop("name", "Test User"),
            "consent": True, "locale": "en", **extra}
    if role == "worker":
        body.setdefault("skills", ["graphic_design"])
        body.setdefault("age_attested", True)
    else:
        body.setdefault("country", "Japan")
    r = client.post("/v1/auth/register", json=body)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# Ramesh's stars for the Dashain card (c1..c4): F (Anjali) meets all four; Bikash misses Nepali text (c3).
def stars_for(letter: str) -> dict:
    if letter == "F":
        return {"c1": 3, "c2": 3, "c3": 3, "c4": 3}
    if letter == "K":  # Bikash in Demo order
        return {"c1": 3, "c2": 3, "c3": 1, "c4": 3}
    return {"c1": 2, "c2": 2, "c3": 2, "c4": 1}


def review_to_pick(client, ramesh: dict) -> dict:
    """Fast-forward the Dashain card, score everyone, attest. Returns the review body."""
    assert client.post(f"/demo/cards/{DASHAIN}/fast-forward").status_code in (200, 409)  # 409: already closed
    review = client.get(f"/v1/cards/{DASHAIN}/review", headers=ramesh).json()
    for a in review["applicants"]:
        r = client.put(f"/v1/reviews/{a['application_id']}", json={"stars": stars_for(a["letter"])}, headers=ramesh)
        assert r.status_code == 200, r.text
    assert client.post(f"/v1/cards/{DASHAIN}/attest-unacquainted", headers=ramesh).status_code == 200
    return review

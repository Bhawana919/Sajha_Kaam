"""Rule checks, posting (first card -> admin queue), level cap and Pahilo Kaam eligibility."""

from sqlmodel import Session

from app.db import engine
from app.models import Engagement, PassportClaim
from app.seed import ADMIN_ID, ANJALI_ID, RAMESH_ID
from app.services.rules import check_card, find_terms
from app.services.templates import draft_from_template
from tests.conftest import ANJALI_APP, DASHAIN, auth, register


def _codes(card, skill="social_media_posts"):
    return {i.code for i in check_card(card, skill) if i.severity == "error"}


def _seed_card():
    return draft_from_template("५ वटा दसैं पोस्ट चाहियो")


def test_template_card_passes():
    assert _codes(_seed_card()) == set()


def test_price_below_floor():
    card = _seed_card()
    card.price.amount_minor = 1000  # $10 for 5 posts
    assert "price_below_floor" in _codes(card)


def test_untestable_item_in_either_language():
    card = _seed_card()
    card.checklist[1].text_en = "Posts look professional"
    assert "untestable_item" in _codes(card)
    card = _seed_card()
    card.checklist[1].text_ne = "पोस्ट राम्रो देखिन्छ"
    assert "untestable_item" in _codes(card)


def test_forbidden_asks_whole_words_only():
    card = _seed_card()
    card.questions[0].en = "Please send a photo of yourself and your age"
    assert "forbidden_ask" in _codes(card)
    card = _seed_card()
    card.questions[0].ne = "तपाईंको जात के हो?"
    assert "forbidden_ask" in _codes(card)
    # 'page', 'image', 'Photoshop' and 'पत्थर' are fine.
    assert find_terms("Deliver 2 pages as image files made in Photoshop", ["age", "photo"], []) == []
    assert find_terms("पत्थरको चित्र", [], ["थर"]) == []


def test_free_labour_sample_is_refused():
    card = _seed_card()
    card.sample_brief_en = "Design 2 of the 5 posts as your sample (about 45 minutes)."
    card.sample_brief_ne = "नमुनाका लागि ५ मध्ये २ पोस्ट बनाउनुहोस् (करिब ४५ मिनेट)।"
    assert "free_labour" in _codes(card)


def test_deliverable_without_checklist_item():
    card = _seed_card()
    card.checklist = [c.model_copy(update={"deliverable_id": "d9"}) for c in card.checklist]
    assert "deliverable_without_check" in _codes(card)


def test_blocked_work():
    assert "blocked_work" in _codes(draft_from_template("write 20 fake reviews for my restaurant"))


def _write(card, skill="social_media_posts", source="template"):
    return {"card": card.model_dump(), "skill": skill, "pahilo_kaam": True, "source": source}


def test_first_card_goes_to_admin_queue_then_opens(client):
    new_client = register(client, "client", "first.client@example.org", name="Mina S")
    created = client.post("/v1/cards", json=_write(_seed_card()), headers=new_client).json()
    assert created["state"] == "ai_drafted" and created["draft_source"] == "template"
    posted = client.post(f"/v1/cards/{created['id']}/post", headers=new_client).json()
    assert posted["posted"] and posted["state"] == "pending_review"

    admin = auth(client, ADMIN_ID)
    assert any(q["card_id"] == created["id"] for q in client.get("/v1/admin/queue", headers=admin).json())
    assert client.get("/v1/admin/queue", headers=new_client).status_code == 403
    r = client.post(f"/v1/admin/cards/{created['id']}/decision", json={"decision": "approve", "reason": "Clear card"},
                    headers=admin)
    assert r.json()["state"] == "open"
    assert created["id"] in {c["id"] for c in client.get("/v1/board").json()["items"]}


def test_returning_client_posts_straight_to_board(client):
    ramesh = auth(client, RAMESH_ID)
    created = client.post("/v1/cards", json=_write(_seed_card()), headers=ramesh).json()
    assert client.post(f"/v1/cards/{created['id']}/post", headers=ramesh).json()["state"] == "open"


def test_failed_rules_must_be_edited_before_posting(client):
    ramesh = auth(client, RAMESH_ID)
    bad = _seed_card()
    bad.checklist[0].text_en = "Looks good"
    created = client.post("/v1/cards", json=_write(bad, source="manual"), headers=ramesh).json()
    result = client.post(f"/v1/cards/{created['id']}/post", headers=ramesh).json()
    assert not result["posted"] and result["state"] == "rules_failed"
    issue = next(i for i in result["rules"] if i["code"] == "untestable_item")
    assert issue["item_id"] == "c1" and issue["message_ne"]
    assert client.post(f"/v1/cards/{created['id']}/post", headers=ramesh).status_code == 409
    fixed = client.patch(f"/v1/cards/{created['id']}", json=_write(_seed_card()), headers=ramesh).json()
    assert fixed["state"] == "client_edited" and fixed["version"] == 2
    assert client.post(f"/v1/cards/{created['id']}/post", headers=ramesh).json()["state"] == "open"


def test_workers_cannot_post_and_clients_cannot_apply(client):
    anjali, ramesh = auth(client, ANJALI_ID), auth(client, RAMESH_ID)
    assert client.post("/v1/cards", json=_write(_seed_card()), headers=anjali).status_code == 403
    body = {"sample_text": "A past greeting post in Nepali.", "sample_lang": "en", "answers": ["a", "b"],
            "consent": True, "no_identifying_details": True}
    assert client.post(f"/v1/cards/{DASHAIN}/applications", json=body, headers=ramesh).status_code == 403


def _give_confirmed_jobs(user_id: str, n: int) -> None:
    with Session(engine) as s:
        for i in range(n):
            eng = Engagement(card_id=DASHAIN, application_id=ANJALI_APP, worker_id=user_id, state="accepted")
            s.add(eng)
            s.flush()
            s.add(PassportClaim(user_id=user_id, engagement_id=eng.id, type="client_confirmed_delivery",
                                skill="graphic_design", summary_en=f"Job {i}", summary_ne=f"काम {i}",
                                level_at_time="learner", source_label="test", on_time=True))
        s.commit()


APPLY = {"sample_text": "Past work: a 1080x1080 greeting post with Nepali and English text.", "sample_lang": "en",
         "answers": ["Canva", "Nepali on top, English below."], "consent": True, "no_identifying_details": True}


def test_pahilo_kaam_is_for_beginners_only(client):
    worker = register(client, "worker", "experienced@example.org", name="Experienced Worker")
    me = client.get("/v1/me", headers=worker).json()
    _give_confirmed_jobs(me["id"], 3)
    r = client.post(f"/v1/cards/{DASHAIN}/applications", json=APPLY, headers=worker)
    assert r.status_code == 403 and r.json()["detail"] == "pahilo_kaam_only_beginners"


def test_level_cap_blocks_bigger_jobs(client):
    ramesh = auth(client, RAMESH_ID)
    big = _seed_card()
    big.price.amount_minor = 40000  # $400 > Learner cap $50
    big.price.is_suggestion = False
    created = client.post("/v1/cards", json=_write(big), headers=ramesh).json()
    assert client.post(f"/v1/cards/{created['id']}/post", headers=ramesh).json()["state"] == "open"
    worker = register(client, "worker", "learner@example.org", name="New Learner")
    r = client.post(f"/v1/cards/{created['id']}/applications", json=APPLY, headers=worker)
    assert r.status_code == 403 and r.json()["detail"] == "above_level_cap"


def test_registration_rules(client):
    base = {"email": "x@example.org", "password": "long-enough-pw", "display_name": "X", "consent": True}
    assert client.post("/v1/auth/register", json={**base, "role": "worker", "skills": ["graphic_design"]}).status_code == 422
    assert client.post("/v1/auth/register", json={**base, "role": "worker", "age_attested": True}).status_code == 422
    assert client.post("/v1/auth/register", json={**base, "role": "client", "consent": False, "country": "UK"}).status_code == 422
    ok = client.post("/v1/auth/register", json={**base, "role": "client", "country": "UK"})
    assert ok.status_code == 200
    assert client.post("/v1/auth/login", json={"email": "x@example.org", "password": "wrong-pw"}).status_code == 401
    tokens = client.post("/v1/auth/login", json={"email": "X@example.org", "password": "long-enough-pw"}).json()
    refreshed = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert client.post("/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}).status_code == 401


def test_stress_test_rules_fallback_finds_vague_items_and_never_touches_terms(client):
    from app.services.stress import rule_based

    card = _seed_card()
    assert rule_based(card).issues == [] and rule_based(card).testable_before == 4
    card.checklist[1].text_en, card.checklist[1].text_ne = "Posts look professional", "पोस्ट व्यावसायिक देखिन्छ"
    card.checklist[2].text_en, card.checklist[2].text_ne = "Text is correct", "लेख सही छ"
    result = rule_based(card)
    by_id = {i.item_id: i for i in result.issues}
    assert by_id["c2"].severity == "high" and "logo" in by_id["c2"].suggested_rewrite_en
    assert by_id["c3"].severity == "medium" and by_id["c3"].suggested_rewrite_en == ""  # no guessed fix offline
    assert (result.testable_before, result.testable_after_if_all_applied, result.total_items) == (2, 3, 4)
    assert result.source == "rules"

    ramesh = auth(client, RAMESH_ID)
    r = client.post("/v1/cards/stress-test", json={"card": card.model_dump()}, headers=ramesh)
    assert r.status_code == 200 and r.json()["testable_before"] == 2
    assert client.post("/v1/cards/stress-test", json={"card": card.model_dump()},
                       headers=auth(client, ANJALI_ID)).status_code == 403


def test_stress_test_uses_ai_when_available_and_drops_unknown_items():
    from app.services.stress import StressBody, StressIssue, stress_test

    class FakeLLM:
        def stress_test(self, card):
            issue = dict(problem_en="p", problem_ne="प", why_dispute_risk_en="w", why_dispute_risk_ne="व",
                         suggested_rewrite_en="r", suggested_rewrite_ne="र", severity="low")
            return StressBody(issues=[StressIssue(item_id="c1", **issue), StressIssue(item_id="zzz", **issue)],
                              testable_before=9, testable_after_if_all_applied=9)

    out = stress_test(_seed_card(), llm=FakeLLM())
    assert out.source == "ai" and [i.item_id for i in out.issues] == ["c1"] and out.testable_before == 4

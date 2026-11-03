from app.seed import DASHAIN_CARD_ID


def test_board_lists_open_cards(client):
    items = client.get("/v1/board").json()["items"]
    assert {c["id"] for c in items} >= {DASHAIN_CARD_ID, "card-london-menu", "card-toronto-reels"}
    dashain = next(c for c in items if c["id"] == DASHAIN_CARD_ID)
    assert dashain["applicant_count"] == 12 and dashain["max_applicants"] == 15
    assert dashain["client_country"] == "Australia"
    assert dashain["window_closes_at"].endswith(("Z", "+00:00"))  # UTC on the wire


def test_pahilo_filter(client):
    items = client.get("/v1/board", params={"pahilo": True}).json()["items"]
    assert items and all(c["pahilo_kaam"] for c in items)
    assert "card-toronto-reels" not in {c["id"] for c in items}


def test_search_works_in_both_scripts(client):
    for q in ("translation", "अनुवाद", "anuwad"):
        ids = {c["id"] for c in client.get("/v1/board", params={"q": q}).json()["items"]}
        assert ids == {"card-london-menu"}, q
    ids = {c["id"] for c in client.get("/v1/board", params={"q": "भिडियो"}).json()["items"]}
    assert ids == {"card-toronto-reels"}


def test_card_detail_shows_country_not_client_identity(client):
    body = client.get(f"/v1/cards/{DASHAIN_CARD_ID}").json()
    text = str(body)
    assert "Ramesh" not in text and "ramesh@" not in text and "Himalayan Spice" not in text
    assert len(body["checklist"]) == 4 and body["reference_language"] == "ne"


def test_unknown_card_is_404(client):
    assert client.get("/v1/cards/nope").status_code == 404

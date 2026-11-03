"""Leak Guard (phones in both scripts, emails, URLs, handles, names) and the audit hash chain."""

import io

from PIL import Image
from sqlmodel import Session

from app.db import engine
from app.seed import ANJALI_ID, RAMESH_ID
from app.services import audit
from app.services.leakguard import redact, scan, scan_message, strip_exif
from app.services.llm import translate
from tests.conftest import ANJALI_APP, BIKASH_APP, DASHAIN, auth, register


def kinds(text, names=None):
    return [f.kind for f in scan(text, names)]


def test_phones_in_both_scripts():
    assert kinds("call +977 9812345678 now") == ["phone"]
    assert kinds("मेरो नम्बर ९८१२३४५६७८ हो") == ["phone"]
    assert kinds("9841234567") == ["phone"]
    assert kinds("1080x1080 px, 5 posts, $40") == []


def test_email_url_handle():
    assert kinds("mail me at anjali.t@gmail.com") == ["email"]
    assert kinds("see behance.net/anjali or https://x.co/y") == ["url", "url"]
    assert kinds("insta @anjali_designs") == ["handle"]


def test_declared_name_tokens_latin_and_devanagari():
    names = ["Anjali", "Thapa", "अञ्जली", "थापा"]
    assert kinds("Designed by Anjali Thapa", names) == ["name", "name"]
    assert kinds("डिजाइन: अञ्जली थापा", names) == ["name", "name"]
    assert kinds("Thapathali road poster", names) == []  # not a whole-word match


def test_redact_keeps_the_rest():
    text = "Call 9812345678 for files"
    assert redact(text, scan(text)) == "Call ▇▇▇ for files"


def test_message_scanner_warns_about_off_platform_contact():
    assert scan_message("Let's talk on WhatsApp, my number is ९८१२३४५६७८") == ["off_platform", "phone"]
    assert scan_message("Uploaded the final PNGs") == []


def test_strip_exif_removes_metadata():
    img = Image.new("RGB", (2000, 1000), "red")
    exif = Image.Exif()
    exif[0x010F] = "SecretCam"  # Make
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    assert b"SecretCam" in buf.getvalue()
    clean = strip_exif(buf.getvalue())
    assert b"SecretCam" not in clean
    with Image.open(io.BytesIO(clean)) as out:
        assert max(out.size) == 1280 and not out.getexif()


def test_apply_is_blocked_until_identifying_details_are_removed(client):
    worker = register(client, "worker", "sunil@example.org", name="Sunil Magar")
    body = {"sample_text": "Poster by Sunil, call 9812345678", "sample_lang": "en",
            "answers": ["Canva", "My insta @sunil.art"], "consent": True, "no_identifying_details": True}
    r = client.post(f"/v1/cards/{DASHAIN}/applications", json=body, headers=worker)
    assert r.status_code == 422
    assert sorted(f["kind"] for f in r.json()["detail"]["findings"]) == ["handle", "name", "phone"]
    scan_out = client.post("/v1/leakguard/scan", json={"text": body["sample_text"]}, headers=worker).json()
    assert scan_out["redacted"] == "Poster by ▇▇▇, call ▇▇▇"


def test_audit_chain_breaks_at_the_edited_event(client):
    ramesh = auth(client, RAMESH_ID)
    client.post(f"/demo/cards/{DASHAIN}/fast-forward")
    client.put(f"/v1/reviews/{ANJALI_APP}", json={"stars": {"c1": 3, "c2": 3, "c3": 3, "c4": 3}}, headers=ramesh)
    client.put(f"/v1/reviews/{BIKASH_APP}", json={"stars": {"c1": 3, "c2": 3, "c3": 1, "c4": 3}}, headers=ramesh)
    with Session(engine) as s:
        chain = audit.events(s, DASHAIN)
        assert len(chain) >= 3 and audit.verify(chain) is None
        target = chain[-2]
        target.payload_json = target.payload_json.replace('"total":12', '"total":4')
        assert audit.verify(chain) == target.seq
        s.rollback()


def test_translate_works_offline():
    assert translate("Shop logo appears on every post", "ne").model_dump() == {
        "text": "हरेक पोस्टमा पसलको लोगो छ", "source": "glossary"}
    assert translate("हरेक पोस्टमा पसलको लोगो छ", "en").text == "Shop logo appears on every post"
    assert translate("Something nobody wrote before", "ne").source == "original"


def test_translate_endpoint_needs_sign_in(client):
    assert client.post("/v1/translate", json={"text": "hi", "target": "ne"}).status_code == 401
    r = client.post("/v1/translate", json={"text": "hi", "target": "ne"}, headers=auth(client, ANJALI_ID))
    assert r.json()["source"] == "original"

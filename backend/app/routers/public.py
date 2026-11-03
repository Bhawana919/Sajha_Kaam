"""Public proof pages: signing keys, the claim Verify page and the Fair Pick Receipt.

Both pages carry the raw data and re-check it in the viewer's browser (static/verify.js):
the Receipt recomputes every audit hash, the Verify page checks the Ed25519 signature.
No names of unpicked applicants appear anywhere; applicants are letters only.
"""

import html
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.db import get_session
from app.models import AcquaintanceAttestation, Card, PassportClaim
from app.services import audit, passport, signing
from app.services.cards import GROUPS, active_apps, letters, reviews_by_app, rows
from app.services.pages import not_found, page

router = APIRouter(tags=["public"])
RECEIPT_STATES = {"picked", "revealed", "worker_declined"} | GROUPS["in_progress"] | GROUPS["completed"]
SCRIPTS = '<script src="/static/vendor/nacl-fast.min.js"></script><script src="/static/verify.js"></script>'


def _json_script(element_id: str, data: dict) -> str:
    # Safe inside <script>: no "</" can close the tag early.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/json" id="{element_id}">{payload}</script>'


@router.get("/.well-known/sajha-kaam-keys.json")
def keys() -> dict:
    return signing.keyset()


# ---------- signed claims ----------

def _visible_claim(session: Session, claim_id: str, share_token: str | None) -> PassportClaim | None:
    claim = session.get(PassportClaim, claim_id)
    if claim is None or not claim.credential_json:
        return None
    if claim.visibility == "public":
        return claim
    link = passport.active_share(session, share_token) if share_token else None
    if link and link.user_id == claim.user_id and claim.id in json.loads(link.claim_ids_json):
        return claim
    return None


def claim_proof(claim: PassportClaim) -> dict:
    return {"credential": json.loads(claim.credential_json), "signature_b64": claim.signature_b64,
            "key_id": claim.key_id, "keys": signing.keyset()["keys"]}


@router.get("/v1/public/claims/{claim_id}")
def public_claim(claim_id: str, s: str | None = Query(None), session: Session = Depends(get_session)) -> dict:
    claim = _visible_claim(session, claim_id, s)
    if claim is None:
        raise HTTPException(404, "not found")
    return claim_proof(claim)


VERIFY_JS = """
<script>
(function () {
  var data = JSON.parse(document.getElementById('proof').textContent);
  var out = document.getElementById('result');
  function key(id) { return data.keys.filter(function (k) { return k.key_id === id; })[0]; }
  function show(cred) {
    var k = key(data.key_id);
    var ok = !!k && SajhaVerify.verifySignature(cred, data.signature_b64, k.public_key_b64);
    out.className = ok ? 'pass' : 'fail';
    out.innerHTML = ok
      ? '✓ Signature valid. Checked on this device. · <span class="ne">हस्ताक्षर मिल्यो। यही उपकरणमा जाँचियो।</span>'
      : '✗ Signature does not match. This record was changed. · <span class="ne">हस्ताक्षर मिलेन। यो अभिलेख बदलिएको छ।</span>';
  }
  document.getElementById('check').onclick = function () { show(data.credential); };
  document.getElementById('tamper').onclick = function () {
    var copy = JSON.parse(JSON.stringify(data.credential));
    copy.credentialSubject.summary.en += ' (edited)';
    show(copy);
  };
  show(data.credential);
})();
</script>"""


@router.get("/verify/{claim_id}", response_class=HTMLResponse)
def verify_page(claim_id: str, s: str | None = Query(None), session: Session = Depends(get_session)) -> HTMLResponse:
    claim = _visible_claim(session, claim_id, s)
    if claim is None:
        return not_found()
    proof = claim_proof(claim)
    subject = proof["credential"]["credentialSubject"]
    esc = html.escape
    body = (
        '<span class="tag demo">DEMO · <span class="ne">डेमो</span></span>'
        '<h1>Verify a work record · <span class="ne">कामको अभिलेख जाँच्नुहोस्</span></h1>'
        '<p id="result" class="soft">Checking… · <span class="ne">जाँच्दै…</span></p>'
        '<button id="check">Check again · <span class="ne">फेरि जाँच्नुहोस्</span></button>'
        '<button id="tamper" class="quiet">DEMO: try a changed copy · <span class="ne">डेमो: बदलिएको प्रति जाँच्नुहोस्</span></button>'
        f'<div class="card"><h2>{esc(subject["displayName"])}</h2>'
        f'<h3 class="ne">{esc(subject["summary"]["ne"])}</h3><div>{esc(subject["summary"]["en"])}</div>'
        f'<div class="soft">{esc(subject["source"])} · {esc(proof["credential"]["validFrom"][:10])}</div></div>'
        '<div class="card"><strong>What this record says · <span class="ne">यो अभिलेखले के भन्छ</span></strong><ul>'
        '<li>This work was done through Sajha Kaam\'s open, blind process, and the source above confirmed it. · '
        '<span class="ne">यो काम साझा कामको खुला, नाम नहेरी गरिने प्रक्रियाबाट भयो, र माथिको स्रोतले पुष्टि गर्‍यो।</span></li>'
        '<li>Sajha Kaam signed it. Any change breaks the signature. · '
        '<span class="ne">साझा कामले हस्ताक्षर गर्‍यो। कुनै परिवर्तनले हस्ताक्षर बिगार्छ।</span></li></ul>'
        '<strong>What it does not say · <span class="ne">यसले के भन्दैन</span></strong><ul>'
        '<li>It is not a government ID, work permit, tax document or legal identity. · '
        '<span class="ne">यो सरकारी परिचयपत्र, श्रम स्वीकृति, कर कागजात वा कानुनी पहिचान होइन।</span></li>'
        '<li>It does not rate the person or the quality beyond the agreed checklist. · '
        '<span class="ne">यसले तय भएको जाँचसूचीभन्दा बाहिर व्यक्ति वा गुणस्तरको मूल्याङ्कन गर्दैन।</span></li></ul></div>'
        f'<p class="soft">Key {esc(proof["key_id"])} · <a href="/.well-known/sajha-kaam-keys.json">public key</a> · '
        'shaped like a W3C Verifiable Credential (v2), signed with Ed25519.</p>'
        + _json_script("proof", proof)
    )
    return page("Verify · जाँच", body, SCRIPTS + VERIFY_JS)


# ---------- Fair Pick Receipt ----------

def receipt_data(session: Session, card: Card) -> dict:
    letter_of = letters(session, card)
    reviews = reviews_by_app(session, card)
    _, items = rows(session, card.id)
    chain = audit.events(session, card.id)
    attest = session.exec(select(AcquaintanceAttestation).where(AcquaintanceAttestation.card_id == card.id)).first()
    reveal = next((e for e in chain if e.action == "reveal"), None)
    scores = sorted(
        ({"applicant": letter_of[app_id], "stars": json.loads(r.star_scores_json), "total": r.total}
         for app_id, r in reviews.items() if app_id in letter_of),
        key=lambda x: x["applicant"],
    )
    iso = lambda d: d.replace(tzinfo=None).isoformat(timespec="seconds") + "Z" if d else None  # noqa: E731
    return {
        "card_id": card.id, "title_en": card.title_en, "title_ne": card.title_ne, "state": card.state,
        "applicant_count": len(active_apps(session, card.id)),
        "window_opens_at": iso(card.window_opens_at), "window_closes_at": iso(card.window_closes_at),
        "rubric": [{"id": i.id, "en": i.text_en, "ne": i.text_ne} for i in items],
        "scores": scores,
        "picked": letter_of.get(card.picked_application_id) if card.picked_application_id else None,
        "attested_unacquainted_at": iso(attest.attested_at) if attest else None,
        "tie_note": card.tie_note,
        "revealed_at": iso(reveal.created_at_utc) if reveal else None,
        "events": [{"body": audit.event_body(e), "prev_hash": e.prev_hash, "hash": e.hash} for e in chain],
        "final_hash": chain[-1].hash if chain else None,
    }


def _receipt_card(session: Session, card_id: str) -> Card | None:
    card = session.get(Card, card_id)
    return card if card is not None and card.state in RECEIPT_STATES else None


@router.get("/v1/public/receipts/{card_id}")
def receipt_json(card_id: str, session: Session = Depends(get_session)) -> dict:
    card = _receipt_card(session, card_id)
    if card is None:
        raise HTTPException(404, "not found")
    return receipt_data(session, card)


RECEIPT_JS = """
<script>
(function () {
  var data = JSON.parse(document.getElementById('receipt').textContent);
  var out = document.getElementById('result');
  function run(events) {
    out.className = 'soft'; out.textContent = '…';
    document.querySelectorAll('tr.event').forEach(function (r) { r.className = 'event'; r.lastChild.textContent = ''; });
    return SajhaVerify.verifyChain(events).then(function (broken) {
      document.querySelectorAll('tr.event').forEach(function (r) {
        var seq = +r.dataset.seq;
        var bad = broken !== null && seq >= broken;
        r.className = bad ? 'event broken' : 'event';
        r.lastChild.textContent = bad ? (seq === broken ? '✗' : '–') : '✓';
      });
      out.className = broken === null ? 'pass' : 'fail';
      out.innerHTML = broken === null
        ? '✓ Every event checks out. Recomputed on this device. · <span class="ne">सबै घटना मिले। यही उपकरणमा फेरि गणना गरियो।</span>'
        : '✗ The record was changed at event ' + broken + '. · <span class="ne">घटना ' + broken + ' मा अभिलेख बदलिएको छ।</span>';
    });
  }
  document.getElementById('check').onclick = function () { run(data.events); };
  document.getElementById('tamper').onclick = function () {
    var copy = JSON.parse(JSON.stringify(data.events));
    var target = copy.filter(function (e) { return e.body.action === 'score'; })[0] || copy[0];
    if (target.body.payload && 'total' in target.body.payload) target.body.payload.total += 1;
    else target.body.actor = 'Someone else';
    run(copy);
  };
  run(data.events);
})();
</script>"""


@router.get("/receipt/{card_id}", response_class=HTMLResponse)
def receipt_page(card_id: str, session: Session = Depends(get_session)) -> HTMLResponse:
    card = _receipt_card(session, card_id)
    if card is None:
        return not_found()
    d = receipt_data(session, card)
    esc = html.escape
    rubric = "".join(f'<li><span class="ne">{esc(r["ne"])}</span> · {esc(r["en"])}</li>' for r in d["rubric"])
    head = "".join(f"<th>{esc(r['id'])}</th>" for r in d["rubric"])
    score_rows = "".join(
        f'<tr><td><strong>{esc(s["applicant"])}</strong>{" ★" if s["applicant"] == d["picked"] else ""}</td>'
        + "".join(f"<td>{s['stars'].get(r['id'], '')}</td>" for r in d["rubric"])
        + f"<td><strong>{s['total']}</strong></td></tr>"
        for s in d["scores"]
    )
    event_rows = "".join(
        f'<tr class="event" data-seq="{e["body"]["seq"]}"><td>{e["body"]["seq"]}</td><td>{esc(e["body"]["actor"])}</td>'
        f'<td>{esc(e["body"]["action"])}</td><td class="mono">{esc(e["hash"][:16])}…</td><td></td></tr>'
        for e in d["events"]
    )
    tie = (f'<p><strong>Tie note · <span class="ne">बराबरीको कारण</span>:</strong> {esc(d["tie_note"])}</p>'
           if d["tie_note"] else "")
    body = (
        '<span class="tag demo">DEMO · <span class="ne">डेमो</span></span>'
        '<h1>Fair Pick Receipt · <span class="ne">निष्पक्ष चयन रसिद</span></h1>'
        f'<p><span class="ne">{esc(d["title_ne"])}</span><br>{esc(d["title_en"])}</p>'
        '<p id="result" class="soft">Checking… · <span class="ne">जाँच्दै…</span></p>'
        '<button id="check">Verify chain · <span class="ne">शृङ्खला जाँच्नुहोस्</span></button>'
        '<button id="tamper" class="quiet">DEMO: try a changed copy · <span class="ne">डेमो: बदलिएको प्रति जाँच्नुहोस्</span></button>'
        f'<div class="card"><div>{d["applicant_count"]} applicants · <span class="ne">आवेदक</span></div>'
        f'<div class="soft">Window · <span class="ne">समय</span>: {esc(d["window_opens_at"] or "–")} → {esc(d["window_closes_at"] or "–")}</div>'
        f'<div class="soft">"I don\'t personally know any applicant" · <span class="ne">“म कुनै आवेदकलाई चिन्दिनँ”</span>: '
        f'{esc(d["attested_unacquainted_at"] or "–")}</div>'
        f'<div class="soft">Revealed · <span class="ne">नाम खोलिएको</span>: {esc(d["revealed_at"] or "–")}</div></div>'
        f'<div class="card"><strong>Rubric, same for everyone · <span class="ne">सबैका लागि उही जाँचसूची</span></strong><ol>{rubric}</ol>'
        f'<table><tr><th>Applicant</th>{head}<th>Total</th></tr>{score_rows}</table>{tie}'
        '<p class="soft">Applicants are letters only. Names of applicants who were not picked never appear. · '
        '<span class="ne">आवेदक अक्षरले मात्र देखिन्छन्। नछानिएकाको नाम कहिल्यै देखिँदैन।</span></p></div>'
        f'<div class="card"><strong>Audit chain · <span class="ne">अडिट शृङ्खला</span></strong>'
        f'<table><tr><th>#</th><th>Actor</th><th>Action</th><th>Hash</th><th></th></tr>{event_rows}</table>'
        f'<p class="mono">final: {esc(d["final_hash"] or "")}</p>'
        '<p class="soft">Each hash = SHA-256(previous hash + canonical JSON of the event). · '
        '<span class="ne">हरेक ह्यास = SHA-256(अघिल्लो ह्यास + घटनाको क्यानोनिकल JSON)।</span></p></div>'
        + _json_script("receipt", d)
    )
    return page("Fair Pick Receipt · निष्पक्ष चयन रसिद", body, SCRIPTS + RECEIPT_JS)

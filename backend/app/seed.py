"""Fictional demo data. Rebuilt on every startup when the DB is empty (hosted disks can be ephemeral).

Everyone and everything here is invented. Ramesh K. (Sydney) posts the Dashain card;
twelve fictional workers apply; Anjali Thapa is Applicant F in Demo mode.
"""

import hashlib
import json
from datetime import timedelta

import bcrypt
from sqlmodel import Session, select

from app.models import (
    Application,
    Card,
    ChecklistItemRow,
    ClientProfile,
    DeliverableRow,
    User,
    WorkerProfile,
    utcnow,
)
from app.services.templates import draft_from_template

SAMPLE_PASSWORD = "sajha-demo"  # sample identities only; shown in the README

# Fixed IDs so Demo mode, deep links and tests can refer to them.
RAMESH_ID = "u-client-ramesh"
LONDON_ID = "u-client-london"
TORONTO_ID = "u-client-toronto"
ADMIN_ID = "u-admin"
ANJALI_ID = "u-worker-anjali"
BIKASH_ID = "u-worker-bikash"
DASHAIN_CARD_ID = "card-dashain-posts"

# (id, display name, Devanagari name tokens, district, skills, sample text, answers[ne/en], sample lang)
_WORKERS = [
    ("u-worker-pema", "Pema L.", ["Pema", "पेमा"], "Solukhumbu", ["graphic_design"],
     "Festival greeting for a bakery: 1080×1080, logo top-left, English text 'Happy Holidays', warm red background.",
     ["Canva", "I put English big and Nepali small below."], "en"),
    ("u-worker-kiran", "Kiran S.", ["Kiran", "किरण"], "Kaski", ["graphic_design", "social_media_posts"],
     "तिहार पोस्ट: १०८०×१०८०, नेपाली र अंग्रेजी लेख, पसलको लोगो तल दायाँ, बत्तीको चित्र।",
     ["फोटोसप", "नेपाली माथि, अंग्रेजी तल राख्छु।"], "ne"),
    ("u-worker-sunita", "Sunita G.", ["Sunita", "सुनिता"], "Gorkha", ["social_media_posts"],
     "Square post for a tea shop opening, PNG 1080×1080, English text only, shop logo in the centre.",
     ["Canva", "Two text boxes, same font size."], "en"),
    ("u-worker-rohan", "Rohan M.", ["Rohan", "रोहन"], "Morang", ["graphic_design"],
     "Poster for a football match, A4 size, English text, no logo.",
     ["Illustrator", "I would ask the client."], "en"),
    ("u-worker-maya", "Maya B.", ["Maya", "माया"], "Jhapa", ["social_media_posts", "content_writing"],
     "न्यू इयर पोस्ट: १०८०×१०८०, नेपाली र अंग्रेजी, लोगो छ, तर रङ ब्रान्डसँग नमिल्ने।",
     ["Canva", "दुई भाषा दुई लाइनमा।"], "ne"),
    # Applicant F in Demo mode: meets all four checklist items.
    ("u-worker-anjali", "Anjali Thapa", ["Anjali", "Thapa", "अञ्जली", "थापा"], "Surkhet", ["graphic_design", "social_media_posts"],
     "दसैं शुभकामना पोस्ट नमुना: १०८०×१०८० PNG, पसलको लोगो माथि बायाँ, 'दसैंको हार्दिक शुभकामना' र 'Happy Dashain' दुवै लेख, ब्रान्ड रङ।",
     ["Canva र Figma", "नेपाली ठूलो अक्षरमा माथि, अंग्रेजी सानो तल, दुवै पढ्न सजिलो।"], "ne"),
    ("u-worker-dipesh", "Dipesh K.", ["Dipesh", "दिपेश"], "Chitwan", ["graphic_design"],
     "Instagram post 1080×1080 for a gym, English text, logo bottom, bold colours.",
     ["Photoshop", "Nepali on the left, English on the right."], "en"),
    ("u-worker-asha", "Asha R.", ["Asha", "आशा"], "Ilam", ["social_media_posts"],
     "चिया पसलको पोस्ट: १०८०×१०८०, नेपाली लेख मात्र, लोगो छ।",
     ["Canva", "अंग्रेजी अनुवाद तल राख्छु।"], "ne"),
    ("u-worker-nabin", "Nabin P.", ["Nabin", "नबिन"], "Dang", ["graphic_design"],
     "Restaurant menu design, 2 pages, English, PDF.",
     ["Canva", "Use two fonts."], "en"),
    ("u-worker-sarita", "Sarita D.", ["Sarita", "सरिता"], "Dhanusha", ["social_media_posts"],
     "Dashain post 1080×1080, Nepali and English text, logo top, red and gold.",
     ["Canva", "Nepali first line, English second line."], "en"),
    ("u-worker-bikash", "Bikash", ["Bikash", "बिकाश"], "Rupandehi", ["graphic_design", "social_media_posts"],
     "Dashain sale post, 1080×1080 PNG, shop logo top-right, English text 'Big Dashain Sale', brand colours.",
     ["Canva", "I would add Nepali text if the client sends it."], "en"),
    ("u-worker-roshni", "Roshni T.", ["Roshni", "रोश्नी"], "Kailali", ["graphic_design"],
     "Birthday greeting post 1080×1350, Nepali text, no logo.",
     ["Canva", "Nepali only unless asked."], "ne"),
]

def application_id_for(worker_id: str) -> str:
    """Opaque, stable application id. Never derived visibly from a name: clients see these ids."""
    return "app-" + hashlib.sha256(f"sajha-demo|{worker_id}".encode()).hexdigest()[:12]


# Demo-mode letter order: index 5 -> F (Anjali).
DEMO_ORDER_WORKERS = [w[0] for w in _WORKERS]


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=8)).decode()


def _card_from_text(session: Session, card_id: str, client_id: str, text: str, *, state: str,
                    pahilo: bool, skill: str, closes_in: timedelta) -> Card:
    draft = draft_from_template(text)
    now = utcnow()
    card = Card(
        id=card_id, client_id=client_id, state=state, skill=skill,
        reference_language=draft.reference_language,
        title_ne=draft.title_ne, title_en=draft.title_en, summary_ne=draft.summary_ne, summary_en=draft.summary_en,
        price_minor=draft.price.amount_minor, deadline_days=draft.deadline_days,
        revisions_included=draft.revisions_included, pahilo_kaam=pahilo,
        sample_brief_ne=draft.sample_brief_ne, sample_brief_en=draft.sample_brief_en,
        questions_json=json.dumps([q.model_dump() for q in draft.questions], ensure_ascii=False),
        draft_source="template", window_opens_at=now - timedelta(hours=48) + closes_in,
        window_closes_at=now + closes_in, reviewed_by_sajha=True,
    )
    session.add(card)
    for i, d in enumerate(draft.deliverables):
        session.add(DeliverableRow(card_id=card_id, id=d.id, position=i, text_ne=d.text_ne, text_en=d.text_en))
    for i, c in enumerate(draft.checklist):
        session.add(ChecklistItemRow(card_id=card_id, id=c.id, deliverable_id=c.deliverable_id, position=i,
                                     text_ne=c.text_ne, text_en=c.text_en, testable=c.testable))
    return card


def seed(session: Session) -> bool:
    """Insert the demo world if the DB is empty. Returns True if it seeded."""
    if session.exec(select(User).limit(1)).first():
        return False
    pw = _hash(SAMPLE_PASSWORD)
    attested = utcnow()

    for uid, name, email, country, org, locale in [
        (RAMESH_ID, "Ramesh K.", "ramesh@sample.sajhakaam.test", "Australia", "Himalayan Spice Store, Sydney", "ne"),
        (LONDON_ID, "Claire W.", "claire@sample.sajhakaam.test", "United Kingdom", "Corner café, London", "en"),
        (TORONTO_ID, "Sabina P.", "sabina@sample.sajhakaam.test", "Canada", "Momo truck, Toronto", "en"),
    ]:
        session.add(User(id=uid, role="client", email=email, password_hash=pw, display_name=name,
                         locale=locale, consent_version="2026-11", is_sample_identity=True))
        session.add(ClientProfile(user_id=uid, country=country, org_label=org))
    session.add(User(id=ADMIN_ID, role="admin", email="admin@sample.sajhakaam.test", password_hash=pw,
                     display_name="Sajha reviewer", locale="en", is_sample_identity=True))

    for uid, name, tokens, district, skills, *_ in _WORKERS:
        session.add(User(id=uid, role="worker", email=f"{uid.removeprefix('u-worker-')}@sample.sajhakaam.test",
                         password_hash=pw, display_name=name, locale="ne", consent_version="2026-11",
                         age_attested_at=attested, is_sample_identity=True))
        session.add(WorkerProfile(user_id=uid, skills_json=json.dumps(skills), district=district,
                                  name_tokens_json=json.dumps(tokens, ensure_ascii=False)))
    session.flush()

    # Ramesh's Dashain card: 12 applicants, window closing soon (Demo: fast-forward 48 h).
    _card_from_text(session, DASHAIN_CARD_ID, RAMESH_ID, "५ वटा दसैं पोस्ट चाहियो", state="open",
                    pahilo=True, skill="social_media_posts", closes_in=timedelta(hours=2))
    for uid, _name, _tokens, _district, _skills, sample, answers, lang in _WORKERS:
        session.add(Application(
            id=application_id_for(uid), card_id=DASHAIN_CARD_ID, worker_id=uid,
            sample_text=sample, scrubbed_text=sample, sample_lang=lang, consent_at=attested,
            answers_json=json.dumps([{"question_index": i, "text": a, "lang": lang} for i, a in enumerate(answers)],
                                    ensure_ascii=False),
        ))

    # Two more open cards so the board is not empty.
    _card_from_text(session, "card-london-menu", LONDON_ID, "Translate 2 pages of our café menu from English to Nepali, $15, 3 days",
                    state="open", pahilo=True, skill="translation", closes_in=timedelta(hours=30))
    _card_from_text(session, "card-toronto-reels", TORONTO_ID, "I need 3 reels for my momo truck, $75, 4 days",
                    state="open", pahilo=False, skill="video_editing", closes_in=timedelta(hours=40))
    session.commit()
    return True


def demo_order_for(card_id: str) -> list[str] | None:
    if card_id == DASHAIN_CARD_ID:
        return [application_id_for(w) for w in DEMO_ORDER_WORKERS]
    return None


# Shown on the one-tap "Sample identity" list (Demo mode only).
SAMPLE_NOTES = {
    RAMESH_ID: ("Client in Sydney. Owns the Dashain card.", "सिड्नीका ग्राहक। दसैं कार्ड उहाँको हो।"),
    ANJALI_ID: ("Worker in Surkhet. Applicant F on the Dashain card.", "सुर्खेतकी कामदार। दसैं कार्डमा आवेदक F।"),
    BIKASH_ID: ("Worker in Butwal. His sample is missing Nepali text.", "बुटवलका कामदार। उनको नमुनामा नेपाली लेख छैन।"),
    LONDON_ID: ("Client in London. Café menu translation.", "लन्डनकी ग्राहक। क्याफेको मेनु अनुवाद।"),
    ADMIN_ID: ("Sajha Kaam reviewer. Approves first cards.", "साझा कामका समीक्षक। पहिलो कार्ड स्वीकृत गर्नुहुन्छ।"),
}

"""Work Passport API (owner only) and the public pages /p/{slug} and /s/{token}.

Private by default: the public page shows only claims the worker made public; a share link
shows only the claims it was made for, until it expires or is revoked.
"""

import html
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.auth import require_role
from app.db import get_session
from app.models import Passport, PassportClaim, ShareLink, User, utcnow
from app.schemas.api import ClaimOut, LevelOut, PassportOut
from app.services import passport as svc
from app.services.i18n import to_devanagari_digits
from app.services.levels import record
from app.services.pages import not_found, page

router = APIRouter(prefix="/v1", tags=["passport"])
public = APIRouter(tags=["public"])
worker_only = require_role("worker")


class VisibilityIn(BaseModel):
    visibility: str = Field(pattern="^(private|public)$")


class ShareIn(BaseModel):
    claim_ids: list[str] = Field(min_length=1, max_length=50)
    days: int = Field(default=7, ge=1, le=30)


class ShareOut(BaseModel):
    id: str
    url: str | None  # the token is shown once, at creation
    claim_ids: list[str]
    expires_at: str
    revoked: bool


def _level(lv: dict | None) -> LevelOut | None:
    return LevelOut(**{k: lv[k] for k in ("id", "en", "ne", "price_cap_minor")}) if lv else None


@router.get("/me/passport", response_model=PassportOut)
def my_passport(request: Request, user: User = Depends(worker_only), session: Session = Depends(get_session)) -> PassportOut:
    rec = record(session, user.id)
    p = svc.get_or_create(session, user.id)
    session.commit()
    return PassportOut(
        confirmed_jobs=rec.confirmed_jobs, on_time_pct=rec.on_time_pct, level=_level(rec.level),
        next_level=_level(rec.next_level),
        jobs_to_next=max(0, rec.next_level["min_confirmed_jobs"] - rec.confirmed_jobs) if rec.next_level else None,
        claims=[ClaimOut(**c.model_dump(include=set(ClaimOut.model_fields) - {"credential"}), signed=bool(c.signature_b64),
                         credential=json.loads(c.credential_json) if c.credential_json else None)
                for c in svc.claims_for(session, user.id)],
        slug=p.slug, public_url=svc.public_url(p.slug, str(request.base_url)),
    )


@router.patch("/passport/claims/{claim_id}", response_model=ClaimOut)
def set_visibility(claim_id: str, body: VisibilityIn, user: User = Depends(worker_only),
                   session: Session = Depends(get_session)) -> ClaimOut:
    claim = session.get(PassportClaim, claim_id)
    if claim is None or claim.user_id != user.id:
        raise HTTPException(404, "not found")
    claim.visibility = body.visibility
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return ClaimOut(**claim.model_dump(include=set(ClaimOut.model_fields)))


def _share_out(link: ShareLink, url: str | None = None) -> ShareOut:
    return ShareOut(id=link.id, url=url, claim_ids=json.loads(link.claim_ids_json),
                    expires_at=link.expires_at.isoformat(), revoked=link.revoked_at is not None)


@router.post("/passport/shares", response_model=ShareOut)
def create_share(body: ShareIn, request: Request, user: User = Depends(worker_only),
                 session: Session = Depends(get_session)) -> ShareOut:
    mine = {c.id for c in svc.claims_for(session, user.id)}
    if not set(body.claim_ids) <= mine:
        raise HTTPException(404, "not found")
    link, token = svc.create_share(session, user.id, body.claim_ids, body.days)
    return _share_out(link, svc.share_url(token, str(request.base_url)))


@router.get("/passport/shares", response_model=list[ShareOut])
def list_shares(user: User = Depends(worker_only), session: Session = Depends(get_session)) -> list[ShareOut]:
    links = session.exec(select(ShareLink).where(ShareLink.user_id == user.id).order_by(ShareLink.created_at.desc())).all()
    return [_share_out(link) for link in links]


@router.delete("/passport/shares/{share_id}", response_model=ShareOut)
def revoke_share(share_id: str, user: User = Depends(worker_only), session: Session = Depends(get_session)) -> ShareOut:
    link = session.get(ShareLink, share_id)
    if link is None or link.user_id != user.id:
        raise HTTPException(404, "not found")
    link.revoked_at = link.revoked_at or utcnow()
    session.add(link)
    session.commit()
    session.refresh(link)
    return _share_out(link)


@router.get("/passport/export", response_model=dict)
def export(user: User = Depends(worker_only), session: Session = Depends(get_session)) -> dict:
    return svc.export(session, user)


@router.delete("/me/data", response_model=dict)
def delete_my_data(user: User = Depends(worker_only), session: Session = Depends(get_session)) -> dict:
    svc.delete_everything(session, user)
    return {"deleted": True}


# ---------- public pages (no sign-in; also open in any phone browser) ----------

CLAIM_LABEL = {
    "client_confirmed_delivery": ("Client confirmed delivery", "ग्राहकले बुझेको पुष्टि गरे"),
    "both_confirmed_payment": ("Payment confirmed by both", "दुवैले भुक्तानी पुष्टि गरे"),
    "practice_badge": ("Practice badge", "अभ्यास ब्याज"),
}


def _passport_body(session: Session, user: User, claims: list[PassportClaim], scope_en: str, scope_ne: str,
                   share_token: str | None = None) -> str:
    rec = record(session, user.id)
    esc = html.escape
    items = []
    for c in claims:
        en, ne = CLAIM_LABEL.get(c.type, (c.type, c.type))
        timing = '<span class="tag">On time · समयमै</span>' if c.on_time else '<span class="tag">Late · ढिलो</span>'
        items.append(
            f'<div class="card"><span class="tag ok">{esc(en)} · <span class="ne">{esc(ne)}</span></span>{timing}'
            f'<h3 class="ne">{esc(c.summary_ne)}</h3><div>{esc(c.summary_en)}</div>'
            f'<div class="soft">{esc(c.issued_at.date().isoformat())} · {esc(c.source_label)}</div>'
            + (f'<a href="/verify/{esc(c.id)}{"?s=" + esc(share_token) if share_token else ""}">'
               'Verify signature · <span class="ne">हस्ताक्षर जाँच्नुहोस्</span></a>' if c.signature_b64 else "")
            + "</div>"
        )
    if not items:
        items.append('<p class="soft">No records shared here. · <span class="ne">यहाँ कुनै अभिलेख बाँडिएको छैन।</span></p>')
    return (
        '<span class="tag demo">DEMO · <span class="ne">डेमो</span></span>'
        f'<h1>Work Passport · <span class="ne">कामको पासपोर्ट</span></h1>'
        f'<p class="ne"><strong>मेरो काम, मेरो पहिचान।</strong></p>'
        f'<div class="level"><div class="soft">Kaam Path · <span class="ne">काम पथ</span></div>'
        f'<h2>{esc(user.display_name)}</h2><div>{esc(rec.level["en"])} · <span class="ne">{esc(rec.level["ne"])}</span></div>'
        f'<div class="soft">{rec.confirmed_jobs} client-confirmed {"job" if rec.confirmed_jobs == 1 else "jobs"} on Sajha Kaam · '
        f'<span class="ne">साझा काममा ग्राहकले पुष्टि गरेका {to_devanagari_digits(str(rec.confirmed_jobs))} काम</span></div></div>'
        f'<p class="soft">{esc(scope_en)}<br><span class="ne">{esc(scope_ne)}</span></p>'
        + "".join(items)
        + '<p class="soft">A record of work done on Sajha Kaam. Not a government ID, work permit, tax document or '
          'legal identity.<br><span class="ne">साझा काममा गरिएको कामको अभिलेख। यो सरकारी परिचयपत्र, श्रम स्वीकृति, '
          'कर कागजात वा कानुनी पहिचान होइन।</span></p>'
    )


@public.get("/p/{slug}", response_class=HTMLResponse)
def public_passport(slug: str, session: Session = Depends(get_session)) -> HTMLResponse:
    p = session.exec(select(Passport).where(Passport.slug == slug)).first()
    user = session.get(User, p.user_id) if p else None
    if user is None or user.password_hash == "!":
        return not_found()
    claims = svc.claims_for(session, user.id, public_only=True)
    return page("Work Passport", _passport_body(session, user, claims, "Records this worker chose to make public.",
                                                 "कामदारले सार्वजनिक गर्न रोजेका अभिलेख।"))


@public.get("/s/{token}", response_class=HTMLResponse)
def shared_passport(token: str, session: Session = Depends(get_session)) -> HTMLResponse:
    link = svc.active_share(session, token)
    user = session.get(User, link.user_id) if link else None
    if user is None:
        return not_found()
    claims = svc.claims_for(session, user.id, ids=json.loads(link.claim_ids_json))
    return page("Work Passport", _passport_body(
        session, user, claims, f"Shared by the worker until {link.expires_at.date().isoformat()}.",
        f"कामदारले {link.expires_at.date().isoformat()} सम्मका लागि बाँडेको।", share_token=token))

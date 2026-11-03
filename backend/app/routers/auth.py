"""Sign-up, sign-in, token refresh, profile, and Demo-mode sample identities."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.auth import check_password, current_user, decode, hash_password, issue_tokens
from app.config import settings
from app.db import get_session
from app.models import ClientProfile, User, WorkerProfile, utcnow
from app.schemas.api import (
    LevelOut,
    LoginRequest,
    Me,
    MePatch,
    RefreshRequest,
    RegisterRequest,
    SampleIdentity,
    SampleLoginRequest,
    TokenPair,
)
from app.seed import SAMPLE_NOTES
from app.services.levels import record
from app.services.skills import skills

router = APIRouter(prefix="/v1", tags=["auth"])
CONSENT_VERSION = "2026-11"


def _valid_skills(ids: list[str]) -> list[str]:
    known = {s["id"] for s in skills()}
    bad = [s for s in ids if s not in known]
    if bad:
        raise HTTPException(422, f"unknown skills: {', '.join(bad)}")
    return ids


@router.post("/auth/register", response_model=TokenPair)
def register(body: RegisterRequest, session: Session = Depends(get_session)) -> dict:
    if not body.consent:
        raise HTTPException(422, "consent is required")
    email = body.email.strip().lower()
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(409, "an account with this email already exists")
    if body.role == "worker":
        if not body.age_attested:
            raise HTTPException(422, "workers must be 18 or older")
        if not 1 <= len(body.skills) <= 5:
            raise HTTPException(422, "choose 1 to 5 skills")
    elif not body.country:
        raise HTTPException(422, "country is required for clients")
    user = User(role=body.role, email=email, password_hash=hash_password(body.password),
                display_name=body.display_name.strip(), locale=body.locale, consent_version=CONSENT_VERSION,
                age_attested_at=utcnow() if body.role == "worker" else None)
    session.add(user)
    session.flush()
    if body.role == "worker":
        tokens = [t for t in body.display_name.replace(".", " ").split() if len(t) > 1]
        session.add(WorkerProfile(user_id=user.id, skills_json=json.dumps(_valid_skills(body.skills)),
                                  name_tokens_json=json.dumps(tokens, ensure_ascii=False)))
    else:
        session.add(ClientProfile(user_id=user.id, country=body.country or "", org_label=body.org_label))
    session.commit()
    return issue_tokens(user)


@router.post("/auth/login", response_model=TokenPair)
def login(body: LoginRequest, session: Session = Depends(get_session)) -> dict:
    user = session.exec(select(User).where(User.email == body.email.strip().lower())).first()
    if user is None or not check_password(body.password, user.password_hash):
        raise HTTPException(401, "wrong email or password")
    return issue_tokens(user)


@router.post("/auth/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, session: Session = Depends(get_session)) -> dict:
    user = session.get(User, decode(body.refresh_token, "refresh")["sub"])
    if user is None:
        raise HTTPException(401, "account not found")
    return issue_tokens(user)


@router.get("/auth/sample-identities", response_model=list[SampleIdentity])
def sample_identities(session: Session = Depends(get_session)) -> list[SampleIdentity]:
    if not settings().demo_mode:
        return []
    out = []
    for user_id, (note_en, note_ne) in SAMPLE_NOTES.items():
        u = session.get(User, user_id)
        if u:
            out.append(SampleIdentity(user_id=u.id, role=u.role, display_name=u.display_name,
                                      note_en=note_en, note_ne=note_ne))
    return out


@router.post("/auth/sample-login", response_model=TokenPair)
def sample_login(body: SampleLoginRequest, session: Session = Depends(get_session)) -> dict:
    if not settings().demo_mode:
        raise HTTPException(404, "not found")
    user = session.get(User, body.user_id)
    if user is None or not user.is_sample_identity:
        raise HTTPException(404, "no such sample identity")
    return issue_tokens(user)


def me_out(session: Session, user: User) -> Me:
    me = Me(id=user.id, role=user.role, display_name=user.display_name, locale=user.locale,
            numerals_pref=user.numerals_pref, is_sample_identity=user.is_sample_identity)
    if user.role == "worker":
        profile = session.get(WorkerProfile, user.id)
        rec = record(session, user.id)
        me.skills = json.loads(profile.skills_json) if profile else []
        me.confirmed_jobs = rec.confirmed_jobs
        me.level = LevelOut(**{k: rec.level[k] for k in ("id", "en", "ne", "price_cap_minor")})
    elif user.role == "client":
        profile = session.get(ClientProfile, user.id)
        me.country = profile.country if profile else None
    return me


@router.get("/me", response_model=Me)
def get_me(user: User = Depends(current_user), session: Session = Depends(get_session)) -> Me:
    return me_out(session, user)


@router.patch("/me", response_model=Me)
def patch_me(body: MePatch, user: User = Depends(current_user), session: Session = Depends(get_session)) -> Me:
    if body.locale:
        user.locale = body.locale
    if body.numerals_pref:
        user.numerals_pref = body.numerals_pref
    if body.skills is not None:
        if user.role != "worker":
            raise HTTPException(422, "only workers have skills")
        profile = session.get(WorkerProfile, user.id)
        profile.skills_json = json.dumps(_valid_skills(body.skills))
        session.add(profile)
    session.add(user)
    session.commit()
    return me_out(session, user)

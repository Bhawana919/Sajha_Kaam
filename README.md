# Sajha Kaam · साझा काम

**Clear work. Safe pay. Proof that travels.** · स्पष्ट काम। सुरक्षित भुक्तानी। जहाँ गए पनि चल्ने प्रमाण।

Sajha Kaam helps young Nepalis win their first paid global job fairly:

- They are hired blind, for their work.
- They are protected by a clear, AI-drafted agreement (the Kaam Card).
- They keep proof they can carry anywhere (the Work Passport).

The project has two roles. A **Client** hires (for example, a diaspora shop owner in Sydney). A **Worker** wants a job (for example, a 21-year-old designer in Surkhet).

> **Status: Phase 16–28h built.** All P0 features are in: the loop for both roles, a Work Passport with QR, public page and share links, and offline drafts. Still to do: run it on a real phone against the deployed backend. See [Build status](#build-status).

## Layout

```
sajha-kaam/
  backend/   FastAPI + SQLModel + SQLite API, seed data, tests
  mobile/    Expo (SDK 58) + React Native + Expo Router app
  config/    rules.yaml, levels.yaml, task_bands.yaml, skills.yaml (all numbers are assumptions)
  shared/    state_machine.json, kaam_card.schema.json, openapi.json (generated)
  docs/      RULES.md, NEPALI_REVIEW.md
```

## Run it

### Backend

The API seeds itself on startup. From the `Sajha_Kaam_Hackathon_Kit` folder:

```powershell
pip install -r requirements.txt         # first time only: all Python packages, pinned
.\sajha-kaam\backend\start.ps1          # = uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs to explore the API. To run the tests, go to `sajha-kaam\backend` and run `python -m pytest`.

- `backend/requirements.txt` is what the API needs to run; the Dockerfile uses this one.
- `backend/requirements-dev.txt` adds pytest, httpx and ruff.
- The kit's top-level `requirements.txt` installs both.

You can use a virtual environment if you like: `start.ps1` uses `backend\.venv` when it exists.

### Mobile app

```powershell
cd sajha-kaam\mobile
npm install                             # first time only
npm run start:mock                      # UI only, no backend needed
```

Scan the QR code with **Expo Go**; your phone must be on the same Wi-Fi. If the venue blocks this, run `npx expo start --tunnel`. Press `w` to open the app in a browser.

To use the real backend, create `mobile\.env` with your laptop's LAN IP (find it with `ipconfig`), then run `npx expo start`:

```
EXPO_PUBLIC_API_URL=http://192.168.x.x:8000
```

If `EXPO_PUBLIC_API_URL` is not set, the app runs in **mock mode**. You can browse the board, open job details and draft cards, but signing in, posting, applying and the rest of the loop need the backend; the app says so in the user's language.

### The demo loop in two minutes (backend + app running)

1. Sign in as **Ramesh K.** (sample identity). Then:
   - On **Post**, tap **Use the example**, then **Make Kaam Card**, then **Save & post**.
   - Open `card-dashain-posts` (My cards → Open). Tap **DEMO: skip the 48-hour wait**, then **Start blind review**.
   - Score A–L, tick "I don't personally know any applicant", tap **Pick**, then **Reveal & hire**. Anjali is F.
2. On **Help**, tap **Sign out**, then sign in as **Anjali Thapa**. Then:
   - Go to **My work** and tap **Open job**.
   - Paste any `https://` link as the Khalti payment request, then tap **Accept**.
   - Deliver the work.
3. Sign in as **Ramesh K.** again. In the workroom, tick all four items, then tap **Confirm**, then **I've paid** (DEMO).
4. Sign in as **Anjali Thapa** again. In the workroom, tap **I received the payment**. **Passport** now shows two records and the level "First Kaam".
5. To start over, go to **Help** and tap **DEMO: reset sample data**.

### On a phone (same Wi-Fi as the laptop)

1. Start the backend with `--host 0.0.0.0`, as shown above.
2. Copy `mobile/.env.example` to `mobile/.env`. Put your laptop's LAN IP in it (find it with `ipconfig`).
3. Run `npx expo start`, then scan the QR code with Expo Go.

The Passport QR code and share links use whatever address the phone used to reach the API, so they open on the same Wi-Fi with no extra setup. If Windows Firewall asks, allow Python on private networks.

### Deploy the backend (Render, free plan)

1. Push `sajha-kaam/` to a GitHub repo.
2. On Render, choose **New → Blueprint** and pick the repo. `render.yaml` builds `backend/Dockerfile`, generates `JWT_SECRET`, and seeds the demo data on every start.
3. In the Render dashboard, set `PUBLIC_BASE_URL` to the service URL, for example `https://sajha-kaam-api.onrender.com`. To turn on AI drafting, also set `LLM_PROVIDER=anthropic` and `LLM_API_KEY`.
4. Point the app at it: put `EXPO_PUBLIC_API_URL=https://…onrender.com` in `mobile/.env`. This value is also the `preview` profile in `mobile/eas.json`, used for the APK later.

The free plan sleeps when idle, and the first request after that takes about 30 seconds. Open `/health` once before you demo.

### Checks

| Command | What it checks |
|---|---|
| `backend> pytest` | 91 tests: signatures, Receipt, Stress Test, Passport privacy and sharing, state machine, blindness, ownership, the full loop, idempotency, rule checks, Leak Guard, audit chain, drafting and translation fallbacks |
| `backend> ruff check .` | Python lint |
| `mobile> npm run check` | i18n parity + Devanagari, numerals/money format, on-phone signature check against a backend-signed sample, typecheck, lint |
| `mobile> npm run i18n:review` | Regenerates `docs/NEPALI_REVIEW.md` for the native-speaker review |

### Keeping the contract in sync

After changing backend schemas, regenerate the shared contract, the TypeScript types and the mock data:

```powershell
cd sajha-kaam\backend
python scripts\export_openapi.py
python scripts\export_fixtures.py
cd ..\mobile
npm run api:types
```

## Environment variables

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `DEMO_MODE` | backend | `1` | Sample identities, fixed blind letters (Anjali = F) |
| `LLM_PROVIDER` | backend | `none` | `anthropic` to enable AI drafting; `none` uses templates only |
| `LLM_API_KEY` | backend | — | Anthropic API key. Never put it in the app. |
| `LLM_MODEL` | backend | `claude-haiku-5-5` | Small, fast model for JSON drafting |
| `LLM_TIMEOUT_S` | backend | `8` | After this many seconds, the offline template is used |
| `DATABASE_URL` | backend | `sqlite:///backend/sajha_kaam.db` | |
| `JWT_SECRET`, `SIGNING_SEED_B64`, `PUBLIC_BASE_URL`, `ADMIN_DEMO_PASSWORD` | backend | dev values | Used from Phase 4–16 (auth, signed Passport, public pages) |
| `EXPO_PUBLIC_API_URL` | mobile | — | Backend URL; unset means mock mode |
| `EXPO_PUBLIC_USE_MOCK` | mobile | — | `1` forces mock mode |

## Demo identities

All of these are fictional. The password for every sample identity is `sajha-demo`.

| Who | Role | Note |
|---|---|---|
| Ramesh K. (Sydney) | Client | Owns the seeded Dashain card (`card-dashain-posts`) |
| Claire W. (London) | Client | Café menu translation card |
| Sajha reviewer | Admin | Approves a new client's first card (`/admin`) |
| Anjali Thapa (Surkhet) | Worker | Applicant **F** in Demo mode |
| Bikash (Butwal) | Worker | Not picked: his sample is missing Nepali text |
| 9 more workers, 1 more client | | |

## Real, simulated, or needs a reviewed partnership

| Real (works today) | Simulated in the demo | Needs a reviewed partnership |
|---|---|---|
| Kaam Card drafting (AI or template), bilingual UI, board, search, blind review data | All people, cards and applications; the `DEMO · simulated` label wherever money appears | Khalti international payment requests (the worker's own Khalti account) |
| | Payment confirmation screens (Phase 4–16) | Training partners (CODE, UDAAN, EVENT-II type programmes) |

## Known limitations and assumptions

- **Every number in `config/*.yaml` is an untested assumption:** price floors, level caps, the 48-hour window, the 15-applicant limit. Validate them with real freelancers before launch.
- The offline template drafter covers social posts, video, translation, data entry and writing. Anything else falls back to the social-post template, and its clarification questions show what was assumed.
- AI data handling: personal data is stripped before any AI call. Anthropic's commercial API terms say inputs and outputs are not used for training by default. Confirm your account's retention settings before launch.
- Leak Guard (Phase 4–16) cannot read names inside images; OCR is P2.
- The signed Work Passport is *shaped like* a W3C Verifiable Credential (v2 context) and signed by Sajha Kaam with Ed25519. Full DID/VC wallet interoperability is future work. Set `SIGNING_SEED_B64` in production; locally the key is derived from `JWT_SECRET`.
- The offline Stress Test only rewrites vague words. For an item missing a number or format, it explains the problem but offers no rewrite, rather than guess one.
- Voice input is best-effort and arrives in P1.
- This is not legal advice. Get a legal review before serving EU clients.

## Build status

| Phase | Gate | Status |
|---|---|---|
| 0–4h: foundations | App runs; Nepali renders; language switch works | ✅ Verified at phone width on web and as an Android bundle. Still to do: a real-phone check in Expo Go. |
| 4–16h: backend + both roles | Backend tests 1–3 and 6–9 pass; both roles clickable | ✅ 76 backend tests pass. The whole loop was driven through the UI as client and worker (12 screenshots, no console errors). |
| 16–28h: P0 loop on a phone | Full loop on a phone, against the deployed backend, in both languages | 🟡 **Built and checked on web:** the loop for both roles, then 10 Passport, offline and draft checks (QR, private by default, public page, share link create → open → cancel, Nepali URL kept intact, offline banner, draft restored after reload). **Needs you:** deploy to Render and run it on a phone. |
| 28–36h: P1 | Public links open in app and browser | 🟡 **Done:** Fair Pick Receipt (the chain is recomputed in the browser; works over plain http too), signed Work Passport (Ed25519) with a Verify page and an on-phone check, Kaam Card Stress Test (AI, with a labelled rules fallback). Checked in the browser: 12 checks pass. **Still to do:** clarifications, Judge Mode, WhatsApp share and Hire again, deep links, Practice Challenges, voice. |
| Design: Mauri edition | New brand, icons, splash, motion, redesigned key screens | 🟡 **Done:** Mauri mascot (8 vector poses), custom SVG icon set (replaces `@expo/vector-icons`), regenerated app/adaptive/monochrome icons + splash, animated splash, ticket board cards, Kaam Path honeycomb, Passport cover, workroom stepper, Lite Mode, empty/error/offline states. Typecheck, lint and i18n checks pass. **Not yet checked on a real phone or emulator.** See `docs/BRAND.md`. |
| 36–44h: APK + rehearsal | APK installs; E2E green in NE and EN | — |

### API at a glance

- **Auth:** `/v1/auth/register|login|refresh|sample-login`, `/v1/me`
- **Client:** `/v1/cards` (create, edit, post), `/v1/cards/{id}/manage|review|attest-unacquainted|pick|reveal|extend`, `PUT /v1/reviews/{application_id}`
- **Worker:** `/v1/board`, `/v1/cards/{id}/applications`, `/v1/leakguard/scan`, `/v1/me/applications`, `/v1/me/passport`
- **Both roles:** `/v1/engagements/{id}` with `accept`, `decline`, `deliveries`, `request-revision`, `confirm`, `payment/client-paid`, `payment/worker-received` and `messages`; also `/v1/notifications`, `/v1/translate` and `/v1/cases`
- **Passport:** `/v1/me/passport`, `PATCH /v1/passport/claims/{id}`, `/v1/passport/shares`, `/v1/passport/export`, `DELETE /v1/me/data`. Public pages, no sign-in: `/p/{slug}`, `/s/{token}`
- **Proofs, no sign-in:** `/receipt/{card_id}` and `/v1/public/receipts/{card_id}`; `/verify/{claim_id}` and `/v1/public/claims/{claim_id}` (public records, or with `?s=<share token>`); `/.well-known/sajha-kaam-keys.json`. Client only: `POST /v1/cards/stress-test`.
- **Admin:** `/v1/admin/queue`, `/v1/admin/cards/{id}/decision`, `/v1/admin/cards/{id}/audit`. **Demo:** `/demo/reset`, `/demo/cards/{id}/fast-forward`

Mutations accept an `Idempotency-Key` header; the app sends a fresh one per tap.

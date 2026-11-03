# Sajha Kaam: non-negotiable rules

These rules are enforced in code and tests. If a rule conflicts with something that would look good in a demo, the rule wins.

| # | Rule | Where it is enforced |
|---|---|---|
| 1 | **No relative or contact hiring for a first job.** Every first job goes to the Kaam Board, and a client cannot name a person. "Hire again" is only for a worker the client already hired through the open process. | Card routes (Phase 4–16) |
| 2 | **Blindness is structural.** Blind review returns a separate `BlindApplicant` model with no field for name, surname, photo, gender, age, district, phone, email, Khalti link or account ID. Hidden identity never appears in props, navigation params, deep links or logs. | `backend/app/schemas/blind.py`, `backend/tests/test_blindness.py` |
| 3 | **AI never ranks, scores, rejects or selects people.** AI only drafts the Kaam Card, stress-tests it, translates between Nepali and English, writes practice briefs, and gives an optional checklist summary of a *text* sample labelled "AI summary — check yourself". | `backend/app/services/llm.py` (no scoring functions exist) |
| 4 | **Strip personal data before anything goes to an AI provider.** Use provider terms that don't train on our data. | Leak Guard runs before any AI call (Phase 4–16) |
| 5 | **Workers pay nothing, ever.** Sajha Kaam never holds money and never claims escrow. Payment happens outside the app, through the worker's Khalti payment-request link. | Card detail copy; no payment API |
| 6 | **No "verified" without a source label.** `client_confirmed_delivery`, `both_confirmed_payment` and `practice_badge` stay separate. The Work Passport is not a government ID, work permit, tax document or legal identity. | `passport.disclaimer` in both locales |
| 7 | **Data minimisation.** Collect only: display name, language and skills (worker); display name or business label and country (client); a login email that is never shown to the other party; and the worker's Khalti link at accept time. Never caste, religion, citizenship number, photo, age or gender. Workers attest they are 18 or older, and every data request states its purpose. | `models/__init__.py`, `consent.*` strings |
| 8 | **Every AI-written element carries a label:** "Made with AI" / "AI ले बनाएको". Contact details stay hidden until the card is locked. | `common.madeWithAi`, `DraftResponse.source` |
| 9 | **Everything in the demo is fictional** and labelled `DEMO · simulated` wherever money, verification or partners appear. | `DemoBanner`, seed data |
| 10 | **Game-like features reward quality, not time.** No leaderboards, streaks, points, bidding, random rewards or "come back" nudges. | Product rule |
| 11 | **Never infer caste or ethnicity from a surname.** No name-based classifier of any kind. | Product rule |
| 12 | **When a rule conflicts with "it would look cool in a demo", the rule wins.** | Everyone |
| 13 | **One mascot, Mauri, with limits.** She appears only for guidance, empty / error / offline states, onboarding, and a real confirmed step. She never scores, ranks, judges or speaks for a decision, and never appears on Blind Review scoring controls. No confetti, streaks, points or slot-machine rewards. | `components/brand/Mauri.tsx`, `docs/BRAND.md` |
| 14 | **Motion explains, never decorates.** UI motion 120–260 ms; the splash ≤ about 1 s and skippable; all motion off with reduce-motion or Lite Mode. | `lib/motion.ts` |

This is not legal advice. Get a legal review before serving EU clients and before handling real payments.

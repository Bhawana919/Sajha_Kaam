# Mauri design update: what changed

**New**
- `mobile/src/components/brand/geometry.ts`: Mauri's shapes (single source for app + icons)
- `mobile/src/components/brand/Mauri.tsx`: the mascot, 8 poses, wing flutter / hover
- `mobile/src/components/brand/Honeycomb.tsx`: `HoneycombCell`, `KaamPath`, `Stepper`, `LetterCell`
- `mobile/src/components/Icon.tsx`: 30-icon SVG set
- `mobile/src/components/AnimatedSplash.tsx`: launch sequence
- `mobile/scripts/make-icons.ts`, `mobile/scripts/render-icons.py`
- `docs/BRAND.md`, `docs/brand/*` (pose sheet, icon sheet, feature graphic)

**Changed**
- Theme tokens (honey palette, type scale, 400/600 fonts only); `Txt` Devanagari sizing
- `ui.tsx`: press-scale buttons with icons, tones incl. honey/ink, `EmptyState`, `NextAction`, skeleton loading, vector bullet marks
- `motion.tsx` / `lib/motion.ts`: `PressScale`, `Skeleton`, hex `SuccessMark`, `useMotionOK` (reduce-motion + Lite Mode)
- Screens: welcome + language choice, board (ticket cards, search icon), worker home (next step + Kaam Path; now the first tab), Passport cover + stamps, workroom stepper, blind-review letter cells, sign-in, card rows, Help (Lite Mode), offline banner, post/apply success
- Tabs: own icons with honey-hex active state; screen transitions
- `app.json`: `allowBackup: false`, paper background; `package.json`: removed `@expo/vector-icons`, added `npm run icons`
- All app icons + splash regenerated; `RULES.md` rules 13–14; README build status; `NEPALI_REVIEW.md` regenerated (new lines unticked)

**Removed**
- `mobile/scripts/make-icons.py`, `mobile/assets/brand/logo-mark.svg` (old two-cards logo)

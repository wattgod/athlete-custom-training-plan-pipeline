# Plan-Truth: fueling truth + warm-up slice

## G1

- Added `FuelingPrescription` in `athletes/scripts/fueling_policy.py` with a
  version, race target/range, total grams, training tiers, hydration,
  assumptions, and input provenance.
- `calculate_fueling.py` serializes that object to `fueling.yaml` as
  `prescription`, while retaining the legacy `carbohydrates` fields for existing
  callers.
- The policy uses duration, body mass, FTP × goal-specific intensity factor,
  goal, and tolerance. Missing tolerance is explicitly flagged and caps an
  athlete at 70 g/hr below 65 kg or 80 g/hr otherwise. Sex only creates an
  energy-availability warning; it is not a carbohydrate discount.
- The profile builder preserves intake-provided `training_fuel`, the live web
  JSON-to-markdown adapter now carries it, and the policy consumes only explicit
  plausible g/hr values (not ambiguous serving counts such as "2 gels/hour").
- Legacy `fueling.yaml` files are adapted into a prescription projection so
  regenerating an older athlete package still produces workout fuel tags.

## G2

- Removed hardcoded personalized ranges from `FUEL_TAGS` and from Nate workout
  nutrition prose. Package tags are now rendered from the serialized
  prescription tiers; the guide card reads the same prescription.
- Existing `carbohydrates` fields remain only as compatibility projections of
  the prescription. The pre-plan workout, race-day workout, coaching brief,
  guide card, and rendered archetype prose no longer originate independent
  personalized g/hr values. Static education ranges are explicitly labelled
  general guidance and cannot present themselves as the athlete's target.

## G6

- Pure steady endurance/recovery construction caps warm-up end power at the main
  steady power and enforces the repo's ZWO cooldown convention:
  `PowerHigh(end) <= PowerLow(start) <= main power`.
- Variable endurance, terrain, surge, FatMax-with-sprints, and blended sessions
  are structurally excluded, so their activation/variable segments are not
  rewritten.

## Follow-up deliberately left out

Only G1, G2, and G6 were changed. J1, G3–G5, H1, and I1–I2 remain untouched.

## G0 — PlanIR v0 skeleton

- Added a versioned `PlanIR` (`plan_ir_version: "0.1"`) with typed athlete,
  race snapshot, canonical `FuelingPrescription`, weeks/sessions/segments,
  fulfillment, and typed empty `notes`, `entitlements`, and `attachments`
  lists. It is a reflection of completed package artifacts, not a generator
  input: ZWO, fueling, and guide generation remain unchanged.
- `build_plan_ir(athlete_id)` reads `profile.yaml`, `fueling.yaml`,
  `plan_dates.yaml`, `weekly_structure.yaml`, generated `workouts/*.zwo`, and
  (when present) `fulfillment_status.json`; it writes `plan_ir.json` beside
  those artifacts. Missing or unreadable optional artifacts emit warnings and
  produce a partial IR instead of raising.
- Race provenance fields (`source`, `verified_at`, `event_year`, and
  `course_variant`) are copied only when present in current race data; H1 owns
  provenance completeness and freshness. Calendar notes, entitlements, and
  attachments are intentionally empty until G3/G4/I1 populate them. J1 remains
  the owner of `fulfillment_status.json`; G0 only reads its status.
- Extracted the preview's ZWO parser into `zwo_parser.py`. Its existing
  flattened power samples and TSS behavior are retained for the preview, while
  `parse_zwo_structure()` preserves top-level ZWO blocks as typed segments and
  retains `IntervalsT` repetitions rather than unrolling them in PlanIR.

## Verification

`pytest athletes/scripts/ -q -p no:cacheprovider` passed after the Sol review
fixes: **1136 passed, 53 skipped**. One
pre-existing pytest warning remains in `test_custom_guide.py` because that test
returns a boolean instead of asserting; no tests failed before or after this
slice.

Focused merge-gate verification: **74 passed, 4 skipped** across fueling,
artifact, compliance, steady-invariant, and ZWO-format tests. The new webhook
intake-fuel passthrough test also passes. The whole webhook module currently has
15 unrelated pre-existing failures caused by cached module-level data-directory
and environment assumptions; this slice did not change those paths.

## Commit note

The workspace sandbox permits source changes but denies writes to this linked
worktree's external Git metadata (`.../.git/worktrees/wt-plantruth/index.lock`),
so commits could not be created here. No branch was pushed or changed.

## J1 — enforced fulfillment/review state machine

- Added the stdlib-only, atomically-written and `fcntl.flock`-serialized
  fulfillment authority. Generation writes `GENERATED` or `BLOCKED_REVIEW`;
  compliance rules, unmatched A-races, and critical quality gates are recorded
  as structured blockers. Regeneration increments revision and clears approval,
  application, and confirmation records.
- Added authenticated coach transitions for `APPROVED` and `APPLIED`. A blocked
  plan requires a complete recorded waiver; application requires a platform and
  evidence. Confirmation fails closed unless `APPLIED`, sends under the
  per-athlete lock, then marks `CONFIRMED` only when mail succeeds.
- Persistent delivery copies now include the live state authority but both ZIPs
  exclude it. Coach mail uses `ACTION REQUIRED` for blocked plans and
  `REVIEW REQUIRED` for clean plans; it does not label a reviewable plan READY.

### Verification

- `pytest webhook/tests/test_fulfillment_state.py -q`: **10 passed**.
- `pytest athletes/scripts/ -q`: **1140 passed, 53 skipped**.
- Whole webhook suite still has the documented unrelated cached-data/env test
failures; the first observed pre-existing failure was stale-intake cleanup.

## G3 — descriptions render from executable segments

- Added `workout_spec.py`, which normalizes ZWO block XML into typed segments
  and derives the MAIN SET text (reps, on/off duration, and power) from them.
  Nate generation and final package rendering re-project the final/scaled XML
  into its description, so the displayed set cannot retain an old template.
- Calendar-sensitive text is derived from plan week and session/event dates.
  FTP tests carry their actual week label, and a phrase claiming "day before
  race" is converted to neutral pre-event activation unless the dates prove it.

### Verification

- Focused G3/workout tests: **224 passed, 4 skipped**.
- Full `athletes/scripts/` suite: **1143 passed, 53 skipped**.

## G5 — semantic package-consistency validator

- Added `validate_plan_package.py`, which compares the serialized fueling
  prescription, fulfillment state, race facts, PlanIR sessions, final ZWO
  segment structure, displayed interval facts, and FTP week labels against
  `plan_ir.json`. Explicit guide race-fuel/elevation claims are checked when
  present; generic education prose is intentionally excluded.
- The generator runs this gate after PlanIR assembly. Any mismatch becomes a
  structured `BLOCKED_REVIEW` issue and PlanIR is rebuilt to reflect that state;
  package generation remains non-fatal for coach recovery.

### Verification

- Focused mutation tests: **3 passed** (ZWO duration, FTP week, guide fuel,
  and guide elevation).
- Full `athletes/scripts/` suite: **1145 passed, 53 skipped**.

## G4 — recurring-session availability ledger (partial foundation)

- Added a typed ledger for multiple daily sessions, origins, slots, locked
  duration, intensity, residual capacity, total weekly load, hard-day counting,
  cap failures, and structured/free-text contradictions. Intake persists
  structured recurring sessions; the block path subtracts fixed load and keeps
  fixed hard days free of an additional prescribed session.
- This is not yet the requested Heather golden-plan implementation: fixed
  sessions are not fully materialized as PlanIR calendar sessions and the
  compliance rules do not yet aggregate their intensity count. Do not treat G4
  as complete.

## H1 / I1 / I2 — partial foundations only

- Race snapshot entries now preserve provenance fields and an edition mismatch
  becomes `RACE_STALE`; the coach brief shows available source/verification
  data. Freshness threshold, category/variant matching, and fixtures remain.
- A PlanIR-derived fulfillment manifest and a dry-run/resumable TP adapter
  scaffold exist, but no fake-server acceptance tests or J1 APPLIED read-back
  integration were completed.

## G4 — completed

- Locked recurring sessions now materialize into weekly total duration/TSS and
  multi-session day rows before compliance runs. R01/R05 count fixed hard work;
  residual per-day capacity prevents an extra prescribed workout on that day.
- PlanIR reflects locked external sessions (`origin: athlete_fixed`), and the
  ledger rejects cap impossibilities before a builder can run. Structured/free
  text conflicts produce the J1 critical review issue.
- Per-week prescribed budgets are calculated from the target *after that
  week's fixed load* (including recovery/taper multipliers), so recovery-ratio
  checks use total athlete load rather than a residual-only approximation.
- Focused acceptance: `test_availability_ledger.py` (4 passed).

## H1 — completed

- Snapshot refreshes no longer treat snapshot-build time as fact-verification
  time; provenance includes source URL/type, verification time, edition,
  variant, category and sex without overwriting same-slug championship routes.
- The race provenance gate blocks missing/stale sources, edition mismatch, and
  incompatible course category/sex. Coaching briefs show source and verification
  data for accepted records.
- Focused acceptance: race matching + ledger tests (44 passed).

## I1 — completed

- `fulfillment_manifest.json` is now a side-effect-free PlanIR projection:
  stable workout IDs/calendar dates/sport type (MTB=8), native notes, guide
  attachment, mental tasks, course entitlement, and explicit read-back counts.
- The Heather-like manifest fixture verifies the manifest without importing or
  contacting the TrainingPeaks adapter.

## I2 — completed

- The versioned TrainingPeaks adapter performs checkpointed external-ID UPSERT
  operations for workouts, notes, guide attachments, and entitlements; it sets
  sport type, supports dry-run, resumes after a failed operation, and verifies
  all objects by calendar read-back before it can transition J1 to `APPLIED`.
- Fake in-process TP-server contracts cover first apply/idempotence, resume,
  and a read-back mismatch retaining `APPROVED`. This workspace denies loopback
  socket binding, so those three tests are skipped locally rather than touching
  any live endpoint; they execute on socket-enabled CI.

STATUS: COMPLETED: G4, H1, I1, I2 | INCOMPLETE: none

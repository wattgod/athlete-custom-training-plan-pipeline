# Plan-Truth Spec — lessons from the first real fulfillment (Heather Gray)

*Author: Fable (Opus 4.8) + GPT-5.6-sol, 2026-07-14. Verified against live code.*
*Companion to `PIPELINE_HARDENING_AND_INTELLIGENCE_SPEC.md` (Jul-13). This doc
REPRIORITIZES and EXTENDS that one; it does not replace it.*

## The root cause (read this first)

The pipeline has **no canonical plan model**. It independently authors the block
schedule, the ZWO XML, the workout prose, the fueling YAML, the guide, the
coaching brief, the delivery files, and (today) the human-built TrainingPeaks
content. Those are **parallel interpretations of the athlete, not projections of
one authoritative plan** — so each artifact can be internally valid while the
delivered product is collectively false.

Heather's package proved it: four different race-fuel numbers (90 / 80-100 /
70-75 / 60-70) across the race ZWO, guide, and notes; a single workout
description carrying both a "60-90 g/hr" fuel tag and a "30-60 g/hr" nutrition
section; prose that said "0 min recovery" over an XML that was 25s/25s; openers
that always said "day before race"; a Week-8 retest labelled "Week 1/12"; a plan
that counted ~half her real training load; a stale race record (112 mi / 8202 ft
/ Heerlen) for a 75 mi / 10,171 ft Nannup race; and a "READY FOR REVIEW" email
for a plan that had, in fact, failed a critical compliance rule.

### North star: `PlanIR`

Compile the intake into **one versioned `PlanIR`** — race facts (with sources +
`verified_at`), all athlete sessions *including fixed external ones*, executable
segments, a single fueling prescription, calendar context, notes, entitlements,
attachments, and fulfillment state. **ZWO, descriptions, guide, brief, notes, and
platform payloads become serializers of that object — never independent authors.**
Invariants fall out for free: descriptions render from `segments[]`; every fuel
number references the one fueling object; weekly volume sums prescribed + fixed
external load; R01/R05 see all hard sessions; TP and Endure are adapters, not
alternate generators.

This changes hardening-spec **WS-E's direction**: structured JSON is the INPUT to
ZWO, not an output beside it. Land the platform-independent model now; Endure
migration rides on it later.

## What the Jul-13 spec got wrong / thin (given this real fulfillment)

- **B13 is too narrow → promote to P0 and rewrite as G4.** It only prevents
  prescription on an external-hard day; it does not COUNT that ride, support two
  commute legs, reserve residual capacity, adjust recovery weeks, or make
  R01/R05 see the external load. Heather's profile literally documents the lie.
- **C8 (elevation→fueling) can make the wrong carb formula more confidently
  wrong.** Fix the carb model (G1) before/with it.
- **D10 needs semantic fact comparison, not "report matches delivery" (G5).**
- **A4/C5 do not solve "flagged but shipped."** The missing piece is an enforced
  fulfillment STATE MACHINE (J1). "Flag loudly" is not a gate.
- **WS-E is premature as written.** Today's paid TP fulfillment is 100% manual
  and deserves a workstream now (I1/I2).
- **Volume-floor tuning (B9/B10) before modeling real load risks a precisely
  filled but fundamentally wrong plan.** Do G4 first.

## Nutrition caveat (correct the naive fix)

Do NOT reduce grams/hr simply because an athlete is female. Female-athlete
guidance emphasizes adequate carbohydrate availability; treat **sex as a
health/energy-availability CONTEXT input** and **gut tolerance as a hard
constraint**, and scale personalization by **body mass and absolute work rate** —
not a sex discount multiplier. (ISSN female-athlete position stand;
female dose-response work.) The Heather takeaway is "90 g/hr flat for a 61 kg
rider at 230 W is unjustified," not "women eat less."

---

## Tickets (extends the hardening spec; new IDs G/H/I/J)

Severity: P0 blocker · size S/M/L. Every ticket ships with the test named.

### J1 · Make review a real fulfillment state — `P0` · S  *(extends A4/C5)*
Files: `generate_athlete_package.py`, `intake_to_plan.py`, `webhook/app.py`,
`webhook/tests/test_webhook.py`.
Persist `fulfillment_status.json` with states `GENERATED → BLOCKED_REVIEW →
APPROVED → APPLIED → CONFIRMED`. Any critical compliance failure OR an
unmatched/stale A-race sets `BLOCKED_REVIEW`. Rename the coach email subject from
"READY FOR REVIEW" to "ACTION REQUIRED". `/api/confirm/<athlete>` MUST reject
(HTTP 409) unless status is `APPROVED`+`APPLIED`, or an explicit waiver records
{coach, timestamp, rule_ids, reason}.
**Test:** an R05 failure ⇒ `/api/confirm` returns 409, the coach email never
contains "READY", and confirm succeeds only after an approval/waiver fixture.

### G1 · Canonical fueling prescription + policy — `P0` · M  *(extends C8/D9; new model)*
Files: `calculate_fueling.py`, new `fueling_policy.py`, profile builder,
`test_calculate_fueling.py`.
Return ONE `FuelingPrescription` {race target+range, training tiers, total,
hydration, assumptions, input provenance, `policy_version`}. Inputs: duration,
expected absolute work rate, body mass, currently-tolerated g/hr, GI history,
goal, heat, gut-training status. Sex → energy-availability warning, not a
multiplier. Missing tolerated-intake ⇒ conservative ceiling + a flagged
assumption.
**Test:** Heather fixture → coach-approved band (NOT 90 g/hr); a heavier /
higher-absolute-work athlete → higher; changing only `goal_type` cannot jump to
90; target ∈ range; total = target × duration (±rounding).

### G2 · Remove every independent fuel literal — `P0` · S–M  *(builds on G1)*
Files: `constants.py` (`FUEL_TAGS`), `nate_workout_generator.py`,
`generate_athlete_package.py`, `training_guide_builder.py`, guide tests, new
`test_artifact_facts.py`.
Replace `FUEL_TAGS` values (the "60-90"/"30-60" literals) and the guide's
personalized fuel numbers with named references into `FuelingPrescription`.
Generic education ranges must be labelled "general guidance", never "your target".
**Test:** generate Heather's package; extract every personalized g/hr and
total-carb claim from all ZWO + guide + race workout + notes; assert exact
agreement with `fueling.yaml`. No personalized fuel literal originates outside the
fueling renderer.

### G3 · Descriptions render FROM executable segments — `P0` · M  *(changes E1; extends D2/D10)*
Files: new `workout_spec.py`, `nate_workout_generator.py`, `workout_mapper.py`,
`imported_archetypes.py`, `generate_athlete_package.py`, ZWO tests.
Normalize every workout to typed `segments[]` first; render XML AND the MAIN-SET
text from those segments. Calendar phrases ("day before race") derive from
session date vs event date; retest text derives from `plan_week`.
**Test:** for every archetype/level, the rendered description reproduces
reps/on-off/power from segments and round-trips to the same XML; a Week-8 test
says "Week 8"; a non-pre-race opener cannot say "day before race".

### G4 · Recurring-session availability ledger — `P0` · L  *(rewrites B13)*
Files: questionnaire schema, `intake_to_plan.py`, `block_chain.py`,
`block_builder.py`, `block_compliance.py`, weekly-structure builder, golden tests.
Support multiple sessions/day with `origin: prescribed|athlete_fixed|event|rest`,
`slot`, `duration`, `intensity`, `locked`. The builder fills residual capacity
around locked sessions; weekly targets + recovery ratios operate on TOTAL load;
compliance counts fixed hard days; a structured/free-text contradiction ⇒ blocking
review issue.
**Test:** Heather golden plan totals 12-14 h in load weeks, has two Mon/Tue/Wed
commute legs, exactly two hard days incl. Thursday, no extra Thursday workout,
Friday recovery. Impossible per-day caps fail BEFORE generation.

### G5 · Semantic package-consistency validator — `P0` · S  *(strengthens D10)*
Files: new `validate_plan_package.py`, `test_artifact_facts.py`, orchestrator.
Validate a fact registry (race/date/distance/elevation, plan-week/date,
session duration/structure, fueling, weekly volume, fulfillment status) by
extracting from each serializer and comparing to `PlanIR`.
**Test:** mutating any one guide fuel number, race elevation, FTP-test week label,
or ZWO interval duration ⇒ a named blocking failure identifying artifact + field.

### G6 · Steady-workout construction invariants — `P1` · S
Files: `nate_workout_generator.py`, `workout_mapper.py`, workout-gen tests.
For steady endurance/recovery sessions, derive warm-up end power from the main
steady segment and enforce `warmup.high <= main.high`; add cooldown monotonicity
+ nonzero-main-set checks. (Interval warm-ups may keep short activation efforts.)
**Test:** parametrize every endurance/recovery level; no warm-up finishes above
the ride body; a malformed workout fails validation.

### H1 · Race provenance, edition & freshness gate — `P0` · M  *(extends B5-B8/C10)*
Files: cross-repo race schema, `build_race_snapshot.py`, `known_races.py`,
`training_guide_builder.py`, race tests.
Preserve `source_urls`, `source_type`, `verified_at`, `event_year`,
`course_variant`, category/sex. Do NOT collapse men's/women's championship courses
into one unqualified distance. A matched A-race with stale/edition-mismatched
facts ⇒ `BLOCKED_REVIEW`, not "known".
**Test:** a 2024-Heerlen fixture requested as 2026-Nannup is rejected despite the
name match; a sourced 2026 women's Nannup record passes and its provenance shows
in the coach brief.

### I1 · Platform-independent fulfillment manifest — `P1` · M  *(generalizes WS-E)*
Files: new `fulfillment_manifest.py`, orchestrator, persistence.
Emit `fulfillment_manifest.json` {workouts, calendar dates, workout types, native
notes, attachments, mental-training tasks, course entitlement, verification
expectations}.
**Test:** Heather fixture yields the expected session/note counts, MTB type,
Friday recovery entries, guide attachment, mental tasks, and course entitlement —
without contacting TP.

### I2 · Idempotent TrainingPeaks adapter w/ read-back — `P1` · L
Files: new `delivery/trainingpeaks/`, webhook fulfillment, integration tests.
Convert the manifest to TP ops: UPSERT (not blind-append) workouts + notes, set
sport type, attach guide, apply entitlements, read the calendar back. Isolate the
undocumented endpoints behind a versioned adapter; support dry-run + resumable
op-logs. (Endpoint reference: see memory `tp-plan-build-automation` +
`heather-gray-plan-shipped` — workouts `POST fitness/v6/athletes/{id}/workouts`,
notes `POST fitness/v1/athletes/{id}/calendarNote`, MTB type=8, bearer-token via
page reload.)
**Test:** against a fake TP server, first apply creates the manifest, second
creates nothing, a partial failure resumes safely, read-back mismatch blocks
`APPLIED`. A real-sandbox acceptance test is separately gated.

## Build-first order (hand to executor now)
1. **J1** — stop shipping known-bad packages as "ready".
2. **G1 + G2** — canonical personalized fueling + kill duplicate fuel literals.
3. **G3** — segment-first descriptions (kills athlete-visible contradictions).
4. **G4** — recurring-session ledger (largest, but plans must reflect real load).
5. **G5** — semantic consistency gate (locks 1-4 together).
Then H1, I1, G6, I2. Do NOT put Endure work or more volume-floor tuning ahead of
these.

# Spec: Road (Roadie Labs) on the shared plan pipeline — "solid & shipping"

## Framing (read first — verified against live code + a GPT-5.6-sol review)

The custom training plan pipeline is **one shared, multi-brand, discipline-parameterized
engine** — NOT forked per brand. Both brands use the same checkout + webhook +
`run_pipeline()` (`webhook/app.py` create-checkout/handler, discipline threaded into
`generate_athlete_package.py:526-586`). **Do not fork the pipeline.** All work here is on
the shared engine in `athlete-custom-training-plan-pipeline`.

**What's already true (do NOT rebuild):**
- **Roadie intake is already wired.** `road-race-automation/web/training-plans-form.js:12`
  POSTs to `https://athlete-custom-training-plan-pipeline-production.up.railway.app/api/create-checkout`
  — the same shared Stripe checkout gravel uses. A Roadie order already reaches the pipeline.
- **roadielabs.com is LIVE** (HTTP 200). No go-live blocker.

**What is NOT true (the real work):**
- **Brand is NOT authoritative for discipline.** `extract_stripe_data()` briefly sets
  `discipline='road'` (`webhook/app.py:1309-1317`), but `intake_to_plan.py` rewrites
  `profile.yaml` (:3151-3159) and the only surviving signal is `discipline_default`, the
  **lowest-priority** fallback (`archetype.py:204-223`, priority: explicit profile/race
  discipline → race-name keyword → `discipline_default` → `'gravel'`). Consequence: an
  unknown Roadie race resolves `road` via the hint, but **a Roadie order for a race that
  keyword-matches gravel still resolves gravel.** The final profile retains **no brand**.
- **There is no automated TrainingPeaks fulfillment.** The pipeline only writes the manifest
  (`generate_athlete_package.py:2796-2800`); `TrainingPeaksAdapter` (`delivery/trainingpeaks/adapter.py`)
  is a standalone library exercised only by fake-server tests, never called by the webhook.
  The live contract is **coach review + manual import before confirmation**
  (`webhook/app.py:2359-2381`). Do not assume auto-fulfillment.
- **Production runs on gravel defaults.** The Railway image copies only `webhook/` and
  `athletes/` (`webhook/Dockerfile:31-32`) — root `config.yaml` is NOT in the image, so
  prod falls back to gravel defaults in `config_loader.py:109-142`. Brand config must live
  under `athletes/config/` (which IS copied) or the Dockerfile must change.

## Product context (settles the depth question)

**Roadie Labs is overwhelmingly a gran-fondo / endurance brand** — the road catalog is
dominated by gran fondo / sportive / century / hillclimb / stage events, with only a
**handful of true mass-start road races** (e.g. Superior Morgul Road Race, Purgatory Road
Race) — a tiny minority (`athletes/config/races.json`; `archetype.py:183` does recognize
`road race`/`criterium`). Gran-fondo training philosophy is **close to gravel**: long
aerobic-endurance, durability, sustained tempo/threshold, big volume, multi-hour fueling. The
genuine road differences that matter for fondos — faster/draft speeds (fueling), more
sustained climbing, pack/descending skills — are largely already handled (fueling speeds, the
road workout overlay's Threshold/G-Spot flavoring, the real Road Skills chapter). Therefore:
- **"Solid & shipping" is the right scope** — correct branding/discipline/fueling/prose on
  the shared endurance engine, not a road-training rebuild.
- **Format-aware road training (crit=anaerobic, TT=threshold, sprint) stays OUT of scope.**
  The rare true road races in the catalog will be served by the shared endurance engine — an
  imperfect but acceptable fit given their rarity; they are NOT flagged as errors. Format-aware
  depth would improve them and becomes worth revisiting only if Roadie leans into mass-start
  racing as a real segment.

Keep the full suite green (baseline: `pytest athletes/scripts/ -q` → 1163 passed, 53 skipped;
full collection 1216). Add named tests per workstream; do NOT weaken existing tests; do NOT
touch the ~15 pre-existing unrelated `webhook/tests/` failures. Use a git worktree; never
`git add -A` (concurrent committer on main).

---

## R1 — Brand/discipline config: one source of truth (do FIRST)

**Why first:** brand knowledge is split and prod runs on gravel defaults. Centralize before
adding road logic.

**Current touchpoints (all must be reconciled):** root `config.yaml` (gravel repo paths,
`from_email`), `config_loader.py:109-142` (the fallback prod actually uses),
`training_guide_builder.py:156` `BRANDS` (discipline-keyed logo/tagline — note: it is
discipline-keyed and has NO path/footer fields, correct the earlier assumption),
`webhook/app.py` brand handling + hardcoded `[GG]` email subjects + global `RESEND_FROM`,
`email_delivery.py`, guide hosting.

**Change:** create `athletes/config/brands.yaml` (under the copied dir) keyed by the EXISTING
brand keys (`gravelgod` / `roadielabs` — reuse them, don't invent) carrying: `discipline`,
`allowed_disciplines` (so Gravel God can still serve MTB), repo/guide paths, `from_email` /
`RESEND_FROM`, email subject prefix, display strings. Refactor the touchpoints above to
resolve from it. If any consumer needs root `config.yaml`, either move the needed keys under
`athletes/config/` or update `webhook/Dockerfile` to copy them — verify the value prod
actually loads, not just the repo file.

**Acceptance:** one file defines Roadie end-to-end; prod (not just repo) resolves Roadie
branding; Gravel God + its MTB path unchanged (snapshot the existing gravel guide fixture —
byte-identical). Update the structural brand tests at `webhook/tests/test_webhook.py:2440-2556`.

---

## R2 — Make brand authoritative + a loud guard (a Roadie order must never ship a gravel plan)

**Why:** brand is currently the lowest-priority hint and is dropped from the final profile,
so a Roadie order for a gravel-keyword race silently builds a gravel plan.

**Change:**
1. **Carry explicit `brand` through the whole chain** — Stripe metadata → the JSON/markdown
   questionnaire → the parsed profile (`intake_to_plan.py` build path) → persisted in
   `profile.yaml`. It is currently lost at the rewrite (:3151-3159).
2. **Detect the conflict on the CANDIDATE, then force + flag** (order matters — do not force
   first, or the guard is unreachable):
   a. Resolve discipline normally (explicit → race-name keyword → hint) — call this the
      *candidate* (`archetype.derive_discipline`).
   b. If the candidate is NOT in the ordering brand's `allowed_disciplines` (e.g. a
      `roadielabs` order whose race keyword-resolved to `gravel`, or a bad/ambiguous race),
      that is the conflict: **flag it loud** (below), THEN override the output to the brand's
      configured discipline (`road`) so the athlete still gets a correctly-disciplined plan.
   c. For a single-discipline brand (`roadielabs`), the override guarantees `road`; for a
      multi-discipline brand (`gravelgod`: gravel + MTB) a candidate within `allowed_disciplines`
      passes untouched — do NOT force a symmetric "gravel brand must be gravel" rule (it would
      break supported Gravel God MTB orders, `archetype.py:157-170`).
3. **Loud, coach-visible flag** (a J1-only blocker is NOT surfaced — the webhook infers review
   state solely from `GG_NEEDS_REVIEW=1` in stdout, emitted only when `NEEDS_REVIEW.txt`
   exists, `webhook/app.py:881-883`): on a candidate↔brand conflict, write `NEEDS_REVIEW.txt`
   AND add the J1 blocker AND emit the stdout marker — do not just throw. The plan still ships
   (road), but the coach is told the race data resolved to the wrong discipline.

**Acceptance:** extend `test_discipline_detection.py`: (a) a `roadielabs` order whose race
keyword-resolves to gravel BOTH ships a `road` plan AND surfaces the coach-visible review
flag (`NEEDS_REVIEW.txt` + stdout marker) — never a silent gravel plan; (b) a clean
`roadielabs` fondo order ships `road` with NO false review flag (the guard must not fire on
non-conflicts); (c) a `gravelgod` MTB order still builds an MTB plan with no flag; (d)
existing gravel cases green.

---

## R3 — Verify the (already-wired) road path end-to-end; scope the two cross-repo pieces

Roadie checkout already reaches the pipeline, so this is **verify + close gaps**, not build.

**Change:**
1. **Prove the wired path** produces a branded, road-disciplined, coach-deliverable plan for
   a real Roadie fondo (and a hillclimb) — end-to-end through the shared webhook →
   `run_pipeline` → package, using the in-process fakes already used by the webhook +
   `delivery/trainingpeaks` I2 tests. Do NOT contact live Stripe/TP.
2. **Worker retirement is a SEPARATE, cross-repo ticket.** The stale
   `road-race-automation/workers/training-plan-intake/worker.js` (emails + dispatches to
   `wattgod/training-plans-component`) is NOT referenced by the live form and lives in a
   **separate git repo** an executor scoped here cannot touch. File it as its own authorized
   change in `road-race-automation`; document the decision (retire vs repoint). Not in this
   repo's scope.
3. **Automated TP application is a SEPARATE cross-brand ticket** — it does not exist today
   (coach imports manually). Do not add it here unless a follow-up spec defines TP
   credentials, athlete identity, invocation point, the APPLIED approval transition, retries,
   and rollback. This spec's fulfillment target is the existing coach-review contract.

**Acceptance:** an automated test drives a Roadie order through the real shared webhook path
to a correct branded road package under the existing coach-review contract; the two cross-repo
items are filed as tracked tickets, not attempted here.

---

## R4 — Purge gravel prose/author leaks for road athletes (male AND female guides)

**The single worst leak is the confirmation EMAIL, not the guide.** `personal_email.md` is
generated with a hardcoded Gravel God signature ("— Matti / Gravel God Coaching /
gravelgodcycling.com", `intake_to_plan.py:2866`) and `/api/confirm` sends it preferentially
(`webhook/app.py:2527-2531`); the fallback TP and Endure confirmation emails are also
hardcoded (`webhook/app.py:2473`, `:2597`). So a Roadie athlete currently receives a
**Gravel-God-signed email**. Make the signature/sender brand-aware from R1.

Guide/ZWO leaks reachable on the road branch, outside discipline conditionals:
- `training_guide_builder.py:1450` packing "Bike — gravel or similar" → discipline wording.
- `training_guide_builder.py:1900` "Tire pressure ... lower for gravel: 30-40 PSI" → road (or gate).
- **Female road guide leaks** (confirmed): gravel refs at `training_guide_builder.py`
  :2680, :2744, :2763, :2817, :2835 — test the FEMALE road guide, not just male.
- ZWO `<author>Gravel God Training</author>` — brand author from R1 through **all** emitters:
  `nate_workout_generator.py:173` AND `workout_mapper.py:276` (do not miss the second path).
- Sweep `grep -ni gravel athletes/scripts/training_guide_builder.py` for anything reachable on road.
- NOTE (do not "fix"): the surface-hazards rendering is already discipline-neutral and gravel
  surface hazards are already gated (`training_guide_builder.py:1438`, `:2006`) — leave it.

**Acceptance:** generate BOTH a male and a female Roadie plan AND render the confirmation
email path; `grep -i gravel` (case-insensitive) over `training_guide.html`, `workouts/*.zwo`,
AND `personal_email.md` + the sent confirmation payload returns zero athlete-visible gravel
references / no Gravel God signature (race name excepted). Gravel fixture unchanged.

---

## R5 — One discipline-aware race-duration model; road content sanity

**Two gravel-only duration models exist and must both become discipline-aware (and share one
value):**
- `calculate_fueling.py:131` `_SPEED_BY_DISCIPLINE` (fueling — already road-aware).
- `training_guide_builder.py:21-27` `_TIER_AVG_SPEED` — **explicitly gravel**, drives the
  guide's long-ride prose. Make it discipline-aware and reuse the SAME resolved
  race-duration/speed value the fueling code uses, so the guide and fueling never disagree for
  road. Cover ALL of its call sites: `training_guide_builder.py:135-145`, `:385-390`, `:569`,
  and `generate_athlete_package.py:1056` — do not miss one and leave a road plan half-converted.

**Sanity (the "solid" bar, not format-aware depth):** road overlay
(`config/workout_selection.yaml disciplines.road`) rotates sanely; road fueling durations are
sane; the Road Skills chapter (`training_guide_builder.py:2092`, correct the earlier :2260)
renders. Note (do not build): the shared library is durability/ultra-biased — for a fondo
brand that is a DEFENSIBLE fit (fondo ≈ endurance), unlike for road racing. Reference, don't
rebuild.

**Acceptance:** guide long-ride durations and fueling durations agree for a road plan; road
skills present; no gravel-only speed model on the road path.

---

## R6 — Prove it: road E2E verification

Add a **Roadie fixture** (a fondo/hillclimb athlete on a real provenanced road race) to the
E2E harness (`~/gg-e2e/`) or a dedicated road smoke test. `validate_plan_package` (G5) passes
on the road package; guide has zero gravel leaks + correct Roadie branding. Run codex-sol
adversarially on the road package (gravel brief) — no road-brand/discipline/fueling/duration
correctness blockers (advisory prose-drift acceptable, same posture as gravel; see
`docs/PLAN_DERIVED_NARRATIVE_SPEC.md`).

---

## Order & sizing
R1 (config, incl. Docker/prod-load check) → R2 (brand authority + loud guard) → R4/R5 (prose +
duration model) → R3 (verify wired path; file 2 cross-repo tickets) → R6 (verify). Smaller than
first thought: intake is already wired, so the substance is **brand authority + config
centralization + prose/duration de-gravelling**, not intake plumbing.

## Explicitly OUT of scope
- **Format-aware road training** — unnecessary for a fondo brand (no crits/TTs). Revisit only
  if Roadie adds mass-start racing.
- **Automated TrainingPeaks fulfillment** — separate cross-brand ticket; does not exist today.
- **The road-race-automation Worker** — separate cross-repo ticket.
- **XC Ski Labs** — NOT a config port; a near-new vertical (watts→pace/HR intensity model,
  classic-vs-skate technique split = two workout tracks, upper-body/double-poling, roller-ski/
  on-snow dual-season, non-power file format). Own finding-unknowns pass + own spec after road.

---

## Implementation record — 2026-07-16

R1–R6 are implemented on `spec/road-adaptation` and ready for handoff:

- `athletes/config/brands.yaml` is the production-copied source of truth for both brands.
- Roadie brand authority, candidate-discipline conflict detection, `NEEDS_REVIEW.txt`, J1
  blocker, and `GG_NEEDS_REVIEW=1` coach marker are wired end to end without hard-failing an
  order; Gravel God MTB remains allowed.
- Athlete-facing guide, ZWO author, personal email, confirmation, fallback confirmation,
  follow-up, and legacy delivery-CLI surfaces resolve the order brand.
- Guide and fueling use the shared discipline-aware race-duration estimate, and Roadie guides
  render road equipment, tire, skills, and female-athlete copy.
- Real Roadie fondo and hillclimb fixtures exercise the shared `webhook.app.run_pipeline`
  path, package validation, branding/leak checks, compliance, quality, preview, and the
  existing coach-review fulfillment contract.
- The intentionally separate work is tracked in
  `docs/followups/ROADIE_WORKER_RETIREMENT_TICKET.md` and
  `docs/followups/AUTOMATED_TRAININGPEAKS_FULFILLMENT_TICKET.md`; neither was built here.

Verification at handoff:

- `pytest athletes/scripts/ -q` — 1180 passed, 77 skipped.
- `GG_RUN_ACCEPTANCE=1 pytest -q athletes/scripts/test_order_acceptance.py -k roadie` —
  20 passed, 4 skipped (PDF checks skip when the sandbox cannot launch Chrome; HTML remains
  required and package validation passes).
- Focused brand/road/email regression set — 25 passed, including every road-reachable
  workout rotation at every progression level.
- Two GPT-5.6-sol adversarial review passes found and closed the legacy delivery-CLI brand
  propagation gap plus five broader edges: MTB tagline preservation, rotated ZWO narrative,
  customer preview branding, profile-elevation duration parity, and brand-repository guide
  staging. Each is covered by focused or Roadie E2E regression checks.
- The pre-existing unrelated webhook failures remain outside this spec, as directed above.

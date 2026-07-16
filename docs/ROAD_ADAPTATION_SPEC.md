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

**Roadie Labs is a 100% gran-fondo / endurance brand** — 388 gran_fondo + 16 sportive +
10 hillclimb + 2 multi-stage + 1 century; **zero criteriums, road races, or time trials**.
Gran-fondo training philosophy is **close to gravel**: long aerobic-endurance, durability,
sustained tempo/threshold, big volume, multi-hour fueling. The genuine road differences that
matter for fondos — faster/draft speeds (fueling), more sustained climbing, pack/descending
skills — are largely already handled (fueling speeds, the road workout overlay's
Threshold/G-Spot flavoring, the real Road Skills chapter). Therefore:
- **"Solid & shipping" is the right scope** — correct branding/discipline/fueling/prose on
  the shared endurance engine, not a road-training rebuild.
- **Format-aware road training (crit=anaerobic, TT=threshold, sprint) is not deferred so
  much as UNNECESSARY** for a fondo brand. Only revisit if Roadie ever adds mass-start racing.

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
2. **Make brand authoritative for discipline** where the brand is single-discipline: a
   `roadielabs` order resolves `road` regardless of race-name keyword (Roadie has no gravel
   events). Keep `allowed_disciplines` so `gravelgod` (which legitimately serves gravel + MTB)
   is unaffected — do NOT do a symmetric "gravel brand must be gravel" rule (it would break
   supported Gravel God MTB orders, `archetype.py:157-170`).
3. **Loud guard:** after final discipline resolution, if the resolved discipline is not in the
   brand's `allowed_disciplines`, raise a blocking review issue — and make it **loud in the
   coach email**. A J1-only blocker is NOT surfaced: the webhook infers review state solely
   from `GG_NEEDS_REVIEW=1` in stdout, emitted only when `NEEDS_REVIEW.txt` exists
   (`webhook/app.py:881-883`). So write `NEEDS_REVIEW.txt` / emit the marker in addition to
   the J1 blocker; do not just throw.

**Acceptance:** extend `test_discipline_detection.py`: (a) a `roadielabs` order whose race
keyword-matches gravel still resolves `road`; (b) a brand↔discipline conflict produces a
coach-visible review flag (NEEDS_REVIEW surfaced), not a silent gravel plan; (c) a
`gravelgod` MTB order still builds an MTB plan; (d) existing gravel cases green.

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

Reachable on the road branch today, outside discipline conditionals:
- `training_guide_builder.py:1450` packing "Bike — gravel or similar" → discipline wording.
- `training_guide_builder.py:1900` "Tire pressure ... lower for gravel: 30-40 PSI" → road (or gate).
- Surface-hazards section (gravel-framed) → gate/reword for road.
- **Female road guide leaks** (sol-confirmed): gravel references at `training_guide_builder.py`
  :2680, :2744, :2763, :2817, :2835 — test the FEMALE road guide, not just male.
- `nate_workout_generator.py:173` ZWO `<author>Gravel God Training</author>` → brand author
  from R1, through ALL ZWO rendering paths.
- Sweep `grep -ni gravel athletes/scripts/training_guide_builder.py` for anything reachable on road.

**Acceptance:** generate BOTH a male and a female Roadie plan; `grep -i gravel` over
`training_guide.html` + `workouts/*.zwo` returns zero athlete-visible gravel references (race
name excepted). Gravel fixture unchanged.

---

## R5 — One discipline-aware race-duration model; road content sanity

**Two gravel-only duration models exist and must both become discipline-aware (and share one
value):**
- `calculate_fueling.py:131` `_SPEED_BY_DISCIPLINE` (fueling — already road-aware).
- `training_guide_builder.py:21-27` `_TIER_AVG_SPEED` — **explicitly gravel**, drives the
  guide's long-ride prose (:135-145, :385-390). Make it discipline-aware and reuse the SAME
  resolved race-duration/speed value the fueling code uses, so the guide and fueling never
  disagree for road.

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

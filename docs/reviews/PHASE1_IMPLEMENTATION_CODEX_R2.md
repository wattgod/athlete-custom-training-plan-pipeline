# Phase 1 implementation adversarial review — Codex R2

## Verdict: NO-GO

Five of the nine R1 blockers are not fully remediated. The retired delivery
CLIs and pre-worker adapter now refuse, approval and download verification are
materially stronger, legacy quarantine is authority-free, persistence no
longer reports false success, device/token behavior is fail-closed, and the
athlete-m test now runs the real generator. However, the live TrainingPeaks
driver still consumes a mutable post-approval job with no execution-time
authorization and accepts Endure/manual orders; `/api/confirm` sends sealed
artifacts without re-verifying them; the manifest validator ignores executable
top-level projection fields; and facts-omitted regeneration is undone by the
production guide builder's independent race-database lookup. In addition, the
no-intake replacement hard-fails a paid order without creating the durable
`STATE_UNAVAILABLE` quarantine required by B4, and the release seal omits the
named `plan_ir.json` transitional artifact.

Review basis: static inspection of commits `2fcaf25`, `8d49613`, `7f85b7c`,
and `71bf433` after R1 baseline `52dc75e`, the complete resulting production
paths, their regression tests, the r9 specification, and the remediation
notes. I did not trust the notes as evidence. Per the task constraint, I did
not run the socket-dependent/full suite. The human-reported result (2341
passed, 94 skipped, 0 failed) is recorded only as externally supplied and is
not an independent claim of this review.

## R1 blocker dispositions

| # | R1 blocker | Disposition | Code and regression evidence |
|---|---|---|---|
| 1 | Executable release/apply bypasses | **PARTIAL** | The old package and email entry points return before writes (`athletes/scripts/deliver_package.py:37-52`; `athletes/scripts/email_delivery.py:408-425`), the old adapter raises before I/O (`delivery/trainingpeaks/adapter.py:71-79`), and no-intake no longer invokes `--deliver` (`webhook/app.py:1618-1633`). Their regressions call the production entry points (`athletes/scripts/test_phase1_bypass_gates.py:22-60`; `athletes/scripts/test_trainingpeaks_adapter.py:69-77`). The TP CLI also removed local bypass and checks live order/athlete/revision/seal/manifest SHA at job emission (`tools/tp_apply_order.py:209-249,452-481`). But it never requires `delivery_platform == trainingpeaks`, and the server's APPLIED transition also accepts a platform different from immutable state (`webhook/fulfillment_state.py:652-660`). More fundamentally, the emitted `apply_job.json` contains no order/revision/seal/digest (`tools/tp_apply_order.py:295-342`), and the network-writing driver accepts that mutable object without any live authorization check (`tools/tp_apply_driver.js:496-508`). A job generated while approved remains executable after regeneration, seal revocation, or reassignment; an approved Endure/manual order can produce and record a TrainingPeaks apply. Tests mock the status response and stop at job emission (`tools/test_tp_apply_order.py:330-418`); none exercises the actual driver consumer, revocation-after-emission, or platform mismatch. This remains contrary to S1/S2/B1 and D4 (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:107-134,135-190,338-352,875-895`). |
| 2 | Seal enforcement, immutability, and TOCTOU | **PARTIAL** | Approval now verifies under the state lock and persists `SEAL_MISMATCH` (`webhook/fulfillment_state.py:597-651`); same-revision persistence refuses a sealed state/directory (`webhook/app.py:1949-1984`); and download serves the verified open descriptor (`webhook/fulfillment_state.py:505-564`; `webhook/app.py:2634-2662`). Regressions cover approval mutation, descriptor replacement, persistence replacement, and the real download route (`webhook/tests/test_fulfillment_state.py:194-226`; `athletes/scripts/test_phase1_bypass_gates.py:63-150`). But APPLIED transition performs no seal verification (`webhook/fulfillment_state.py:652-660`), and `/api/confirm` checks only status/legacy before reading `personal_email.md` and guide files directly (`webhook/app.py:2950-3020,3118-3155`) and sending the attachment (`webhook/app.py:3230-3233`). Mutation after APPROVED/APPLIED can therefore be sent to the customer and marked CONFIRMED without materializing `SEAL_MISMATCH`. No regression attacks confirmation. This violates S2's every-consumer rule and B1's release-artifact gate (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:172-190,338-352`). |
| 3 | Schema-v1 quarantine completeness and authority | **FIXED** | Historical v1 layout was one direct athlete directory under `DELIVERIES_DIR`; startup scans that layout, migrates write-new/verify/tombstone-old, records all ledger candidates, and repairs lookups (`webhook/app.py:1809-1893,4815-4822`; `webhook/fulfillment_state.py:699-782`). Every state transition and confirmation primitive rejects `legacy` even after binding (`webhook/fulfillment_state.py:597-603,672-688`); status advertises `release_authorized: false` (`webhook/app.py:2863-2904`); `/api/confirm` rejects it (`webhook/app.py:2950-2961`); and the TP gate rejects `legacy` (`tools/tp_apply_order.py:225-230`). Production-function regressions cover shadowed lookup/startup migration, preserved APPLIED evidence, status, confirmation, binding, and post-binding transition refusal (`athletes/scripts/test_phase1_bypass_gates.py:153-205`; `webhook/tests/test_fulfillment_state.py:240-265`). |
| 4 | Double persistence failure reported as success | **FIXED** | `_execute_plan_job` attempts normal persistence, then quarantine persistence, converts an empty result into `success: false`, sends only the failed-order notice, and records `failed` (`webhook/app.py:2349-2406`). The authenticated full-flow endpoint likewise requires non-empty persistence before success (`webhook/app.py:4092-4139`). The regression fault-injects the persistence boundary while exercising the real `_execute_plan_job` orchestration and asserts the failure notice/job (`webhook/tests/test_webhook.py:2987-3016`). It does not inject two successive exceptions, but the same production branch handles both an exception and no durable return; static flow no longer reaches success with `persisted` false. |
| 5 | Final PlanIR/`tp_manifest` validation and altitude schema | **PARTIAL** | The pipeline now rewrites PlanIR/manifest before a second read and validation of final disk bytes (`athletes/scripts/intake_to_plan.py:3537-3564`), and altitude uses the same production metadata fields/threshold as the guide (`athletes/scripts/post_render_validator.py:362-376`; `athletes/scripts/training_guide_builder.py:225-256`). Session projection fields/order and expected counts are compared (`athletes/scripts/post_render_validator.py:105-152`). The tests cover one session-title mutation and a production-shaped altitude object (`athletes/scripts/test_post_render_validator.py:137-160`). But executable top-level manifest projections are not compared: `plan_title` is merely non-empty, `athlete` is ignored, and only `race.date` is checked; `race.name` and `race.priority` are ignored (`athletes/scripts/post_render_validator.py:115-152` versus projection owner `athletes/scripts/plan_ir.py:645-665`). Mutating any of those same-count fields passes validation and changes the plan the TP CLI creates (`tools/tp_apply_order.py:320-335`). The claimed “every TrainingPeaks projection field” fix and its regression are therefore incomplete under C2 (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:427-452`). |
| 6 | `COURSE_UNRESOLVED` facts-omitted remediation | **PARTIAL** | `build_profile` now retains athlete date/distance while omitting matched elevation, courses, variant, category, and race metadata for multi-course records, and `course_facts_mode` clears the blocker (`athletes/scripts/intake_to_plan.py:993-1052,3133-3139`). The test reaches production `build_profile`/blocker assembly and checks those keys (`athletes/scripts/test_intake_to_plan.py:101-145`). It does not run production generation. The shipping guide builder unconditionally resolves the race database again by name (`athletes/scripts/training_guide_builder.py:3706-3760,3973-3978`), then flattens database distance, gain, location, terrain, climate, and metadata into `race_data` (`athletes/scripts/training_guide_builder.py:3980-4014`) without consulting `course_facts_omitted`. Thus a facts-omitted regeneration can still put matched-record facts into the guide. The intake builder also retains database `location` and `discipline` on the omitted profile (`athletes/scripts/intake_to_plan.py:1063-1069`), with discipline consumed by workout/guide selection. The remediation does not satisfy S4/C2's “plan/guide rebuilt from athlete-supplied facts only” rule (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:207-218,420-425,1121-1128`). |
| 7 | Unknown device tokens | **FIXED** | Parsing splits only comma/newline, uses normalized text only for vocabulary lookup, and retains the trimmed original casing/interior spaces for unknowns (`athletes/scripts/intake_to_plan.py:536-575`). Unknown evidence is serialized and produces one required confirmation each (`athletes/scripts/intake_to_plan.py:1508-1514,3150-3157`). Tests exercise production profile and blocker assembly and assert exact strings (`athletes/scripts/test_intake_to_plan.py:66-98`). The webhook and SKU sources use form value/`unknown`, not fabricated devices (`webhook/app.py:1578-1580`; `tp-skus/generate_skus.py:80-82`). |
| 8 | Token fail-closed and operational revocation | **FIXED** | Both issue and verify reach `_keyring`, which rejects absent/invalid audience keys with no `CRON_SECRET`/literal fallback (`webhook/download_tokens.py:43-92,95-134,150-199`). The durable locked jti/kid store is used by verification (`webhook/download_tokens.py:137-147,196-232`), and an authenticated rate-limited route writes it (`webhook/app.py:2779-2802`). Regressions cover missing configuration on both issue and verify, old token rejection, scope binding, per-link/key revocation, and the real Flask revocation endpoint (`webhook/tests/test_download_tokens.py:44-137`). |
| 9 | Athlete-m deterministic production replay | **PARTIAL** | The central R1 defect is repaired: the test supplies the literal questionnaire/frozen snapshot to real `webhook.run_pipeline`, which invokes the subprocess intake and package generator, then reads production profile/fueling/calendar/PlanIR/state and runs real persistence/download/approval behavior (`athletes/scripts/test_athlete_m_phase1.py:56-181`). Expected blocker data is never generation input, and it separately proves the field test, Sunday VO2, race entry, and counted race week (`athletes/scripts/test_athlete_m_phase1.py:95-126`). However, the checked-in calendar is a hand-selected projection, not “the generated plan-dates output itself”: `_plan_dates_golden` drops day descriptors, flags, workout prefixes, and other generated fields (`athletes/scripts/test_athlete_m_phase1.py:26-47`; `tests/fixtures/athlete_m/expected/plan_dates.json:1-15`). A regression in omitted calendar semantics can pass. This is narrower than the exact deterministic calendar-golden obligation at `docs/SPEC_TRUSTWORTHY_FULFILMENT.md:1003-1041`, although it no longer stubs a production stage. |

## New blockers found in R2

### N1. Missing intake is now an unrecoverable paid-order failure, not a durable block

`run_pipeline` labels missing intake as `fulfillment_state: unavailable` but
also returns `success: false` (`webhook/app.py:1623-1633`). `_execute_plan_job`
only calls `persist_deliverables(..., state_unavailable=True)` inside
`if result['success']` (`webhook/app.py:2349-2386`), so this exact path creates
no order-scoped state or `STATE_UNAVAILABLE` blocker; it marks the job failed
and requires manual recovery (`webhook/app.py:2402-2406`). The Stripe regression
actually codifies `pipeline_failed` while describing the result as
“quarantined,” but never asserts a quarantine exists
(`webhook/tests/test_webhook.py:821-849`). This closes the executable bypass by
turning a recoverable missing questionnaire into an order-killer. It violates
B4's required synthetic non-waivable quarantine and the repository's binding
order-safety rule (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:397-402`).

### N2. The release seal omits a named transitional validator artifact

`plan_ir.json` is emitted and is one of C2's two named Phase 1 validator
artifacts, but it is absent from `PRIVATE_DELIVERABLES`
(`webhook/app.py:1757-1769`). Persistence copies only the declared lists plus
workouts (`webhook/app.py:1994-2017`), then seals the copied revision
(`webhook/app.py:2037-2039`). Consequently the approved release manifest cannot
prove which PlanIR was paired with the sealed `tp_manifest.json`, and the
artifact needed to audit the validator decision is discarded from order
authority. This violates the Phase 1 S2 rule to hash every emitted artifact and
the rollout's “seal over transitional artifacts” requirement
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:172-184,427-430,1093-1099`). Athlete-m
does not assert that both named inputs appear in the release manifest.

### N3. Endure/manual authorization can be spent on TrainingPeaks

The status endpoint returns immutable `delivery_platform`
(`webhook/app.py:2884-2900`), but `check_approval_gate` ignores it
(`tools/tp_apply_order.py:209-249`), and APPLIED transition records caller
`platform` without comparing it to state (`webhook/fulfillment_state.py:652-660`).
An APPROVED Endure order can therefore emit the live TP driver job and later be
recorded APPLIED on TrainingPeaks. This is not the permitted Phase 1 behavior
of preserving the Endure target while performing zero platform push, and it
reintroduces the forbidden silent TP fallback in D4/R9 condition 11
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:875-895`;
`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R9.md:126-133`). No platform
mismatch appears in the apply-gate parameterized regression
(`tools/test_tp_apply_order.py:378-388`).

## R1 non-blocking findings: recorded dispositions

1. **Skipped tests — unchanged/deferred.** The archetype sentinel skip and
   optional/Phase 2+ skips remain. The human supplied 2341/94/0 result, but this
   review did not verify which skips ran or execute socket tests.
2. **Stale Endure branches — still present.** `_attempt_endure_delivery` and
   skipped old flow/confirm classes remain (`webhook/app.py:2270-2319`;
   `webhook/tests/test_endure_delivery.py:545-546,759-760`). The normal Phase 1
   job has no caller to the push helper, which preserves the R1 conforming
   disable. The new cross-platform TP authorization in N3 is release-blocking,
   not merely stale test debt.
3. **Missing negative tests — only partially resolved.** New tests cover many
   R1 cases, but there are still no production-consumer negatives for mutated
   confirmation attachments/body, apply-job mutation or revocation after
   emission, delivery-platform mismatch, top-level manifest drift,
   facts-omitted full guide generation, durable no-intake quarantine, or
   PlanIR inclusion in the seal.
4. **Property tests — accurately deferred.** F3 still uses four deterministic
   duration vectors rather than generated properties
   (`athletes/scripts/test_tp_polyline.py:62-75`). No static implementation
   regression was found.
5. **Later-phase statuses — fixed.** Schema validation now accepts only the
   Phase 1 statuses and rejects `APPLYING`, `APPLIED_ATTESTED`, and `CANCELLED`
   (`webhook/fulfillment_state.py:21-34,106-138`;
   `webhook/tests/test_fulfillment_state.py:229-237`). Constants remain defined
   but grant no state authority.
6. **Manual athlete-keyed generation — acceptable only as a draft path.** It
   still writes local athlete-keyed state, but the legacy delivery/email/adapter
   entry points refuse. This remains non-blocking provided it never becomes an
   authoritative manual-order release path.

## No-regression check for R1 conforming items

- **S6 source-scoped blocker merge:** no static regression; production intake
  and post-render callers still use separate source namespaces
  (`athletes/scripts/intake_to_plan.py:3470-3476,3542-3548`), and the merge
  preserves other sources/rejects stale revisions
  (`webhook/fulfillment_state.py:299-346`).
- **D4 pre-approval Endure network disable:** the normal job path still never
  calls `_attempt_endure_delivery`; the active Endure-target regression runs
  `_execute_plan_job` and asserts zero POST (`webhook/tests/test_endure_delivery.py:637-658`).
  N3 is a separate TP fallback hole after approval.
- **F2 fueling truth:** no static regression in the plan-derived alignment or
  guide canonical-target validator. Athlete-m now traverses the full guide and
  asserts exact labels (`athletes/scripts/test_athlete_m_phase1.py:84-126`).
- **F3 polyline:** implementation was untouched after R1; cumulative time,
  clamping, and monotonic fixed cases remain.
- **F6 weeks mismatch:** production blocker assembly still compares paid weeks
  excluding W00, and athlete-m obtains the exact mismatch through production
  (`athletes/scripts/intake_to_plan.py:3140-3148`).
- **F7 intel stats:** the bounded `hours`, rejected `limit`, multi-month read,
  and deterministic ordering path was not changed by remediation; its route
  regression remains at `webhook/tests/test_webhook.py:2779-2820`.

I found no archetype-ID, race-category, workout-catalog, or methodology-policy
renegotiation in these commits. The remediation did add production environment
test seams (`GG_FIXED_NOW` and `GG_RACE_SNAPSHOT_FIXTURE`) and a client-carried
`course_facts_mode`. Those do not by themselves weaken the settled rules, but
the latter is currently the only remediation trigger and the former snapshot
override should remain explicitly test-only operational configuration. The
material scope concern is the partially hardened legacy TP browser driver: it
continues to perform real Phase 5-style writes during a Phase 1 release without
the later worker's execution-time authorization, quiescence, or platform
binding.

## Unverifiable items

1. I did not execute the full or socket-based suite and make no independent
   pass/skip claim. The human-reported 2341 passed, 94 skipped, 0 failed result
   cannot prove missing negative cases.
2. I did not execute the browser driver or any live TrainingPeaks, Endure,
   Gmail/Resend, Stripe, WooCommerce, Railway, or SMTP action. Driver findings
   follow its explicit call graph and payload contract.
3. I could not verify live filesystem permissions prevent mutation of revision
   files. The implementation must enforce correctness even when files are
   writable, and current confirmation/apply consumers do not.
4. I did not verify deployment token keys or revocation-store persistence on
   Railway; checked-in issue/verify behavior is fail-closed when configuration
   or the store is unavailable.
5. I did not inspect the external `gravel-god-training-plans` polyline copy or
   live race/guide data directories; both remain outside this Phase 1 code
   review.

In summary, the verdict remains **NO-GO**. The remediation made real progress
and fully closes legacy quarantine, false-success persistence, device parsing,
and token security, but “blocked means blocked” is still not an end-to-end
invariant: mutable or cross-platform TP jobs can execute, confirmation can send
unverified bytes, manifest truth is incomplete, facts-omitted data can be
rehydrated into the production guide, and missing intake produces no durable
blocked state. Phase 1 should not ship until those consumers and production-path
negative tests are closed and the full named transitional artifact pair is
sealed.

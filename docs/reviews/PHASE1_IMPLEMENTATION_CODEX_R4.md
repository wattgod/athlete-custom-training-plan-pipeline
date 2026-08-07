# Phase 1 implementation adversarial review — Codex R4

## Verdict: GO

The two R3 release blockers are closed. Every checked-in invocation boundary for
the transitional TrainingPeaks browser path now refuses before it can emit or
execute an apply job, and the retained status/capability infrastructure has no
reachable remote-write consumer. Endure cannot enter APPLIED or CONFIRMED while
disabled, including through a claimed manual platform, while a genuinely manual
order can still record its Phase 1 attestation without gaining access to the
TrainingPeaks confirmation route. I found no new Phase 1 blocker and no
regression of an item fixed in R1–R3.

Review basis: I treated
`docs/reviews/PHASE1_IMPLEMENTATION_NOTES.md` as claims, not evidence; reviewed
the complete resulting tree and commits `4301d5b`, `102bd89`, and `67b54c7`
against R3 baseline `921d9be`; re-read the normative Phase 1 sections and R9
conditions; searched all repository references and entry points; and ran two
focused non-socket selections. They produced **129 passed** and **313 passed,
29 skipped**. The supplied external full-suite result remains **2357 passed, 86
skipped, 0 failed**; I did not independently rerun that complete suite.

## R3 item dispositions

| R3 item | R4 disposition | Evidence |
|---|---|---|
| **B1 — transitional TP driver residual** | **FIXED** | `build_apply_job`, `print_runbook`, and `_run_job_mode` unconditionally raise the same Phase 1 disable error (`tools/tp_apply_order.py:225-229,313-314,321-322`). Normal CLI dispatch reaches `_run_job_mode` after read-only package parsing and therefore cannot request status, write `apply_job.json`, or print a runbook (`:376-422`). The JS file throws at its first statement, before its IIFE can install globals, intercept credentials, call the live gate, or reach any TP fetch (`tools/tp_apply_driver.js:1-16`); the production-shaped Node regression proves no network/global side effect (`tools/test_tp_apply_order.py:422-434`). The alternative Python adapter still raises before its historical write body (`delivery/trainingpeaks/adapter.py:71-80`). Repository-wide search found no other apply-job emitter or executable consumer. Current operational docs say the driver is disabled and manual UI application is the interim procedure (`docs/HANDOFF_CUSTOM_PLAN_FULFILMENT.md:152-161`; `docs/TP_API_REVERSE_ENGINEERING.md:8-13`); no current runbook advertises executing it. |
| **N4 — disabled Endure false advance** | **FIXED** | APPLIED rejects if either the requested or immutable platform is Endure, before release verification or application mutation (`webhook/fulfillment_state.py:653-681`). The exact R3 route attack returns 409 and leaves `APPROVED`/`application: null`; confirmation then returns 409 before artifact/email construction and performs zero sends (`athletes/scripts/test_phase1_bypass_gates.py:318-368`; `webhook/app.py:3058-3077`). A separate replay using `platform:"manual"` against the approved Endure state was also refused with the same D4/R9 guard and left the state unchanged. `write_generation` makes delivery platform immutable across revisions (`webhook/fulfillment_state.py:223-242`), so regeneration cannot relabel Endure as manual. A true manual order may record APPLIED evidence, but `/api/confirm` rejects every non-TrainingPeaks platform before copy construction/send (`webhook/tests/test_fulfillment_state.py:234-265`; `athletes/scripts/test_phase1_bypass_gates.py:371-399`). |

## Re-attack of the changed surface

- The hard-disabled Python job path stops before its retained approval helper;
  direct calls to both construction helpers also fail. Receipt mode can validate
  historical evidence and record the already-authorized TrainingPeaks APPLIED
  transition, but it cannot build or run a browser job. That is equivalent to
  the allowed Phase 1 manual/attested TP path, not a remote-write path.
- The retained status and live-gate endpoints are authenticated/read-only and
  issue a five-minute, release-bound capability only for a sealed APPROVED
  TrainingPeaks order (`webhook/app.py:2868-3012`). With both checked-in remote
  writers stopped before I/O, the capability cannot itself mutate TP. Token
  verification now rejects non-object claims, malformed base64/Unicode, missing
  or mistyped `iat`, excessive lifetime, and `exp == now`
  (`webhook/app.py:2810-2832`; focused regressions at
  `athletes/scripts/test_phase1_bypass_gates.py:224-249`).
- Confirmation still verifies the complete release manifest before selecting a
  guide. The fixture now seals PDF and HTML, and mutation of the selected PDF,
  unselected HTML, or personalized body produces 409, zero sends, and durable
  non-waivable `SEAL_MISMATCH`
  (`webhook/app.py:3082-3130`; `athletes/scripts/test_phase1_bypass_gates.py:402-447`).
- The retired `generate_guide` helper now shares the production facts-omitted
  predicate and skips both catalog loading and date cross-reference
  (`athletes/scripts/training_guide_builder.py:297-307,341-363`). The shipping
  builder continues to use the same predicate before catalog access (`:3995-4013`).

## New blockers

None.

## No-regression check

| Previously fixed surface | R4 result |
|---|---|
| **R1 B1 legacy delivery/email/adapter bypasses** | No regression. The package CLI returns before copying/publishing/sending (`athletes/scripts/deliver_package.py:37-52`), the email CLI returns before loading artifacts (`athletes/scripts/email_delivery.py:408-428`), and the adapter raises before its historical apply body (`delivery/trainingpeaks/adapter.py:71-80`). The TP driver is now closed more strongly. |
| **R1 B2 seal enforcement and immutable revision serving** | No regression. Approval and APPLIED still verify under the state lock and materialize mismatches; same-revision sealed persistence remains refused; downloads/confirmation use verified descriptors (`webhook/fulfillment_state.py:608-681`; `webhook/app.py:1971-1989,3082-3130`). |
| **R1 B3 schema-v1 quarantine** | No regression. Startup migration remains write-new/verify/tombstone-old; legacy state is authority-free before and after binding; ambiguous athlete lookup does not select an order (`webhook/app.py:1828-1899`; `webhook/fulfillment_state.py:724-818`). |
| **R1 B4 / R2 N1 state failure and missing-intake quarantine** | No regression. No durable persistence forces the job failure path; a durable `STATE_UNAVAILABLE` quarantine alone is treated as a successful blocked workflow (`webhook/app.py:2280-2356`). |
| **R1 B5 / R2 B5 final PlanIR and TP projection validation** | No regression. The validator still compares all TP top-level and ordered session projection fields and exact counts, and retains date, schedule, fueling, and altitude checks (`athletes/scripts/post_render_validator.py:105-165,266-397`). |
| **R1 B6 course facts omitted** | No production regression. Intake retains only athlete-supplied planning facts for an unresolved multi-course target, and both guide entry points now honor the durable omission signal (`athletes/scripts/intake_to_plan.py:1000-1091`; `athletes/scripts/training_guide_builder.py:297-307,3995-4013`). |
| **R1 B7 device truth** | No regression. Form-source handling, comma/newline vocabulary parsing, verbatim unknown evidence, and required confirmations remain present (`athletes/scripts/intake_to_plan.py:536-575,1260,1570,3172-3180`). |
| **R1 B8 typed download tokens** | No regression. Missing keys fail closed; scope, revision, time, jti/kid revocation, and the authenticated operational revoke route remain enforced (`webhook/download_tokens.py:43-232`; `webhook/app.py:2729-2752`). |
| **R1 B9 / R2 B9 athlete-m gate** | No regression. The test still runs production generation, compares the complete emitted calendar golden, asserts the literal blocker/confirmation sets and surfaces, and seals both PlanIR and TP manifest (`athletes/scripts/test_athlete_m_phase1.py:33-167`). It passed in the focused run. |
| **R2 N2 PlanIR seal coverage / N3 platform binding** | No regression. `plan_ir.json` and `tp_manifest.json` remain private sealed deliverables (`webhook/app.py:1762-1775,2012-2044`); immutable platform equality remains enforced, with the new Endure refusal stronger than R3. |
| **S6, F2, F3, F6, F7** | No regression. Source-scoped blocker merge, plan-derived fueling labels, unrounded/clamped polyline, weeks mismatch, and bounded multi-month intel stats remain intact. Their focused validator/intake/fueling/polyline tests passed. |

No archetype ID, race mapping, plan catalog, workout catalog, methodology
policy, or scheduling contract was changed by the R3-closure commits.

## Non-blocking findings

1. **The retired guide helper has one defensive edge left.** In its
   facts-omitted branch, `target_race.get('distance_miles', race_distance)` can
   fall back to `derived.race_distance_miles` if a malformed/manual legacy
   profile omits the key (`training_guide_builder.py:341-348`). Production
   facts-omitted profiles always create the key, the shipping builder has no
   fallback, and repository search found no production order caller of this
   helper, so this does not reopen B6. Using only
   `target_race.get('distance_miles')` would make the retired helper strictly
   fail-closed too.
2. **Platform enforcement for confirmation is at the route boundary, not the
   generic primitive.** `confirm_after_send` checks legacy/status but not
   `delivery_platform` (`webhook/fulfillment_state.py:697-721`). Its only
   production caller is `/api/confirm`, which performs the platform guard first,
   so no current bypass is reachable. Phase 5's E2 typed-evidence replacement
   should keep platform/evidence validation inside the locked primitive rather
   than rely on caller ordering.
3. **Historical driver source remains deliberately present.** The top-of-file
   throw makes the checked-in JS inert, and current docs label the remaining
   body as migration evidence. It should remain non-exposed until D0 parity is
   proven, then be removed at the later cutover; its mere retained source is not
   a Phase 1 release path.

## Unverifiable items

1. The sandbox cannot run socket tests. I ran 442 focused tests with 29 skips;
   the complete 2357/86/0 result is human-supplied.
2. I did not execute a live browser, TrainingPeaks, Endure, Stripe,
   WooCommerce, Railway, Resend, or SMTP action. No live-platform claim is
   needed for a hard-disabled Phase 1 write surface.
3. I could not verify deployed secrets, proxy/CORS policy, revocation-store
   durability, persistent-volume permissions, or deployed code/version parity.
   Checked-in missing-secret and mutation behavior fail closed.
4. I did not verify the external `gravel-god-training-plans` polyline copy;
   the spec explicitly tracks it as a non-gating cross-repo follow-up.

## Remaining standing conditions and phase owners

**No condition remains on the Phase 1 gate.** The R9 rollout conditions below
remain mandatory before their later surfaces are enabled; this GO does not
authorize them early.

1. **Phase 2 — review authority:** implement S3/C1/C2/C4, including the
   authenticated review page, typed value snapshots, credential provenance,
   resolution policy, and a complete seal-bound page approval.
2. **Phase 3 — truthful model and offline apply contract:** implement A1/A3 and
   D0, generate/enforce the exact `apply_contract/v1` schema, pass HR/LTHR/HRmax/
   RPE and first/subsequent positional fixtures, and prove fake-server migration
   parity. The historical JS remains non-exposed until parity and is removed at
   cutover.
3. **Phase 4 — read-only worker evidence:** implement the zero-write D1/D2
   probe/inspection worker, capability validation, identity binding and account
   confirmations, the Phase 4 athlete-m golden, and the scheduled live read-only
   canary.
4. **Phase 5 — mutation safety:** implement and prove D1/D3 authorization,
   lease/fencing/quiescence, intent/journal/effective-inventory reconciliation,
   supersession, every kill point, rollback/compensation, F4/F5, and controlled
   live TP write/readback evidence. Endure remains disabled unless it
   independently satisfies the same gate and never silently falls back.
5. **Phase 5 — release and confirmation:** implement the in-state S5 outbox,
   deterministic/private/revocable guide release, Gmail draft creation, typed
   provider/manual evidence with reviewed deviations, and a confirmation
   primitive that never sends to the athlete.
6. **Phase 5 — rollout proof:** complete one controlled real order through
   generated → reviewed → approved → applied → readback-verified → guide
   released → Gmail-drafted → coach-sent → provider-verified CONFIRMED. Continue
   the non-waivable course-facts safeguard until the tracked `courses[]` work
   lands, retain the external polyline follow-up, and keep the accepted TP ToS
   exposure recorded as business risk rather than technical assurance.

## Summary

Phase 1 now satisfies “blocked means blocked” across every reachable Phase 1
surface reviewed here. Blocked or unsealed orders cannot expose executable
artifacts, the transitional TP emitters and consumers are inert, Endure cannot
be advanced or customer-confirmed under any accepted Phase 1 platform label,
and the legitimate manual path cannot borrow TrainingPeaks copy. The remaining
work is the explicitly later-phase model, worker, reconciliation, release, and
provider-evidence machinery listed above; none is required to justify the
Phase 1 hard-disable closures.

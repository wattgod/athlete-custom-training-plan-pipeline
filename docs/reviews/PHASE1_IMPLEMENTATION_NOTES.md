# Phase 1 implementation notes — review round 2 closure

## Baseline and review disposition

- This closure starts from R2 review commit `d3106d7` and treats
  `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` as normative.
- Every PARTIAL residual and new blocker in
  `docs/reviews/PHASE1_IMPLEMENTATION_CODEX_R2.md` was factually accurate.
  No finding is rebutted.
- The de-identified task brief is retained as `.codex-phase1-fix2-brief.md` so
  the requested scope remains auditable with the implementation commits.

## Required finding dispositions

1. **B1 residual + N3 — fixed: apply jobs are release- and platform-bound.**
   `apply_job.json` now embeds `order_id`, `athlete_id`, immutable
   `delivery_platform`, `generation_revision`, `model_seal`,
   `release_manifest_digest`, and the sealed `tp_manifest.json` SHA-256. The
   builder refuses incomplete bindings. The authenticated status endpoint
   issues a five-minute HMAC capability bound to those exact values only for
   an APPROVED, seal-verified TrainingPeaks order. The browser driver refuses
   missing fields, calls the live server gate before any TrainingPeaks request,
   and calls it again after duplicate inspection immediately before the first
   POST. The live endpoint re-verifies current artifact bytes, approval,
   status, legacy flag, platform, revision, seal, manifest digest, and TP
   manifest digest. Regeneration, mutation, expiry, reassignment, or status
   revocation therefore kills an emitted job. `check_approval_gate` requires
   `delivery_platform == "trainingpeaks"`; APPLIED rejects a caller platform
   different from immutable state. Production regressions cover regeneration
   and seal mutation after emission, cross-platform refusal, missing driver
   bindings, and the driver's no-TP-write behavior after gate revocation.

2. **B2 residual — fixed: APPLIED and confirmation re-verify the seal.**
   APPLIED performs the same full release-manifest verification as APPROVED
   while holding the state lock and materializes non-waivable `SEAL_MISMATCH`
   on failure. `/api/confirm` requires approval/current-release equality,
   verifies the entire manifest, and reads `personal_email.md`,
   `intake_backup.json`, and the selected guide attachment through verified
   open descriptors. It passes captured guide bytes to the sender rather than
   reopening a mutable path. A mismatch is persisted as `SEAL_MISMATCH` and
   the send is never attempted. Real-route regressions mutate both the email
   body artifact and guide after APPLIED and assert 409, zero sends, and
   durable non-waivable quarantine.

3. **B5 residual — fixed: every executable top-level TP projection is
   validated.** The post-render validator derives projection truth with the
   same rules as `plan_ir.project_tp_manifest` and compares `plan_title`,
   `athlete`, `race.name`, `race.date`, and constant `race.priority`, in
   addition to the complete ordered session projection and expected counts.
   A parameterized regression mutates each top-level field without changing
   session count and requires `PostRenderValidationError`.

4. **B6 residual — fixed: facts-omitted survives production guide
   generation.** Multi-course intake no longer falls back to database name,
   date, distance, location, or discipline for an omitted target. It retains
   athlete-supplied name/date/distance; discipline is retained only when
   explicitly derivable from the athlete's discipline/category/format input,
   otherwise the existing generic discipline path handles workout selection.
   The target records `course_facts_omitted` and normalized
   `course_facts_mode`. The shipping guide builder recognizes either signal,
   skips both race-data resolution and date cross-reference, and constructs
   `race_data` only from retained athlete facts. A fixed-clock production
   intake/package/guide replay seeds distinctive database distance, gain,
   location, terrain, climate, metadata, hazard, and discipline values and
   proves none appears in the profile target or rendered guide.

5. **B9 residual — fixed: athlete-m uses the complete calendar golden.** The
   hand-selected JSON projection was deleted. The fixed-clock production run
   regenerated `tests/fixtures/athlete_m/expected/plan_dates.yaml` directly
   from emitted `plan_dates.yaml` (328 lines). The gate compares the complete
   parsed structure, including all top-level naming metadata, every week/day
   descriptor, recovery/race flags, and workout prefixes. An explicit
   `GG_UPDATE_ATHLETE_M_GOLDEN=1` path reruns the same production generation
   before replacing the golden; no expected artifact is generation input.

6. **N1 — fixed: paid missing-intake orders quarantine durably.**
   `_execute_plan_job` now treats `fulfillment_state == "unavailable"` as a
   persistence-required outcome even when generation returned false. It
   creates the order-scoped revision/state with non-waivable
   `STATE_UNAVAILABLE`, sends the BLOCKED REVIEW coach notice, records the job
   succeeded as a durable workflow outcome, and never exposes a release
   artifact. Missing review-token configuration suppresses the link and logs
   loudly without destroying the quarantine. Stripe (both prior duplicate
   regressions) and Woo production handlers now assert durable
   `BLOCKED_REVIEW`; the Stripe job asserts `succeeded`, not `failed`.

7. **N2 — fixed: `plan_ir.json` is sealed.** It is a private deliverable copied
   into every order revision before transitional release finalization. The
   athlete-m production gate reads the actual release manifest and asserts
   both `artifacts/plan_ir.json` and `artifacts/tp_manifest.json` are present.

8. **R2 non-blocking finding 2 — fixed now: stale Endure execution surfaces
   removed.** `_attempt_endure_delivery`, its now-unused profile loader, the
   confirm-time Endure/invitation customer-email branch, and the two skipped
   legacy flow/confirm test classes were deleted. Phase 1 still preserves an
   Endure order's immutable target and performs zero platform push. The Endure
   module's mapping/transport code and health telemetry remain later-phase
   implementation, but no Phase 1 job or confirmation path calls them.

## R2 findings already fixed in R1 remediation

- **B3 legacy quarantine:** unchanged and still authority-free after binding.
- **B4 double persistence:** unchanged; no durable state still means failure.
- **B7 device evidence:** unchanged; unknown tokens remain verbatim required
  confirmations.
- **B8 download tokens:** unchanged; issue/verify remain fail-closed and
  revocable.

## Other R2 non-blocking finding dispositions

1. **Skipped tests.** The eight obsolete Endure-flow skips were deleted. The
   remaining 86 skips are opt-in acceptance, external-fixture/submodule,
   optional dependency, platform, and socket tests. Per the task, socket tests
   remain for the human environment rather than being claimed here.
2. **Stale Endure branches.** Closed in required disposition 8 above.
3. **Missing negative tests.** Closed for every R2 residual: driver missing
   binding, live revocation/regeneration, live seal mutation, platform
   mismatch, APPLIED seal mutation, confirm body/attachment mutation, all five
   TP top-level fields, production facts-omitted regeneration, durable no-
   intake quarantine, and both named sealed validator inputs.
4. **Property tests.** Still accurately deferred. F3 retains deterministic
   boundary vectors; no requested finding or implementation change requires a
   Phase 1 property-test expansion.
5. **Later-phase statuses.** Remains fixed: schema v2 accepts only Phase 1
   authority statuses and rejects `APPLYING`, `APPLIED_ATTESTED`, and
   `CANCELLED`.
6. **Manual athlete-keyed generation.** Remains a draft-only path. The release,
   email, and legacy adapter entry points still hard-fail, and order-scoped
   state remains the only authority.

## Verification

- Focused authority/artifact/order-safety selection: **132 passed**, 456
  deselected.
- Complete sandbox suite: `pytest -q` → **2357 passed, 86 skipped**, 21 existing
  warnings, 0 failures.
- `python3 -m compileall -q athletes/scripts delivery tools webhook` passes.
- `git diff --check` passes.
- Socket/live TrainingPeaks, Endure, Stripe, Resend, Railway, and browser tests
  were not run in the sandbox and remain human/live-environment checks.

## Commits

1. `6c30547` — Close Phase 1 release authority gaps.
2. `7847c6a` — Enforce Phase 1 artifact and course-fact truth.
3. `067259a` — Pin full-fidelity athlete-m production replay.
4. `2d3de32` — Align quarantine regression and apply documentation.
5. This notes/task-brief update (required final commit).

No push was attempted.

## Deferred Phase 2+

Review UI/catalog, the full apply-contract worker and lease/quiescence model,
durable outbox, guide publishing, provider evidence/readback reconciliation,
and re-enabling Endure remain gated by their own rollout phases. The Phase 1
live browser gate is a narrowly scoped safeguard for the retained transitional
driver; it does not implement Phase 4/5 worker machinery.

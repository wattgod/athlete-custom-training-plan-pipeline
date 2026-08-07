# Phase 1 implementation notes

## Baseline and review disposition

- The remediation started from adversarial review commit `52dc75e` and treats
  `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` as normative.
- All nine review blockers were factually accurate. No finding is rebutted.
- The pre-existing untracked `.codex-phase1-fix-brief.md` is the de-identified
  task brief. It contains no customer data and is included in the intended
  final commit set rather than deleted.

## R1 blocker dispositions

1. **Release/apply bypasses — fixed.** The athlete-keyed package and email
   scripts and the pre-worker TrainingPeaks adapter now hard-fail before any
   write or network operation. The no-intake webhook fallback no longer calls
   `generate_full_package.py --deliver`. `tp_apply_order.py` has no bypass
   flag and requires live, authenticated equality across order id, athlete id,
   revision, model seal, approval seal/manifest binding, release authorization,
   and the exact local `tp_manifest.json` SHA-256. Receipt transitions repeat
   the same gate. Production-path regressions cover every retired entry point
   and mismatched apply binding.

2. **Seal enforcement and TOCTOU — fixed.** Approval verifies the release
   manifest against current bytes while holding the state lock. A failed check
   revokes authority and durably merges non-waivable `SEAL_MISMATCH`.
   Persistence refuses to replace or delete a sealed same-revision directory;
   corrections require `write_generation`. Downloads hash and serve the same
   open descriptor. Download and status verification failures also persist
   `SEAL_MISMATCH`. Regressions mutate bytes before approval, after approval,
   during descriptor replacement, and before an actual download request.

3. **Schema-v1 quarantine — fixed.** Startup scans every legacy athlete-keyed
   v1 file, migrates with write-new/verify/tombstone-old ordering, records all
   ledger candidates without inference, and repairs lookups. Lookup examines
   legacy state before trusting a newer v2 projection, closing repeat-customer
   shadowing. Preserved legacy status is evidence only: authenticated status
   reports `legacy: true` and `release_authorized: false`; transition,
   `confirm_after_send`, `/api/confirm`, and the apply consumer refuse it even
   after manual binding. Regeneration is required to regain authority.

4. **False success — fixed.** `_execute_plan_job` marks a job succeeded and
   emits a success notice only after durable normal or quarantine persistence.
   If both fail (or persistence returns no record), it marks the job failed and
   sends only the operator failure notice. The authenticated test-full-flow
   endpoint follows the same rule. Former tests that treated an empty
   persistence result as success now require durable-state-shaped persistence
   or assert failure.

5. **Transitional artifact validation — fixed.** The post-render validator
   compares every TrainingPeaks projection field and ordering between PlanIR
   and `tp_manifest.json`, so equal-count semantic drift fails. Generation
   rebuilds PlanIR/manifest first, rereads the final disk bytes, and validates
   only after the last rewrite. Altitude reads production
   `target_race.race_metadata.start_elevation_feet/avg_elevation_feet`, matching
   the guide trigger; total course gain cannot trigger it. Tests include an
   equal-count title mutation and a production-shaped altitude snapshot.

6. **Unresolved course facts — fixed.** Multi-course matches retain identity
   and provenance but omit every matched-record course fact, including gain,
   variants, course rows, category, and race metadata. Questionnaire distances
   such as `75 miles` are now parsed as athlete facts rather than silently
   falling back to the headline database course. A facts-omitted regeneration
   mode clears `COURSE_UNRESOLVED` while keeping database course facts absent.
   The regression builds both states through `build_profile`.

7. **Unknown device tokens — fixed.** Comma/newline splitting trims token
   boundaries while retaining unknown-token casing and interior spacing.
   Unknowns remain verbatim in profile evidence and each produces a required
   `DEVICE_UNKNOWN_CONFIRM_N` item. The regression asserts both exact strings.

8. **Token fail-closed and revocation — fixed.** Token issue/verify refuses on
   first use unless `DOWNLOAD_TOKEN_KEYS` or `DOWNLOAD_TOKEN_SECRET` is set;
   neither `CRON_SECRET` nor `dev-secret` is a signing fallback. An
   authenticated, rate-limited operational endpoint revokes a real issued jti
   and/or kid in the durable revocation store. Tests do not globally seed
   keys, and explicitly cover missing configuration, old month-HMAC rejection,
   typed scope binding, per-link/per-key revocation, and endpoint revocation.

9. **Athlete-m production golden — fixed.** The gate feeds the literal
   questionnaire and frozen race snapshot through the real webhook intake
   adapter, `intake_to_plan.py`, date calculator, package generator, PlanIR and
   manifest builders, final validator, blocker assembly, sealing, and bundle
   persistence under `GG_FIXED_NOW`. No expected file is generation input and
   no blocker list is handcrafted. The literal `expected/phase1.json` is
   unchanged. The checked-in calendar is compared with production
   `plan_dates.yaml`; the gate separately proves the 2026-08-05 W00 start, one
   Week 1 HR field test, Sunday VO2 mismatch, race-day entry, and at least
   three counted race-week sessions.

## Non-blocking findings

1. **Skipped tests.** The full suite still contains opt-in acceptance,
   external-fixture, optional dependency/submodule, platform, and socket tests.
   Phase 1 regressions themselves run locally. Socket tests remain for the
   human run outside the sandbox, per the task; broad optional-fixture cleanup
   is unrelated to the nine blockers.
2. **Stale Endure branches.** Phase 1 keeps Endure network delivery disabled.
   The active target-preservation test now requires durable persistence and
   proves zero Endure network calls. Later-phase Endure mapping/retry branches
   and their skipped tests remain deferred rather than being presented as
   Phase 1 release authority.
3. **Missing negatives.** Added production regressions for no-intake and all
   legacy consumers, apply binding mismatch, missing token configuration,
   legacy tokens, real revocation, approval/download seal mutations, final-byte
   manifest drift, production altitude schema, course-fact omission and
   regeneration, verbatim unknown devices, quarantine confirmation/status,
   startup/shadow migration, and persistence failure.
4. **Property tests.** Deterministic boundary and production-replay tests now
   cover the reviewed failure modes. General property/fuzz expansion remains a
   later hardening task and is not used as evidence for this gate.
5. **Later-phase statuses.** Fixed now: schema-v2 validation accepts only
   Phase 1 statuses (`GENERATED`, `BLOCKED_REVIEW`, `APPROVED`, `APPLIED`,
   `CONFIRMED`) and rejects `APPLYING`, `APPLIED_ATTESTED`, and `CANCELLED`.
6. **Manual athlete-keyed pipeline.** Standalone generation may still use an
   athlete label for local draft production, but it cannot release: every
   legacy delivery/apply consumer hard-fails, and the authoritative webhook
   generation root and persisted state are order-scoped. Building later-phase
   worker behavior was intentionally not pulled into Phase 1.

## Verification

- Focused blocker/authority suite: **513 passed, 29 skipped**.
- First complete run after remediation: **2339 passed, 94 skipped**, with one
  stale Endure assertion found and corrected.
- Final complete suite: `pytest -q` → **2341 passed, 94 skipped**, 21 existing
  warnings. Socket-based tests are intentionally left to the human environment.
- `python3 -m compileall -q athletes/scripts delivery tools webhook` and
  `git diff --check` pass.

## Commit limitation

The requested commit grouping is prepared as: (1) release authority/seals and
quarantine, (2) artifact/input truth and token security, (3) deterministic
athlete-m gate, and (4) this notes update. In this managed sandbox `.git` is
read-only: `git commit` cannot create `.git/worktrees/trustworthy-fulfilment/index.lock`
(`Operation not permitted`). No push was attempted. If that filesystem policy
remains in force, the exact commit commands and dirty-tree status are reported
in the handoff instead of claiming a clean committed tree.

## Deferred Phase 2+

Review UI/catalog, apply-contract worker, durable outbox, guide publishing,
provider evidence/readback reconciliation, and re-enabling Endure remain gated
by their own rollout phases. No later-phase functionality was added to satisfy
Phase 1.

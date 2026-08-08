# Phase 2 implementation notes — review round 2 closure

Date: 2026-08-08

Normative basis: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` r9 and
`docs/reviews/PHASE2_IMPLEMENTATION_CODEX_R2.md`. The review was factually
correct; no rebuttal was required. Phase 1 controls remain in force.
TrainingPeaks/Endure application, provider readback, guide release, Gmail
drafting, and all other Phase 3+ work remain disabled or out of scope.

## Round 2 blocker dispositions

### 1. Residual query-token GET authentication — closed

- `GET /api/download/<order_id>` no longer reads `request.args['token']` for
  any artifact. Customer-bundle typed capabilities are accepted only in the
  `Authorization: Bearer` header (with `X-Cron-Secret` retained for operator
  use).
- The GET endpoint rejects `review_bundle` before resolving state or verifying
  a capability. The revision-bound, CSRF-protected
  `POST /review/<order_id>/bundle` is now the only review-bundle fetch path.
- The request-target redaction filter remains defense in depth for rejected
  old links and scanners. It recognizes literal `token` and single-pass
  percent-encoded spellings such as `%74oken` and `t%6fken`; it is installed
  on the application, Werkzeug, and Gunicorn access loggers.
- Production-route regressions prove valid header, literal-query, and
  percent-encoded-query review-bundle bearers all receive 401 on GET. A valid
  customer capability in a query string also receives 401, while the same
  capability in `Authorization` reaches the unchanged approval/seal gate.

### 2. Seal-mismatch approval provenance — closed

- Seal-mismatch supersession still creates a new unsealed `BLOCKED_REVIEW`
  revision with a non-waivable `SEAL_MISMATCH` finding and clears all current
  approval, waiver, application, confirmation, and seal authority.
- Before clearing authority, the transition deep-copies the complete prior
  approval into `superseded_approvals[]`, together with the waiver,
  application, confirmation, prior status/revision, seal metadata, mismatch
  reason/message, and supersession timestamp. Each record is explicitly
  `authoritative: false` and is schema-validated as historical evidence.
- `approval_matches_release` remains based solely on the current top-level
  seal-bound approval. A superseded record cannot authorize a release or a
  later action. The archive survives subsequent `write_generation` calls.
- The authenticated page renders archived confirmations, typed values,
  dispositions, waiver, credential, and digest only under “Superseded approval
  history,” labeled “Historical evidence only” and “non-authoritative.” It
  never renders the archived decision as Approved and exposes no application
  action for the superseded revision.
- The production regression approves distinct typed blocker/confirmation
  values with a waiver through the real page, mutates the sealed review ZIP,
  triggers supersession through the session bundle route, reloads state, and
  proves the exact snapshot, dispositions, waiver reason, credential, catalog
  digest, and seals remain recoverable without authority. A focused state test
  also proves application and confirmation evidence are retained.

## Round 1 controls retained

- Approval remains bound to the exact complete rendered catalog through the
  server-recomputed `review_catalog/v1` digest and
  `approval_snapshot/v2`. Catalog mutators still reject sealed revisions.
- Page success remains derived only from `approval_matches_release`, not a
  status label. Incomplete, stale, legacy-version, or seal-mismatched approval
  snapshots do not render as Approved or expose download/later actions.
- Review sessions remain revision-bound, CSRF-protected, short-lived,
  no-store, and revalidated against parent jti/kid revocation on every use.
  Review-bundle token issuance remains capped at five minutes even though GET
  no longer consumes those typed tokens.
- Generation email review links remain fragment-carried and exchange into an
  opaque server session; no bearer is emitted in a request query string.
- Phase 1 customer-bundle approval gating, scoped capability verification,
  exact open-descriptor seal verification, platform disables, and
  customer-safe failure behavior were not weakened.

## Regression coverage and verification

Production-path coverage now includes:

- valid literal and percent-encoded query bearer rejection on GET;
- review-bundle header bearer rejection on GET and sole session-POST success;
- percent-encoded request-target redaction and logger topology;
- valid customer query bearer rejection plus Authorization-header acceptance;
- seal-mismatch supersession through the authenticated bundle route;
- full value-bearing approval/waiver provenance recovery and history-only page
  rendering; and
- preservation of prior application and confirmation evidence without current
  authority.

Verification results:

- Final named encoded-query/seal-provenance regression selection: **8 passed**,
  60 deselected.
- Focused state/review regression run: **53 passed**.
- Focused state/review/Phase 1 bypass plus compile/diff checks: **68 passed**.
- Reviewer's focused Phase 1/2 set (state, review, download-token,
  review-auth, athlete-m, bypass, Endure, webhook): **330 passed**, 18 warnings.
- Complete sandbox suite: `python3 -m pytest -q --disable-warnings
  --maxfail=20` → **2,398 passed, 86 skipped, 21 warnings, 0 failed**.
- `python3 -m py_compile` passed for every changed Python module and test.
- `git diff --check` passed.
- Socket-dependent tests remain for the human to run outside the sandbox, per
  the task instruction.

## Commit boundaries

1. Close both Round 2 blockers with production changes and focused regressions:
   remove review-bundle GET/query-token authentication and preserve
   seal-mismatch approval provenance as non-authoritative history.
2. Document Round 2 closure and final verification results (this file,
   committed last).

The sandbox denied Git index creation at the real worktree metadata path
(`.git/worktrees/trustworthy-phase2/index.lock: Operation not permitted`). No
files were staged or committed, and no push was attempted. The pre-existing
untracked `.codex-phase2-fix2-brief.md` was not modified or included. The tree
is intentionally left dirty for the human to commit using the boundaries
above.

## Remaining live Phase 2 gate

After the human socket tests and rereview, deploy with the existing typed token
configuration (or explicit review keyring), run one real paid order without a
non-waivable blocker, and have a human coach inspect the bundle and approve.
Retain evidence that:

- `approval.snapshot_version == "approval_snapshot/v2"`;
- `approval.review_catalog_digest == state.review_catalog_digest`;
- the approval credential begins `review-link:`;
- approval revision and both seal fields equal current state; and
- `approval.confirmations` contains one complete entry and persisted
  disposition for every `review_items` entry.

Stop at APPROVED. All automated application and later release work remains
behind its later phase gate.

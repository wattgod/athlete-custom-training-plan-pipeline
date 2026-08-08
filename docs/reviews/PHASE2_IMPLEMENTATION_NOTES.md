# Phase 2 implementation notes — review round 1 closure

Date: 2026-08-08

Normative basis: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` r9 and
`docs/reviews/PHASE2_IMPLEMENTATION_CODEX_R1.md`. Phase 1 controls remain in
force. TrainingPeaks/Endure application, provider readback, guide release,
Gmail drafting, and all other Phase 3+ work remain disabled or out of scope.

## Round 1 blocker dispositions

### 1. Exact rendered-catalog approval binding — closed

- `review_catalog_digest` is the SHA-256 digest of canonical JSON containing
  `review_catalog/v1` plus the complete ordered `review_items` array. State
  stores the current digest, the page embeds it, and the operator endpoint
  requires it.
- `transition(..., APPROVED)` requires the digest and an explicit decision
  list. Under the state lock it rebuilds the authoritative catalog, recomputes
  the digest, compares it with `hmac.compare_digest`, and only then evaluates
  decisions and copies values. The compatibility branch that synthesized
  verified-fact decisions was removed.
- Successful approvals use `approval_snapshot/v2`, persist
  `review_catalog_digest`, and copy each complete reviewed catalog entry plus
  its disposition. The snapshot therefore preserves message, typed value,
  display unit, source, basis, sensitivity, revision, policy fields, and the
  actual disposition.
- `set_generation_blockers` and `merge_generation_blockers` reject any sealed
  state and require `write_generation`. A detected artifact/seal mismatch no
  longer edits the sealed revision's catalog: it supersedes that generation
  into a new unsealed `BLOCKED_REVIEW` revision, clears all release authority,
  and records the non-waivable `SEAL_MISMATCH` regeneration requirement.
- Production-route regressions change a required confirmation's value and,
  separately, a blocker's message/value without changing id or revision after
  render. Both submissions return 409 and persist no approval. Success coverage
  proves the submitted digest is persisted in the approval.

### 2. Authority-derived page state — closed

- Page success is derived only from `approval_matches_release`, never from a
  status label. This predicate requires a current, non-legacy, seal-bound,
  `approval_snapshot/v2` snapshot whose digest and complete copied entries
  match the current catalog.
- A release-like status without authority renders `APPROVAL NOT AUTHORITATIVE`
  and the loud remediation: “Approval not authoritative —
  regenerate/re-approve.” It exposes no approval form, bundle download, or
  application/later-phase action.
- A valid approval renders `approval.confirmations`—the persisted snapshot—not
  live `review_items`, including each persisted disposition.
- Production page-route regressions cover a missing snapshot entry, changed
  value, changed type, approval seal-field mismatch, and old snapshot version.
  Every case renders remediation and never renders the Approved success or a
  later action.

### 3. Revocation cascade and bearer hygiene — closed

- The page and generation email no longer place a review-bundle bearer in a
  query string. The page downloads through a CSRF-protected POST using the
  existing opaque review session; every fetch rechecks parent jti/kid
  revocation and session expiry.
- Typed review-bundle tokens remain for non-page compatibility. When derived
  from a review credential they carry `parent_review_jti` and
  `parent_review_kid`; verification checks the shared durable revocation store
  for both child and parent. The download route also accepts an Authorization
  bearer so new callers need not use a query string.
- Every review-bundle token, derived or standalone, is capped at five minutes.
  Customer-bundle token TTL and approval gating are unchanged.
- Both the same-session bundle response and typed review-bundle response set
  `Cache-Control: no-store, max-age=0`, `Pragma: no-cache`, and
  `Referrer-Policy: no-referrer`.
- Legacy query-token compatibility remains, so application-managed webhook and
  Werkzeug loggers install a request-target filter that replaces the token
  value with `[REDACTED]`.
- Production-route regressions prove a previously valid derived token returns
  401 after its parent review jti is revoked, the same-session POST also dies
  after parent revocation, successful bundle responses are no-store, and the
  derived lifetime is no more than 300 seconds.

## Non-blocking findings and rotation item

1. **Producer metadata — cheap production cases addressed; generic fallback
   deferred.** The cited availability, brand, quality-gate, compliance,
   state-unavailable, validator-crash, and package-consistency producers now
   provide explicit typed values, factual bases, and sensitivities. Seal and
   v1-quarantine findings do too. `_review_item` still retains its compatibility
   synthesis for older/generic producers not enumerated in round 1. Removing it
   globally is deferred because it would turn an unconverted diagnostic into a
   paid-order hard failure; a separate producer inventory/migration should
   precede making all metadata fields structurally mandatory. This does not
   weaken digest binding: synthesized entries are still included verbatim in
   the rendered catalog digest and approval snapshot.
2. **Side-effectful review GET — closed.** Authenticated and unauthenticated
   review GET use an explicit order-id-only resolver. They cannot invoke legacy
   migration or write lookup/tombstone state. A route regression proves a v1
   athlete-path file is byte-for-byte unchanged after GET.
3. **State approval footgun — closed.** `review_decisions=None` no longer
   synthesizes confirmations. All approval callers and fixtures now submit
   explicit decisions and the exact catalog digest.
4. **End-to-end value traversal — closed for the requested cheap coverage.**
   The deterministic athlete-m production replay now proves values created by
   the real intake assembler and post-render validator survive generation,
   persistence, sealing, review-session exchange, and page rendering. The
   smaller route fixture continues through successful approval and reload.
5. **Key precedence divergence — closed.** `review_auth.py` now matches
   `download_tokens.py`: typed `DOWNLOAD_TOKEN_KEYS` take precedence over the
   legacy `DOWNLOAD_TOKEN_SECRET` during rotation. Coverage configures both and
   proves the typed current coach kid wins.

## Phase 1 and scope disposition

- Complete approval snapshots, release/application gates, customer-bundle
  gating, typed token scope, artifact descriptor verification, and all Phase 1
  platform disables remain enforced.
- Seal mismatch handling is stronger: authority is cleared and the failed
  sealed generation is superseded instead of receiving an in-place catalog
  edit.
- No canonical power model, D0 worker contract, browser worker, provider
  readback, automated apply, guide release, or Gmail evidence path was enabled.
- No live Stripe, Railway, TrainingPeaks, Endure, Resend, SMTP, or browser
  action was performed.

## Regression coverage and verification

Production paths cover:

- exact catalog digest success and confirmation/blocker drift rejection;
- sealed catalog-mutator rejection and seal-mismatch revision supersession;
- missing, changed, stale, legacy-version, and seal-mismatched approval
  snapshots on the authenticated page;
- persisted snapshot dispositions on the authoritative page;
- operator digest requirement and wrong-digest rejection;
- same-session POST download, CSRF, no-store headers, parent revocation, derived
  token revocation, five-minute TTL, and application log redaction;
- scanner-safe GET without legacy migration; and
- real athlete-m intake/post-render values through persistence and page render.

Verification results:

- Focused state/review/token/auth run: **70 passed**.
- Phase 1 bypass + athlete-m + webhook/endure integration run: **255 passed**.
- Complete sandbox suite: `pytest -q --disable-warnings --maxfail=20` →
  **2,393 passed, 86 skipped, 21 warnings, 0 failed**.
- `python3 -m py_compile` passed for all changed production Python modules.
- `git diff --check` passed.
- Socket-dependent tests remain for the human to run outside the sandbox, per
  the task instruction.

## Commit status and intended boundaries

The sandbox denied Git index creation at the real worktree metadata path:
`.../.git/worktrees/trustworthy-phase2/index.lock: Operation not permitted`.
Nothing was staged or committed, and no push was attempted. The untracked
`.codex-phase2-fix-brief.md` was not modified or included.

Intended local commit boundaries for the human:

1. **Harden Phase 2 review authority and bearer handling** — state/catalog
   digest and snapshot v2, authority-derived rendering, session POST bundle,
   parent token revocation, TTL/cache/log controls, and all corresponding
   production-route/Phase 1 fixture updates.
2. **Add explicit metadata to Phase 2 finding producers** — availability,
   brand, quality, compliance, package consistency, state-unavailable,
   validator-crash, seal-mismatch, and quarantine metadata plus athlete-m
   traversal coverage.
3. **Document Phase 2 review round 1 closure** — this file, committed last.

## Remaining live Phase 2 gate

After human socket tests and rereview, deploy with the existing typed token
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

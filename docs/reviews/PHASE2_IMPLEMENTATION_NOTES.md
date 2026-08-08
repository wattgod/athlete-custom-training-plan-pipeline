# Phase 2 implementation notes — review surface

Date: 2026-08-07

Normative basis: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` r9, especially S3,
C1, C2, C4, and the Phase 2 rollout gate. Phase 1's reviewed controls remain
in force; the TrainingPeaks browser driver, Endure writes, and all Phase 3+
worker/apply/release machinery remain disabled or unimplemented as assigned.

## Per-item disposition

1. **S3 review-item catalog — implemented.** Schema-v2 state now carries
   `review_catalog/v1`: a server-rebuilt, revisioned catalog covering every
   blocker, required confirmation, soft confirmation, and the verified order
   and release-seal facts needed for a meaningful clean-order review. Each
   item stores a JSON-native canonical value plus `value_type`, display unit,
   source, basis, sensitivity, message, revision, and any server-owned
   resolution choices. Catalog equality is validated on state load; duplicate
   item ids, non-JSON values, empty provenance, and unknown sensitivity labels
   fail closed.
2. **Approval snapshot with values — implemented.** `approval_snapshot/v1`
   copies every cataloged value into `approval.confirmations`, with item id,
   typed value, disposition, and revision. It also records the approving
   credential, revision, model seal, and release-manifest digest. The server
   never accepts a value from the form or operator request. Release authority
   now requires a complete snapshot whose ids, values, types, and revisions
   still equal the current catalog; a pre-Phase-2/incomplete approval cannot
   authorize a download or APPLIED transition.
3. **C1 review page — implemented.** `/review/<order_id>` renders the required
   order: header, blockers, required confirmations, soft confirmations,
   verified facts, and the post-approval application status. The page provides
   waiver controls only for waivable blockers, remediation copy instead of a
   control for non-waivable blockers, explicit acknowledgements, and a typed-
   token review-bundle download. After approval it displays the persisted
   sealed result. Later-phase apply/readback/draft controls are intentionally
   not enabled; the page says they remain behind their rollout gates.
4. **C2 surface — implemented.** Current intake and post-render findings now
   supply structured reviewed values for race matching/provenance, estimated
   FTP, unresolved course, weeks mismatch, unknown devices, race-week/session
   date rules, scheduling, fueling, carbohydrate targets, and altitude. Older
   or generic structural findings still receive a canonical string value from
   their server-generated message, so no blocker or confirmation can disappear
   from the catalog.
5. **C4 authentication — implemented.** Review links are signed for one order,
   athlete, revision, `review` action, and coach audience, with `kid`, `jti`,
   issued-to label, and a maximum/default seven-day TTL. The bearer is placed
   in the URL fragment, which is not sent in HTTP URLs, access logs, or Referer
   headers. Static bootstrap code POSTs it to a session exchange. That exchange
   creates an opaque 12-hour server-side session under `DATA_DIR`, stored mode
   0600, and sets an HttpOnly/SameSite=Strict cookie (Secure in production).
   Every request rechecks expiry and jti/kid revocation. GET performs no audited
   action; approval requires a CSRF token. Provenance is honestly recorded as
   `review-link:<kid>:<jti>-<issued-to>`, while the existing authenticated curl
   path records `operator-secret` and must submit the same revisioned catalog
   decisions.
6. **Policy enforcement — implemented in the state authority.** Exact waiver
   coverage and a nonempty reason are required; non-waivable ids are recomputed
   from server policy and rejected even when submitted in a complete waiver.
   Every required confirmation and verified fact must be resolved for the
   current revision, soft confirmations are snapshotted as confirmed or
   unconfirmed, unknown/duplicate/wrong-revision ids are rejected, and only
   server-declared `resolved:<choice>` values are legal. Seal verification runs
   under the state lock before the approval is committed; a mismatch becomes a
   durable non-waivable `SEAL_MISMATCH` blocker.
7. **Phase 2 athlete-m page gate test — implemented.** The deterministic route
   test reads the checked-in de-identified `athlete_m/intake.json` values,
   creates a dedicated remediated review revision, performs fragment-link login
   → durable session → authenticated page → typed review download → waiver and
   required confirmation → APPROVED, then reloads state and proves the complete
   value-bearing snapshot matches the catalog and both seal fields. The exact
   Phase 1 athlete-m production replay remains unchanged and blocked by its two
   non-waivable findings; the page test does not waive or delete those controls.

## Security and failure-path decisions

- The webhook's existing Flask stack is retained; no framework or dependency
  was added.
- Data-derived HTML is escaped server-side. The page embeds no JSON and uses no
  `innerHTML`. The only script is static login bootstrap code protected by a
  per-response CSP nonce; the authenticated page permits no script. Review
  responses set `Cache-Control: no-store`, `Pragma: no-cache`, and
  `Referrer-Policy: no-referrer`.
- An unauthenticated GET always receives a generic shell containing no order,
  athlete, state, blocker, artifact, or existence information. The session
  exchange also returns a generic failure.
- The page never opens artifact files directly. Its review download uses the
  existing typed, order/revision/audience-bound token route and the existing
  verified open-descriptor seal check.
- Review signing can use explicit `REVIEW_TOKEN_KEYS` / `REVIEW_TOKEN_SECRET`.
  For a no-dead-link rollout, it can also derive a domain-separated review key
  from the already-required Phase 1 download-token secret/keyring and honors
  its current coach `kid`. Missing keys fail closed.
- Review sessions remain valid only while their original signing `kid` exists;
  rotating a key out or using the existing jti/kid revocation endpoint ends the
  session.
- State/catalog corruption, missing durable state, missing seal, typed-token
  failure, stale session, CSRF failure, and seal mutation all fail closed. None
  turns the pipeline job into a customer-visible failure or enables a release.

## Required negative regression coverage

Production routes now cover:

- approval with a missing required confirmation;
- a waiver that omits one blocker;
- a waiver containing a non-waivable blocker;
- a stale revision/session;
- a same-revision artifact mutation/seal mismatch;
- an unknown review item and a wrong item revision;
- missing/wrong CSRF;
- unauthenticated page and artifact access;
- post-login jti revocation;
- XSS payloads in both messages and typed values;
- operator approval without a revisioned decision list;
- incomplete historical approval snapshots attempting release/application.

The signed-link unit coverage also includes order/athlete/revision scope,
audience/action, expiry, missing keys, rotated-current-kid selection, jti
revocation, opaque server sessions, cross-order session reuse, and session
revocation.

## Phase 1 regression disposition

All Phase 1 tests remain green. One existing assertion in
`test_unknown_device_is_a_verbatim_required_confirmation` evolved because S3
legitimately supersedes that confirmation's shape: it now asserts the same
verbatim token plus the new typed value, basis, and sensitivity fields required
by S3. No Phase 1 control, expected blocker set, calendar golden, bypass gate,
platform disable, token gate, or seal assertion was weakened. The original
athlete-m production replay passes unchanged.

## Verification

- Dedicated new review-auth/page tests: **19 passed**.
- Phase 1 athlete-m + bypass + review/state focused run: **63 passed**.
- Webhook suite during integration: **479 passed** (before the final added
  review regression; the complete suite below is authoritative).
- Complete sandbox suite: `python3 -m pytest -q` → **2380 passed, 86 skipped,
  21 existing warnings, 0 failed**.
- `python3 -m compileall -q athletes/scripts delivery tools webhook` passes.
- `git diff --check` passes.
- Socket tests remain among the environment-dependent skips and were not run
  outside the sandbox. No live Stripe, Railway, TrainingPeaks, Endure, Resend,
  SMTP, or browser action was performed.

## Commits

1. `73a96ae` — Add value-bound review approval snapshots.
2. `65df723` — Add authenticated coach review page.
3. `88b8558` — Harden review approval authority.
4. Intended final boundary: `Document Phase 2 review surface`. The sandbox
   denied creation of the worktree `index.lock` when staging this notes file,
   so the file is deliberately left uncommitted for the human to commit last.

No push was attempted.

## Coach steps for the live Phase 2 gate

The code obligation is complete; the spec still requires one real paid order
and a human coach, which this sandbox cannot supply.

1. Deploy these commits with the existing typed download-token configuration,
   or configure an explicit review keyring. For explicit keys, set
   `REVIEW_TOKEN_KEYS` to a JSON `{kid: secret}` object and optionally
   `REVIEW_TOKEN_KID` to the current kid. No browser receives `CRON_SECRET`.
2. Generate one real order that has no non-waivable blocker. If it has waivable
   blockers, the coach must be willing to record a real reason. Confirm the
   generation email contains an `Open review page` fragment link.
3. Open that link in a normal browser. Download and inspect the sealed review
   bundle from the page. Review blockers in order, resolve every required
   confirmation, acknowledge both verified facts, and enter a reason for every
   checked waiver.
4. Select **Approve sealed revision**. Confirm the page reloads as APPROVED.
5. Inspect the order's server-side `fulfillment_status.json` and retain the gate
   evidence: `approval.snapshot_version == "approval_snapshot/v1"`, credential
   begins `review-link:`, `approval.revision` equals the current revision,
   `approval.model_seal` and `approval.release_manifest_digest` equal the state,
   and `approval.confirmations` has exactly one value-bearing entry for every
   `review_items` entry.

Stop at APPROVED for this phase. Automated apply, provider readback, guide
release, Gmail drafting, and confirmation remain Phase 4/5 work and are not
authorized by this gate.

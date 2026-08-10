# Phase 2 implementation adversarial review — Codex R2

## Verdict: NO-GO

The rendered-catalog binding and authority-derived page fixes close Round 1
blockers 1 and 2. Most of blocker 3 is also repaired: the page uses a
CSRF-protected session POST, parent revocation kills both that session and a
derived child, review-bundle tokens are capped at five minutes, and successful
responses are `no-store`. Phase 2 is nevertheless not gate-ready. The residual
GET compatibility route accepts an encoded `token` query key that bypasses the
installed request-target redaction filter, and the new seal-mismatch
supersession deletes the only value-bearing approval and waiver evidence from
state. Both contradict current Phase 2 invariants, not merely later platform
work.

Review basis: the complete tree at `6dc4e64`, including claimed fixes
`baa85eb` and `739a33f`; Round 1; the r9 specification and R9 standing
conditions. The implementation notes were treated as claims. I independently
ran 282 targeted state, review, token, athlete-m, Phase 1 bypass, and webhook
tests; all passed. I also ran direct canonicalization, encoded-query, and
concurrent-revocation attacks. The human-reported complete external suite is
2,393 passed, 86 skipped, 0 failed.

## Round 1 blocker dispositions

| Round 1 blocker | Disposition | Evidence and assessment |
|---|---|---|
| **1. Approval not bound to the rendered catalog** | **RESOLVED** | The page submits `review_catalog_digest` (`webhook/review_surface.py:152-160`); both page and operator routes require it (`webhook/app.py:2763-2793,3163-3187`). `transition` recomputes the complete authoritative catalog and digest and then copies that same catalog while holding the order-state lock (`webhook/fulfillment_state.py:920-1048`). `set_generation_blockers` and `merge_generation_blockers` reject a sealed revision (`:547-637`). Replaying the exact confirmation-value mutation and the blocker message/value mutation after render now returns 409 with no approval. A subset digest, reordered object keys, or a stale stored digest does not pass. |
| **2. Page treats an incomplete historical approval as authoritative** | **RESOLVED** | Page success is derived from `approval_matches_release`, not the status label (`webhook/review_surface.py:109-180`). Completeness requires snapshot v2, current revision and catalog digest, a one-to-one full catalog copy, valid dispositions, credential, and both seal fields (`webhook/fulfillment_state.py:298-337,752-762`). A valid page renders persisted `approval.confirmations`, including dispositions; missing entries, changed values/types, stale snapshot versions, and seal-field mismatches render `APPROVAL NOT AUTHORITATIVE` with no download or later action. |
| **3. Parent revocation, URL bearer, cache, and log hygiene** | **NOT RESOLVED** | The session POST and parent-revocation mechanics are fixed, as are the five-minute TTL and `no-store` headers. However, `/api/download/<order_id>` still accepts a bearer from `request.args['token']` (`webhook/app.py:2854-2875`). The request-target filter only recognizes literal `[?&]token=` (`:94-118`). Flask decodes `%74oken` to `token`, so an actual request using `?artifact=review_bundle&%74oken=<valid bearer>` returned 200 while the filter left the bearer unchanged in the logged target. The filter is attached to `gravel-god-webhook` and `werkzeug`, not `gunicorn.access`; it cannot redact an upstream Railway request log. Blocker 1 below is the still-open portion of this Round 1 blocker. |

## Release blockers

### 1. The residual GET bearer is accepted in request targets that evade redaction

**Evidence.** The compatibility endpoint selects `bearer or
request.args.get('token', '')` (`webhook/app.py:2871-2878`). Its redaction
regular expression matches only a literal query parameter spelling
(`webhook/app.py:94-102`). I verified both halves against the production Flask
app:

- Flask parsed `/api/download/x?...&%74oken=secret-value` as
  `request.args['token'] == 'secret-value'`.
- `_BearerQueryRedactionFilter` returned the same request target, including
  `%74oken=secret-value`.
- With a real issued five-minute review-bundle token and sealed fixture, the
  encoded-query production route returned 200.

The only regression constructs a synthetic Werkzeug record with literal
`&token=` (`webhook/tests/test_review_surface.py:603-612`). It neither attacks
URL-encoded parameter names nor proves the deployed request logger. The Docker
command runs Gunicorn (`webhook/Dockerfile:53-58`), but no filter is installed
on `gunicorn.access`, and application filters cannot sanitize Railway's
upstream request target.

**Violated clauses.** C4 requires tokens redacted from logs
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:473-483`); B3 defines the typed bearer and
revocation contract (`:375-395`); R9 condition 8 requires token and revocation
fail-closed proof
(`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R9.md:114-119`).

**Required closure.** Remove query-token authentication from the GET route and
accept typed capabilities only in `Authorization`, retaining the session POST
for the page. Do not rely on application regexes to sanitize a bearer already
present in an upstream request target. Add a production-route negative test
for literal and percent-encoded query keys and a logger-topology assertion for
every application-managed request logger.

### 2. Seal-mismatch supersession revokes authority by deleting approval provenance

**Evidence.** `_materialize_seal_mismatch` correctly creates a new unsealed
revision, but it sets `approval`, `waiver`, `application`, and `confirmation`
to `None` (`webhook/fulfillment_state.py:777-806`). Its history entry retains
only the prior revision, status, and model seal. The earlier approval
transition history records the credential but not the copied catalog values,
dispositions, or waiver reason (`:1038-1048,1089-1095`). Therefore, after a
post-approval seal mismatch, the state file can no longer answer what the coach
confirmed or waived. Existing tests affirm `approval is None` but do not assert
historical evidence retention (`webhook/tests/test_fulfillment_state.py:305-321`;
`athletes/scripts/test_phase1_bypass_gates.py:148-195`).

This is reachable from production review/download/status seal checks, including
the authenticated review GET (`webhook/app.py:2677-2689`), the new session POST
download (`:2828-2839`), and residual GET download (`:2893-2906`). Revoking
current authority is correct; destroying the audit record is not.

**Violated clauses.** I5 requires the state file alone to retain the approving
credential, waived facts, and confirmed values
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:92-94`). S3 requires the value-bearing
approval snapshot (`:192-205`). R9 condition 8 requires seal/state failure
behavior to fail closed without invalidating the evidence model. F4's later
phase rule also confirms that terminal facts are preserved across
supersession/cancellation (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:974-987`), though
the present I5/S3 violation already belongs to Phase 2.

**Required closure.** Revoke current authority and start the new revision while
moving the complete prior approval, waiver, application, and confirmation into
an immutable revision-history record. `approval_matches_release` must remain
false for the new revision. Add a regression that approves distinct typed
values and a waiver, triggers seal-mismatch supersession through a production
route, and proves those exact values, dispositions, reason, credential, and
seal remain recoverable from the state file but grant no authority.

## Re-attacks of the changed surface

- **Digest canonicalization — PASS.** The digest covers a version wrapper plus
  the entire ordered `review_items` array (`webhook/fulfillment_state.py:82-106`).
  Object key order and escaped-vs-literal Unicode canonicalize identically;
  decomposed Unicode changes the digest; equivalent float lexical forms
  canonicalize identically; integer and number types remain distinguishable;
  NaN and infinity are rejected. This matches the spec's stated UTF-8,
  sorted-key, no-whitespace JSON rule.
- **Subset/forgery attack — PASS.** The server reconstructs the catalog from all
  blocker, required, soft, and verified-fact sources, checks the stored catalog
  for exact equality, and compares the submitted digest to its own full digest.
  The operator endpoint reaches the same primitive. No caller-selected subset
  becomes authoritative.
- **Digest-check/snapshot-copy race — PASS.** Both occur in one
  `locked_state` critical section. A concurrent sanctioned writer must wait;
  after approval it is rejected or `write_generation` creates a newer revision
  and clears current authority.
- **Revocation chain — PASS with durability caveat.** Parent `jti`/`kid` checks
  apply to derived tokens (`webhook/download_tokens.py:219-231`), and review
  sessions recheck revocation, expiry, and key presence on every request
  (`webhook/review_auth.py:305-328`). The exact revoke-parent-then-use-child
  attack returns 401 on both the residual GET/Bearer path and the session POST.
  Concurrent revocation writers use one lock and atomic replacement; a 32-writer
  attack retained all 32 entries.
- **TTL/cache — PASS.** Review-bundle issuance and verification both enforce a
  maximum 300 seconds (`webhook/download_tokens.py:18-19,119-125,201-208`). Both
  successful review-bundle response paths set `Cache-Control: no-store,
  max-age=0`, `Pragma: no-cache`, and `Referrer-Policy: no-referrer`
  (`webhook/app.py:2840-2847,2908-2918`).
- **POST download CSRF — PASS.** The route is POST-only, requires a current
  revision-bound session, rejects missing/wrong CSRF with a constant-time
  comparison, and the cookie is HttpOnly/SameSite=Strict (Secure in production)
  (`webhook/app.py:2731-2739,2804-2824`). Extra approval-form fields do not
  trigger approval on the bundle route.

## Non-blocking findings

1. **The Round 1 side-effectful-GET finding is only narrowly closed.** Review
   GET now uses the order-id-only resolver, and the legacy-migration regression
   passes (`webhook/app.py:1937-1943,2651-2667`). But authenticated GET still
   calls `record_seal_mismatch`, which increments the revision and writes state
   (`:2677-2689`), contrary to C4's literal “GET renders only.” It is fail-closed
   and requires a valid session, so I do not elevate this beyond the evidence-
   deletion blocker above. Render the mismatch loudly and require an explicit
   POST/operator action to materialize it.
2. **Producer metadata is materially improved, but structural enforcement is
   still deferred.** The availability, brand, quality, compliance,
   state-unavailable, validator-crash, package-consistency, seal, and quarantine
   producers cited in R1 now carry explicit typed values, bases, and
   sensitivities. `_review_item` still falls back to message/source/internal
   metadata (`webhook/fulfillment_state.py:176-224`). No current production
   Phase 2 producer gap was found, but a complete producer inventory should
   precede removing this paid-order-safe compatibility fallback.
3. **The requested cheap value-traversal coverage is now credible.** Athlete-m
   runs the real intake assembler and post-render validator through persistence,
   sealing, session exchange, and page rendering
   (`athletes/scripts/test_athlete_m_phase1.py:128-145`). The smaller production-
   route fixture continues through approval and reload. Athlete-m itself cannot
   approve because its normative non-waivable blockers correctly remain.
4. **Key precedence is aligned.** Explicit typed download keys now beat the
   legacy root secret in review authentication, matching download-token
   behavior (`webhook/review_auth.py:71-104`), with both-configured rotation
   coverage.
5. **The revocation file is atomic across writers but not crash-durable to the
   same standard as fulfillment state.** `revoke_download_token` locks, fsyncs
   the temporary file, and replaces atomically, but does not fsync the parent
   directory (`webhook/download_tokens.py:235-264`). Add the directory fsync
   before treating an acknowledged revocation as power-loss durable. Its reader
   should also reject a structurally non-object JSON store with
   `DownloadTokenError` rather than an uncaught `AttributeError`; the current
   failure is closed (500/no artifact), but poorly classified.
6. **One terminal idempotency surface still trusts a status label.** The confirm
   route returns `confirmed` immediately for `status == CONFIRMED` before
   checking `approval_matches_release` (`webhook/app.py:3406-3417`), and the
   state primitive has the same early return
   (`webhook/fulfillment_state.py:1106-1118`). It grants no new action and avoids
   a duplicate send, so it does not reopen Round 1 blocker 2's page/release
   authority issue, but a corrupted/incomplete historical approval can still
   produce a success-labeled response. Preserve idempotence while returning a
   loud non-authoritative state.

## Phase 1 regression and Phase 3+ boundary

The Phase 1 athlete-m golden, bypass gates, customer-bundle approval gate,
artifact-descriptor serving, Endure disable, state migration, and webhook
integration tests passed in the targeted run. Catalog immutability and
authority checks are stronger. The approval-evidence deletion in release
blocker 2 is the one regression introduced by the new mismatch strategy: the
old in-place blocker retained the top-level snapshot, while the replacement
revision now discards it.

No Phase 3+ implementation leakage was found. These commits do not add the
canonical power model, D0 apply contract, worker/probe, provider readback,
automated platform apply, guide release, Gmail evidence, or later-phase page
controls.

## Unverifiable items

1. The one-real-order human Phase 2 gate has not been run and must not be run
   until the two blockers close.
2. Socket tests and the full suite were not independently run in this sandbox.
   The supplied external result is 2,393 passed, 86 skipped, 0 failed.
3. A real browser/proxy path was unavailable, so fragment history removal,
   production cookie behavior, HSTS/HTTPS enforcement, scanner/link-rewriter
   behavior, and Railway edge logging remain unverified.
4. Deployed keyring contents, rotation state, persistent-volume permissions,
   and revocation behavior across a real process/volume crash remain unverified.
5. No live Stripe, Railway, TrainingPeaks, Endure, email, or customer action was
   performed.

## Gate judgment

The page path is **not ready** for the one-real-order human step. After removing
query-token authentication and preserving superseded approval evidence without
authority, rerun the encoded-query regression, the seal-mismatch provenance
regression, focused Phase 1/2 tests, and the human socket suite. Only then should
the paid-order gate proceed, stopping at `APPROVED` as Phase 2 requires.

## Summary

Round 2 confirms that the central “approve exactly what was rendered” control
now works and that incomplete historical approvals no longer fool the page.
The new POST download and revocation cascade also work. Release is still NO-GO
because the retained GET compatibility path accepts a valid bearer spelling
that the redaction filter does not recognize, and a seal failure now destroys
the value-bearing approval record that I5 requires state to preserve. Close
those two failures before using a real paid order as the Phase 2 gate.

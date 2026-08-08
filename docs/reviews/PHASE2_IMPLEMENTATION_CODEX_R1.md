# Phase 2 implementation adversarial review — Codex R1

## Verdict: NO-GO

Phase 2 is not safe to release. The ordinary-path implementation is substantial:
the browser and operator endpoints enforce the expected order/revision/session,
CSRF, waiver, required-confirmation, non-waivable-policy, and artifact-seal
checks. However, three release blockers remain. Most importantly, a same-revision
catalog change between page render and approval causes the server to record the
new value as confirmed even though the coach saw the old value. The page can also
claim that an incomplete historical approval is valid, and review-link revocation
does not revoke a review-bundle capability minted from that link.

Review basis: commits `73a96ae`, `65df723`, `88b8558`, and `43aacb3`, stacked on
Phase 1 at `9a9aa43`; the complete current production paths and tests; the r9
specification and R9 standing conditions. `PHASE2_IMPLEMENTATION_NOTES.md` was
treated as a claim, not evidence. The human-reported full-suite result is 2,380
passed, 86 skipped, 0 failed. I independently ran the review-auth, review-page,
fulfillment-state, post-render-validator, unknown-device, and athlete-m Phase 1
tests: 62 passed.

## Conformance matrix

| Phase 2 item | Result | Evidence and assessment |
|---|---|---|
| **S3 review-item catalog** | **FAIL** | The catalog contains copied JSON-native values, types, provenance fields, sensitivity, and revision (`webhook/fulfillment_state.py:177-279`). Duplicate ids and non-JSON values fail closed. But the catalog is mutable after sealing at the same revision (`:522-604`), while the page/form binds no catalog digest. Blocker 1 means the catalog approved need not be the catalog shown. Generic producers also rely on synthesized message/basis/sensitivity defaults; finding 1. |
| **C1 review page** | **FAIL** | The page has the required ordering, waiver/remediation distinction, confirmation controls, verified facts, escaping, and later-phase-disabled copy (`webhook/review_surface.py:27-73,102-162`). It verifies artifact bytes before rendering (`webhook/app.py:2635-2660`). It nevertheless labels any `APPROVED` status as a valid sealed decision without checking approval authority; blocker 2. |
| **C2 surface** | **PASS (static)** | Named Phase 2 findings now carry structured values: race match/provenance, FTP estimate, course resolution, weeks mismatch, and unknown devices (`athletes/scripts/intake_to_plan.py:3122-3226`); schedule, race-week, session-date, fueling-label, carb-target, and altitude findings do likewise (`athletes/scripts/post_render_validator.py:248-292,295-457`). Existing Phase 1 finding logic was not weakened. Production end-to-end value traversal is under-tested; finding 4. |
| **C4 authentication** | **FAIL** | Review tokens bind action, audience, order, athlete, revision, time, `kid`, and `jti` (`webhook/review_auth.py:150-239`). Sessions are opaque, server-side, expiry-bound, and recheck revocation/key presence (`:273-326`). Routes check cross-order/revision state and CSRF (`webhook/app.py:2616-2632,2676-2759`) and pages are escaped/no-store/no-referrer/CSP-protected (`:2596-2607`). Derived download authority, URL logging/cache behavior, and revocation are incomplete; blocker 3. GET also has a side-effectful legacy-resolution edge; finding 2. |
| **Approval snapshot with reviewed values and seal** | **FAIL** | Approval copies values rather than references and records credential, revision, `model_seal`, and manifest digest (`webhook/fulfillment_state.py:942-1001`). Release authority checks completeness and current seal (`:282-326,719-729`). But it copies the catalog current at POST time, not necessarily the values rendered to the coach; blocker 1. |
| **Policy enforcement** | **PARTIAL** | The actual page and operator HTTP endpoints reject missing required confirmations, unknown/duplicate/wrong-revision decisions, partial or reasonless waivers, non-waivable blockers, stale revisions, and artifact mismatch (`webhook/app.py:2707-2759,3053-3089`; `webhook/fulfillment_state.py:869-991`). This is real state-authority enforcement, not page JavaScript. It is undermined by the missing catalog-identity predicate and the false-success rendering in blockers 1-2. |
| **Phase 1 preservation** | **PASS, except for the new page-derived capability issue** | The only pre-existing test changed adds S3 fields without deleting an assertion (`athletes/scripts/test_intake_to_plan.py:86-93`). Review rendering and approval reverify the Phase 1 seal, release/application still require `approval_matches_release`, the customer bundle remains gated, and no apply driver was re-enabled. Blocker 3 is a new review-page consumer problem, not a reopening of the customer bundle or TP write gates. |
| **Phase 3+ boundary** | **PASS** | No canonical power model, D0 contract, worker/probe, automated apply, guide publish, or Gmail evidence path was enabled by these commits. The page explicitly leaves those controls disabled (`webhook/review_surface.py:152-155`). |
| **Phase 2 live gate** | **NOT READY / UNVERIFIED** | The real paid-order/human approval is correctly a human rollout step (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:1100-1102`), but the code path is not gate-ready while blockers 1-3 remain. No claim is made that the human step should already have been executed. |

## Release blockers

### 1. The approval request is not bound to the catalog values rendered to the coach

**Evidence.** The page form submits only `generation_revision`, selected item ids,
and CSRF (`webhook/review_surface.py:133-141`). The route turns those ids into
decisions carrying only id/revision/disposition (`webhook/app.py:2728-2750`).
Meanwhile, both catalog mutation operations remain legal in `GENERATED` or
`BLOCKED_REVIEW` even after `model_seal` has been finalized
(`webhook/fulfillment_state.py:522-604`); neither rejects a sealed state nor bumps
the revision. At approval, the transition rebuilds the **current** catalog and
copies its current values into the snapshot (`:908-982`). Artifact verification
then checks only the release manifest bytes (`:983-1001`; `:676-716`), so it does
not detect a state/catalog-only change.

I reproduced the production-state sequence: render a sealed confirmation value
`{"target": 40}`, replace that same item id at revision 1 with
`{"target": 120}` using `merge_generation_blockers`, and submit the ids from the
old page. Approval returned `APPROVED`; the persisted snapshot said the coach
confirmed `{"target": 120}`. The snapshot contains a value, but it is not the
value shown.

**Violated clauses.** I3 and I5 (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:87-94`),
S2's finalized/no-rewrite rule (`:150-165,186-190`), S3 (`:192-205`), and the
Phase 2 value-bearing page gate (`:1100-1102`).

**Required closure.** Make post-seal catalog mutation require
`write_generation`, and bind the form/operator decision to a canonical digest of
the exact catalog rendered. Verify that digest under the state lock before
copying values and persist it in the approval. Add a production-route regression
that changes an item's value (and separately a blocker's message/value) without
changing its id or revision and proves approval is rejected.

### 2. The page reports an invalid/incomplete approval as valid and seal-bound

**Evidence.** `approval_matches_release` correctly denies authority to an
approval without a complete current snapshot (`webhook/fulfillment_state.py:719-729`).
But the page's `approved` predicate is only
`status in {APPROVED, APPLIED, CONFIRMED}` (`webhook/review_surface.py:111-115`).
It then states “Approved” and “This decision is bound” (`:143-150`). The route
verifies artifact bytes before rendering but never checks
`approval_matches_release` (`webhook/app.py:2635-2660`).

I reproduced this using the same incomplete historical approval shape already
constructed by `test_incomplete_legacy_approval_snapshot_grants_no_release_authority`:
`approval_matches_release` returned false, while authenticated `GET /review/...`
returned 200 and displayed both “Approved” and “This decision is bound to
revision”. Because the state is already `APPROVED`, the approval endpoint also
cannot repair it; it rejects `APPROVED -> APPROVED`.

**Violated clauses.** I6 (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:95-96`), S3
(`:192-205`), C1's authoritative post-approval surface (`:408-416`), and R9
condition 8's fail-closed state/seal behavior
(`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R9.md:114-119`).

**Required closure.** Derive the page's effective state from
`approval_matches_release`, not the status label. An incomplete/stale approval
must render a loud, non-success remediation state and expose no later action.
Render the persisted approval snapshot/dispositions for a valid approval. Add
page-route tests for missing entries, changed values/types, seal fields, and old
snapshot versions.

### 3. Revoking a review link does not revoke the bundle capability it minted; that bearer is URL-logged and not no-store

**Evidence.** Every authenticated page render creates a new review-bundle token
and places it in an `href` query string (`webhook/app.py:2638-2647`). Download
tokens receive an independent random `jti` (`webhook/download_tokens.py:95-134`).
Revoking the original review `jti` terminates the session
(`webhook/review_auth.py:303-325`), but the bundle endpoint validates only the
child download token and its unrelated `jti` (`webhook/app.py:2781-2806`;
`webhook/download_tokens.py:150-199`).

I logged in, captured the page-minted download URL, revoked the original review
`jti`, and retried both paths. The page fell back to the generic shell, but the
captured bundle URL still returned 200. Its response header was
`Cache-Control: no-cache`, not `no-store`. The bearer also appears in the HTTP
query string, so standard proxy/access logs receive it; there is no application
or server log-redaction mechanism for that request target. This defeats a
compromised-link response: an attacker who opened the page before revocation
retains up to a seven-day PII-bearing review-bundle capability.

**Violated clauses.** C4's `jti` revocation, no-store, and token-log-redaction
requirements (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:473-483`), B3's per-link
revocation contract (`:375-393`), and R9 condition 8
(`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R9.md:114-119`).

**Required closure.** Prefer a session-authorized download response that places
no bearer in a URL. If a derived typed token remains necessary, bind it to the
parent review credential and reject it when the parent `jti`/`kid` is revoked;
also set `Cache-Control: no-store`, `Pragma: no-cache`, and prove request-target
redaction at the deployed access-log layer. Add the revoke-after-mint negative
test.

## Non-blocking findings

1. **S3 validation invents provenance and sensitivity instead of requiring it.**
   `_review_item` falls back from missing `review_value` to `message`, defaults
   sensitivity to `internal`, and synthesizes source/basis
   (`webhook/fulfillment_state.py:185-209`). Production availability, brand,
   quality-gate, compliance, state-unavailable, and validator-crash findings
   still omit one or more of those fields (for example
   `athletes/scripts/availability_ledger.py:121-138`,
   `athletes/scripts/intake_to_plan.py:1962-1972,2841-2849`, and
   `athletes/scripts/generate_athlete_package.py:840-846`). A canonical string
   is a typed JSON value, but a source name is not a factual basis, and
   athlete-authored session titles should not silently become `internal`.
   Require explicit metadata or define accurate server-owned metadata per rule.

2. **Unauthenticated review GET is not strictly render-only.**
   `_authorized_review` calls `_resolve_order_id` before validating the session
   (`webhook/app.py:2616-2624`), and `_resolve_order_id` may migrate and tombstone
   a legacy athlete-path state (`:1888-1905`). Startup migration should normally
   make this edge dormant, and it grants no release authority, but it contradicts
   C4's scanner-safe “GET renders only” rule. Review routes should use a
   side-effect-free, order-id-only resolver.

3. **The state primitive retains an approval footgun that the HTTP endpoints
   correctly avoid.** If `review_decisions is None`, `transition` automatically
   confirms verified facts (`webhook/fulfillment_state.py:911-925`). Both current
   HTTP approval paths require a decision list, so this is not a remote bypass,
   but it weakens the claimed state-authority invariant and has already allowed
   many tests to avoid the Phase 2 policy. Remove the compatibility branch once
   callers/tests submit explicit decisions.

4. **The route tests are useful but overstate production traversal.** The
   athlete-m page test reads a few fixture values, then hand-constructs one
   blocker and one confirmation using test helpers
   (`webhook/tests/test_review_surface.py:44-83,128-180`). It does not run
   `assemble_intake_review_items`, the post-render validator, persistence, and
   the review routes as one chain. Existing tests also omit the two authority
   regressions in blockers 1-2, parent-to-child revocation, session expiry/key
   removal at the Flask route, browser execution of the fragment bootstrap,
   duplicate form ids, missing CSRF (only wrong CSRF is covered), and deployed
   log/cache behavior. The tests do exercise real Flask production routes rather
   than mocking the endpoint checks, which is why the ordinary negative cases
   are credible.

5. **No Phase 1 regression-test weakening or Phase 3+ enablement was found.**
   The unknown-device assertion was extended rather than relaxed, artifact seal
   verification still precedes page rendering/approval, the full customer ZIP
   remains approval-gated, and the TP/Endure/later release controls remain off.

## Unverifiable items

1. The required real paid-order/human Phase 2 gate has not been performed here;
   that is expected, but it must wait for blocker closure.
2. I could not execute a real browser, so fragment removal/history behavior,
   cookie behavior through the production proxy, and scanner/link-rewriter
   behavior remain unproven. Static bootstrap code does not embed
   athlete-derived JSON and appears XSS-safe.
3. I could not verify that Railway forces HTTPS/HSTS or redacts query strings in
   its edge/access logs. The emailed review URL is HTTPS and the production
   session cookie is marked Secure, but the app itself does not enforce the
   fragment exchange over HTTPS.
4. I could not verify deployed review/download keyring contents, rotation state,
   persistent-volume permissions, or revocation-store durability. In
   particular, mixed legacy `DOWNLOAD_TOKEN_SECRET` plus keyring configuration
   has different precedence in `review_auth.py` and `download_tokens.py` and
   should be exercised during rotation.
5. Socket-dependent tests were not run in this sandbox. The human reports the
   full external result as 2,380 passed, 86 skipped, 0 failed; I did not
   independently reproduce that complete run.

## Summary

Phase 2 has the right general shape and closes the obvious direct approval
bypasses, but it does not yet prove the central claim that the coach approved
the values actually shown. Same-revision catalog drift can create a complete,
seal-bearing but false approval record; the page can independently report a
non-authoritative historical approval as valid; and review-link revocation
does not contain a bundle capability already minted from that link. Close those
three gaps, add the missing negative regressions through production routes, and
then rerun this review before attempting the one-real-order Phase 2 gate.

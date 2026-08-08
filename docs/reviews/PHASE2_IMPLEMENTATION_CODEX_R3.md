# Phase 2 implementation adversarial review — Codex R3

## Verdict: GO-WITH-CONDITIONS

The two Round 2 release blockers are closed. The review-bundle GET path no
longer accepts any bearer, query or header; customer-bundle GET authentication
ignores query parameters and accepts typed capabilities only through
`Authorization`. Seal-mismatch supersession now preserves the complete prior
decision record as explicitly non-authoritative history while every current
authority consumer remains bound exclusively to the new revision's top-level
approval and seal.

I found no new Phase 2 blocker, no regression of a Round 1/2 closure, and no
weakening of a Phase 1 gate. The page path is ready for the specified one-real-
order human gate, but that human gate has not yet been performed. Phase 2 is
therefore GO-WITH-CONDITIONS rather than fully complete: deploy the reviewed
code, approve one suitable real order entirely on the page, verify the durable
snapshot below, and stop at `APPROVED`.

Review basis: commits `f0b4f46` and `47b8342`, their diff from `7932932`, the
complete current authority consumers, Round 1 and Round 2 reviews, the r9 spec,
and R9 standing conditions. The implementation notes were treated as claims.
The human-reported complete external suite is 2,398 passed, 86 skipped, 0
failed. I independently ran the focused state, review, token, auth, athlete-m,
Phase 1 bypass, Endure, and webhook set: 330 passed. The six named closure
tests ran as eight parametrized cases: eight passed. I also replayed broader
encoded spellings, logger reload, and archive-authority attacks outside the
authored regressions.

## Disposition of the two Round 2 items

### 1. Encoded query-token GET path — RESOLVED for Phase 2

`GET /api/download/<order_id>` rejects `review_bundle` before state resolution
or capability verification (`webhook/app.py:2862-2873`). For the remaining
`customer_bundle` branch, the only typed token source is the
`Authorization: Bearer` header; there is no `request.args['token']` fallback
(`webhook/app.py:2881-2896`). The only successful review-bundle route is the
revision-bound, revocation-aware, CSRF-protected session POST
(`webhook/app.py:2812-2855`).

I replayed valid issued review/customer tokens under `token`, `%74oken`,
`t%6Fken`, `to%6ben`, `tok%65n`, `toke%6e`, fully encoded
`%74%6f%6b%65%6e`, and mixed encoded spellings. Review-bundle GET returned 401
for query and header bearers. Customer-bundle GET returned 401 for every query
spelling, while the same current token in `Authorization` reached the approval
and seal gate and returned the artifact for an approved fixture. Duplicate or
encoded parameter-name handling did not reveal a second bundle branch.

The defense-in-depth filter covers every raw single-pass spelling that Flask
decodes to the exact lowercase `token` key and recursively redacts both log
messages and arguments (`webhook/app.py:94-119`). It is installed on
`gravel-god-webhook`, `werkzeug`, and the production server's request-target
logger namespace, `gunicorn.access` (`webhook/app.py:122-126`;
`webhook/Dockerfile:53-58`). Reloading the application module retained working
filters on all three logger objects. See non-blocking finding 2 for its
non-idempotent reload behavior and unverifiable item 2 for actual deployed
Gunicorn/Railway emission.

An exhaustive search did find one other query token in the repository:
`GET /api/fulfillment/<order_ref>/apply-gate` reads its distinct, short-lived
Phase 1 TrainingPeaks apply-gate capability from `?token=`
(`webhook/app.py:3274-3278`). It is not a bundle/download capability or a
residual branch of the removed path; it predates Phase 2 and is part of the
Phase 1 browser-driver gate previously reviewed GO. Removing it in this round
would change a settled Phase 1 control. Under the instruction to judge Phase 2
only, it does not reopen this blocker, but it remains a named later-phase
boundary fact rather than supporting a repo-wide claim that no query bearer of
any kind exists.

**Spec assessment.** The Phase 2 bundle/download implementation now satisfies
B3's scoped artifact authentication and C4's session/POST, revocation,
no-store, and request-target hygiene requirements
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:375-395,473-483`) and R9 condition 8 for
the implemented Phase 1/2 token subset.

### 2. Seal-mismatch supersession evidence — RESOLVED

Before clearing authority, `_materialize_seal_mismatch` deep-copies the prior
approval, waiver, application, confirmation, status/revision, model seal,
release-manifest identity, mismatch reason, and timestamp into
`superseded_approvals[]`, with `authoritative: false`
(`webhook/fulfillment_state.py:795-827`). It then increments the revision,
installs the non-waivable `SEAL_MISMATCH` blocker, and clears every current
approval/application/release field (`:828-848`). `write_generation` carries the
archive forward across later revisions (`:525-541`).

The replay approved distinct typed blocker and confirmation values with a
waiver, advanced a second fixture through application and confirmation,
triggered seal mismatch, and reloaded the state. The archive retained exact
values, value types, dispositions, credential, waiver reason, application and
confirmation evidence, and both seal identities. The new revision had no
top-level approval or seal authority, and `approval_matches_release` was false.

I then attacked every named consumer:

- The page derives success and later actions only from
  `approval_matches_release`; archived entries render below “Superseded
  approval history,” “Historical evidence only,” and “non-authoritative,” with
  no Approved banner or application action (`webhook/review_surface.py:83-128,
  155-234`).
- The operator status endpoint returned `BLOCKED_REVIEW`,
  `release_authorized: false`, no current approval, and no apply-gate token. It
  does not serialize `superseded_approvals` into its authority response
  (`webhook/app.py:3200-3271`).
- `approval_matches_release` reads only the current top-level `approval` and
  current seal/catalog (`webhook/fulfillment_state.py:770-780`).
- APPLIED transition, confirm, the old revision-bound customer token, and a
  newly issued current-revision customer token all failed closed. The release
  route never consults the archive (`webhook/app.py:2898-2915,3379-3420`;
  `webhook/fulfillment_state.py:1068-1105`).

**Spec assessment.** The state file alone retains the approving credential,
waived facts/reason, confirmed typed values and dispositions, and later
decision evidence without making them current authority. This closes the I5
and S3 violation (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:92-94,192-205`) while
preserving I3/I6 fail-closed seal behavior.

## Re-attacks and regression assessment

- **Round 1 rendered-catalog binding — PASS.** Approval still submits the
  complete catalog digest; the state transition recomputes it and copies the
  exact catalog under the state lock. Sealed catalog mutators remain rejected.
  No closure commit changed this path.
- **Round 1 authority-derived page — PASS.** The page still uses
  `approval_matches_release`, not a status label. Missing, stale, incomplete,
  wrong-version, or seal-mismatched snapshots expose no current success or
  later action.
- **Session, CSRF, revocation, TTL, and cache — PASS.** Review sessions remain
  order/revision-bound and revalidate parent jti/kid status on each request.
  The sole bundle response is POST + CSRF and `no-store`; revoking the parent
  ends the session fetch.
- **Archive injection into authority — PASS.** Page, status, approval matcher,
  APPLIED, confirm, and both old/new customer-release capabilities ignored the
  archived record for authority.
- **Phase 1 controls — PASS.** Athlete-m, non-waivable blockers, customer
  release gating, exact artifact-descriptor verification, schema-v1
  quarantine, Endure disable, TP platform binding, and confirm/application seal
  rechecks remained intact in the 330-test run. The changed tests replace the
  intentionally removed query credential with `Authorization` and add negative
  assertions; no gate assertion was deleted to manufacture green.
- **Phase 3+ boundary — PASS.** No canonical power model, D0 contract, worker,
  probe/inspection, automated platform application, guide publication, Gmail
  evidence, or later-phase page action was enabled by `f0b4f46`/`47b8342`.

## New blockers

None.

## Non-blocking findings

1. **Authenticated review GET still writes on a seal failure.**
   `_render_authorized_review` calls `record_seal_mismatch`, increments the
   revision, and archives/clears authority while serving GET
   (`webhook/app.py:2678-2699`). This is fail-closed and no longer destroys
   evidence, but C4 literally says GET renders only. Move mismatch
   materialization to an explicit POST/operator reconciliation action in a
   later hardening pass.
2. **Logger installation survives reload but is not idempotent.** A module
   reload left two equivalent filters on each named logger rather than one.
   Redaction still worked, so this is overhead/maintenance rather than an
   exposure. Install by stable filter type/name or remove the prior instance
   before adding a replacement.
3. **Historical-record validation checks the envelope, not the full nested
   snapshot schema.** `_validate_state` requires a non-authoritative record,
   revision, reason, timestamp, and approval object
   (`webhook/fulfillment_state.py:382-396`), but does not re-run the complete
   approval-snapshot validation against archived catalog data. The production
   transition deep-copies a previously authoritative snapshot and the replay
   proves exact retention; the archive cannot authorize anything. A dedicated
   immutable-history validator would make corruption detection more explicit.
4. **The separate Phase 1 apply-gate query capability remains.** It is outside
   the Phase 2 bundle fix and its removal is properly deferred to the D1/D3
   worker/capability replacement, but operational documentation should avoid
   saying that the entire application has no query bearer.
5. **Two carried hardening items remain unrelated to this closure.** The
   revocation-store replace still lacks a parent-directory fsync, and the
   already-CONFIRMED idempotent response still trusts the status label before
   rechecking current approval. Neither grants authority in the superseded
   flow or regressed in this round.

## Unverifiable items

1. I did not independently run socket-dependent tests or the complete suite in
   this sandbox. The supplied outside result is 2,398 passed, 86 skipped, 0
   failed; my independent non-socket focused result is 330 passed.
2. Gunicorn is declared in the production requirements but is not installed in
   this review environment. I verified the exact `gunicorn.access` logger
   attachment and synthetic record shape, not a live Gunicorn worker restart;
   the Docker command also does not explicitly enable Gunicorn access-log
   output. Railway edge/proxy request logging occurs before application filters
   and remains externally unverifiable. Normal Phase 2 links put the review
   token in the URL fragment, and bundle/customer credentials are POST-session
   or header-carried, so the production path no longer sends those bearers in
   a request target.
3. I did not execute a real browser or production proxy. Fragment removal,
   browser history, deployed Secure-cookie behavior, HTTPS/HSTS, scanner/link-
   rewriting behavior, and cache behavior through Railway remain live checks.
4. I did not inspect deployed review/download keyrings, rotation state,
   persistent-volume permissions, or revocation across an actual process/power
   failure.
5. The required one-real-order Phase 2 gate has not been performed. No live
   Stripe, Railway, TrainingPeaks, Endure, email, guide-publish, or customer
   action was taken in this review.

## Remaining conditions and owners

| Condition | Owner | When |
|---|---|---|
| Deploy `47b8342` with explicit production review/download key configuration and verify HTTPS/Secure-cookie and application-log behavior. Retain the supplied green human full-suite result. | Human deploy/operator | Before the live Phase 2 order |
| Complete one real paid-order review and approval entirely through `/review/<order_id>`, retain the evidence below, and stop at `APPROVED`. | Coach, witnessed by pipeline operator | Phase 2 live gate |
| Keep automated TP/Endure application, guide release, Gmail drafting/confirmation, and all write-capable page controls disabled. | Pipeline owner | Until their dependency-ordered Phase 3-5 gates |
| Implement/prove canonical power and D0 offline projection fixtures. | Phase 3 owner | Later phase; not a Phase 2 blocker |
| Implement/prove the read-only worker, identity binding, and zero-write canary. | Phase 4 owner | Later phase; not a Phase 2 blocker |
| Implement/prove D1/D3 apply, rollback/supersession, release components, Gmail evidence, guide privacy/revocation, and the controlled end-to-end canary. Replace the Phase 1 apply-gate query capability here. | Phase 5 owner | Later phase; no customer writes before this gate |

## Exact live-gate checklist for the coach

1. Deploy the reviewed commit and confirm the externally run suite is green.
   Use explicit production token keyrings/secrets; do not rely on development
   defaults.
2. Select one new real paid order whose generation completed durably. Prefer a
   clean order. Do not use an order carrying `FTP_ESTIMATED`,
   `COURSE_UNRESOLVED`, `STATE_UNAVAILABLE`, validator-crash, or
   `SEAL_MISMATCH`; those are non-waivable and must be fixed/regenerated.
3. Open the review link from the coach notification. Confirm the browser lands
   on `/review/<order_id>` with no token in the visible query string, and that
   order id, athlete, platform, revision, and status are the intended order.
4. Review the page in order: blockers, required confirmations, soft
   confirmations, and verified facts. Check the displayed typed values,
   source, basis, unit, sensitivity, and revision—not only the prose label.
5. Download the sealed review bundle using the page button. Confirm it is the
   same order/revision and contains only review material: preview, coaching
   brief, unpublished guide draft, and human-readable summaries. It must not
   contain `.zwo`, TP-native/apply payloads, customer ZIP contents, or another
   executable delivery artifact.
6. If any value, seal, revision, artifact, or page state is wrong—or the page
   says superseded, non-authoritative, or unavailable—stop. Do not use an
   operator endpoint/manual bypass. Correct the source, regenerate, and reopen
   the newly issued revision link.
7. For every waivable blocker, deliberately select it and enter a substantive
   waiver reason. Never attempt to waive a non-waivable blocker. Confirm every
   required confirmation and verified fact; record the intended disposition of
   each soft confirmation.
8. Submit **Approve sealed revision** once on the page. After the redirect,
   require the Approved banner to name the same revision and state that the
   decision is bound to its seal and displayed values. Confirm the page shows
   the persisted values/dispositions and does not expose an automated apply,
   confirm, guide-release, or Gmail action.
9. From the server-side state, record and verify all of the following:
   `status == "APPROVED"`;
   `approval.snapshot_version == "approval_snapshot/v2"`;
   `approval.review_catalog_digest == state.review_catalog_digest`;
   `approval.credential` begins `review-link:`;
   `approval.revision == state.generation_revision`;
   `approval.model_seal == state.model_seal`;
   `approval.release_manifest_digest == state.release_manifest_digest`; and
   `approval.confirmations` has exactly one unique, value/type-identical entry
   and persisted disposition for every current `review_items` entry.
   Independently require `approval_matches_release(state) == true`.
10. Verify `application is null` and `confirmation is null`, with no TP/Endure
    write, customer send, public guide, or Gmail draft triggered. Preserve a
    redacted gate record, then **stop at `APPROVED`**. Do not continue into the
    Phase 3-5 controls.

## Summary

Round 3 closes the last two Phase 2 code blockers. Query credentials no longer
authorize any bundle/download GET path, encoded spellings fail, and the actual
application-managed request loggers carry the defense-in-depth filter. A seal
mismatch now revokes current authority without erasing the coach's complete
value-bearing decision record, and every page/status/apply/confirm/release
consumer treats that record strictly as history. Focused regressions are green,
no earlier control weakened, and no new Phase 2 blocker emerged. The page is
ready for the one-real-order human gate; Phase 2 becomes fully complete only
when that order is approved on the page with the verified snapshot above and
the process stops at `APPROVED`.

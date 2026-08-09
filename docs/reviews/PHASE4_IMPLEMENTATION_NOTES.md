# Phase 4 implementation notes — read-only worker and D2 review flow

Date: 2026-08-09

Binding contract: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md`, converged R9,
especially D1, D2, C's review/approval surface, the athlete-m fixture
contract, and the rollout entry for Phase 4.

## Scope and safety boundary

Phase 4 implements the complete offline path through the read-only worker
transport boundary and the D2 coach-review flow. It performs no TrainingPeaks
network or browser operation. The only executable worker operations are
`probe_athlete(identity)` and `inspect_account(tp_id)` against an injected
read-only transport.

`apply`, `verify`, and `rollback` exist on the worker interface and refuse
unconditionally. Mutation execution-grant exchange also refuses
unconditionally. The older webhook browser apply-grant issuer now refuses,
the authenticated status response issues no apply token or URL, and the
legacy apply-gate route always returns HTTP 409. Consequently neither a
valid Phase 4 capability nor an older route can authorize a remote write.

The legacy adapter, JavaScript driver, and `tp_apply_order` remain disabled.
No live TrainingPeaks, browser, external-network, email, Stripe, or worker
mutation action was attempted during implementation or verification.

## D1 — read-only session-service boundary

`delivery/trainingpeaks/worker_service.py` defines:

- `ReadOnlyWorkerTransport`, the operation boundary for `probe_athlete` and
  `inspect_account`;
- `CannedProbeTransport`, which consumes the checked-in
  `worker_probes.json` shape and performs no I/O beyond reading that fixture;
- `ReadOnlyWorkerService`, which binds each request to a verified capability
  and a durable replay record before invoking the transport;
- `CapabilityCodec`, with rotating `kid`-selected HMAC-SHA256 keys and exact,
  closed claim schemas;
- `ProbeExecutionStore`, an atomic, order-scoped, file-locked jti store; and
- the offline mutation exchange predicate plus explicit Phase 4 refusal
  stubs.

Probe claims are exactly:

```text
{order_id, subject: {kind: identity_query, exactly one of email |
 tp_athlete_id | candidate_list_ref}, action: probe|inspect,
 audience, iat, exp, jti}
```

Verification covers token encoding, header algorithm/type, `kid`, signature,
audience, exact action and claim shape, exact subject locator, issuance and
expiry, a 15-minute maximum lifetime, safe order ids, and jti syntax. The
request must exactly match the signed subject. A probe capability is rejected
for every mutation action.

Probe replay records use the D1 lifecycle
`accepted -> running -> succeeded|failed`, with a canonical request digest.
Writing each state uses fsync plus atomic replace while holding the per-record
lock. A retry with the same order/jti/digest returns its recorded successful
result (or its recorded failure); a different request digest fails closed.
The records are segregated by order id.

Mutation capabilities use the exact D1 shape:

```text
{order_id, tp_athlete_id, generation_revision, model_seal,
 action: apply|verify|rollback, audience, iat, exp, jti}
```

Their type and validation are implemented for Phase 5 reuse. The pure offline
exchange predicate pins the R9 action table: initial apply at `APPROVED`,
same-attempt apply resume at `APPLYING`, verify at
`APPLYING|APPLIED|APPLIED_ATTESTED`, and operator-authorized rollback at the
eligible apply/cancellation states. It additionally binds the authoritative
order, platform identity, revision, seal, cancellation state, jti, and request
digest. This predicate never issues a grant in Phase 4.

## D2 — identity, inspection, and state commands

`webhook/d2_identity.py` owns the D2 state extension and validates it on every
fulfilment-state load/write. Supported identity outcomes are `bound`,
`multiple-candidates`, `not-coached`, `not-found`, and `unresolved`.
Candidate selection is an authenticated state-changing review command. A
binding is stored as order-scoped `platform_identity`; automated-platform
approval requires it, while manual delivery remains governed by APPLIED
delivery evidence.

The automated identity outcomes map to the R9 policy:

- `not-coached` -> non-waivable `ATHLETE_UNLINKED`;
- `not-found` -> non-waivable `ATHLETE_NO_ACCOUNT`; and
- multiple/unresolved without a binding -> non-waivable
  `ATHLETE_IDENTITY_UNRESOLVED`.

Inspection stores typed account facts and emits the fixture-backed review
items:

- `D2_THRESHOLD_LTHR_STALE_MISMATCH`, required, for the account LTHR of
  148 bpm dated 2019-05-01 against an HR-controlled plan;
- `D2_DEMOGRAPHIC_AGE_MISMATCH`, required, for account age 19 versus intake
  age 45; and
- `D2_ACCOUNT_DORMANCY`, soft, for zero workouts since 2019.

Age, FTP, LTHR, expiry, and workout-history observations remain in
authenticated server state. Their registry entries are typed
`externally_observed`, sensitive derived values with source, method/version,
observed time, dependency references, confidence, and review policy. External
status surfaces continue through the Phase 3 recursive projection, so these
values are not exposed by the operational API.

All four resolution choices execute server-side state commands:

1. `use-tp-value` copies the inspected value to canonical input overrides,
   invalidates the seal and approval, advances the authoritative revision,
   records a durable regeneration requirement, and re-enters the normal
   generation job. The regenerated review item carries the new sealed plan
   value.
2. `update-from-intake` preserves the plan anchor and emits a D0
   `threshold_update`/`zone_update` desire with the inspected before-image.
   The normal generation path builds it into the apply contract; no operation
   is executed in Phase 4.
3. `manually-corrected` records a pending readback requirement and leaves
   approval blocked. `record_manual_readback` accepts only exact worker
   evidence and records its probe jti before clearing the requirement.
4. `cannot-resolve` creates a non-waivable D2 blocker.

Any sealed command that changes generation inputs or the apply contract first
persists the new non-approvable state. Only then does the review route queue
the long generation job. Queue/source failures therefore leave a loud durable
`D2_REGENERATION_REQUIRED` condition rather than an old approval or seal.
Candidate binding uses this same path.

Approval validation is server-side. It requires an automated-platform
binding, no pending regeneration/readback, a resolution on every required D2
item, and consistency among the selected resolution, inspected account value,
and sealed control-metric value. A posted generic confirmation cannot bypass
these checks.

## Review surface

The authenticated Phase 2 review page now renders an identity panel with the
outcome, bound id, candidates, and candidate-binding control. Typed D2 items
render resolution selectors that post to dedicated authenticated, CSRF-bound
commands. Approval snapshots record the chosen resolution as
`resolved:<choice>` and remain bound to the current revision and review
catalog digest.

## athlete-m Phase 4 fixture contract

The checked-in `tests/fixtures/athlete_m/worker_probes.json` already matched
the converged R9 literal fixture and was therefore retained byte-for-byte. The
Phase 4 pipeline activates it only when `GG_WORKER_PROBES_FIXTURE` and a
distinct 32-byte-or-longer `GG_WORKER_CAPABILITY_SECRET` are explicitly
provided. It then exercises the real signed-capability, replay-store, and
canned-transport path.

`tests/fixtures/athlete_m/expected/phase4.json` pins:

- identity outcome `bound` with `fixture-athlete-m`;
- the unchanged Phase 3 blocker set;
- exactly `D2_DEMOGRAPHIC_AGE_MISMATCH`,
  `D2_THRESHOLD_LTHR_STALE_MISMATCH`, and
  `SCHEDULE_MISMATCH_CONFIRM` as required confirmations;
- account LTHR 148 bpm dated 2019-05-01 for control metric `hr`; and
- account age 19 versus intake age 45.

The golden also proves unresolved D2 selections reject approval, preserves
all Phase 1 negative assertions, retains the Phase 3 null-power/no-watts
contract, and checks the authenticated identity/resolution surface. The more
general Phase 3 `POWER_BASIS_NONE_CONFIRM` is removed once the inspected LTHR
provides the account-specific HR decision.

## Deviations and remaining live gate

There is no offline contract deviation. The real TrainingPeaks session/browser
transport, scheduled canary, and live identity/inspection proof are expressly
the Phase 4 rollout's human-scheduled LIVE gate and are not fabricated here.
The optional webhook exchange endpoint for probes was not needed because the
read-only worker verifies and consumes signed capabilities directly. Apply
grant issuance remains deliberately absent/refused until Phase 5.

## Verification evidence

- Focused worker, D2, review, fulfilment-state, and legacy-gate suite:
  **92 passed**.
- Complete sandbox suite: **2,522 passed, 87 skipped, 21 warnings, 0
  failed**.
- Opt-in production acceptance with a writable `HOME`: **36 passed, 4
  skipped, 4 failed**. The four failures are the unchanged mandatory PDF
  presence/structure checks for Gravel Full Gym and Masters in this sandbox,
  which has no PDF engine. The Roadie HTML fallbacks and package cases account
  for the four expected skips.
- The isolated Phase 3 baseline and Phase 4 fixed-clock acceptance builds each
  contain exactly **253 ZWOs** (89 Gravel, 77 Masters, 41 Road Fondo, 46 Road
  Climb). Their sorted per-file manifests are identical and hash to
  `e82ebcd550b7cbedc46b9c0d8ae4ff2a955bbc690a26231f110797344c885c7c`.
- `python3 -m compileall -q delivery/trainingpeaks webhook athletes/scripts`
  and `git diff --check` pass.

The sandbox-forbidden loopback/PDF checks and the scheduled live read-only
canary remain external verification items. No push is part of this phase.

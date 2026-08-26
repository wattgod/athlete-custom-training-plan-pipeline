# Phase 5 TrainingPeaks mutation implementation

Status: **implemented behind a release gate; production capability remains disabled**.

The Phase 5 kernel lives in
`delivery/trainingpeaks/phase5_service.py`. It adds:

- exact order, athlete, revision, model-seal, action, canonical contract digest,
  approval-snapshot digest, and release-manifest binding;
- signed capabilities exchanged for short-lived signed execution grants;
- athlete-scoped leases, monotonically increasing fencing tokens, and
  cancellation epochs;
- durable accepted/running/succeeded/failed attempt records;
- durable mutation intents before transport writes;
- landed remote IDs and contract-wide readback receipts;
- execution replay for an already-issued grant, one-time action-authorization
  exchange, and fencing of older workers;
- cancellation quiescence and separately signed, typed compensation rollback;
- `APPROVED -> APPLYING -> APPLIED` only after exact complete readback; and
- a credential-free, zero-write browser-transport dry-run projection.

The reviewed Playwright bridge is implemented in
`delivery/trainingpeaks/playwright_transport.py`, with its canonical entrypoint
at `tools/tp_phase5_execute.py`. The server process checkpoints the complete
mutation-intent set before starting the browser runner, stages exact contract
bytes with mode `0600`, suppresses browser-process output, accepts only an
exact contract/athlete/action/operation-bound receipt, and removes raw staging
artifacts after ingestion. The browser payload and Playwriter adapter are:

- `tools/tp_phase5_browser_payload.js`
- `tools/tp_phase5_playwriter_cli.mjs`
- `tools/tp_phase5_playwriter_run.js`

The payload currently advertises only `workout_upsert` and
`calendar_note_upsert`, matching the canary policy. Its fake-remote harness
proves protected-item preservation, RPE creation, HR-structure update,
targeted delete, ambiguous-POST reconciliation, and exact rollback. This is
offline evidence only; it does not open the live gate.

Global writes default off. Before rollout, a server-owned canary lane may be
enabled with `GG_TP_CANARY_ENABLED=1` and an exact
`GG_TP_CANARY_ATHLETE_IDS` allowlist. It additionally requires a `canary_`
order, a protected `keep` operation, approved resource kinds, and a bounded
mutation count. This lane is not the public plugin capability flag.

Focused evidence is in
`delivery/trainingpeaks/test_phase5_service.py`. It covers exact binding,
canonical `apply_contract/v1` schema validation at exchange, every operation
substitution class, stale approvals, expiry, cancellation, partial execution
resume, authorization replay, readback mismatch, mandatory pre-mutation
intents, privacy, and signed rollback.

## Action authorization contract

Mutation capabilities are closed-shape, HMAC-signed action authorizations.
They carry the canonical contract digest, exact current approval digest,
release-manifest digest, opaque authorization ID, opaque actor reference,
`trainingpeaks:athlete-calendar` scope, `iat`/`exp`, and a one-time exchange
JTI. Actions are namespaced and single-purpose:
`trainingpeaks.apply`, `trainingpeaks.verify`, or
`trainingpeaks.rollback`. Raw credentials never belong in claims or durable
mutation records.

Exchange re-runs the generated `apply_contract/v1` JSON Schema and semantic
validator before taking the `APPROVED -> APPLYING` transition, then compares
the canonical bytes to the signed digest. Any operation substitution,
reordering, addition, deletion, payload/before-image/rollback change, approval
drift, release drift, action mismatch, or authorization replay fails closed.
The resulting execution grant retains only the bounded authorization
references needed by the worker.

Rollback has no Boolean command-line bypass. A rollback call uses a fresh,
short-lived `trainingpeaks.rollback` authorization with its own authorization
ID and JTI, bound to the same exact contract, approval, release, actor, and
scope.

## Gates that still block production enablement

Do not enable TrainingPeaks read/write compatibility flags until all of these
are attached to the inspected commit:

1. A real transport implements every contract kind it advertises and calls
   the Phase 5 checkpoint boundary for each mutation.
2. Its generated browser dry-run proves zero external writes and a complete
   receipt for the canary contract.
3. A named disposable fixture athlete proves identity binding, external-marker
   round trip, HR and RPE structures, create/update/delete, protected-calendar
   preservation, ambiguous-timeout reconciliation, and rollback/restore.
4. Credential/cookie, PII, health-data, and plan-payload logging is reviewed.
5. One approved sealed real order completes apply, readback, receipt, and
   confirmation through the production entrypoint.

## Playwright runner configuration

The entrypoint reads credentials and browser selection only from server
configuration. Never put these values in an order or command output:

- `GG_WORKER_CAPABILITY_SECRET` and optional
  `GG_WORKER_CAPABILITY_KID`;
- `GG_TP_EXECUTION_GRANT_SECRET` and optional
  `GG_TP_EXECUTION_GRANT_KID`;
- `GG_TP_PLAYWRITER_BIN`, an absolute reviewed Playwriter executable;
- `GG_TP_PLAYWRITER_BIN_SHA256` and `GG_TP_PLAYWRITER_VERSION`, binding its
  exact bytes and release;
- `GG_TP_PLAYWRITER_SESSION`, `GG_TP_PLAYWRITER_PROFILE`, and
  `GG_TP_PLAYWRITER_BROWSER_KEY`, binding the reviewed logged-in browser
  session, Chrome profile, and extension connection;
- either `GG_TP_LIVE_WRITES_ENABLED=1`, or the exact-target canary variables
  described above.

The short-lived capability is supplied by a mode-`0600` file. The runner
never accepts a browser executable, session, profile, or command from the
contract. It validates the configured runtime before every action, executes a
single private runner file instead of handing paths across persistent session
state, requires the exact HTTPS TrainingPeaks origin, and clears browser/session
globals before returning.

The retired `tools/tp_apply_driver.js`, the Phase 4 mutation refusal, and the
plugin compatibility flags must remain unchanged until those gates pass.

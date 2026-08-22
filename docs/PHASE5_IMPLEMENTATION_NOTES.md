# Phase 5 TrainingPeaks mutation implementation

Status: **implemented behind a release gate; production capability remains disabled**.

The Phase 5 kernel lives in
`delivery/trainingpeaks/phase5_service.py`. It adds:

- exact order, athlete, revision, model-seal, action, and contract binding;
- signed capabilities exchanged for short-lived signed execution grants;
- athlete-scoped leases, monotonically increasing fencing tokens, and
  cancellation epochs;
- durable accepted/running/succeeded/failed attempt records;
- durable mutation intents before transport writes;
- landed remote IDs and contract-wide readback receipts;
- restart/replay behavior for the same request and fencing of older workers;
- cancellation quiescence and operator-authorized compensation rollback;
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
expiry, cancellation, partial execution resume, replay, stale fencing,
readback mismatch, mandatory pre-mutation intents, privacy, and rollback.

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
- `GG_TP_PLAYWRITER_SESSION` for the reviewed logged-in browser session;
- either `GG_TP_LIVE_WRITES_ENABLED=1`, or the exact-target canary variables
  described above.

The short-lived capability is supplied by a mode-`0600` file. The runner
never accepts a browser executable, session, profile, or command from the
contract.

The retired `tools/tp_apply_driver.js`, the Phase 4 mutation refusal, and the
plugin compatibility flags must remain unchanged until those gates pass.

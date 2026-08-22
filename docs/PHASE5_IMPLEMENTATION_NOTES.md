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

The retired `tools/tp_apply_driver.js`, the Phase 4 mutation refusal, and the
plugin compatibility flags must remain unchanged until those gates pass.

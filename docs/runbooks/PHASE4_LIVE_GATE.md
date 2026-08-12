# Phase 4 live gate — identity and inspection, zero writes

Owner: coach plus pipeline operator. This gate is currently pending because the
live browser/session transport does not exist. `tools/canary_probe.py
--transport live` must continue to fail with `live transport not implemented —
Phase 4 live gate pending` until that transport is reviewed and deployed.

## Real-order gate

- [ ] Complete the [Phase 2 live gate](PHASE2_LIVE_GATE.md) prerequisites.
- [ ] Confirm the deployed worker exposes only `probe_athlete` and
      `inspect_account`; `apply`, `verify`, `rollback`, and execution-grant
      issuance still refuse before transport.
- [ ] Use one real order whose platform identity can be confirmed by the coach.
- [ ] From the authenticated review flow, issue a fresh probe capability through
      the server-configured codec. Never paste a capability or account identifier
      into logs, tickets, or repository files.
- [ ] Confirm an identity outcome is recorded. For `multiple-candidates`, the
      coach selects exactly one candidate on the page; for `not-coached`,
      `not-found`, or `unresolved`, approval remains blocked.
- [ ] For a bound identity, execute `inspect_account` once with a fresh inspect
      capability.
- [ ] Confirm the stored inspection has the complete D2 shape: account/coached
      flags, account identity, age, nullable FTP and date, nullable LTHR and date,
      expiry, workout count, observation time, and capability jti.
- [ ] Confirm any threshold/demographic/dormancy findings appear on the same
      revision's review page with typed resolution controls.
- [ ] Confirm the authoritative replay root contains succeeded v3 probe and
      inspect records for the attempts.
- [ ] Verify transport/audit evidence contains only probe and inspect calls and
      that TrainingPeaks calendar/account mutation counts did not change.
- [ ] Record a redacted gate result in the rollout PR or release record. Raw
      values remain only in authenticated state and worker audit storage.

Green means the identity is durably resolved as expected, the D2 inspection
shape and review findings are present, both replay records succeeded, all output
is redacted, and there were zero TrainingPeaks writes.

## Scheduled cheesehead canary live flip

The daily workflow runs fixture self-test mode today. After the live transport
has passed review:

- [ ] In repository Actions secrets, set `TP_CANARY_EMAIL` and/or
      `TP_CANARY_ATHLETE_ID` to the dedicated canary account locator.
- [ ] Set `GG_WORKER_CAPABILITY_SECRET` to the deployed worker's signing secret.
- [ ] Never echo, commit, or place those values in workflow inputs or artifacts.
- [ ] In repository Actions variables, set `CANARY_LIVE=true`.
- [ ] Manually dispatch **Daily TrainingPeaks Canary Probe** once.
- [ ] Require a zero exit, an uploaded `trainingpeaks_canary_probe/v1` artifact
      with every assertion passed, and succeeded probe/inspect records.
- [ ] Confirm again that the worker audit contains no mutation operation.
- [ ] Leave the daily schedule enabled. If it fails, set `CANARY_LIVE=false` and
      treat the live gate as closed until the transport or SPA drift is repaired.

The label `cheesehead` is safe for logs. Its email, TrainingPeaks athlete id,
credentials, and capabilities are secrets.

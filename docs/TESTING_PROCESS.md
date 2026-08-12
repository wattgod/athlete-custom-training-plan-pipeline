# Testing process

This is the recurring trust map for paid-order fulfilment. A green fast suite is
necessary but not sufficient: fixed fixtures catch regressions, real-clock jobs
catch calendar rot, read-only canaries catch worker-boundary drift, and human
gates retain approval authority.

| When | What runs | Owner | Failure action |
|---|---|---|---|
| Pull request | `test-pipeline.yml`: athlete unit/guard suite, recurring-process tool tests, and fixed-clock order acceptance with Chromium | Author; reviewer verifies evidence | Fix before merge. Date pins change only through the [golden refresh](runbooks/GOLDEN_REFRESH.md). |
| Nightly | `nightly-rot.yml`: repository-wide pytest with no global fixed clock, the same opt-in acceptance suite CI uses, and the real-today fixture-freshness gate | Pipeline maintainer | Triage next working session; stale pins get a dedicated refresh PR. |
| Daily | `canary-probe.yml`: Phase 4 fixture-mode signed capability → replay record → probe → inspect self-test, with a redacted JSON artifact | Pipeline operator | Treat failure as a closed worker gate. Live mode stays off until the [Phase 4 gate](runbooks/PHASE4_LIVE_GATE.md). |
| Daily/weekly | Existing checkout health, follow-up lifecycle, avatar judge, coverage sweep, and weekly test-pipeline schedules retain their current owners and scopes | Service/operator or quality owner named by workflow | Follow that workflow's issue/log path; do not hide failures in the customer channel. |
| Hourly on webhook host | `audit_fulfillment_states.py`: stale review/readback warnings plus critical apply/cancel/seal anomalies | Webhook host operator | Connect the critical nonzero exit to host alerting and investigate authenticated state before changing it. This does not run in GitHub Actions because production state is not there. |
| Per release | Synthetic lifecycle walk; human performs the approval click | Release operator + coach | Follow [release synthetic order](runbooks/RELEASE_SYNTHETIC_ORDER.md). Phase 4 stops honestly at `APPROVED`. |
| One-time live rollout | Real-order page approval and read-only identity/inspection | Coach + pipeline operator | Follow [Phase 2](runbooks/PHASE2_LIVE_GATE.md) and [Phase 4](runbooks/PHASE4_LIVE_GATE.md); close the gate on any mismatch. |
| Per incident | Reproduce with de-identified input, add the smallest deterministic fixture and regression, then add it to the appropriate recurring layer | Incident owner | Every incident becomes a fixture. No real name, email, account id, order id, credential, or health free text enters the repository. |

## Webhook-host state audit

The production image contains only the read-only audit tool. Install this on the
webhook host's crontab (the Docker image's persistent root is `/data`):

```cron
17 * * * * cd /app && /usr/local/bin/python /app/tools/audit_fulfillment_states.py --root /data/deliveries/orders --out /data/reports/fulfillment-state-audit.json >> /data/fulfillment-state-audit.log 2>&1
```

The audit exits nonzero for expired APPLYING authorization, unacknowledged
cancellation, unsealed approval, malformed state, or unavailable state root.
`BLOCKED_REVIEW` and pending D2 readback older than three days are warnings.
Artifacts and the human table pass through the shared external-state projection;
order references are hashed.

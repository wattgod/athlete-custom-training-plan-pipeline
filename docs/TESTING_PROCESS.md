# Testing process

This is the recurring trust map for paid-order fulfilment. A green fast suite is
necessary but not sufficient: fixed fixtures catch regressions, real-clock jobs
catch calendar rot, read-only canaries catch worker-boundary drift, and human
gates retain approval authority.

| When | What runs | Owner | Failure action |
|---|---|---|---|
| Pull request | `test-pipeline.yml`: athlete unit/guard suite, recurring-process tool tests, and fixed-clock order acceptance with Chromium | Author; reviewer verifies evidence | Fix before merge. Date pins change only through the [golden refresh](runbooks/GOLDEN_REFRESH.md). |
| Nightly | `nightly-rot.yml`: repository-wide pytest with no global fixed clock, the same opt-in acceptance suite CI uses, and the pin-age freshness gate (acceptance goldens fail past a 180-day-old pinned clock; athlete-m is spec-frozen and exempt) | Pipeline maintainer | Triage next working session; stale pins get a dedicated refresh PR. |
| Daily | `canary-probe.yml`: Phase 4 fixture-mode signed capability → replay record → probe → inspect self-test, with a redacted JSON artifact | Pipeline operator | Treat failure as a closed worker gate. Live mode stays off until the [Phase 4 gate](runbooks/PHASE4_LIVE_GATE.md). |
| Daily | `daily-drill.yml`: cancel yesterday's drill and any leftover same-day drill, submit today's signed WooCommerce order to Railway, run real generation and the real coach notification, then prove the review bundle exists and customer download still returns 409 | Coach + pipeline operator | The coach should receive one clearly synthetic **Daily Drill** order email. Triage any missing email or red workflow with the [daily drill runbook](runbooks/DAILY_DRILL.md). |
| Daily/weekly | Existing checkout health, follow-up lifecycle, avatar judge, coverage sweep, and weekly test-pipeline schedules retain their current owners and scopes | Service/operator or quality owner named by workflow | Follow that workflow's issue/log path; do not hide failures in the customer channel. |
| Hourly | `state-audit.yml` first curls production `/health` (schema file + review/download token keys) then calls Railway's authenticated `POST /api/cron/state-audit` | Pipeline operator | A 503 health or a critical audit finding makes the workflow red. Investigate authenticated state before changing it. |
| Per release | Synthetic lifecycle walk; human performs the approval click | Release operator + coach | Follow [release synthetic order](runbooks/RELEASE_SYNTHETIC_ORDER.md). Phase 4 stops honestly at `APPROVED`. |
| One-time live rollout | Real-order page approval and read-only identity/inspection | Coach + pipeline operator | Follow [Phase 2](runbooks/PHASE2_LIVE_GATE.md) and [Phase 4](runbooks/PHASE4_LIVE_GATE.md); close the gate on any mismatch. |
| Per incident | Reproduce with de-identified input, add the smallest deterministic fixture and regression, then add it to the appropriate recurring layer | Incident owner | Every incident becomes a fixture. No real name, email, account id, order id, credential, or health free text enters the repository. |

## Railway-native state audit

Railway service containers do not have an operator crontab. The production image
contains the read-only audit tool, and the webhook exposes it only through:

```text
POST /api/cron/state-audit
X-Cron-Secret: <Railway CRON_SECRET>
```

`state-audit.yml` calls that endpoint at minute 17 each hour. The audit returns
HTTP 500 for expired APPLYING authorization, unacknowledged cancellation,
unsealed approval, malformed state, or an unavailable state root. Ordinary drill
age warnings are suppressed because yesterday's drill is deliberately cancelled;
critical classes are never suppressed for drill orders. `BLOCKED_REVIEW` and
pending D2 readback older than three days remain warnings for real orders. The
response and Railway log entry pass through the shared external-state projection;
order references are hashed.

## Daily drill operator expectations

The workflow is disabled until repository variable `DRILL_ENABLED` is exactly
`true`. Once enabled, the coach receives a real Resend notification at
`NOTIFICATION_EMAIL` every day for athlete **Daily Drill**. The order is a
manual-delivery synthetic order, so the drill creates no TrainingPeaks write.
The workflow never opens the review link, waives a blocker, approves a revision,
or confirms delivery.

The previous UTC day's non-terminal drill is cancelled before today's order is
sent. A drill the coach has already taken to a terminal `CONFIRMED` state is left
alone. Clicking **Approve sealed revision** is a real human approval and makes
the sealed release authoritative; it does not manufacture application evidence
or auto-send athlete-facing prose. Continue only through whatever downstream
human delivery/confirmation controls the deployed phase legitimately provides.
See [Daily Drill](runbooks/DAILY_DRILL.md).

# Plan-Truth verified handoff

Date: 2026-07-14  
Branch/worktree: `plan-truth-fixes` at `/private/tmp/claude-501/-Users-mattirowe/96b0c48e-8e4e-4dfe-afa4-b65e20b53138/scratchpad/wt-plantruth`

## Executive gate

Sol's original verdict was **NO-GO**, and live-code verification confirmed the
material findings. I applied the bounded mechanical fixes directly to the
worktree. The repaired athlete pipeline is green, but the branch should remain
**HOLD / NO-GO** until the carb heuristic's missing policy inputs and edge-case
matrix are explicitly accepted or implemented.

The remaining hold is not a test failure. It is a policy-validity gap: duration
does not alter the hourly target, goal affects both assumed IF and a second goal
adjustment, and heat, sweat rate, GI history, and actual gut-training state are
not modeled. Current edge outputs are:

| Case | Target | Range | Note |
|---|---:|---:|---|
| Heather, 61 kg / 230 W / 5.6 h podium, tolerance unknown | 63 g/hr | 56–70 | conservative ceiling flagged |
| 80 kg / 310 W / 5.6 h podium, trained to 80 | 69 g/hr | 62–76 | higher than Heather, but modest |
| 100 kg / 600 W / 4 h podium, tolerance unknown | 80 g/hr | 73–87 | new all-athlete unknown-tolerance ceiling |
| 80 kg / 310 W / 16 h podium, trained to 80 | 69 g/hr | 62–76 | shows duration-independence |
| 70 kg / 300 W / 6 h compete, demonstrated 20 | 30 g/hr | 23–37 | internally consistent; coach warning emitted |

## Verified findings and what changed

1. **G6 cooldown semantics were reversed — confirmed and fixed.** The repo's
   ZWO convention is `PowerLow=start`, `PowerHigh=end`. The invariant now enforces
   `PowerHigh <= PowerLow <= main_power`. Name-only matching was also too broad;
   variable endurance, terrain, surge, FatMax-with-sprints, and blended sessions
   are structurally excluded and tested as untouched.

2. **Captured tolerance never reached policy — confirmed and fixed.** The live
   JSON-to-markdown adapter now carries `training_fuel` when supplied, profile
   tolerance is passed into `FuelingPrescription`, and ambiguous text such as
   `2 gels per hour` is not parsed as `2 g/hr`.

3. **Low tolerance could put the target outside its own range — confirmed and
   fixed.** The final range is computed after every clamp and always contains the
   target. Missing tolerance now applies a conservative ceiling to every athlete,
   not just sub-65 kg riders.

4. **Independent shipping fuel claims survived — confirmed and fixed.** The
   pre-plan ZWO, race-day ZWO, coaching brief, guide personalized card, and the
   rendered advanced-archetype execution line now project the prescription. The
   retired parallel guide calculation was removed. Static education ranges remain
   only under explicit `General Guidance` labels.

5. **Legacy `fueling.yaml` regeneration lost workout tags — confirmed and fixed.**
   `prescription_from_fueling()` now adapts the legacy `carbohydrates` block into
   a projection without calculating a new race target.

6. **`FUEL_TAGS == {}` is safe — confirmed.** No production caller indexes those
   keys. Updating `test_compliance_rules.py` was legitimate, not test weakening;
   the replacement artifact coverage was simply too narrow and has now been
   expanded.

Nuance on Sol's literal scan: most numeric `fueling` fields in the archetype data
are currently dormant because the description renderer ignores that field. They
remain architectural debt, but the one numeric value in an `execution` field did
ship and was removed.

## Verification

- Focused fuel/artifact/compliance/ZWO suite: **74 passed, 4 skipped**.
- Full athlete pipeline: **1,136 passed, 53 skipped**.
- Changed Python modules compile; `git diff --check` is clean.
- New webhook training-fuel passthrough test: **1 passed**.
- Whole webhook module: **165 passed, 15 pre-existing failures**. The failures
  reproduce unrelated cached module-level data-directory/environment assumptions,
  an existing test-endpoint auth mismatch, date parity, and old mock signatures.
  None touches the new nutrition passthrough.

All repair edits are currently uncommitted in the named worktree. The handoff spec
file remains untracked there, as it was before the repair.

## J1 executor contract

### Files

- New: `webhook/fulfillment_state.py` — pure stdlib, no Flask dependency.
- Change: `athletes/scripts/generate_athlete_package.py`.
- Change: `athletes/scripts/intake_to_plan.py`.
- Change: `webhook/app.py`.
- Change: `webhook/tests/test_webhook.py` plus focused pipeline state tests.

The pipeline may import the shared module by adding the repo's `webhook/`
directory to its module path. Keep all schema validation and transition rules in
that one module; do not duplicate them in the generator and Flask app.

### Canonical locations

- Generation staging: `athletes/<athlete-id>/fulfillment_status.json`.
- Persistent authority: `DATA_DIR/deliveries/<normalized-athlete-id>/fulfillment_status.json`.
- `persist_deliverables()` copies the staging file to the persistent location.
- Exclude the status file from both customer and full-package ZIPs; otherwise a
  downloaded ZIP becomes a stale snapshot after approval/application.

### Schema

```json
{
  "schema_version": 1,
  "athlete_id": "heather_gray",
  "generation_revision": 1,
  "status": "BLOCKED_REVIEW",
  "blocking_issues": [
    {
      "id": "R05",
      "source": "block_compliance",
      "severity": "CRITICAL",
      "message": "Intensity count: W8 ..."
    }
  ],
  "approval": null,
  "waiver": null,
  "application": null,
  "confirmation": null,
  "history": [],
  "updated_at": "server-generated ISO-8601"
}
```

Every write is atomic (`fsync` + `os.replace`). Every read-modify-write transition
uses a per-athlete `fcntl.flock` lock because Railway runs two gunicorn workers.
Malformed or missing persistent state fails closed.

### Transitions

| From | To | Requirement |
|---|---|---|
| successful package | `GENERATED` | workouts, guide, and summary completed |
| `GENERATED` | `BLOCKED_REVIEW` | one or more structured critical issues |
| `GENERATED` | `APPROVED` | authenticated coach review |
| `BLOCKED_REVIEW` | `APPROVED` | waiver covers every blocker, or regeneration clears all blockers |
| `APPROVED` | `APPLIED` | coach records platform, identity, and nonempty evidence/reference |
| `APPLIED` | `CONFIRMED` | customer confirmation email succeeds |
| `CONFIRMED` | `CONFIRMED` | idempotent response; never resend |

Regeneration increments `generation_revision` and invalidates previous approval,
application, and confirmation. Preserve prior records in `history`.

### Where blockers are created

- `generate_athlete_package.py`: after `validate_plan`, create one issue for each
  failed entry in `_compliance['rules']`. Do not parse `critical_score`; it is a
  passed/total string, not a failure count. Keep `NEEDS_REVIEW.txt` and the stdout
  marker temporarily for compatibility.
- `intake_to_plan.py`: add `RACE_UNMATCHED` when the A-race match method is `none`.
  Critical quality-gate failures append their structured issue before
  `copy_to_downloads()`.
- `RACE_STALE` is a reserved blocker ID only. J1 cannot honestly detect it until
  H1 defines provenance fields and a stale threshold.

### Operator API

Add authenticated `POST /api/fulfillment/<athlete_id>/transition`, protected by
the existing constant-time `X-Cron-Secret` check.

Approval without blockers:

```json
{"to":"APPROVED","coach":"matti@gravelgodcycling.com"}
```

Approval with waiver:

```json
{
  "to": "APPROVED",
  "coach": "matti@gravelgodcycling.com",
  "waiver": {
    "rule_ids": ["R05"],
    "reason": "Reviewed W8 and accepted/corrected the distribution."
  }
}
```

Reject empty coach/reason, unknown blocker IDs, partial waiver coverage, illegal
transitions, and client-supplied timestamps. The server supplies timestamps.

Application:

```json
{
  "to": "APPLIED",
  "coach": "matti@gravelgodcycling.com",
  "platform": "trainingpeaks",
  "evidence": "TP athlete 12345; workouts through race week verified"
}
```

A waiver never bypasses `APPLIED`; the customer email explicitly claims the plan
is live. Current Endure delivery does not automatically count as `APPLIED` because
coach approval is still pending.

### Confirm enforcement and email

In `/api/confirm/<athlete_id>`, immediately after ID normalization/validation and
before log lookup or `_send_email`:

1. Lock and load persistent state.
2. Return 409 for missing/malformed state or any status except `APPLIED`.
3. If already `CONFIRMED`, return 200 idempotently without sending.
4. Send the email while the transition is serialized.
5. On success, write `CONFIRMED` with message/provider metadata.
6. On failure, leave `APPLIED` so a retry is safe.

For `BLOCKED_REVIEW`, coach email subject plus HTML and plain-text headers must say
`ACTION REQUIRED`; none may contain `READY`. Clean `GENERATED` mail may say
`REVIEW REQUIRED`, but confirmation remains impossible until approval and apply.

### Named tests

- `test_r05_failure_writes_blocked_review_with_rule_id`
- `test_unmatched_a_race_writes_blocked_review`
- `test_clean_generation_writes_generated`
- `test_critical_quality_gate_appends_blocker`
- `test_status_file_persisted_but_excluded_from_both_zips`
- `test_blocked_email_is_action_required_and_contains_no_ready`
- `test_confirm_blocked_returns_409_without_sending`
- `test_confirm_generated_and_approved_return_409`
- `test_blocked_approval_requires_complete_waiver`
- `test_apply_requires_approved`
- `test_confirm_applied_sends_once_and_marks_confirmed`
- `test_confirm_email_failure_leaves_applied`
- `test_confirmed_retry_is_idempotent`
- `test_concurrent_confirm_sends_once`
- `test_missing_or_malformed_state_fails_closed`
- `test_regeneration_invalidates_prior_approval_and_application`

## Recommended order

1. Finish/accept the G1/G2/G6 merge gate described above.
2. J1 plus a minimal H1a contract defining future `RACE_STALE` inputs/threshold.
3. Add a persisted, versioned **PlanIR v0 skeleton** ticket.
4. G3 segment-first descriptions/XML.
5. Full H1 provenance, edition, and freshness logic.
6. G4 recurring-session ledger, including the live questionnaire source and the
   webhook JSON-to-markdown adapter—not only `intake_to_plan.py`.
7. G5 semantic consistency gate against PlanIR.
8. I1 platform-independent manifest.
9. I2 idempotent TrainingPeaks adapter/read-back.

The PlanIR v0 skeleton is the additional high-leverage improvement: without a
persisted schema owner before G3/G4, those tickets risk producing two more adjacent
models and G5 has no canonical object to compare artifacts against.

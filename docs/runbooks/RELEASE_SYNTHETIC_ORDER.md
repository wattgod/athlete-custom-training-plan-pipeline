# Per-release synthetic order walk

Owner: release operator; the coach owns the one approval click. The target walk
is `blocked → reviewed → approved → applied → verified → confirmed`, with every
transition backed by durable evidence and no customer data.

## Current release boundary

Phase 4 implements the scripted path through read-only inspection and the human
review/approval surface. Phase 5 apply, readback verification, release
components, and a safe confirmation sink do not exist yet. Therefore no current
release may claim the full synthetic walk: stop at `APPROVED`. Never substitute
the live TrainingPeaks account or the customer-email route to make later boxes
green.

## Checklist

- [ ] Start from a clean checkout of the release candidate.
- [ ] Run `daily-drill.yml` with `workflow_dispatch` and retain its redacted
      artifact. This proves the deployed signed intake, real generation, coach
      notification, review-bundle persistence, pre-approval 409, and previous-day
      cancellation path before the human walk begins.
- [ ] Run the fixed athlete-m Phase 4 fixture:
      `python -m pytest athletes/scripts/test_athlete_m_phase1.py -q`.
      This is scripted and must prove a durable `BLOCKED_REVIEW`, signed canned
      probe/inspection records, exact D2 findings, and refusal of premature
      approval.
- [ ] Run the fixture canary with an ephemeral 32-byte-or-longer
      `GG_WORKER_CAPABILITY_SECRET`, an isolated `GG_WORKER_REPLAY_DIR`, and a
      non-real `.invalid` `TP_CANARY_EMAIL`. This is scripted and read-only.
- [ ] Open the synthetic review page in the release environment and check every
      blocker, value, source, unit, and resolution. This review is human.
- [ ] Resolve only the fixture-defined items and click **Approve sealed
      revision** once. The click is the sole human state-changing step; scripts
      must not manufacture the approval snapshot.
- [ ] Prove the approval snapshot is complete and seal-bound, with no application
      or confirmation evidence.
- [ ] Stop here while Phase 4 is the deployed boundary.

The target per-release walk is therefore **daily drill + human review click +
normal delivery evidence + human send → CONFIRMED**. On the currently deployed
Phase 4 boundary, the honest release evidence ends at `APPROVED`; do not invent
`APPLIED` or `CONFIRMED` merely to complete the checklist. Once Phase 5 is live,
the same drill order may continue through the real downstream controls below.

After Phase 5 supplies a reviewed fake/canned mutation transport and a
non-delivering confirmation sink, extend the same release run with these gates:

- [ ] **Applied (scripted):** reconcile the sealed contract against the fake
      remote, persist every landed operation, and reach `APPLIED` only after the
      required set exists.
- [ ] **Verified (scripted):** read back the fake remote and match every required
      operation and singleton before recording verified evidence.
- [ ] **Confirmed (scripted sink):** exercise the confirmation transition with a
      fake mail provider that captures but cannot deliver; verify provider and
      state evidence.
- [ ] Exercise cancellation/rollback and a retry kill point in the same fake
      environment before declaring the release walk complete.

## Cleanup

- [ ] Delete only the isolated synthetic order directory, replay directory, and
      captured mail artifacts created for this run.
- [ ] Remove temporary environment variables and ephemeral signing material.
- [ ] Do not delete shared fixtures, production state, or any broad data root.
- [ ] Attach the redacted assertion summary to the release record. Keep raw
      fixture artifacts out of the repository unless they are deliberately
      promoted as reviewed regression fixtures.

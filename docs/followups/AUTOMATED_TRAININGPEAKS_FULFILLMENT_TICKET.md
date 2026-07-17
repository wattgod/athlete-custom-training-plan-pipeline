# Ticket: specify automated TrainingPeaks plan fulfillment

- Status: filed; not implemented by the shared-pipeline road adaptation
- Scope: cross-brand (`gravelgod` and `roadielabs`)
- Current contract: generate package, coach review/import, then explicit confirmation
- Decision owner: coaching operations and platform engineering

## Problem

The webhook does not apply plans to athlete TrainingPeaks accounts. It generates
the fulfillment manifest and package, after which a coach reviews and imports the
plan manually. The existing `TrainingPeaksAdapter` is a standalone library with
fake-server tests, not a production webhook fulfillment path.

Automating only the API call would bypass the current coach-review and approval
state machine, and would leave identity, retry, and rollback failures undefined.

## Required follow-up specification

Before implementation, define:

- credential ownership, rotation, and least-privilege storage;
- unambiguous athlete identity and account-linking behavior;
- the invocation point after package validation and coach approval;
- the transition into `APPLIED`, including who can authorize it;
- idempotency keys, retry/backoff behavior, and duplicate-plan prevention;
- partial-application recovery and rollback;
- audit logging, coach-visible failure notification, and manual fallback;
- brand-neutral behavior and test fixtures for both brands.

## Acceptance criteria

- A reviewed design names the state transitions and failure ownership.
- In-process fake-server integration tests cover success, retry, duplicate,
  partial failure, rollback, and manual fallback.
- No athlete receives an unreviewed plan.
- The existing manual workflow remains available throughout rollout.
- Production credentials are never required by unit or E2E tests.

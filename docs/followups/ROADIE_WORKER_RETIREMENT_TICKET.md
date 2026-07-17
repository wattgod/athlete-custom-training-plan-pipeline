# Ticket: retire or repoint the stale Roadie training-plan Worker

- Status: filed; not implemented by the shared-pipeline road adaptation
- Owner repository: `road-race-automation`
- Target: `workers/training-plan-intake/worker.js`
- Decision owner: Roadie Labs web/operations owner

## Problem

The live Roadie questionnaire posts directly to the shared
`athlete-custom-training-plan-pipeline` checkout. The older Worker still emails
and dispatches to `wattgod/training-plans-component`, but it is not referenced by
the live form. Leaving two apparent intake paths makes future maintenance and
incident response ambiguous.

## Authorized follow-up

In `road-race-automation`, verify all production and preview bindings, then choose
one explicit outcome:

1. retire the unused Worker, routes, secrets, and deployment configuration; or
2. repoint it to the shared checkout only if a documented consumer still needs a
   proxy.

Retirement is preferred when no consumer is found. Do not recreate plan dispatch
or athlete email delivery in the Worker.

## Acceptance criteria

- Repository-wide and deployment-level references to the Worker are inventoried.
- The decision and evidence are recorded in the owning repository.
- If retired, routes, secrets, docs, and deployment config are removed together.
- If repointed, it forwards the complete brand/intake contract and has a test
  proving Roadie orders reach the shared webhook exactly once.
- The live questionnaire continues to complete checkout successfully.

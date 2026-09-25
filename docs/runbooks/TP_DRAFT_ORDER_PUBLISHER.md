# Sealed-order TP DRAFT publisher (Card 2)

`tools/publish_tp_draft.py` is a library function with an injected transport.
There is deliberately no live browser adapter or CLI in this card. Importing
or testing it makes no TP calls. It only stages a `DRAFT` plan in the coach's
plan library and never writes an athlete calendar or fulfillment state.

## Input and review boundary

Supply the explicit paid order ID, canonical `fulfillment_status.json`, its
current `revisions/rN` directory, Card 1 package directory, a durable journal
path, an injected transport, and the exact target folder label. The package
must have `ready_for_review: true`, match a fresh rebuild from the sealed
source, and remain at the same model seal and release digest. `GENERATED` is
valid for a review DRAFT; final `APPROVED` is **not** required. `APPROVED` is
the later release decision after coach review.

Keep the journal outside the disposable package directory and on persistent
storage. Use one journal per order and generation revision. A later revision
needs a new journal; a journal never silently adopts a different package,
folder, order, or seal. A file lock serializes callers sharing the journal.

## Transport contract

An adapter must implement these methods using only the proven `plans/v1`
operations, in an authenticated, dedicated `app.trainingpeaks.com` browser
context:

| Method | Proven operation |
| --- | --- |
| `list_plans()` | `GET /plans/v1/plans`, raw array |
| `create_plan(body)` | `POST /plans/v1/plans` |
| `get_plan(plan_id)` | `GET /plans/v1/plans/{id}` |
| `update_plan(plan_id, body)` | whole-object `PUT /plans/v1/plans/{id}` |
| `list_workouts(plan_id, start, end)` | ranged `GET /plans/v1/plans/{id}/workouts/{start}/{end}` |
| `create_workout(plan_id, body)` | `POST /plans/v1/plans/{id}/workouts` |
| `delete_workout(plan_id, workout_id)` | `DELETE /plans/v1/plans/{id}/workouts/{workoutId}` |
| `list_notes(plan_id, start, end)` | ranged `GET /plans/v1/plans/{id}/calendarNote/{start}/{end}` |
| `create_note(plan_id, body)` | `POST /plans/v1/plans/{id}/calendarNote` |
| `delete_note(plan_id, note_id)` | `DELETE /plans/v1/plans/{id}/calendarNote/{noteId}` |

The note delete call was verified on a disposable plan with a 1 → 0 note
readback on 2026-09-18, recorded in the private TrainingPeaksPublisher
`plan-builds/_shared/RUNBOOK.md`. All adapter list methods must return full
arrays; an unavailable, paginated, or incomplete readback must raise. GETs
need `credentials: include`. Treat 401, timeouts, empty error bodies, and
unknown response shapes as errors. Pace writes at least 120 ms apart in the
browser adapter.

The publisher writes an intent to its fsynced journal before every remote
mutation. On retry it finds a possibly created plan by its order-specific
DRAFT title, then reconciles each workout and note by full content. It
deletes extra or outdated cards in the same plan ID, adds missing cards, and
verifies the complete workout/note multiset and `isDynamic` by fresh readback.
It does not assume a successful HTTP response means content persisted.

## Folder capability boundary

The current captured API material does not include a folder write or folder
readback contract. `publish(...)` therefore returns `folder_pending` after
content verification when no folder verifier is supplied. It cannot report
`verified` without an injected `folder_verifier(plan_id, expected_folder)`
returning a proof with `verified: true`, the exact `plan_id`, exact `folder`,
and nonempty `evidence`. A mismatch fails closed and keeps the journal at
`folder_pending`.

The folder verifier is an integration responsibility. A coach may inspect
the TP UI and record a dated, plan-ID-specific screenshot or UI observation
as the evidence in an injected verifier; do not infer folder membership from
the plan title or from the existence of a folder elsewhere in the account.
No live-mode success or release claim should use a bare test stub as proof.
The target folder placement mechanism remains unimplemented until its
actual TP contract or a reviewed manual procedure is established.

The return status describes only the plan-library draft. It is never an
`APPLIED`, `CONFIRMED`, or athlete delivery receipt.

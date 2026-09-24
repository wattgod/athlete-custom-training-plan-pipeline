# Motoren: custom-plan fulfillment at ten orders/day

Status: execution in progress, 2026-09-24. Ten paid custom orders/day is a
target to prove, not a measured capacity claim. Card 1 is implemented; the
coach has authorized work on the remaining cards and a klokkaskaddla test.
This is not authorization to bypass the separate Phase 5 athlete-calendar
release gate or to send athlete messages.

## Decision and product boundary

Keep the existing generator, canonical training model, PlanIR, TP manifest,
guide renderer, fulfillment state, release seal, and offline apply contract.
Finish the **order-bound delivery boundary** around those artifacts instead of
introducing another plan generator. In the standard TP delivery path, a custom
paid order is complete only when the athlete receives the approved plan and
matching guide and the provider readback/confirmation is recorded. Explicit
`FULFILLED_EXTERNALLY` closure remains a separate, truthful manual fallback.
A DRAFT Dynamic Plan in the coach's TP
library is a reviewable intermediate artifact, not completed fulfillment.

The first operating mode remains coach approval. The desired coach action is
to inspect one order-specific review packet, repair named exceptions, then
authorize release of that exact revision. The machine must never silently
waive a ratified training rule, invent athlete/race facts, or call a library
draft an athlete delivery. AE rules in `docs/ALGORITHM_EVIDENCE.md` remain the
training authority; training changes cite the corresponding AE IDs.

## Evidence and current state

- `athletes/scripts/generate_athlete_package.py` builds the guide from the
  canonical model and creates PlanIR/TP-manifest projections. The paid-order
  path in `athletes/scripts/intake_to_plan.py` adds review blockers and an
  offline apply contract.
- `webhook/app.py:persist_deliverables` copies order artifacts into a revision
  directory and `webhook/fulfillment_state.py:finalize_transitional_release`
  seals them. `verify_release_manifest` checks the state, model seal, release
  digest, and artifact bytes. These are the authority for a new adapter.
- `tools/build_tp_plan_payload.py` already builds workout and note payloads,
  exclusions, and ae-lint findings from athlete manifests. It is not yet
  bound to a sealed paid order; W00 exclusions currently require manual
  disposition. A sealed revision may not contain `plan_dates.yaml`, so a new
  adapter must derive plan day one from sealed material or fail explicitly.
- `athletes/scripts/trainingpeaks_delivery.py` still instructs the coach to
  import dated ZWOs and place each day by hand. Phase 5 TP calendar mutation
  remains disabled behind the documented release gate in
  `docs/PHASE5_IMPLEMENTATION_NOTES.md`. TP **plan-library** publishing is a
  separate operation and must get its own scoped transport/receipt.
- `webhook/app.py:_start_job_thread` starts an unbounded per-order thread;
  job writes are process-local locked while Gunicorn runs two workers. Durable
  records and a stuck-job sweep exist, but a ten-order burst has not been
  measured for duplicate ownership, throughput, or coach workload.
- The existing order-acceptance suite proves several generated artifacts and
  guide facts. It does not prove live TP delivery or ten-order capacity. The
  live health endpoint reported a healthy deployed service on 2026-09-24,
  with zero successful Endure deliveries; that is not TP fulfillment proof.

`docs/SPEC_DELIVERY_LAYER.md` is a useful older design, not a literal
inventory of what is missing today: some of its DeliveryIR functions now live
in the canonical model, renderer, and manifests. Reuse and test those first.

## Invariants for every card

1. The order ID and generation revision, not athlete name or email, identify
   the release. Two orders for one athlete cannot share authority or receipts.
2. The canonical paid-order state is
   `/data/deliveries/orders/<order>/fulfillment_status.json`; a copied athlete
   state is not authority. A model seal/release digest mismatch stops work.
3. Built artifacts remain available to the coach after a quality failure,
   but a non-waivable blocker cannot be approved. The paid order is never
   silently discarded, and internal failures are loud to the coach, not the
   athlete (`.claude/skills/order-safety/SKILL.md`).
4. No provider write before exact athlete identity, exact sealed revision,
   an operation journal, and the applicable canary authorization. A DRAFT
   library plan may be staged from `ready_for_review` before coach approval;
   athlete-calendar application requires exact revision approval. Protected
   calendar items are never overwritten by a library-plan operation.
5. Plan and guide must describe the same athlete, goals, events, schedule,
   strength, fuel prescription, and revision. All TP content must reconcile
   with the sealed source; exclusions need an explicit coach disposition.
6. A TP library DRAFT, an APPLIED athlete calendar, and CONFIRMED athlete
   delivery are distinct states. None implies the next.

## Work cards and order

### Card 1 — sealed-order Dynamic Plan package (first Sol PR)

**Why:** Make the existing payload builder safe and useful for paid custom
orders now, without requiring live TP authority.

**Owns:** a small offline adapter/CLI in `tools/` plus focused tests. Input is
an explicit paid order ID, canonical order-state path/root, and immutable
revision directory; no athlete-name lookup. Verify the sealed release using
`verify_release_manifest` before reading any artifact. Reuse
`build_tp_plan_payload.py` to emit `plan_payload.json`,
`notes_payload.json`, `exclusions.json`, and `lint.json`. Add a machine-readable
coverage receipt bound to `order_id`, `generation_revision`, `model_seal`,
`release_manifest_digest`, and the sealed HTML plus optional customer PDF
guide digests. Identify which guide file the customer would receive. Compute deterministic
plan day one from the sealed PlanIR/TP manifest or reject ambiguous input.
The receipt must classify every source session and note as included,
re-dated by a documented rule, or excluded with a named W00/manual action;
it must not call a blocked source approvable. Expose a single `ready_for_review`
Boolean or equivalent, not `approved`/`delivered`. The receipt is evidence,
not authority: every later publisher must revalidate it against the current
canonical order state and seal immediately before any remote operation.

**Must not change:** live TP, the athlete calendar, guide publication,
fulfillment state, checkout, coach approval, or training methodology. Do not
add a parallel plan model or permit an allowlist to suppress a non-waivable
AE-lint failure. Preserve the existing standalone payload CLI for non-order
draft use.

**Acceptance:** tests reject stale revision, edited guide/model, mismatched
order ID, missing source artifact, unresolved lint failure, and ambiguous
day one; two orders for one athlete yield distinct receipts. A fixture with
W00 sessions/notes accounts for each item without silently dropping it.
Included payload dates, control targets, duration, and note content reconcile
to the sealed manifests. The output is deterministic for identical sealed
inputs, and failure leaves no stale `ready_for_review` payload. Run focused
tests, the full unit/guard suite, and order acceptance in CI.

**Recovery:** leave source release untouched; rerun into a new output
directory after a regenerated, resealed revision. Parent integration review
checks the diff and the complete source-to-payload count.

### Card 2 — resumable TP Dynamic Plan library publisher

Depends on card 1. Consume only a sealed `ready_for_review` package. Persist
intent before each remote action, bind remote plan/object IDs to order and
release, and read back workouts, notes, folder, and `isDynamic`. Reconcile an
ambiguous POST before retry; resume after browser/session loss or restart.
Plan-library publication must not transition the paid order to APPLIED or
CONFIRMED. Reuse reviewed Phase 5 transport/journal components only where
their contracts actually cover plan containers; do not conflate them with
athlete-calendar writes. The coach reviews the library DRAFT before approval;
card 3 consolidates the existing seal-bound approval, not a second state.

Acceptance: injected-transport tests for duplicate requests, partial notes,
ambiguous timeout, expired session, stale revision, and readback mismatch;
zero duplicate containers/entries and no false success. Live write remains
off until a separately authorized canary.

### Card 3 — one coach review/release packet

Depends on cards 1–2's receipt contract; can begin read-only before live TP
publishing. Present the exact plan, matching guide/PDF, assumption provenance,
quality blockers, W00 dispositions, TP readiness, and week-one/middle/race-
week spot checks in one order view. One approval binds the exact model seal,
guide digest, payload receipt, and release digest. Regeneration invalidates
approval. Hosted-guide access and athlete delivery/confirmation receive
separate evidence; no guide URL is invented. The guide publishing policy in
`docs/SPEC_DELIVERY_LAYER.md` remains a coach decision before automation.

Acceptance: deliberate plan/guide drift, broken guide link, unaccounted
content, identity ambiguity, or unresolved blocker prevents release. A
library draft alone never confirms the customer order. Coach can repair and
regenerate without losing the paid order.

### Card 4 — bounded job ownership and recovery

Can proceed independently after card 1's receipt format is stable. Replace
per-order unbounded thread spawning with a bounded worker claim/lease that is
atomic across the two web processes, while preserving order-scoped durable
state, idempotency-before-long-work, retries, and coach alerts. Capture queue,
generation, review-wait, publication, and confirmation durations separately.

Acceptance: two concurrent processes/sweepers claim one job once; restart
recovery neither duplicates artifact revisions nor sends duplicate delivery;
ten queued synthetic orders drain under a stated, measured resource/time
budget with no lost jobs. No capacity estimate is published before this run.

### Card 5 — production-equivalent cohort and authorized canary

Depends on cards 1–4. Replay ten varied, privacy-safe orders (short/long
runway, constrained schedule, unknown FTP, HR/RPE, full-gym/no-strength,
multi-A races, repeat buyer). Include deliberate failure injections and
coach repairs. Then authorize a disposable TP plan-library canary, verify
folder/workout/note/`isDynamic` readback, and separately satisfy the existing
Phase 5 athlete-calendar canary gate before any automatic calendar delivery.

Exit bar: every order reaches a truthful terminal state or named, alerted
repair state; zero unexplained session/note omissions; plan, guide, and TP
readback agree; no manual artifact editing; measured coach minutes/order,
exception rate, queue age, and recovery time are reported. Run a ten-order
burst and a three-day, 30-order soak. **Proposed business release targets**
(not current measurements): every clean order confirmed within the existing
24-hour promise, no duplicate remote entries or missing workouts/notes, and
no more than 60 minutes/day of coach handling for ten clean orders. A blocked
order must alert the coach and retain its artifact rather than count as a
successful delivery. Include actual athlete-calendar placement in the timed
path; a library DRAFT alone does not satisfy the target. Only then call the
product ready for ten paid orders/day. Enabling athlete-calendar auto-apply
still requires the separate Phase 5 authorization and canary proof; if that
gate exposes gaps, file bounded repair cards rather than bypassing it.

## Execution checkpoint

Card 1 landed in `3f91d19d`. Cards 2–4 now have offline implementations and
tests. Card 2's publisher has no live TP adapter or proven folder-placement
contract; it returns `folder_pending` without exact folder evidence. Card 3's
existing coach approval now binds the exact ready TP package receipt and guide;
its packet still blocks release when W00 disposition, verified DRAFT, identity,
or other required evidence is missing. Card 4's bounded workers passed
cross-process claim, sweep, and restart tests; review, publication, and confirmation durations
remain uninstrumented.

Card 5's first real offline ten-order replay sealed all ten in 43.019 seconds
with complete session/note coverage, but **0/10** were ready for review. All
were honestly `BLOCKED_REVIEW`, including 47 hard-minute-floor findings; see
`docs/reports/2026-09-24-ten-order-rehearsal.md`. The bounded repair diagnosis
is in `docs/reports/2026-09-24-hard-minute-floor-repair-card.md`; it needs a
ratified accounting ruler and novice-state design before generator changes.
The three-day soak and live TP readback remain open.

The klokkaskaddla preflight found the existing plan-library DRAFT is stale,
unsealed, and lint-failing, with an unresolved September 26 race conflict; see
`docs/reports/2026-09-24-klokkaskaddla-canary.md`. No new TP or athlete-calendar
write is justified from that source. A DRAFT alone never counts as delivery or
ten-orders/day proof.

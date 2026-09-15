# Endure purchased-plan delivery

This path moves one coach-approved, sealed custom plan into Endure. It does not
change the default platform and it never falls back to TrainingPeaks silently.

## Pilot boundary before checkout

- The ordinary store checkout remains TrainingPeaks by default.
- Enroll only a buyer who has agreed to the Endure pilot by adding the exact
  tuple `gravelgod:training_plan:custom:buyer@example.com` to the
  comma-separated `ENDURE_PLAN_PILOT_BUYERS` Railway variable. Do not enroll
  Roadie Labs or XC Ski Labs buyers in this pilot.
- `ENDURE_DELIVERY_URL` and `ENDURE_DELIVERY_SECRET` must both be configured or
  the checkout stays on TrainingPeaks even when the buyer tuple is present.
- Checkout must return to
  `/training-plans/success/?session_id=...&delivery=endure`, where the buyer is
  told that Endure opens the reviewed first block, the guide carries the full
  plan, manual workout upload is the dependable data path, and the purchase
  does not start ongoing coaching.
- A plan-only buyer does not receive later blocks generated from live athlete
  data. Ongoing coaching uses a separate coached plan after explicit consent;
  otherwise continuation requires a future immutable prescription import.

## Normal path

1. Confirm the order is `APPROVED` and `delivery_platform` is `endure`:

   ```sh
   curl -H "X-Cron-Secret: $CRON_SECRET" \
     "$PIPELINE_URL/api/fulfillment/$ORDER_ID/status"
   ```

2. Stage the exact approved release. Before approval, persistence creates
   `endure_first_block.json`, seals its bytes in the release manifest and model
   seal, and presents the same release identity for coach approval. Staging
   reopens that verified artifact rather than deriving a new representation.
   Endure verifies its digest before creating or resuming one order-bound
   athlete, invitation, plan, and draft first block. It does not call another
   plan engine or fuzzy-map the purchased prescription:

   ```sh
   curl -X POST -H "X-Cron-Secret: $CRON_SECRET" \
     "$PIPELINE_URL/api/fulfillment/$ORDER_ID/stage-endure"
   ```

3. Open the returned Endure review URL. Review the first block on its sealed
   Monday start date and schedule it. Moving the block requires an explicit
   plan revision; approval will not silently shift its dates. Endure must report an exact
   one-for-one calendar match, including Rest and Strength operations, source
   operation identities, dates, types, titles, descriptions, durations,
   nullable planned TSS, and ordered workout steps. A coach edit is allowed,
   but unchanged workouts retain their source prescription and every actual
   change is stored as a before/after coach revision.

4. Verify the calendar and send the athlete one access email:

   ```sh
   curl -X POST -H "X-Cron-Secret: $CRON_SECRET" \
     "$PIPELINE_URL/api/confirm/$ORDER_ID"
   ```

5. Read status again. `CONFIRMED` is valid only with the exact Endure receipt,
   first-block digest, calendar verification, recipient digest, and Resend
   evidence.

6. Immediately after confirmation, bind the live Stripe payment to both
   production systems with the diagnostic verifier. It accepts one
   already-enrolled `cs_live_*` buyer and emits only hashed identifiers. Run it
   before a pending invitation is accepted; an account whose coaching
   relationship was already accepted at staging is also supported:

   ```sh
   ENDURE_PILOT_ORDER_ID="$ORDER_ID" \
   EXPECTED_PIPELINE_SHA="$EXPECTED_PIPELINE_SHA" \
   EXPECTED_ENDURE_SHA="$EXPECTED_ENDURE_SHA" \
   ENDURE_PILOT_RECEIPT_PATH="/private/tmp/endure-live-purchase-receipt.json" \
   python3 tools/verify_endure_live_purchase.py
   ```

   The process also requires live `STRIPE_SECRET_KEY`, `CRON_SECRET`, and
   `ENDURE_DELIVERY_SECRET` environment variables. The pipeline status GET may
   revoke release authority if its seal no longer matches, and Endure's
   readiness GET may backfill a missing email on the already-linked athlete;
   those are existing fail-closed integrity reconciliations, not new delivery
   actions. A pass proves pinned
   deployments, payment, routed and sealed pipeline confirmation, accepted
   Resend attempt, recipient identity binding, and Endure's exact calendar
   readback. It does not enroll a buyer, stage or activate a plan, send email,
   create an account, accept an invitation, clean anything up, authorize a
   change to `ENDURE_PLAN_PILOT_BUYERS` or `DELIVERY_TARGET_DEFAULT`, or prove
   the first-week training loop. Verify the athlete and coach loop separately.
   Never paste raw status JSON into tickets or logs; it contains the live
   invitation capability.

## Failed staging and safe retry

Endure releases the order's compare-and-swap staging lease immediately when a
stage fails. The pipeline performs at most one retry for transport errors or a
5xx response. If the retry encounters only a stale "already in progress"
response, the pipeline retains the first actionable server error for the
operator. After a returned stage failure, retry without waiting 15 minutes or
hand-editing the staging row. A truly concurrent request still owns its lease
and must be allowed to finish.

Any legacy stage without `first_block_digest` is an integrity failure. Do not
reclaim or edit it in place. An operator must first quarantine or remove the
exact stale stage, regenerate a fresh artifact-bound revision, review it, and
approve that revision before staging again.

## Deployment ordering and rollback

1. Apply and verify the Endure migration before merging application code. It
   adds nullable, SHA-256-formatted
   `purchased_plan_delivery_stages.first_block_digest`, widens the two planned
   load columns to `numeric(7,2)`, and replaces the atomic calendar-activation
   function. The transaction can briefly lock those live tables, so use the
   normal production change window and stop on any SQL error.
2. Deploy Endure's exact-import contract.
3. Deploy the pipeline serializer and retry correction.
4. Run a test-mode fake-order stage, approve it in Endure, and verify calendar
   readback before any email action.

   The operator-only test route accepts an explicit per-order target, so this
   canary does not require changing `DELIVERY_TARGET_DEFAULT` or enrolling a
   real buyer:

   ```sh
   curl -X POST -H "X-Cron-Secret: $CRON_SECRET" \
     -H "Content-Type: application/json" \
     "$PIPELINE_URL/webhook/test" \
     --data @/private/tmp/endure-canary-request.json
   ```

   The request must include `"delivery_target":"endure"`, a valid inline
   `questionnaire` (a stored `intake_id` is rejected), and the paired disposable
   identity expected by the purchased-plan browser canary: `order_id` must be
   `codex-pilot-YYYYMMDDHHMMSS-8hex`, the email must be
   `endure-pilot-YYYYMMDDHHMMSS-8hex@example.com`, and the stamp must be less
   than ten minutes old. Both the outer request and questionnaire must use that
   email and the exact name `Endure Pilot Rider`; `questionnaire.race_name` and
   the first `questionnaire.races[].name` must contain `Pilot`. The route rejects
   mismatched, future, stale, or already-processed identities before storing the
   intake, and leaves the store default unchanged.

For an emergency rollback, deploy the previous applications and leave the
compatible schema changes in place. Do not narrow the load columns, drop the
digest, or restore the older function while four-part release receipts may
exist; those destructive changes require a separate, data-audited migration.

## Unknown Resend outcome

The pipeline saves the Resend key, exact message fingerprint, release, athlete,
plan, block, recipient digest, and calendar verification before making the
provider request. A retry waits for the two-minute local lease and reuses the
same key and message only inside the provider's 24-hour idempotency window.
Outside that window it stops for provider reconciliation; do not hand-edit the
state or send the email again.

Use the status endpoint or coach review page to copy the exact `idempotency_key`
and `payload_digest`, then inspect that key in Resend.

If Resend shows the message was delivered, record the provider message ID:

```sh
curl -X POST \
  -H "X-Cron-Secret: $CRON_SECRET" \
  -H "Content-Type: application/json" \
  "$PIPELINE_URL/api/fulfillment/$ORDER_ID/reconcile-endure-email" \
  --data '{
    "outcome": "delivered",
    "operator": "OPERATOR_NAME",
    "evidence": "Verified in Resend delivery log",
    "expected_idempotency_key": "EXACT_KEY_FROM_STATUS",
    "expected_payload_digest": "EXACT_DIGEST_FROM_STATUS",
    "provider_message_id": "EXACT_RESEND_MESSAGE_ID"
  }'
```

If Resend proves no message was accepted, clear only that exact attempt. A new
explicit send can then create a new durable attempt:

```sh
curl -X POST \
  -H "X-Cron-Secret: $CRON_SECRET" \
  -H "Content-Type: application/json" \
  "$PIPELINE_URL/api/fulfillment/$ORDER_ID/reconcile-endure-email" \
  --data '{
    "outcome": "not_sent",
    "operator": "OPERATOR_NAME",
    "evidence": "No Resend message exists for the exact key",
    "expected_idempotency_key": "EXACT_KEY_FROM_STATUS",
    "expected_payload_digest": "EXACT_DIGEST_FROM_STATUS"
  }'
```

Both recovery actions run under the order lock and reject stale keys, stale
message fingerprints, missing evidence, non-Endure orders, and invalid state.

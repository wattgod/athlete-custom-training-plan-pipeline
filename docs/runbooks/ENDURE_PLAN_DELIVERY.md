# Endure purchased-plan delivery

This path moves one coach-approved, sealed custom plan into Endure. It does not
change the default platform and it never falls back to TrainingPeaks silently.

## Normal path

1. Confirm the order is `APPROVED` and `delivery_platform` is `endure`:

   ```sh
   curl -H "X-Cron-Secret: $CRON_SECRET" \
     "$PIPELINE_URL/api/fulfillment/$ORDER_ID/status"
   ```

2. Stage the exact approved release. This creates or resumes one order-bound
   athlete, invitation, plan, season outline, and draft first block:

   ```sh
   curl -X POST -H "X-Cron-Secret: $CRON_SECRET" \
     "$PIPELINE_URL/api/fulfillment/$ORDER_ID/stage-endure"
   ```

3. Open the returned Endure review URL. Review the first block, choose the
   current or a later Monday, and schedule it. Endure must report an exact
   activity-and-strength calendar match.

4. Verify the calendar and send the athlete one access email:

   ```sh
   curl -X POST -H "X-Cron-Secret: $CRON_SECRET" \
     "$PIPELINE_URL/api/confirm/$ORDER_ID"
   ```

5. Read status again. `CONFIRMED` is valid only with the exact Endure receipt,
   calendar verification, recipient digest, and Resend evidence.

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

# Daily real-path order drill

Owner: pipeline operator. The coach owns every review, waiver, and approval
decision. The workflow owns only submission, observation, and safe pre-apply
cancellation of yesterday's drill and any leftover same-day drill.

## Setup

Both workflows hardcode the production Railway URLs and reuse the existing
`CRON_SECRET` repository secret (same value as the Railway `CRON_SECRET` env
var, the contract `daily-followup-emails.yml` already relies on). Required
configuration:

| Name | Kind | Value |
|---|---|---|
| `CRON_SECRET` | secret (already set) | Same value as Railway `CRON_SECRET`; used for status, pre-approval download assertion, cancellation, and the state audit |
| `DRILL_WEBHOOK_SECRET` | secret | Same value as Railway `WOOCOMMERCE_SECRET` |
| `DRILL_CUSTOMER_EMAIL` | variable (optional) | Defaults to `gravelgodcoaching@gmail.com`; must support plus addressing — the tool derives `local+drill@domain` |

Railway must have the matching `WOOCOMMERCE_SECRET` and `CRON_SECRET`, a
persistent `DATA_DIR` volume, working review/download token keys, and the real
email configuration: `RESEND_API_KEY`, `NOTIFICATION_EMAIL`, and the configured
brand sender. The notification is intentionally not suppressed.

Leave repository variable `DRILL_ENABLED` unset or `false` while configuring.
Run `state-audit.yml` manually first, then run `daily-drill.yml` manually. After
both are green and the coach received the notification, set repository variable
`DRILL_ENABLED=true`. The scheduled drill runs daily at 13:00 UTC; the state
audit runs independently at minute 17 of every hour.

## What the drill sends

The payload is deterministic for the UTC date: order id `drill-YYYYMMDD`, athlete
name **Daily Drill**, a plus-address derived from `DRILL_CUSTOMER_EMAIL`, and a
synthetic gravel event 140 days out. It is serialized once, signed with the
WooCommerce HMAC-SHA256/base64 scheme, and posted as raw JSON to the production
Woo webhook. The unknown synthetic race deliberately produces exactly the
waivable `RACE_UNMATCHED` blocker, giving the coach a real blocked review surface
without using a real person's data.

Delivery platform is `manual`, so this drill performs zero TrainingPeaks writes.
The previous UTC day's drill is cancelled through the authenticated fulfilment
transition only when it is non-terminal and has no application evidence.
Cancellation refuses to hide an application that would require compensation.

## What green means

A green artifact proves all of the following:

- the production Woo signature verifier accepted the exact submitted bytes;
- the durable generation job completed;
- state is exactly `BLOCKED_REVIEW` with blocker set exactly
  `{RACE_UNMATCHED}`;
- the sealed review bundle exists;
- the customer status is not download-ready and the authenticated customer
  bundle request returns 409 before approval;
- yesterday's non-terminal drill is durably `CANCELLED`, or was absent/already
  terminal;
- no secret, URL, or customer email appears in the uploaded JSON artifact.

The coach should also receive the normal real order notification email for
**Daily Drill**. The workflow cannot prove inbox delivery, so absence of that
email is red operationally even if every HTTP assertion passed.

The drill never clicks, waives, approves, applies, or confirms. If the coach
opens the real review URL and clicks **Approve sealed revision**, that click is
recorded with the real revision, review catalog, credential, and seals. Approval
alone does not auto-apply or auto-send an athlete email: the trustworthy
fulfilment contract requires legitimate downstream evidence and a human send.
When the deployed phase offers those controls, using them sends to the drill
plus-address through the real configured email path.

## Triage a red run

1. Download the `daily-order-drill-*` JSON artifact. Start with the first failed
   assertion; it contains no response body, secret, or PII.
2. If signed intake failed, compare the GitHub `DRILL_WEBHOOK_SECRET` with
   Railway `WOOCOMMERCE_SECRET`. Do not loosen signature verification.
3. If generation timed out or the job failed, inspect Railway logs and the
   authenticated job/order state. Keep the failure invisible to the synthetic
   customer and loud to the coach.
4. If the blocker set changed, reproduce locally with
   `tools/daily_order_drill.py --date YYYY-MM-DD` against a local test service.
   Treat extra critical blockers as findings; do not weaken the expected set.
5. If review-bundle or 409 assertions fail, close the release gate immediately.
   A pre-approval customer download is a critical bypass.
6. If cleanup fails because application evidence exists, do not force
   `CANCELLED`. Follow the compensation/cleanup path appropriate to that state.
7. If HTTP checks are green but the coach email is absent, verify
   `NOTIFICATION_EMAIL`, `RESEND_API_KEY`, brand sender configuration, and Resend
   delivery logs. Do not add an email-suppression exception for drills.
8. For a red `state-audit.yml`, inspect every critical anomaly. Drill orders are
   exempt only from routine age warnings, never from expired grants/leases,
   cancellation acknowledgement, malformed state, or unsealed approval.

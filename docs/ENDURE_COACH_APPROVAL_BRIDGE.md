# Endure coach approval bridge

Motoren remains the sole authority for the seal-bound `APPROVED` state. Endure
is the authenticated coach console and audit system. It may read the current
non-executable review catalog and submit the exact human decision; it receives
no apply, cancellation, confirmation, guide-release, email, or TrainingPeaks
write capability.

## Request authentication

Railway stores `ENDURE_APPROVAL_KEY_ID` and `ENDURE_APPROVAL_SECRET`. Vercel
stores the same values as `MOTOREN_APPROVAL_KEY_ID` and
`MOTOREN_APPROVAL_SECRET`. The secret must be at least 32 characters and must
not equal `CRON_SECRET`.

Every request supplies:

- `X-Endure-Key-Id`
- `X-Endure-Timestamp` as Unix seconds, accepted only within five minutes
- `X-Endure-Signature` as HMAC-SHA256

The signed message is:

```text
endure-approval/v1
<METHOD>
<PATH>
<UNIX_SECONDS>
<SHA256_OF_CANONICAL_JSON_BODY_OR_EMPTY_BYTES>
```

Canonical JSON sorts object keys recursively and uses no insignificant
whitespace. The path is the exact encoded request path.

The durable `source_command_digest` in the approval receipt is the body digest
from that signed message. The timestamp remains part of HMAC authentication,
but not durable command identity, so a byte-equivalent canonical command can
be retried with a fresh timestamp without creating a second approval.

## Endpoints

`GET /api/fulfillment/<order>/endure-review` returns the current sealed
`review_catalog/v2`, order/athlete/revision identity, model seal, release
manifest digest, approval status, and any exact pending revision-request
receipt. It never returns `apply_contract/v1`, TP payloads, executable files,
or release artifacts.

`POST /api/fulfillment/<order>/endure-revision-request` accepts one strict
`endure_revision_request/v1`. It binds the coach and organization, current
sealed before-image, selected review items, and plain-language directive.
Motoren records the request under the fulfillment-state lock and returns
`motoren_revision_request_receipt/v1`. The old sealed bytes remain readable as
the before-image, but approval is refused until the canonical producer calls
`write_generation`, consumes the pending request, and creates revision N+1.
The command neither edits generated artifacts nor queues an alternative
generator. Exact retries preserve the provider observation time and receipt.

`POST /api/fulfillment/<order>/endure-approval` accepts one strict
`endure_approval_command/v1`. The command binds the Endure coach user,
organization, membership role, request UUID, order, athlete, generation
revision, catalog digest, model seal, release-manifest digest, typed review
decisions, and waiver state. Motoren re-runs its existing approval invariants
under the state lock and returns `motoren_approval_receipt/v1` only when
`approval_matches_release()` is true and no external write occurred.

Exact command replay is idempotent. A different approval or revision request
against a claimed revision fails. The generic `CRON_SECRET` transition endpoint
cannot enter `APPROVED`; authoritative approval comes only from an authenticated
review session or this narrow bridge.

## Deployment order

1. Deploy Motoren with both Railway variables set.
2. Configure the matching three Endure Vercel variables, including
   `MOTOREN_APPROVAL_BASE_URL`.
3. Verify a signed review read against a synthetic sealed order.
4. Apply the Endure approval-ledger migration.
5. Deploy the Endure coach console.

Do not enable the Endure UI before the Motoren endpoint and shared key are
live. Missing or mismatched configuration is a hard hold, not a fallback to
`CRON_SECRET` or local approval.

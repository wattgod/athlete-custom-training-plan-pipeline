# Verdict: NO-GO

**Convergence: not reached, but only one localized D0 repair remains.** D1 now
meets the r5 quiescence-barrier requirement. D0 repairs the principal dated-
object defects (`keep` evidence and compensable `update`/`delete`), but its
normative union still cannot encode every disposition it allows, and its
append-only `landed[]` records are not yet a defined effective remote inventory
after delete or compensation. Those are spec-level contradictions, not facts
that implementation or a live canary can choose.

Disposition summary: **1 RESOLVED, 1 NOT RESOLVED**.

No broad architecture round is warranted. The required changes below are a
small D0/D3 clarification. After they are made, the convergence result should
be GO-WITH-CONDITIONS for implementation, with production rollout held by the
existing phase gates and live evidence requirements.

## Review basis

I read the complete Codex r1 through r5 reviews first, then the complete r6
document and Appendix 1's r5→r6 map. I checked the D1 and D0 edits against S2,
S5, D2, D3, F4, the rollout, and the fixture, and checked the four r5 editorial
items.

All code-dependent checks used only `git show origin/main:<path>`, never the
dirty working tree. `git show -s --format=%H origin/main` returned
`af284c2647b20388c7bb57678fc123780f6a6660`. I rechecked the pinned manifest
inventory and derived `calendar_dates` in
`athletes/scripts/fulfillment_manifest.py:21-80`, the adapter's POST/checkpoint
behavior and operation coverage in `delivery/trainingpeaks/adapter.py:40-94`,
the one-file state writer/current transitions in
`webhook/fulfillment_state.py:69-109, 124-234`, and the TP-native workout shape
in `tools/tp_apply_order.py:237-248`.

## Disposition of the two r5 blockers

| # | r5 blocker | r6 disposition | Evidence-based reason |
|---|---|---|---|
| 1 | D1 cancellation quiescence | **RESOLVED** | D1 now requires grant/epoch revalidation immediately before every remote mutation, advances the epoch and issues no new grant after cancellation/regeneration, orders stop as journal flush → lease release → acknowledgement, permits the unreachable-worker fallback only after grant expiry plus the fixed maximum mutation duration `M`, and takes F4's landed snapshot after that barrier. This closes the r5 race: cancellation/compensation cannot finalize merely because a batch-level grant expired while an authorized batch may still be writing. The same TP-athlete lease serializes compensation. |
| 2 | D0 self-verifying and compensable supersession | **NOT RESOLVED** | The core dated-object repair is present: `keep` carries a desired digest; dated `update`/`delete` carry `prior_payload` and restore/recreate strategies; dispositions are restricted per kind; and never-landed resources are intended to be creates. But the common-field requirements contradict the allowed singleton/keep cases, and `landed[]` remains an operation journal rather than a normatively defined current remote inventory. See blockers 1 and 2. |

## New spec-level blockers

### 1. The closed disposition union still has allowed operations that cannot satisfy its common fields

> “`payload`: ... `null for keep/delete`”

> “`expected_digest` = sha256 of the canonically serialized `payload`”

> “for `keep` the payload is the predecessor's, so the digest is copied”

> “`predecessor` ... REQUIRED for update/keep/delete; remote_id NOT nullable”

> “singletons ... `update`/`keep` only”

There are two normative collisions.

First, a serialized `keep` has `payload: null`, while the single global digest
definition says to hash that serialized payload. The same section instead
requires copying the predecessor's non-null desired-payload digest. The intended
readback rule is clear, but the claimed single digest definition and the
serialized operation cannot both be validated literally.

Second, D2 can emit a first-revision `threshold_update` or `zone_update` against
an inspected account singleton. D0 permits only `update|keep` for that kind, but
requires every update to carry a predecessor `{op_id, remote_id}`. On the first
revision there is no predecessor operation, and singleton identity is explicitly
positional. `before_image` supplies the compensation source, but it cannot
supply the nonexistent predecessor `op_id`. The same common rule also needs an
explicit initial/already-present rule for any positional `keep` such as an
entitlement.

This is not a live TrainingPeaks question: it is whether a document can satisfy
the normative schema. The pinned adapter has no singleton update primitive to
inherit; it currently POSTs only its existing workout/note/attachment/
entitlement shapes, so implementation cannot resolve the contradiction by
appealing to an existing contract.

**Required change:** make required/forbidden fields a per-kind/per-disposition
matrix. Define `expected_digest` as the desired remote field-set digest:
create/update hash their non-null `payload`; keep carries the predecessor or
otherwise computed desired digest despite `payload: null`; delete alone has no
expected digest. Require `predecessor` only when a prior landed resource record
actually exists. Permit an initial singleton update with `predecessor: null`,
positional identity, and required `before_image`; specify the equivalent rule
for an already-present positional entitlement. Make the generated JSON Schema
and equivalence tests enforce these branches.

### 2. Append-only `landed[]` is not the “last landed remote inventory” needed by supersession

> “Completeness is measured against the landed inventory, not the prior
> contract”

> “MUST contain exactly one operation for every logical id with a landed remote
> id”

> “Each landed operation is appended durably to the attempt's `landed[]`
> (`op_id`, `remote_id`, `result`) as it completes.”

> “`delete` ... remove via predecessor `remote_id`; rollback =
> `recreate_from_prior_payload` (new remote id recorded on recreation).”

An append-only list of successful operations is not itself the current remote
inventory. A successful delete is a landed operation and can retain the deleted
`remote_id` in its journal result, but that remote resource is absent. A later
compensation may recreate it under a new remote ID. Update and rollback likewise
change which payload/digest is current. Applying the literal “every logical id
with a landed remote id” rule to the historical journal can therefore require a
disposition for an already-deleted resource or select a stale remote ID.

The distinction matters to both consumers: F4 needs the post-barrier operation
journal to compensate what just landed, while revision n+1 needs the effective
post-operation remote inventory to construct and validate its diff. One data
structure cannot be assumed to mean both without transition rules.

The sentence “prior logical ids that never landed ... appear as `create`” also
needs to be scoped to resources still desired in revision n+1; a never-landed
resource removed from the new desired model must remain absent, not be created.

**Required change:** retain append-only `landed[]` as the attempt/compensation
journal, and define a separate materialized `effective_remote_inventory` (or a
deterministic projection with an exact schema). Specify its transition for each
successful create/update/keep/delete and every compensation: delete removes the
logical ID, restore changes its payload/digest, recreation installs the newly
returned remote ID, and never-landed/removed resources remain absent. Take this
inventory snapshot after D1's barrier. D0 completeness and predecessor selection
must consume that snapshot; F4 compensation must consume the operation journal.

## Implementation-gated items

Once the two D0/D3 text corrections above land, all remaining uncertainty is
properly closed only by building or controlled external evidence:

1. Live TrainingPeaks HR/LTHR/HRmax/RPE acceptance and readback, marker search,
   exact create/update/delete behavior, attachment digest visibility,
   singleton CAS feasibility, ambiguous-timeout recovery, and session refresh.
2. Worker login/TOTP/session survival, coaching checks, capability exchange,
   per-mutation epoch validation, enforced mutation deadline `M`, lease fencing,
   acknowledgement/fallback quiescence, kill-point recovery, rate/egress
   controls, and audit redaction.
3. Per-kind apply-contract projection, generated JSON-Schema equivalence,
   effective-inventory transitions, fake-server parity, supersession and
   compensation fixtures, and safe JS-driver retirement.
4. Checking in and executing athlete-m and the metric-neutral HR/LTHR/HRmax/RPE
   fixtures, including the Phase 1/3/4 literal goldens.
5. S5 consumer idempotence and kill-point recovery for notices, guide release,
   and drafts.
6. Gmail OAuth, aliases, sent-state verification, MIME canonicalization,
   body hashing, draft/message relationships, and attachment-byte verification.
7. Deterministic guide rendering, private/ZIP-only release, publication,
   caching, supersession, and revocation.
8. Endure readback/rollback/invitation suppression; Endure remains safely off
   unless its Phase 5 gate passes.
9. Course `courses[]` implementation/backfill, the external polyline-copy
   change, and the accepted TrainingPeaks ToS/business risk.

## Non-blocking findings

1. **All four r5 editorial items are repaired.** S2 numbers the transitional
   Phase 1 sequence independently; B3's literal release list includes APPLYING
   and APPLIED_ATTESTED; D3 points to D0's fixed per-kind policy; and the
   Saturday negative fixture assertion cites C2's race-day exemption.
2. **D1's expiry fallback is a real contract, not grant-expiry-as-quiescence.**
   Implementation must make `M` an enforced maximum (including browser/network
   timeout behavior), not an observed average, and must prove the journal-flush,
   lease-release, acknowledgement ordering at kill points. Those are build
   obligations under the now-specified protocol, not requests for more
   architecture text.
3. **The dated-object compensation data is otherwise sufficient in text.**
   `prior_payload`, `restore_prior_payload`, and
   `recreate_from_prior_payload` directly repair the r5 before-image gap; live
   support for those writes remains correctly canary-gated.
4. **`calendar_dates` remains correctly classified.** At the pinned ref it is
   derived by sorting workout dates in `fulfillment_manifest.py:66-71`; the
   adapter mutation loops do not consume it. Keeping it as verification
   inventory does not drop a remote operation.

## Could not verify

1. I could not verify any live TrainingPeaks marker, remote ID, HR/RPE shape,
   update/delete/restore/recreate behavior, singleton write, entitlement
   revocation, attachment readback, or idempotency guarantee.
2. I could not verify the worker, execution grants/epochs, mutation-level
   revalidation, lease fencing, acknowledgement, durable journal, effective
   inventory, or cancellation fallback. They are specification-only at the
   pinned ref.
3. I could not verify state schema v2, APPLYING/APPLIED_ATTESTED/CANCELLED,
   model/release/component manifests, the in-state outbox, typed tokens,
   review pages, or the apply-contract projection. The pinned code remains the
   v1 state and manifest paths cited above.
4. I could not execute athlete-m. `git show
   origin/main:tests/fixtures/athlete_m/intake.json` has no such pinned path;
   no real customer's Railway intake was accessed or copied.
5. I could not verify Gmail provider/manual evidence, aliases, OAuth,
   MIME/body hashing, content snapshots, attachment fidelity, or outbox
   reconciliation.
6. I could not verify deterministic guide privacy/publication/revocation, live
   Endure behavior, production course matching, or the external
   `gravel-god-training-plans` polyline copy.
7. I could not verify TrainingPeaks terms-of-service acceptability; the spec
   records it as an accepted business risk rather than a technical claim.

## Convergence assessment

The convergence rule is not yet met. D1 is now a complete spec-level
quiescence contract; its remaining questions require implementation and kill-
point/live proof. D0, however, still contains two choices that code cannot make
without contradicting the normative text: how initial positional operations
satisfy the predecessor rule, and how historical landed operations become the
current inventory used for a supersession diff.

Repair those two localized contracts (including the `keep` digest formula),
then stop redesigning and implement. No further broad architecture review is
warranted.

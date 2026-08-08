# Verdict: NO-GO

**Convergence: not reached.** r7 makes the intended architectural repair: it
separates the append-only `landed[]` journal from a materialized effective
inventory, routes D0 and F4 to the correct post-barrier views, and adds a
kind-by-disposition field matrix. However, the new normative text still
contradicts itself at the exact repaired boundary. The `keep` digest has two
incompatible definitions; the blanket completeness/predecessor rules cannot
encode the new positional branches; and the effective-inventory schema does
not support all transitions it says are deterministic.

These are localized D0/D3 repairs, not grounds for broader architecture
review. They are nevertheless spec-level contradictions that an implementation
cannot choose between while remaining conformant. Under the same convergence
rule applied in r6, they cannot be deferred as implementation conditions.

## Review basis

I read the complete Codex r1 through r6 reviews first, then the complete r7
draft, including Appendix 1's r6→r7 map. I checked the repair against S2, D0,
D1, D2, D3, F4, and the rollout gates.

All code-dependent checks used only `git show origin/main:<path>`, never the
dirty working tree. `git show -s --format=%H origin/main` returned
`af284c2647b20388c7bb57678fc123780f6a6660`. I rechecked the pinned adapter
operation/checkpoint behavior, manifest operation inventory, v1 state writer
and transitions, and TP-native workout projection through that ref. The
blockers below are primarily contradictions in the new normative spec text;
they do not depend on an unverified working-tree implementation.

## Disposition of the r6 blocker pair

| r6 blocker | r7 disposition | Evidence-based reason |
|---|---|---|
| 1. Per-kind/per-disposition field collisions, including the `keep` digest and first-revision positional operations | **NOT RESOLVED** | The matrix correctly makes first-revision singleton predecessors nullable and gives `keep` a required digest despite null payload. But S2 still defines every `expected_digest` as a payload hash; D0's common predecessor type cannot represent an inventory predecessor whose `remote_id` is null; and D0's blanket absent-inventory rule requires `create` where the matrix requires positional `update` or `keep`. A pre-existing entitlement `keep` also has no normative digest source. See blockers 1 and 2. |
| 2. Append-only `landed[]` journal vs effective remote inventory | **NOT RESOLVED** | The separation and consumer routing are correct, and D3 now requires both structures to update in the same durable write. But the materialized inventory's declared schema omits the payload reference its own transition writes, and the transition set does not define how an initial positional `update` or an observed pre-existing `keep` acts when no entry exists. Thus it is not yet a total deterministic projection. See blocker 3. |

## New spec-level blockers

### 1. S2 still gives the old universal payload-hash formula, contradicting D0's `keep` formula

S2 says:

> “**`expected_digest` is defined exactly once, in D0: the hash of the
> canonically serialized operation `payload`.**”

D0 now says:

> “for `keep` the payload is `null` and the digest is the desired digest of
> the resource being kept, copied from the effective remote inventory entry”

and the matrix requires:

> “dated `keep` | ∅ | REQ (copied)”

These definitions cannot both hold. Hashing the serialized null payload does
not produce the retained resource's desired field-set digest. This is the
same keep collision r6 required the repair to eliminate, now expressed as a
cross-section contradiction.

There is a second edge in the same formula: an entitlement that was already
present on the account has `predecessor: null`, hence by D0's own predecessor
rule it has no effective-inventory entry from which to copy the digest. The
singleton-keep row explicitly permits a D2 inspection digest when the value
was never ours; the pre-existing-entitlement row requires a digest but does
not define the equivalent inspection source. Appendix 1 mentions an
“inspection digest,” but D0 declares its matrix/formulas the single normative
authority and does not say this for entitlement keeps.

**Required change:** make S2 defer to D0's complete per-disposition definition
instead of restating the create/update payload formula. In D0, define the
pre-existing entitlement `keep` digest as the canonical digest of the
inspected desired entitlement field set (at minimum `{product_id}`), with the
inspection snapshot/provenance named as its source. Keep one formula per
disposition across S2, the matrix, readback, and generated schema tests.

### 2. The positional matrix conflicts with both the common predecessor type and the completeness rule

D0's common shape fixes predecessor as:

> “`predecessor`: `{ "op_id": str, "remote_id": str } | null”

The effective-inventory schema permits:

> “`{logical_id → {remote_id | null, desired_digest, kind, last_op_id}}`”

and D0 then requires:

> “`predecessor` is required **exactly when an effective-inventory record for
> this logical id exists**”

After an initial positional singleton has landed, an effective-inventory
record can exist with `remote_id: null`. The next singleton `update` or `keep`
must therefore carry a predecessor, but the common predecessor schema requires
its `remote_id` to be a string. The same problem can occur for a positional
entitlement whose identity is the product id rather than a remotely returned
object id. The newly added matrix does not override the nested predecessor
shape.

The blanket completeness rule creates another direct conflict:

> “logical ids absent from the snapshot ... if still desired they are
> `create`”

But the matrix permits only `update|keep` for singletons and specifically
requires a first-revision singleton `update` or `keep` with no predecessor.
It also requires `keep`, not `create`, for a pre-existing entitlement. Those
are desired logical ids absent from the operation-derived inventory, so the
blanket rule rejects the very positional branches the matrix added.

**Required change:** make the predecessor sub-schema branch-specific:
`remote_id` must be nullable/forbidden for positional kinds and required only
for operations whose reconciliation strategy needs a remote object id. Then
replace the blanket absent→create rule with a kind-aware rule: absent dated
resources create; inspected singletons update/keep positionally; absent
entitlements create; inspected-present entitlements keep. The generated JSON
Schema and completeness tests must cover first and subsequent revisions of
each branch.

### 3. `effective_remote_inventory` is separate, but its schema and transition function are not total

D0 declares the complete materialized shape as:

> “`{logical_id → {remote_id | null, desired_digest, kind, last_op_id}}`”

but immediately says an update/restore transition changes:

> “digest **(and payload reference)**”

There is no payload or payload-reference field in the declared inventory
shape. That matters because a later dated `update` or `delete` must serialize
`prior_payload` in the new contract. The stated materialization cannot retain
the value its own transition says it retains.

The transition list is also undefined at the new positional boundaries:

> “`create`/recreation → entry installed; `update`/restore → digest ...
> replaced; `keep` → unchanged”

A first-revision singleton `update` is explicitly legal when no inventory
record exists, so there is nothing to “replace.” Likewise, a verified
first-revision singleton keep or pre-existing entitlement keep starts with no
record; “unchanged” leaves the supposedly effective remote inventory unaware
of the verified remote resource. If retaining those externally pre-existing
resources outside the inventory is intentional, the completeness exceptions
must say so; if they enter the inventory after verification, the install
transition and subsequent predecessor semantics must be stated.

**Required change:** give the inventory one exact schema, including the
canonical payload snapshot or immutable payload reference needed to construct
`prior_payload`. Define a closed transition table for every successful
operation and compensation, including `update` on absent positional entries,
`keep` on absent inspected resources, create-compensation deletion,
update-compensation restore, delete-compensation recreation with a new remote
id, and singleton compensation. State whether each transition installs,
replaces, leaves, or removes the entry and how `last_op_id`, `remote_id`,
digest, and payload reference change. D3's same-write rule should apply that
exact function.

## GO-WITH-CONDITIONS conditions

Not applicable because the verdict is NO-GO. The existing phase gates and
live-evidence requirements remain the prospective standing obligations once
the three localized contradictions above are repaired; they cannot substitute
for repairing a normative schema that is currently internally inconsistent.

## Non-blocking findings

1. **The architectural journal/inventory split is correct.** D1 now names
   both post-barrier reads, D0 completeness/predecessor selection points at the
   effective inventory, F4 points at the journal, and D3 requires both to move
   in the same durable write. No broader redesign is indicated.
2. **The dated-resource repair is otherwise sound in text.** Dated create,
   update, keep, and delete now have the payload/prior-payload/digest branches
   and compensation strategies r5/r6 required.
3. **The first-revision singleton intent is clear.** Required `before_image`,
   positional identity, and `predecessor: null` are the correct branch. The
   blocker is the surrounding common type/completeness/materialization rules,
   not that design choice.
4. **No unrelated new architecture blocker was found.** The failures above
   are confined to the r7 D0/D3 repair and its stale S2 cross-reference. The
   rest of r6's implementation-gated list remains appropriately gated on
   building or controlled live evidence.
5. **The pinned-code premise remains unchanged.** At `origin/main` the adapter
   still POSTs/checkpoints the old operation shapes and supplies no existing
   singleton/effective-inventory primitive that could resolve these spec
   choices implicitly. This supports treating the conflicts as normative,
   not as implementation details.

## Could not verify

1. I could not verify live TrainingPeaks marker, remote-id, HR/RPE,
   update/delete/restore/recreate, singleton, entitlement, attachment-readback,
   or idempotency behavior. Those remain Phase 5 canary obligations.
2. I could not verify the worker, execution grants/epochs, per-mutation
   revalidation, lease/quiescence protocol, durable journal, or materialized
   effective inventory; none exists at the pinned ref.
3. I could not verify the generated `apply_contract/v1` JSON Schema or its
   equivalence tests, because the normative projection is not implemented at
   `origin/main`.
4. I could not execute athlete-m or the HR/LTHR/HRmax/RPE fixtures; they are
   not present at the pinned ref. No real customer's Railway input was
   accessed.
5. I could not verify Gmail evidence/drafting, guide rendering/privacy and
   revocation, live Endure behavior, production course matching, the external
   polyline copy, or TrainingPeaks ToS acceptability.

## Convergence assessment

The r6 convergence decision applies unchanged: do not reopen the architecture,
but do not call an internally contradictory normative schema converged. r7 has
the right repair shape and most of the right routing, yet the stale S2 digest
definition, positional completeness/predecessor collisions, and incomplete
inventory transition schema are choices the spec can resolve now.

Repair those localized statements and transition branches, then stop reviewing
and implement. At that point the correct verdict should be
**GO-WITH-CONDITIONS**, with production rollout held by the already specified
phase gates, fake-server/kill-point proofs, and controlled live canary evidence.

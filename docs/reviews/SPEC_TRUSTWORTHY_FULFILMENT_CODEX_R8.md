# Verdict: NO-GO

**Convergence: not reached, by one remaining localized D0 contradiction.**
R8 fully repairs the stale S2 digest statement and makes the effective remote
inventory schema/transition function total for the declared operation and
compensation set. The predecessor type and kind-aware completeness repair is
architecturally correct, but two positional branches in that new prose still
contradict the matrix that D0 calls the single normative authority.

This is not a preference or a request to reopen architecture. It is the same
schema-conformance bar applied in R6 and R7: the generated JSON Schema cannot
both require and forbid the same field for the same legal branch. Repair the
two phrases identified below, then the correct verdict is
**GO-WITH-CONDITIONS** and implementation should begin. No broader spec round
is warranted.

## Review basis

I read the complete Codex R1 through R7 reviews first, then the complete R8
draft, including Appendix 1's R7→R8 map. I checked the three changes against
S2, the D0 common shape and matrix, the materialized-inventory transition
table, D1/D2, D3, F4, and the rollout gates.

All code-dependent checks used only `git show origin/main:<path>`, never the
dirty working tree, at the required pinned ref `af284c2`. In particular:

- `delivery/trainingpeaks/adapter.py:40-100` still has POST-then-checkpoint
  behavior and only the old workout/note/attachment/entitlement operations;
  it supplies no singleton, predecessor, compensation, or effective-inventory
  primitive that could resolve a normative ambiguity implicitly.
- `athletes/scripts/fulfillment_manifest.py:21-80` still carries the old
  segments-based workout shape plus notes, attachments, mental tasks,
  entitlement, and derived `calendar_dates`.
- `tools/tp_apply_order.py:4-17, 50-51, 237-248` still prepares the separate
  TP-native browser-driver contract.
- `webhook/fulfillment_state.py:69-109, 124-234` still has the one-file atomic
  writer and v1 transitions, without the R8 operation journal or materialized
  inventory.

The blocker below is therefore a contradiction in R8's normative text, not an
unverified claim about a working-tree implementation.

## Disposition of the three R7 blockers

| R7 blocker | R8 disposition | Evidence-based reason |
|---|---|---|
| 1. S2's stale universal payload-hash formula; no digest source for pre-existing entitlement keeps | **RESOLVED** | S2 now defers entirely to D0's per-disposition definition. D0 defines create/update from their payload, keep from the effective-inventory entry when present, otherwise from the recorded D2 inspection snapshot, explicitly using `{product_id}` for an entitlement; delete has no digest. The matrix and readback rule agree. |
| 2. Predecessor type and blanket absent→create conflict with positional operations | **NOT RESOLVED** | `predecessor.remote_id: str | null` and the kind-aware absent rules are the right repair. However, the new singleton-keep completeness sentence requires a `before_image` that the matrix forbids, and the entitlement-keep row still keys predecessor presence to whether “we granted it,” while the transition table installs a predecessor-bearing inventory entry for a pre-existing entitlement. See the blocker below. |
| 3. Effective-inventory schema omitted payload provenance and its transition function was not total | **RESOLVED** | The exact schema now includes `payload_snapshot_ref`. The closed table installs/replaces/removes entries for dated create/update/delete and their compensations, install-or-replaces first-revision singleton updates and singleton compensation, installs verified absent keeps, advances existing keeps, and installs entitlement creates. Entitlements have rollback `none`, so there is no omitted successful entitlement compensation branch. |

## New spec-level blocker

### 1. The kind-aware completeness repair still conflicts with the single-authority field matrix

R8 declares:

> “Which of these fields are required, null, or forbidden depends on
> `kind × disposition`: the matrix below is the single normative authority.”

The matrix says:

> “singleton `keep` ... `before_image` ∅”

but the new completeness branch says:

> “a desired singleton absent from the snapshot is the first-revision
> positional `update` (or verified `keep`), `predecessor: null`,
> `before_image` required.”

Taken literally, a legal first-revision singleton `keep` must both omit and
include `before_image`. A keep performs no mutation and D0 already gives it a
D2 inspection digest/provenance source, so the matrix's omission is coherent;
the completeness sentence is not.

The entitlement branch has the same class of second-revision collision. The
matrix says:

> “entitlement `keep` ... predecessor ∅ when pre-existing; REQ when we
> granted it”

while the new transition table says:

> “verified `keep` on an absent entry ... pre-existing entitlement ...
> **install** ... so subsequent revisions have a predecessor”

and the global rule says:

> “`predecessor` is required exactly when an effective-inventory record for
> this logical id exists”

with completeness requiring every present entry's
`{last_op_id, remote_id}` predecessor. After revision 1 adopts a pre-existing
entitlement, revision 2 has an inventory entry and therefore must carry a
predecessor. But the resource remains pre-existing—not “granted by us”—so the
matrix still says the predecessor must be absent. Because the matrix is the
declared JSON-Schema authority, the surrounding exact rule does not erase this
collision.

**Required change:**

1. Split the absent-singleton completeness branch: an initial singleton
   `update` requires `before_image`; a verified initial singleton `keep`
   requires `before_image` to be absent and uses the D2 inspection
   digest/provenance already defined by D0.
2. Make the entitlement-keep matrix use inventory existence, not historical
   origin: predecessor is absent only for the first inspected-present keep
   when no inventory record exists, and required for every subsequent keep
   once the verified keep or grant installed an inventory record.
3. Require generated-schema/completeness tests for first and subsequent
   revisions of both an adopted singleton keep and an adopted pre-existing
   entitlement keep.

These edits implement R8's stated design; they do not require a new state,
identity, compensation, or platform decision.

## GO-WITH-CONDITIONS conditions

Not applicable while the verdict is NO-GO. The implementation/live-proof
obligations already present in the rollout remain the prospective standing
conditions once the localized matrix/completeness collision is repaired.

## Non-blocking findings

1. **The R8 digest repair is complete.** S2 no longer restates an incompatible
   formula, and D0 covers both inventory-backed and inspection-backed keeps
   with recorded provenance. No further digest redesign is indicated.
2. **The inventory transition architecture is now implementable in text.**
   `landed[]` remains the compensation journal, while
   `effective_remote_inventory` is the supersession authority. The new
   `payload_snapshot_ref` supplies later `prior_payload`, and the transitions
   cover install-on-absent for the positional cases R7 identified.
3. **D3's phrase “state stays APPLYING with the exact landed inventory” is
   editorially stale.** D0 and the preceding D3 sentence clearly require both
   an append-only `landed[]` journal and a separately updated effective
   inventory. Renaming this phrase to “exact landed journal and effective
   inventory” would prevent terminology drift, but it does not create a second
   behavioral interpretation.
4. **No unrelated new architecture blocker was found.** The sole failure is
   confined to two field requirements in the R8 positional completeness
   repair. Settled seals, capability/quiescence, manual-application status,
   release evidence, fixture contract, and rollout gates remain at the R7 bar.
5. **The current fake server is not live idempotency evidence.** At the pinned
   ref, `test_trainingpeaks_adapter.py:31-39` implements its own external-ID
   deduplication. R8 correctly leaves real marker/idempotency behavior behind
   fake-server and controlled-canary gates.

## Could not verify

1. I could not verify live TrainingPeaks marker, remote-ID, HR/RPE,
   update/delete/restore/recreate, singleton, entitlement, attachment-readback,
   or idempotency behavior. Those remain Phase 5 canary obligations.
2. I could not verify the worker, execution grants/epochs, per-mutation
   revalidation, lease/quiescence protocol, durable journal, or materialized
   effective inventory; none exists at the pinned ref.
3. I could not verify the generated `apply_contract/v1` JSON Schema,
   equivalence tests, or first/subsequent-revision transition fixtures because
   the normative projection is not implemented at `origin/main`.
4. I could not execute athlete-m or the HR/LTHR/HRmax/RPE fixtures.
   `git show origin/main:tests/fixtures/athlete_m/intake.json` reports that the
   path does not exist; no real customer's Railway input was accessed.
5. I could not verify Gmail evidence/drafting, deterministic guide
   rendering/privacy/revocation, live Endure behavior, production course
   matching, or the external polyline copy.
6. I could not verify TrainingPeaks terms-of-service acceptability; the spec
   records it as an accepted business risk rather than a technical claim.

## Convergence assessment

Apply the R6/R7 rule unchanged: do not manufacture implementation blockers,
but do not call a normative schema converged while one legal operation branch
both requires and forbids fields. R8 resolves two blockers and supplies the
right architecture for the third. It has not yet made that third branch
internally conformant.

Repair the two matrix/completeness phrases above, then stop reviewing and
implement. At that point the correct verdict is **GO-WITH-CONDITIONS**, with
production rollout held by the specified phase gates, fake-server and
kill-point proofs, and controlled live-canary evidence.

# Verdict: NO-GO

**Convergence: not reached.** r5 resolves four of the six r4 blockers. The
seal/finalization protocol, manual-delivery status, athlete-m contract, and
changed-content evidence now cross the prior bar. Two items remain spec-level:
D1 still permits cancellation to finalize on grant expiry without proving the
currently authorized batch has stopped, and D0's closed supersession union
cannot verify a `keep` or compensate an `update`/`delete` as written.

Disposition summary: **4 RESOLVED, 2 NOT RESOLVED**.

These are narrow contract repairs, not grounds for another broad architecture
rewrite. Once they are fixed, every remaining uncertainty in this review is
closed only by implementation, fake-server proof, or a controlled live canary;
the spec should then converge and implementation should begin.

## Review basis

I read the complete r1, r2, r3, and r4 Codex reviews before reviewing the full
r5 document and Appendix 1's r4→r5 map. I checked each of the six edits against
S2, S5, C2, D0–D3, E2, F4, the fixture contract, and the rollout gates.

All code-dependent evidence was obtained only with
`git show origin/main:<path>`, never from the dirty working tree. The review
uses the required pinned ref, `origin/main` @
`af284c2647b20388c7bb57678fc123780f6a6660`. In particular, I rechecked:

- generation order in
  `athletes/scripts/generate_athlete_package.py:3044-3052, 3124-3151`;
- the intake age/HR fields and device hardcode in
  `webhook/app.py:1248-1275, 1483-1490`;
- the pinned manifest inventory and derived `calendar_dates` in
  `athletes/scripts/fulfillment_manifest.py:21-80`;
- the TP-native workout shape in `tools/tp_apply_order.py:237-248`;
- checkpoint-after-POST behavior and current operation coverage in
  `delivery/trainingpeaks/adapter.py:40-94`;
- the one-file atomic writer and current send-then-confirm primitive in
  `webhook/fulfillment_state.py:69-109, 124-165, 169-234`; and
- v1 day-list normalization and synthesized rest days in
  `athletes/scripts/intake_to_plan.py:1033-1077` and
  `athletes/scripts/plan_ir.py:455-464, 490-503`.

## Disposition of the six r4 blockers

| # | r4 blocker | r5 disposition | Evidence-based reason |
|---|---|---|---|
| 1 | S2 acyclic finalization, one `expected_digest`, immutable release/component manifests, Phase 1 hash input | **RESOLVED** | S2 now gives the post-A1.1 order as finalized sources/operation payload → `model_seal` → sealed contract file → artifact bytes → immutable release manifest → approval. `expected_digest` has one definition in D0. Later components have separate immutable manifests. Phase 1 explicitly hashes only the path/digest/size `artifacts` array, excluding the containing seal/digest fields, which correctly binds the eager bytes that pinned PlanIR cannot reproduce. |
| 2 | D1 action predicates, resume re-grant, batch renewal, cancellation finalization | **NOT RESOLVED** | The predicate table, initial atomic APPROVED→APPLYING exchange, same-attempt re-grant, verify/rollback predicates, and batch renewal are present. The cancellation rule nevertheless treats an **expired** grant as quiescence even though authorization is checked only between batches; the already-started batch may still mutate. See blocker 1. |
| 3 | D0 common shape, logical keys, complete supersession validation, `calendar_dates` | **NOT RESOLVED** | The requested fields, per-kind keys (including attachments), full prior-ID validation, and `calendar_dates` clarification are present. But `keep` deliberately carries neither payload nor digest while readback requires a digest, and the per-kind rollback strategies cannot undo supersession updates/deletes. Partial APPLYING supersession and irreversible kinds are also inconsistent with the universal disposition rule. See blocker 2. |
| 4 | D3/S5 honest manual-application status | **RESOLVED** | `APPLIED_ATTESTED` is provenance-distinct, release-equivalent, upgradeable only after complete readback, and excluded from automated rollback when non-reconcilable. APPLIED retains one global meaning: the complete required set verified by readback. |
| 5 | C2 + athlete-m fixture contradictions | **RESOLVED** | C2 normatively exempts the race-day entry from an off-day prohibition; intake pins age 45 and an empty HR threshold; the Phase 4 probe pins account age 19 and LTHR 148; and D2 confirmations now appear only in the Phase 4 golden. The pinned intake adapter confirms `age` and `hr_threshold` are real input keys. The Phase 1 sets are closed and contain only Phase 1 outputs. |
| 6 | E2 evidence for `used_exactly:false`; confirm never sends | **RESOLVED** | The changed-content path now stores actual body and attachment digests, a content snapshot reference, the comparison result, and a second reviewed override bound to that evidence and revision. The v2 primitive is explicitly evidence validation plus exactly-once state recording and never sends to the athlete. This cleanly replaces the pinned callback, which currently invokes `send()` before recording CONFIRMED. |

## New spec-level blockers

These are contradictions exposed by the r5 fixes themselves. They are not
live-platform questions and cannot be delegated to implementation choice.

### 1. Grant expiry is not proof that the last authorized batch has stopped

> “Grants are short-TTL and must be renewed between operation batches”

> “CANCELLED may finalize (and F4 compensation may begin) only after every
> grant for the order is expired or revoked-and-acknowledged”

> “compensation never races a live writer”

Renewal between batches means a worker may validate a grant, start a bounded
batch, and continue that batch past the grant's wall-clock expiry. The rule then
allows CANCELLED to finalize merely because the grant is expired, even though
the batch has not acknowledged cancellation or completion. A TTL lease has the
same problem: after expiry another holder can acquire it, but TrainingPeaks does
not enforce the local fencing token against the old holder's already-running
HTTP calls. Therefore “expired” does not establish the claimed no-live-writer
condition.

F4 depends on the missing fact: any landed set enters compensation, and D3
appends landed operations as they complete. If cancellation snapshots the set
and starts compensation while the final batch can still append to it, the
cleanup set is incomplete and compensation can race or miss a late mutation.
This is the exact cancellation-finalization race left by r4 blocker 2, narrowed
but not closed by batching.

**Required change:** define an authoritative cancel-request/execution epoch and
a quiescence handshake. After cancellation is requested, no new batch may
start. CANCELLED and compensation may proceed only after every in-flight batch
has acknowledged stop/completion and released the lease. Expiry may count as
quiescence only if the worker revalidates the grant/epoch and fencing token
immediately before **every** remote mutation and durably proves no mutation is
in flight. Make the final landed inventory snapshot occur after that barrier.

### 2. The supersession document cannot verify `keep` or undo `update`/`delete`

> “`payload`: ... `null for keep/delete`”

> “`expected_digest`: ... `null for keep/delete`”

> “`keep` — digest equal, no write”

> “remote object ... field-set digest equals `expected_digest`”

For `keep`, the contract contains neither the desired payload nor its digest.
It therefore cannot establish the stated “digest equal” precondition or perform
the per-kind readback comparison. `predecessor.op_id` is only a pointer; D0 does
not normatively require dereferencing and retaining the predecessor payload or
digest, and it describes this contract as the complete serialized diff.

The rollback union is also incompatible with the allowed dispositions. D0 says
a dated `update` writes in place and a `delete` removes the predecessor, but the
dated kinds' only rollback strategy is `delete_by_remote_id`. Deleting an
updated object does not restore its prior content, and deleting an object that
the supersession already deleted cannot recreate it. F4 nevertheless promises
rollback of reconcilable landed operations. The contract carries no prior
payload/before-image or `restore_prior_payload`/`recreate_predecessor` strategy
for those cases.

Two boundary cases reinforce the contradiction:

- the complete-document rule applies when revision n merely reached APPLYING,
  while `predecessor.remote_id` is nullable. It does not say how revision n+1
  classifies a prior logical ID that never landed; `update`/`delete` require a
  remote ID, while `create` is stated to be only for new logical IDs;
- the rule requires a delete disposition for every removed prior logical ID,
  but entitlements have no remote marker and explicitly have rollback/revocation
  strategy `none`; singleton removal is likewise not defined.

Pinned evidence makes the migration need real rather than hypothetical: the
current adapter only POSTs workouts, notes, attachments, and entitlements and
checkpoints after the request, while the other path emits TP-native `structure`.
The new schema must therefore carry the missing reconciliation data; it cannot
inherit an existing rollback/readback primitive.

**Required change:** make every disposition self-verifying and compensable or
explicitly non-reconcilable. At minimum, `keep` must carry the desired digest
(and a normative predecessor-payload lookup or payload snapshot); `update`
must carry prior content plus restore semantics; `delete` must carry prior
content plus recreate semantics where the platform supports it. Define allowed
dispositions per kind and the manual-cleanup rule for irreversible operations.
Base completeness on the last landed remote inventory, not merely every
operation in a revision that entered APPLYING, or define the prior-but-unlanded
case explicitly. D3 verification and F4 compensation must consume those same
fields.

## Implementation-gated items

After the two text repairs above, the remaining uncertainty is correctly gated
on building or controlled external evidence:

1. Live TrainingPeaks HR/LTHR/HRmax/RPE acceptance and readback, searchable
   markers, exact create/update/delete behavior, attachment digest visibility,
   singleton CAS feasibility, ambiguous-timeout recovery, and session refresh.
2. Worker login/TOTP/session survival, coaching checks, durable operation
   journal recovery, grant exchange/renewal, lease fencing, quiescence at every
   kill point, rate/egress controls, and audit redaction.
3. Per-kind apply-contract projection, JSON-Schema equivalence, fake-server
   parity, supersession/compensation fixtures, and safe retirement of the JS
   driver after the corrected D0 contract exists.
4. Checking in and executing athlete-m and the metric-neutral HR/LTHR/HRmax/RPE
   fixtures, including the Phase 1/3/4 literal goldens.
5. S5 consumer idempotence and kill-point recovery for notification, guide,
   and draft effects.
6. Gmail OAuth, aliases, sent-state verification, draft/message relationships,
   MIME canonicalization, body hashing, and byte-level attachment verification.
7. Deterministic guide rendering, private/ZIP-only release, publication,
   caching, supersession, and revocation.
8. Endure readback/rollback/invitation suppression. Endure remains safely off
   unless its Phase 5 gate passes.
9. Course `courses[]` implementation/backfill, the external polyline-copy
   change, and the already accepted TrainingPeaks ToS/business risk.

## Non-blocking findings

1. **The Phase 1 seal wording is temporally awkward but decidable.** It calls
   the artifact inventory the “step-4 `artifacts` array” while defining “step
   1's” seal from it. In Phase 1, D0 does not yet exist, so the implementable
   transitional order is: emit all eager bytes → build the path/digest/size
   array → hash that array → write the release-manifest envelope/state. The
   containing seal and manifest digest are expressly excluded. Renumbering the
   transitional steps would improve clarity, but no product/design choice is
   missing.

2. **S5's APPLIED_ATTESTED override should be applied mechanically to literal
   status lists.** B3 lists customer-download states as `{APPROVED, APPLIED,
   CONFIRMED}`, while E1/E2 say “on/after APPLIED.” S5 and D3 explicitly state
   that APPLIED_ATTESTED has the same downstream release rights and that E1/E2
   accept either. That controlling rule makes the behavior unambiguous; the
   literal lists should be updated during implementation to avoid drift.

3. **D3 retains stale “per operation policy” wording.** D0 now fixes the policy
   directly and says there is no policy indirection. Reading D3's phrase as a
   cross-reference to D0 is unambiguous, so this is editorial rather than a
   missing design decision.

4. **`calendar_dates` is now characterized correctly.** Pinned
   `fulfillment_manifest.py:66-71` derives it by sorting the dates already
   present on workout records; the adapter's mutation loops do not consume it.
   Treating it as verification inventory preserves the feature without
   inventing a remote operation.

5. **The fixture's remaining Saturday wording is harmless.** Phase 1 says
   `SCHEDULE_CONTRADICTION` does not fire because “no explicit prohibition
   exists,” although Saturday is an explicit off-day. The operative reason is
   the new C2 race-day exemption, which the fixture states directly. The golden
   result is therefore determinate.

## Could not verify

1. I could not verify any live TrainingPeaks marker, remote ID, HR/RPE
   structure, update/delete/rollback, singleton, entitlement-revocation,
   attachment-readback, or idempotency behavior. The pinned adapter supplies no
   such proof; its local fake server itself deduplicates by external ID.
2. I could not verify the worker, capability exchange, execution grants,
   cancellation acknowledgement, lease fencing, or durable journal. They are
   specification-only at the pinned ref.
3. I could not verify state schema v2, `APPLIED_ATTESTED`, model/release/component
   manifests, the in-state outbox, review pages, typed tokens, or the normative
   apply-contract projection; the pinned code remains the v1 state/manifest
   paths cited above.
4. I could not execute athlete-m. `git show
   origin/main:tests/fixtures/athlete_m/intake.json` reports no such path at the
   pinned ref; no real customer's Railway intake was accessed or copied.
5. I could not verify Gmail provider evidence, changed-content UI capture,
   aliases, OAuth, MIME/body hashing, attachment fidelity, or exactly-once
   outbox reconciliation.
6. I could not verify deterministic guide publishing/privacy/revocation, live
   Endure behavior, production course matching, or the external
   `gravel-god-training-plans` polyline copy.
7. I could not verify TrainingPeaks terms-of-service acceptability; the spec
   records it as an accepted business risk rather than a technical claim.

## Convergence assessment

The convergence rule is not yet met. The two remaining issues are not matters
that only code can answer: the text must define a real no-writer cancellation
barrier and a supersession record that can verify and compensate every allowed
disposition.

No further broad architecture round is warranted. After those two localized
contracts are repaired, all remaining items above require implementation or
live evidence, so the next step should be implementation rather than another
speculative redesign.

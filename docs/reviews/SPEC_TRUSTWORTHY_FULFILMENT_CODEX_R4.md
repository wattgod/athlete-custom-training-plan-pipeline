# Verdict: NO-GO

**Convergence: not reached.** r4 closes three of the nine r3 blockers and
substantially improves four more, but six remain spec-level. They are decidable
in text now: the seal/finalization graph, the action-specific capability/state
handshake, the serializable supersession contract, APPLIED semantics for manual
delivery, the athlete-m golden contract, and changed-content manual-send
evidence. The remaining live-platform questions are still properly
implementation-gated.

Disposition summary: **3 RESOLVED, 6 NOT RESOLVED**.

## Review basis

I read the r1, r2, and r3 Codex reviews before reviewing r4. I then checked the
nine changed areas against the whole r4 document, including S/C/D/E/F and the
rollout gates.

All code-dependent evidence in this review was obtained only with
`git show origin/main:<path>`, never from the dirty working tree. The required
ref resolves to:

```text
$ git rev-parse origin/main
af284c2647b20388c7bb57678fc123780f6a6660
```

Working-tree reads were limited to the supplied specification and prior review
documents. Relevant pinned anchors were rechecked for the one-file atomic
write/lock and current confirmation primitive
(`webhook/fulfillment_state.py:69-109, 169-234`), generation order
(`athletes/scripts/generate_athlete_package.py:3044-3052, 3124-3151`), the two
manifest shapes (`athletes/scripts/fulfillment_manifest.py:21-42, 67-80` and
`tools/tp_apply_order.py:237-248`), adapter checkpoint behavior
(`delivery/trainingpeaks/adapter.py:40-94`), the intake schema/device hardcode
(`webhook/app.py:1248-1275, 1485-1487`), and day-list/off-day normalization
(`athletes/scripts/intake_to_plan.py:1033-1077`).

## Disposition of the nine r3 blockers

| # | r3 blocker | r4 disposition | Evidence-based reason |
|---|---|---|---|
| 1 | Self-referential seal / Phase 1 authority | **NOT RESOLVED** | Zeroing the contract's seal field removes the direct fixed-point hash, and Phase 1 now binds eager artifact bytes. However, the stated finalization order hashes the apply-contract artifact before its `model_seal` can be filled, `expected_digest` has two contradictory definitions, and approval binds a release-manifest digest that r4 later permits appending to. See blocker 1. |
| 2 | Adjacent-file outbox is not crash-atomic | **RESOLVED** | S5 puts the transition and pending entry in the same state object and commits both with the one atomic replacement supported by the pinned state writer. Marking delivery in a later locked write is consistent with a transactional outbox; it is not supposed to be in the originating transition. Handler idempotence remains a build/proof obligation. |
| 3 | Capability cannot represent probe, revocation, and crash-safe retry | **NOT RESOLVED** | The probe/mutation union and durable per-JTI record solve the missing-subject and burn-before-mutate defects. The online exchange nevertheless authorizes only `APPROVED`, which is incompatible with `APPLYING` resume and with verify/rollback; one-time exchange also has no re-grant rule after a crash, and cancellation can still race a live grant. See blocker 2. |
| 4 | Apply contract is not normative/implementable | **NOT RESOLVED** | The table is much better, but its declared common operation shape omits fields the same section requires, and it has no serializable representation for keep/delete supersession dispositions. A JSON Schema cannot be generated equivalently from the text as claimed. See blocker 3. |
| 5 | Revision-scoped identity breaks supersession | **NOT RESOLVED** | The conceptual split among `logical_id`, revision-scoped `op_id`, and non-revisioned optional `remote_marker` is correct. The operation union does not carry `remote_marker` or `predecessor`, does not define all logical keys, and cannot encode removed or kept prior resources, so D3/F4 still cannot execute the promised diff. See blocker 3. |
| 6 | Partial application remains APPROVED and cancellation leaks landed work | **RESOLVED** | APPROVED → APPLYING → APPLIED, durable `landed[]`, and F4's branch on landed operations close the exact r3 leak. A separate new contradiction remains: manual fallback may record APPLIED with no readback even though APPLIED is defined as completely verified. See blocker 4. |
| 7 | athlete-m is not an exact, consistent fixture | **NOT RESOLVED** | The week arithmetic, date discrimination, generated-placement schedule rule, device key, and closed-list intent are improved. The fixture still has an off-day/race-day contradiction, expects D2 values absent from its inputs, and requires Phase 4 outputs at the Phase 1 gate. See blocker 5. |
| 8 | Manual send evidence does not bind sent content | **NOT RESOLVED** | `used_exactly: true` is now a content-specific attestation. When it is false, however, r4 stores only the expected digests and free-text deviation—not the actual sent snapshot/digests required by r3—yet permits a second action to confirm. See blocker 6. |
| 9 | v1 migration cannot recover order identity safely | **RESOLVED** | S1 now refuses slug inference, assigns an opaque legacy identity, quarantines inherited authority, preserves evidence, requires authenticated manual binding, revokes old tokens, records multiple candidates, and defines recoverable path movement. This is a fail-closed migration. |

## Remaining and new spec-level blockers

### 1. The two-layer seal is still not a coherent immutable finalization protocol

> “`model_seal` ... [includes] the apply contract normalized with every
> seal/digest-result field set to the empty string before hashing”

> “`expected_digest` results computed *from* the seal — not operation
> payloads”

> “`expected_digest` = sha256 of the canonically serialized `payload`”

> “finalization order is: emit artifacts → compute per-artifact digests →
> compute model_seal → write both to state”

> “Approval records `{model_seal, release_manifest_digest}`”

> “projections built after approval ... append[] to the release manifest”

The explicit hash fixed point is gone, but the finalization graph remains
contradictory:

1. The apply-contract envelope contains `model_seal`. Under the stated order,
   the apply-contract file is emitted and hashed before that seal exists. Filling
   the seal afterward changes the file and invalidates its Layer 2 digest;
   leaving it empty violates the final contract envelope used by the worker.
2. S2 says `expected_digest` is computed from the seal and not from operation
   payloads, while D0 defines it as the hash of the payload.
3. Approval records `release_manifest_digest`, but post-approval appends change
   that digest. The release manifest can no longer match the approval it is
   required to match.

The Phase 1 improvement itself is sound: hashing the ordered path/digest/size
inventory of every eager artifact binds the ZWO/guide bytes that pinned PlanIR
cannot reproduce. Pinned generation really is ZWO → guide → advisory PlanIR at
`generate_athlete_package.py:3044-3052, 3124-3131`.

**Required change:** define one acyclic immutable sequence, for example:
canonical model + normalized contract payload → `model_seal` → finalized apply
contract → all artifact bytes → immutable release manifest →
`release_manifest_digest` → approval. Define `expected_digest` once. Either
forbid appending to an approved release manifest or make later projections a
separate, model-seal-bound component manifest with its own immutable digest and
explicit approval rule. State exactly whether the Phase 1 hash input is the
`artifacts` array only (excluding its containing `model_seal` and digest).

### 2. The online capability exchange conflicts with APPLYING, verify, rollback, resume, and cancellation

> “the webhook ... re-validates its authoritative state (status is APPROVED,
> revision current, not CANCELLED, seal matches)”

> “APPROVED → APPLYING (attempt record created ...) → APPLIED”

> “retry resumes reconciliation under the same jti/lease”

> “rollback is a separate capability requiring explicit operator action”

The exchange predicate can authorize only the initial apply. Once D3 creates
APPLYING, a retry cannot pass an APPROVED-only exchange. Verification occurs
during/after application, and rollback is needed from APPLYING, APPLIED, or a
cancellation workflow; neither can satisfy that predicate. A crash after the
one-time exchange but before a durable successful result also needs a new grant,
possibly under a new fencing token, but r4 defines neither reissue nor transfer.

There is also still a cancellation race. A grant is checked once “before its
first mutation.” Cancellation can commit after that check while the worker
continues to land later operations. F4 can inspect and compensate the landed set
too early, then mark CANCELLED while a valid worker continues writing. A
short-lived grant narrows this window; it does not close it.

This does **not** contradict the worker's authority boundary: r4 says the worker
does not hold *authoritative fulfilment state*, while its leases and operation
journal are explicitly operational state. That distinction is coherent.

**Required change:** define action-specific exchange predicates and an atomic
handshake. An initial apply should atomically bind its grant to the matching
APPROVED → APPLYING attempt; resume should authorize only the same APPLYING
attempt/digest; verify and rollback need predicates for their actual states.
Define re-grant behavior for `accepted|running` recovery with a new fencing
token. Cancellation/compensation must coordinate on the same TP-athlete lease,
revoke or advance an execution epoch, and require the worker to observe
cancel-requested between operations before CANCELLED can finalize.

### 3. D0 cannot serialize the supersession diff it normatively requires

> “Operation union — common fields `{op_id, logical_id, kind, payload,
> expected_digest, rollback}`”

> “`remote_marker` — optional, present only for kinds with a remote field that
> round-trips”

> “removed → delete via `remote_id`”

> “Each superseding operation records `predecessor: {op_id, remote_id}`”

The declared common shape contains neither `remote_marker` nor `predecessor`.
The union contains only upserts/grants/singleton updates: there is no delete or
no-op/disposition record that can represent a removed or kept revision-n
resource. In particular, a removed logical ID has no revision-n+1 upsert on
which the required predecessor could be stored. The text also omits a logical
key for attachments and does not say whether singleton `before_image` is inside
`payload` or beside it.

This is not theoretical schema polish. D0 says the implementation JSON Schema
must be generated from this definition, D3 persists landed `op_id`s, and F4
depends on logical-ID-matched predecessor-linked compensation. Those consumers
cannot agree on a document the normative union cannot express. Pinned evidence
also confirms why an exact migration is necessary: the adapter manifest carries
internal `segments`, attachments, tasks, and entitlement
(`fulfillment_manifest.py:21-42, 67-80`), while the JS path carries TP-native
`structure` (`tp_apply_order.py:237-248`).

**Required change:** extend the normative schema with the identity fields and a
closed supersession-disposition union (`keep|update|delete|create`, or explicit
operation kinds), including predecessor/remote-ID requirements per disposition.
Define logical-key construction for every kind, exact placement and schema of
before-images/readback data, and required/forbidden fields. Then make ordering,
landed inventory, verify, and rollback refer to those same serializable records.

### 4. Manual fallback violates the global meaning of APPLIED

> “APPLIED remains strictly the *complete verified* calendar fact”

> “APPLIED means the complete required operation set verified by readback”

> “I imported manually records APPLIED with a typed inventory ... + optional
> readback”

These cannot all be true. A typed inventory without readback is evidence of a
coach assertion, not a verified calendar fact. `non_reconcilable` describes
rollback capability; it does not establish that the required objects actually
landed.

**Required change:** either require complete readback before any automated or
manual path reaches APPLIED, or introduce an honestly named manual/unverified
status and define which release actions it permits. Do not weaken APPLIED in one
branch while S5/D3 use it as the release truth everywhere else.

### 5. athlete-m still cannot produce its literal Phase 1 golden

> “off-day `saturday`”

> “race date `2026-09-19`”

> “`SCHEDULE_CONTRADICTION` [must not fire] (no explicit prohibition exists)”

> “Required confirmations exactly ... D2 threshold mismatch (`lthr` ...), D2
> demographic mismatch (age 19 vs 45)”

There are three concrete contradictions:

1. 2026-09-19 is a Saturday. C2 explicitly defines “a stated off-day
   scheduled” as `SCHEDULE_CONTRADICTION`, and the golden requires a race-day
   entry on that date. The fixture therefore both supplies and denies an
   explicit prohibition. No race-day exception is specified.
2. The listed intake values do not give age 45 or an LTHR/HR-threshold value,
   and `worker_probes.json` gives FTP 197 W but no account LTHR. The two exact
   D2 confirmations cannot be derived from the stated bytes. The pinned intake
   schema does have `age` and `hr_threshold` fields
   (`webhook/app.py:1251-1259`), so the fixture can and must pin them.
3. The Phase 1 gate requires the literal required-confirmation set, but S3 is
   Phase 2 and D1/D2 probes are Phase 4. Phase 1 cannot emit D2 inspection
   confirmations under r4's own dependency order.

The requested arithmetic/discrimination otherwise checks out: W00 is excluded,
so W1–W6 is six delivered paid weeks versus seven purchased; Aug 5 is after the
Aug 4 local order date but before the Aug 6 local generation date; and disjoint
long/interval lists are compatible with C2 because the confirmation is caused
by the generated Sunday VO2 placement, not list overlap.

**Required change:** either remove Saturday as an off-day or normatively exempt
the race-day entry from that constraint. Add exact intake/account age and LTHR
fields. Move D2 confirmation goldens to the Phase 4 fixture/gate, or move their
prerequisites earlier; each phase's closed set must contain only outputs that
exist in that phase.

### 6. The changed-content manual confirmation path still does not bind what was sent

> “the system supplies the expected values”

> “`{... expected_body_digest, expected_attachment_digests, used_exactly:
> true|false, deviation?, ...}`”

> “`used_exactly: false` requires a `deviation` description and an explicit
> reviewed override”

For `used_exactly: true`, this is a clear attestation that the sealed bytes were
used. For `false`, the record still contains only the expected digests and a
free-text difference. It does not contain the actual sent body digest,
attachment inventory/digests, or content snapshot. A second confirm action can
approve the fact of deviation, but cannot make the missing evidence identify
what was delivered.

The pinned `confirm_after_send` currently calls a Boolean `send()` callback
while holding the state lock and then records arbitrary metadata
(`fulfillment_state.py:215-234`). Retaining its serialization/idempotence
pattern is compatible with human sending only if r4 explicitly changes that
callback into evidence validation; it cannot retain the current send semantics
after removing the customer send.

**Required change:** when content differs, require the actual coach-attested
body digest/snapshot and complete actual attachment inventory/digests, store the
comparison result, and bind the reviewed override to that actual evidence and
revision. State explicitly that the v2 primitive validates typed evidence under
the lock and never invokes an athlete send.

## Implementation-gated items

Subject to the six text repairs above, r3's implementation-gated list remains
correct and should not trigger another speculative design round:

1. Live TrainingPeaks HR/LTHR/HRmax/RPE acceptance and readback, marker search,
   exact create/update/delete behavior, singleton CAS feasibility, ambiguous
   timeout recovery, and session refresh.
2. Worker login/TOTP/session survival, SPA drift handling, coaching checks,
   fenced lease behavior, operation-journal recovery, rate/egress controls, and
   audit redaction.
3. Per-kind apply-contract projection/parity and safe retirement of the JS
   driver after the corrected D0 schema exists.
4. Execution of athlete-m and metric-neutral fixtures after their contradictory
   golden contract is repaired.
5. Gmail OAuth, sender aliases, provider message/draft relationships, MIME
   canonicalization, sent-state lookup, and byte-level attachment verification.
6. Deterministic guide PDF rendering, private/ZIP-only release, publishing,
   cache behavior, and revocation.
7. Endure readback/rollback/invitation suppression; Endure must remain disabled
   until this passes.
8. Course `courses[]` implementation/backfill, the external polyline-copy
   change, and the accepted TrainingPeaks terms-of-service/business decision.
9. S5 handler idempotence and kill-point recovery for each outbox consumer.
   The in-state outbox now gives correct at-least-once delivery; proving that a
   Gmail draft, notification, or publish effect can reconcile by `event_id`
   requires building the handler/provider adapter.

## Non-blocking findings

1. **S5's later locked status write is internally consistent.** Atomicity is
   needed between the business transition and enqueue, not between enqueue and
   an external side effect. The later write should reload state under lock and
   update only the matching `event_id`; concurrent consumers and
   effect-before-mark are handled by the required idempotence/reconciliation.

2. **The worker does hold state, but not fulfilment authority.** Its lease,
   per-JTI operation record, intents, and results do not contradict the claim
   that the webhook remains authoritative. “No authoritative state” is the
   precise statement; “worker holds no state” would be false, but r4 does not
   make that broader claim.

3. **The three-identity model is directionally correct.** A cross-revision
   logical resource, a revision attempt, and an optional remote marker are the
   right distinctions. The blocker is that the normative operation document
   does not actually serialize the fields/dispositions D3 and F4 need.

4. **C2's schedule semantics now match the adjudicated v1 meaning.** Disjoint
   long-ride and interval lists do not themselves conflict. A generated VO2
   session on Sunday is a `SCHEDULE_MISMATCH_CONFIRM`; it is not evidence that
   the input lists overlap.

5. **The date and week rules are now discriminating.** The fixture's Aug 5
   session correctly separates `SESSION_PREDATES_GENERATION` from
   `SESSION_PREDATES_ORDER`, and W00 is correctly excluded from the six-versus-
   seven F6 comparison.

6. **Legacy migration is now fail-closed.** Implementation should keep
   `legacy_order_id` immutable and record a later ledger binding as a relation,
   rather than rewriting the primary identity; that follows S1's intent and
   does not require another spec round.

7. **`calendar_dates` is an inventory/verification field in the pinned
   fulfillment manifest, not an adapter mutation loop.** D0's statement that
   every pinned “operation class” is retained should avoid calling
   `calendar_dates` a remote operation class, but no feature is necessarily
   lost if dates remain derived from dated operations.

## Could not verify

1. I could not verify any live TrainingPeaks protocol behavior: stable markers,
   HR/RPE structures, remote IDs, update/delete/rollback, singleton writes,
   idempotency, or readback. No controlled live evidence exists at the pinned
   ref.
2. I could not verify the worker, online capability exchange, lease fencing,
   durable operation journal, or cancellation behavior; they are
   specification-only.
3. I could not verify state schema v2, the in-state outbox, model/release seals,
   review pages, tokens, release components, or the normative apply-contract
   projection; none is implemented at `origin/main`.
4. I could not execute athlete-m. Its claimed checked-in files and expected
   goldens do not exist at the pinned ref, and the real customer's Railway
   intake was not accessed or copied.
5. I could not verify Gmail provider evidence, manual evidence UI, OAuth,
   aliases, MIME/body hashing, attachment fidelity, or outbox-level draft
   idempotence.
6. I could not verify deterministic guide publishing/privacy/revocation, live
   Endure behavior, production course matching, or the external
   `gravel-god-training-plans` polyline copy.
7. I could not verify TrainingPeaks terms-of-service acceptability; r4 records
   it as an accepted business risk rather than a technical claim.

## Convergence assessment

r4 is close, but the convergence rule is not yet met. The six blockers above
are not questions that only code or live canaries can answer: the spec can and
must choose the immutable seal order, state/action exchange predicates,
serializable supersession records, the meaning of APPLIED, consistent fixture
inputs/phase goldens, and the schema for changed manual-send evidence.

Once those contracts are repaired, the remaining uncertainty is the execution
and live-platform evidence listed under implementation-gated items. At that
point the spec should converge and implementation should begin without another
broad architecture rewrite.

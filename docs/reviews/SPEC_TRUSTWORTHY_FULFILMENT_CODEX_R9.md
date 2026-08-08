# Verdict: GO-WITH-CONDITIONS

**Convergence: reached at the specification level.** R9 repairs the sole R8
blocker without reopening or weakening the settled architecture. The D0 field
matrix, kind-aware completeness rules, effective-inventory transitions, and
required generated-schema tests now agree for first and subsequent revisions
of both positional keep branches. I found no new spec-level contradiction.

Implementation should begin. This verdict is not approval for an ungated
production rollout: the phase gates, fake-server and kill-point proofs, and
controlled live-canary evidence below remain mandatory.

## Review basis

I read the Codex R1 through R8 reviews before reviewing the complete R9 draft,
including D0, D1-D3, F4, the rollout, the review log, and Appendix 1. I applied
the same convergence rule used in R6-R8: a normative contradiction remains a
spec blocker, while behavior that can only be established by implementation or
a controlled external proof becomes a standing implementation condition.

All code-dependent checks used only `git show origin/main:<path>`, never the
dirty working tree. `git show -s --format=%H origin/main` returned
`af284c2647b20388c7bb57678fc123780f6a6660`. The pinned code still has the old
POST-then-checkpoint adapter and operation set, two different manifest/apply
shapes, the v1 one-file state machine, and a fake server that supplies its own
external-ID deduplication. Those facts support keeping the remaining platform
claims behind implementation and canary gates; they provide no implicit rule
that would alter R9's normative positional branches.

## Disposition of the R8 blocker

**RESOLVED.** Both collisions identified in R8 are repaired to the same
evidentiary standard.

1. **First-revision singleton keep:** the field matrix makes `before_image`
   absent for every singleton `keep` and makes `predecessor` depend solely on
   effective-inventory existence. The completeness branch now distinguishes a
   mutating first-revision singleton `update` (`before_image` required) from a
   verified first-revision singleton `keep` (`before_image` absent, digest and
   provenance supplied by the D2 inspection snapshot). This agrees with the
   keep digest rule and the install-on-absent inventory transition.
2. **Adopted pre-existing entitlement keep:** the matrix now requires no
   predecessor only when the effective inventory has no record, and requires
   one after either a grant or a verified keep installed a record. That agrees
   with the global predecessor rule, the verified-keep install transition, and
   the absent-entitlement completeness branch. Historical origin no longer
   controls schema validity.
3. **Branch coverage:** D0 now expressly requires generated JSON-Schema and
   completeness tests for first and subsequent revisions of an adopted
   singleton keep and an adopted pre-existing entitlement keep. These are the
   exact branches whose predecessor requirement changes after inventory
   installation.

The adjacent R8 editorial finding is also repaired: D3 now says a partial
failure retains the exact landed **journal and effective inventory**, preserving
the journal/inventory distinction established in D0.

## New spec-level blockers

None.

I checked the repaired phrases against the declared single-authority matrix,
the per-disposition digest rule, the common predecessor schema, the closed
inventory transition table, the kind-aware completeness rules, D3's same-write
rule, and F4's journal-based compensation rule. No legal branch now requires
and forbids the same field, and the repaired branches do not introduce a new
identity, state, compensation, or ordering conflict.

## Standing conditions for implementation and production rollout

1. **Keep the dependency-ordered rollout and satisfy every phase gate.** Do
   not advance a write-capable path merely because its code exists. Phase 1's
   athlete-m golden, Phase 2's seal-bound page approval, Phase 3's offline
   projection fixtures, Phase 4's zero-write live inspection, and Phase 5's
   end-to-end gate remain release criteria.
2. **Generate and enforce the D0 schema exactly.** The checked-in
   `apply_contract/v1` JSON Schema must be equivalent to D0, including all
   kind/disposition field branches and first/subsequent-revision cases for the
   adopted singleton and adopted pre-existing entitlement keeps. Unknown
   contract versions fail closed.
3. **Prove migration parity before retiring the JS driver.** Against the fake
   server, the old fulfillment-manifest path and the new contract must have
   equivalent effects for workouts, derived calendar-date verification,
   notes, attachments, mental tasks, and course entitlement. The old driver
   stays non-exposed and is retired only after this gate passes.
4. **Prove reconciliation, supersession, and compensation at every kill
   point.** Tests must cover persisted intents, ambiguous timeouts, zero/one/
   multiple remote matches, remote-ID persistence, singleton CAS, the atomic
   landed-journal/effective-inventory update, every inventory transition,
   partial APPLYING recovery, cross-revision diffs, cancellation barriers, and
   all supported rollback/restore/recreate paths. Irreversible entitlement and
   non-reconcilable manual cases must remain explicit coach-cleanup work, never
   reported as automatically rolled back.
5. **Prove the worker's authorization and quiescence protocol.** Capability
   exchange, action predicates, request-digest replay handling, durable
   accepted/running recovery, per-athlete lease fencing, per-mutation grant and
   epoch revalidation, enforced maximum mutation duration `M`, journal flush,
   lease release, acknowledgement/fallback ordering, cancellation, credential
   isolation, rate/egress controls, and audit redaction all require fake-server
   and kill-point proof before production writes.
6. **Obtain controlled live TrainingPeaks evidence before customer use.** The
   canary must establish SPA/session behavior, coaching and identity checks,
   stable marker round-trip/search, persisted remote IDs, HR/LTHR/HRmax/RPE
   acceptance and readback, exact create/update/delete/restore/recreate
   behavior, attachment visibility, singleton feasibility, ambiguous-timeout
   recovery, rollback, and the limits of TP-side idempotency. The current fake
   server is not that evidence. Canary health must gate every apply batch as
   D1 specifies.
7. **Check in and pass the deterministic fixtures.** Athlete-m's literal Phase
   1/3/4 goldens and the HR-with-LTHR, HR-only-HRmax, and RPE-only fixtures must
   pass, including zero-watt assertions, exact blocker/confirmation sets,
   review-bundle non-executability, and the new positional first/subsequent
   revision completeness cases. No real customer data may enter the fixture.
8. **Prove state, token, seal, and outbox failure behavior.** Schema-v2
   migration/quarantine, order isolation, revision-bound scoped tokens,
   revocation, seal checks, blocker merging, release-component state, and the
   in-state outbox must fail closed. Every outbox consumer must reconcile by
   `event_id`, with kill-point tests for entry-before-effect and
   effect-before-mark.
9. **Gate Gmail confirmation on typed evidence.** Before production release,
   prove OAuth/alias handling, provider sent-state verification, recipient and
   revision binding, MIME/body canonicalization, byte-level attachment
   digests, draft/message relationships, manual-attestation snapshots and
   reviewed overrides, and that the v2 confirm path never sends to the
   athlete.
10. **Gate guide release on deterministic and revocable behavior.** Prove
    rendering, artifact-seal verification, privacy, cache behavior,
    supersession, and cancellation revocation. Until the Phase 5 privacy
    decision is made and its path is proven, the safe default remains no public
    URL: guide delivery is ZIP/attachment only.
11. **Meet all Phase 5 prerequisites before enabling a platform.** F4
    cancellation/regeneration compensation, F5 brand isolation, the guide
    privacy decision, rollback proof, HR/RPE acceptance, and marker round-trip
    must be complete. Endure remains disabled unless it independently meets
    the same approval, readback, rollback, failure, and no-platform-email gate;
    it may not silently fall back to TrainingPeaks.
12. **Finish with controlled end-to-end evidence.** Production rollout
    requires the specified real order to move through generated, reviewed,
    approved, applied, readback-verified, guide released, Gmail-drafted,
    coach-sent, and provider-verified CONFIRMED states without bypasses. Course
    facts remain protected by the non-waivable `COURSE_UNRESOLVED`/facts-omitted
    path until the tracked `courses[]` work lands. The external polyline-copy
    follow-up remains tracked, and the accepted TrainingPeaks ToS exposure must
    remain logged as a business risk rather than represented as technical
    assurance.

## Non-blocking findings

1. **Appendix 1 omits the claimed R8→R9 disposition map.** The review log at
   the top accurately records the R9 repairs, but Appendix 1 begins with
   “r7 blockers → r8”; there is no R8→R9 table. This is bookkeeping, not a
   normative ambiguity: D0 and D3 contain the repairs and are internally
   consistent. Add the missing map when the spec is next touched.
2. **The draft-status header is now administratively stale.** This review
   supplies the requested convergence decision, so “awaiting adversarial
   re-review” can be changed when implementation begins. It does not affect the
   contract.
3. **The effective-inventory design is now coherent.** `landed[]` remains the
   append-only compensation source, while the materialized inventory is the
   supersession authority. The positional keep installs make the exact same
   inventory-existence predicate usable by the matrix, predecessor rule, and
   next revision.
4. **No broader redesign is indicated.** The remaining uncertainty is the
   implementation/live-evidence work already named by the spec and prior
   reviews. Reopening settled identities, states, seals, or manual-delivery
   semantics would not improve convergence.

## Could not verify

1. I could not verify live TrainingPeaks marker, remote-ID, HR/RPE,
   update/delete/restore/recreate, singleton, entitlement, attachment-readback,
   or idempotency behavior. No controlled live evidence exists at the pinned
   ref.
2. I could not verify the worker, capability/grant exchange, execution epochs,
   per-mutation revalidation, lease/quiescence protocol, durable journal,
   materialized effective inventory, or cancellation fallback; none exists at
   `origin/main`.
3. I could not verify the generated `apply_contract/v1` JSON Schema,
   equivalence/completeness tests, fake-server migration parity, or
   first/subsequent-revision positional fixtures because they are not
   implemented at the pinned ref.
4. I could not execute athlete-m or the HR/LTHR/HRmax/RPE fixtures. The pinned
   ref does not contain athlete-m, and no real customer's Railway input was
   accessed or copied.
5. I could not verify schema-v2 migration, APPLYING/APPLIED_ATTESTED/CANCELLED,
   model/release/component manifests, typed tokens, review pages, or outbox
   consumer recovery; the pinned code remains the v1 implementation.
6. I could not verify Gmail evidence/drafting, deterministic guide rendering
   and revocation, live Endure behavior, production course matching, or the
   external polyline copy.
7. I could not verify TrainingPeaks terms-of-service acceptability. The spec
   explicitly records browser automation as an accepted business risk, not a
   technical claim.

## Convergence assessment

The R6/R7/R8 decision rule now yields **GO-WITH-CONDITIONS**. R9 removes the
last choice that implementation could not make without violating one of two
normative clauses. The remaining unknowns are precisely the facts that require
code, fake-server/kill-point execution, or controlled live-platform evidence;
they are captured above as rollout conditions rather than manufactured into a
tenth speculative spec round.

Stop reviewing and implement. Production remains held by the specified phase
gates and proof obligations.

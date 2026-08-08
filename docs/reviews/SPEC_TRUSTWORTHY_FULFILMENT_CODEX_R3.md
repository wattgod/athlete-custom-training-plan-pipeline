# Verdict: NO-GO

**Convergence: not reached.** r3 resolves most of r2's findings and is materially closer to an implementable design, but nine remaining defects are still spec-level: they can and must be closed by changing the normative text before implementation. The residual live-platform questions are listed separately under “Implementation-gated items”; those do satisfy the team's “only building can close them” rule, but the nine blockers do not.

Disposition summary:

- r2 new blockers: **9 resolved, 5 partially resolved, 1 not resolved**.
- r2-partial/unresolved r1 blockers: **7 resolved, 4 partially resolved, 1 not resolved**.
- r2 non-blocking findings: most are folded in; the exact fixture remains unresolved, and the cross-repo polyline tracking and device-input contract remain partial.

## Review basis

I read the r1 and r2 Codex reviews first, then r3, the handoff, the Monika findings, the updated race-course ticket, and the prior TrainingPeaks ticket. The prior TP ticket is absent from the working tree but present at the pinned ref, so I read it with `git show`.

All code evidence below is from the required ref, never the dirty working tree:

```text
$ git rev-parse origin/main
af284c2647b20388c7bb57678fc123780f6a6660
```

For every code excerpt I used `git show origin/main:<path>`. Working-tree reads in this review are limited to the supplied specification, reviews, and context documents.

## Prior-item disposition

### r2 new blockers 1–15

| r2 blocker | r3 status | Evidence-based disposition |
|---|---|---|
| 1. Consumers scheduled before prerequisites | **RESOLVED** | The rollout now names the dependency graph, gives Phase 1 the existing PlanIR + `tp_manifest.json` transitional inputs, moves D0 offline projection to Phase 3, D1/D2 to Phase 4, and live HR/RPE/write canaries to Phase 5. The original inversions are gone. |
| 2. Approval not bound to reviewed content | **PARTIALLY RESOLVED** | S2 adds seal-bound approval and seal checks, but the digest includes a contract that itself contains the digest, and Phase 1 does not define a reproducible authority for artifacts produced before the transitional model. See new blocker 1. |
| 3. State cannot recover confirmed values | **RESOLVED** | S3 stores the typed catalog value in the approval snapshot, rejects unknown/wrong-revision IDs, and gives sensitive values an explicit server-only home. |
| 4. D2 choices do not change the plan | **RESOLVED** | `use-tp-value` regenerates, `update-from-intake` emits a singleton mutation, `manually-corrected` requires readback, and approval checks consistency against the sealed plan. |
| 5. `apply_contract/v1` is only a name | **PARTIALLY RESOLVED** | D0 supplies an operation union and parity inventory, but defers the actual JSON Schema and payload/readback definitions to implementation, leaves digest canonicalization undefined, and mandates an embedded external ID for kinds that have no such remote object. See new blocker 4. |
| 6. Broker lacks authorization truth/replay/lease | **PARTIALLY RESOLVED** | Signed single-action capabilities and a fenced TP-athlete lease are the right architecture, but the capability subject cannot represent pre-ID probes, a capability survives cancellation/regeneration, and consume-before-mutate strands a crash. See new blocker 3. |
| 7. Reconciliation covers calendar POSTs only | **PARTIALLY RESOLVED** | D3 now defines calendar, singleton, entitlement, and manual behavior. It still records partial remote mutation while leaving the order `APPROVED`, which makes F4's pre-APPLIED cancellation path leak landed objects. See new blocker 6. |
| 8. APPLIED cannot represent release side effects | **NOT RESOLVED** | Component substates fix the truth-model problem, but “state file + adjacent outbox file under one lock” is not crash-atomic. See new blocker 2. |
| 9. Confirm accepts arbitrary evidence | **PARTIALLY RESOLVED** | Provider evidence is substantially specified. Manual evidence makes the content digest optional and omits attachment digests, so it still need not identify what was sent. See new blocker 8. |
| 10. APPROVED/APPLIED emails are unreachable | **RESOLVED** | B2 removes bespoke state emails, makes the review page the control surface, and assigns durable notices to the outbox. |
| 11. Endure bypasses the state machine | **RESOLVED** | D4 makes disabling the current pre-approval push a Phase 1 requirement and permits re-enable only under the full gate. Deferral is a safe production disposition. |
| 12. No order identity | **RESOLVED for new orders** | S1 puts `order_id` in storage, routes, claims, artifacts, external IDs, audit, and transitions, with the requested collision/concurrency tests. Legacy v1 migration is a new, separate defect because v1 lacks enough information to recover that identity (new blocker 9). |
| 13. Validator “append” calls a replace API | **RESOLVED** | S6 defines a revision-checked, source-namespaced merge under the state lock and includes preservation/cleanup tests. |
| 14. Structural-rule definitions miss the observed defects | **RESOLVED in C2** | Counted kinds exclude synthesized rest/day-off and notes/strength; pre-generation and pre-order dates are separate and timezone-defined. The fixture does not yet pin those rules exactly (new blocker 7). |
| 15. “Hard” blockers remain waivable | **RESOLVED** | S4 creates server-owned waivability policy, makes fabricated FTP/unresolved course/state/seal failures non-waivable, and requires negative tests. |

### r1 items that r2 marked PARTIALLY or NOT RESOLVED

| r1 blocker | r3 status | Evidence-based disposition |
|---|---|---|
| 1. Adapter idempotency unproven | **PARTIALLY RESOLVED** | D1/D3 add lease, intent, lookup, remote IDs, ambiguity stops, and per-type recovery. Capability consumption and partial-application state still make crash/cancel recovery unsafe (new blockers 3 and 6). |
| 2. Two manifests/apply paths | **PARTIALLY RESOLVED** | D0 chooses the owner, inventories retained features, and gates JS retirement on parity. The purported normative contract is not yet sufficient to implement parity (new blocker 4). |
| 3. No source model for HR/RPE | **RESOLVED** | A1.1 defines the upstream metric-neutral model and moves live acceptance to the first write-capable phase. |
| 6. Structural rules at wrong gate | **RESOLVED** | C2 puts them post-render and names the exact Phase 1 transitional inputs. |
| 8. Confirmations cannot be stored | **RESOLVED** | S3 defines the server catalog and value-bearing approval snapshot. |
| 10. Download authority lacks order identity | **RESOLVED** | S1/B3 bind tokens and routes to immutable order, athlete, revision, artifact, audience, and JTI. |
| 12. TP threshold choices are soft/no write-back | **RESOLVED** | D2 makes control-metric resolution required and defines regeneration, mutation, or verified manual correction per choice. |
| 13. Worker security incomplete | **PARTIALLY RESOLVED** | Isolation, credential custody, capabilities, rate/egress limits, audit, and a lease are present. Capability lifecycle remains internally unsafe (new blocker 3). |
| 16. Monika replay unsafe/non-reproducible | **NOT RESOLVED** | The fixture is synthetic and names paths/clocks, but its “exact” expected blocker set contains an open-ended union and contradictions; it also does not specify the generated plan seed or exact JSON field for devices. See new blocker 7. |
| 19. `intel-stats` fixed window | **RESOLVED** | F7 selects `hours`, defines default/max/error behavior, multi-month reads, deterministic ordering, auth, and tests. |
| 21. Course mismatch soft | **RESOLVED** | `COURSE_UNRESOLVED` is non-waivable and may clear only after course resolution or a facts-omitted regeneration. The updated ticket carries the long-term schema. |
| 22. Whole-flow decisions deferred | **PARTIALLY RESOLVED** | F4/F5 now define cancellation, regeneration choices, compensation direction, and unknown-brand failure. Partial-apply state and revision-scoped remote identity still make cancellation/supersession incomplete (new blockers 5 and 6). |

### r2 non-blocking findings

| r2 finding | r3 disposition |
|---|---|
| 1. Appendix 2 anchor audit | **VERIFIED AGAIN.** All newly changed anchors requested for r3 are accurate; details are in non-blocking finding 1. |
| 2. Fueling inventory broader than `GUT_TRAINING_PHASES` | **RESOLVED IN SPEC.** F2 explicitly inventories/classifies the guide's independent numbers. |
| 3. Device fabrication originates in the adapter/SKU | **PARTIALLY RESOLVED.** A2 fixes the correct source, but neither A2 nor the fixture names the actual new questionnaire JSON key, while the pinned paid-order schema has no device field. Folded into new blocker 7 because it prevents the promised exact fixture. |
| 4. Per-link revocation is not a `kid` blacklist | **RESOLVED for review/download links.** B3 has both JTI and key revocation. Worker-capability cancellation is a different lifecycle gap (new blocker 3). |
| 5. Other polyline copy is outside this repository | **PARTIALLY RESOLVED, non-blocking.** F3 names the repository and says it has an owner, but still gives no repository URL, pinned ref, or actual ticket. It correctly does not gate this repo's Phase 1. |
| 6. `athlete-m` needs an exact contract | **NOT RESOLVED.** See new blocker 7. |
| 7. F7 should choose an API | **RESOLVED.** |
| 8. A3 sensitivity needs enforcement | **RESOLVED IN SPEC.** A3 names prohibited surfaces and a seeded leakage test. |
| 9. Follow-up documents occupy different refs | **ACKNOWLEDGED/UNCHANGED.** The TP ticket remains readable only through `origin/main`; the updated race ticket is working-tree context. This did not prevent verification. |

## New blockers — spec-level

### 1. The content seal is self-referential, and its Phase 1 authority is not reproducible

> “Each generation computes a canonical content digest over ... the apply contract (once it exists) ...”

> `"content_seal": str, // must match approval (S2)`

> “Release projections ... must be deterministic functions of the sealed model so they can be built after approval yet provably match it.”

Hashing an apply contract that contains the hash being computed is circular. No ordinary canonical digest can satisfy that contract. The problem is normative, not an implementation choice.

The transitional claim is also incomplete. At the pinned ref, ZWO files are generated first, the guide reads them, and PlanIR is assembled afterward from the emitted files:

```text
$ git show origin/main:athletes/scripts/generate_athlete_package.py | nl -ba | sed -n '3044,3052p;3124,3131p'
  3044  # Generate ZWO workout files FIRST (guide reads from workouts dir)
  3046  zwo_files = generate_zwo_files(...)
  3049  # Generate training guide AFTER workouts ...
  3052  generate_training_guide(...)
  3124  # G0 reflection only: aggregate the artifacts just generated.
  3125  # deliberately advisory ...
  3129  from plan_ir import build_plan_ir
  3130  build_plan_ir(athlete_id)
```

Thus Phase 1's PlanIR + `tp_manifest.json` are reflections of release artifacts, not an upstream model from which the original ZWO bytes can necessarily be rebuilt. “Customer-artifact inventory” does not say it includes content digests, and a filename inventory does not bind the hidden eager artifacts.

**Required change:** define two non-circular layers. For example, compute a `model_seal` over canonical sources plus a normalized apply contract with all seal/digest-result fields omitted; then record per-projection artifact digests in a separate release manifest that refers to `model_seal`. For Phase 1, explicitly seal the bytes/digests of every eagerly built hidden release artifact because the pinned PlanIR is not their source. Specify canonical serialization, field exclusions, inventory entry shape, and finalization order.

### 2. A lock cannot make two adjacent files crash-atomic

> “A durable outbox (state-file-adjacent, written under the same lock) makes ‘transition + enqueue side effect’ atomic.”

The pinned lock serializes callers, but `_atomic_write` atomically replaces exactly one JSON file:

```text
$ git show origin/main:webhook/fulfillment_state.py | nl -ba | sed -n '69,86p;89,109p;208,211p'
    69  def _atomic_write(path: Path, state: Dict[str, Any]) -> None:
...
    78      os.replace(tmp, path)
...
    89  @contextlib.contextmanager
    90  def locked_state(...):
...
   100      fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
...
   208  state["status"] = to
   211  _atomic_write(state_path, state)
```

If state is replaced and the process dies before the adjacent outbox file is replaced, the transition exists without its job. If the write order is reversed, a job can exist for a transition that did not commit. Holding one `flock` prevents concurrency; it does not provide a multi-file transaction across a crash.

**Required change:** place pending outbox records inside the same state JSON and commit them in the one atomic replacement, or specify a real write-ahead transaction protocol with transaction IDs, commit markers, fsync order, startup recovery, and consumer rules that make either crash window deterministic. Update S5's atomicity claim and tests to include kill points after every durable write.

### 3. The single-action capability lifecycle cannot represent probe, revocation, and crash-safe retry

> “signed `{order_id, tp_athlete_id, generation_revision, content_seal, action, audience, iat, exp, jti}`”

> “persists jti consumption before any mutation (replay defense)”

> “same-`{order,revision}` re-entry returns the recorded idempotent result.”

Three cases are undefined or contradictory:

1. `probe_athlete(identity)` exists specifically before a TP athlete ID is known, but the only capability shape requires `tp_athlete_id`.
2. A valid apply capability remains cryptographically valid after the webhook cancels or regenerates the order. The worker intentionally has no authoritative state and D1 defines no capability revocation/epoch check, so it cannot learn that the approval disappeared before mutation.
3. Consuming JTI before the first mutation and then crashing leaves no completed result to return. A retry is replay-rejected, while “same re-entry returns the recorded result” covers only the completed case. The same loss occurs if the lease cannot be acquired after consumption.

The pinned authority is a separate webhook-local file, confirming that these facts are not already shared with a worker:

```text
$ git show origin/main:webhook/app.py | nl -ba | sed -n '2367,2368p;2414,2423p'
  2367  def _fulfillment_status_path(athlete_id: str) -> Path:
  2368      return Path(DELIVERIES_DIR) / athlete_id / 'fulfillment_status.json'
...
  2414  secret = request.headers.get('X-Cron-Secret', '')
...
  2421      state = load_fulfillment_state(_fulfillment_status_path(norm_id))
```

**Required change:** define a capability union with a pre-binding probe subject and a bound TP-ID subject. Define cancellation/regeneration invalidation—such as an online one-time exchange immediately before mutation, a worker-readable revocation/approval epoch, or webhook-to-worker job creation with cancellable durable job state. Replace “consumed” with a durable operation record (`accepted|running|succeeded|failed`, request digest, fencing token, resume policy); lease acquisition and acceptance ordering must be explicit, and an accepted in-progress request must resume reconciliation rather than be rejected as replay.

### 4. The purported normative apply contract is internally inconsistent and still defers essential semantics

> “`apply_contract/v1` (JSON Schema shipped with the implementation; normative shape here)”

> `"external_id": str, // embedded remote marker, kind-appropriate`

> `"payload": {...}`

> `"readback": { "expectations": [...] }`

This is an outline, not yet a normative schema. Per-kind payloads and readback expectations are elided, `expected_digest` has no canonical encoding, update policy is deferred to an unspecified “operation policy,” and compatibility/versioning behavior is not defined.

The common-field rule is also false for its own union. D3 treats thresholds/zones as account singletons and entitlements as grant-if-absent, yet D0 requires every operation to carry an **embedded remote marker**. A threshold value or zone table is not an external-ID-keyed remote calendar object; D3's CAS/before-image semantics acknowledge that. An entitlement may likewise have a synthetic local correlation ID without an embedded remote marker.

Pinned code shows why feature names alone are insufficient: the old contracts use materially different payloads (`segments` versus TP-native `structure`) and the adapter currently POSTs only its own shape:

```text
$ git show origin/main:athletes/scripts/fulfillment_manifest.py | nl -ba | sed -n '29,39p;67,80p'
    29  external_id = f"{ir['athlete']['id']}:w..."
...
    37  'segments': session.get('segments', [])
...
    70  'workouts': workouts,
    72  'native_notes': notes,
    73  'attachments': attachments,
    74  'mental_training_tasks': tasks,
    75  'course_entitlement': entitlement,

$ git show origin/main:tools/tp_apply_order.py | nl -ba | sed -n '237,248p'
   237  def _workout_entry(...):
...
   246      "structure": session.get("structure"),
```

**Required change:** put the complete schema in the spec or a pinned normative artifact now—not “shipped with implementation.” Define per-kind required/forbidden fields, exact target/payload schemas, readback schema, canonical JSON/digest algorithm, update-vs-stop policy, operation dependency ordering, and version compatibility. Separate a local `op_id`/correlation ID from an optional remote embedded marker, making the latter required only for remote types that support it.

### 5. Revision-scoped external IDs make the promised supersession diff create duplicates

> `"op_id": str, // stable: {order_id}:{revision}:{kind}:{ordinal}`

> “External-id construction includes `order_id` and revision.”

> “Regeneration after APPLIED requires ... *supersede* (new revision, re-review, re-apply as a reconciled diff)”

Every operation's identity changes when the revision changes. D3 lookup-before-write therefore sees the superseding revision's workouts as absent and creates them, while the prior revision's remote objects remain. Nothing defines how the “reconciled diff” matches a new workout to the old remote object, deletes removed sessions, or preserves a remote ID for an unchanged logical session.

The pinned manifest already demonstrates the importance of logical identity: its current external ID is based on athlete/week/sequence/date, not a separate attempt record (`fulfillment_manifest.py:27-31`). r3 correctly needs order scope, but adding revision to the only remote identity defeats cross-revision reconciliation.

**Required change:** define two identities: a logical operation/resource ID stable across revisions of an order, and a revision-scoped attempt/op ID. Specify the supersession diff algorithm, including matching, unchanged/changed/removed/added behavior, remote-ID reuse, delete policy, and singleton CAS behavior. If remote markers must be revisioned, store an explicit predecessor link and require cleanup of the prior marker before completion.

### 6. Partial apply is represented as APPROVED, so cancellation can leave remote mutations behind

> “Partial failure: state stays APPROVED; coach notified with exact landed set”

> “Pre-APPLIED refund → CANCELLED, tokens revoked (jti), artifacts unexposed.”

Those rules conflict. A partial failure can have workouts, notes, or a threshold already landed while the top-level state is still APPROVED. F4 then classifies its refund as “Pre-APPLIED” and performs no D3 rollback, leaving the remote mutations on the athlete's account. It also makes “APPLIED remains strictly the calendar fact” incomplete: real calendar facts exist while state says only APPROVED.

The pinned state has only a single jump from APPROVED to APPLIED and no attempt/landed-operation representation:

```text
$ git show origin/main:webhook/fulfillment_state.py | nl -ba | sed -n '199,211p'
   199  elif to == APPLIED:
   200      if current != APPROVED:
   201          raise FulfillmentStateError("application requires APPROVED status")
...
   204      state["application"] = {...}
   208  state["status"] = to
   211  _atomic_write(state_path, state)
```

**Required change:** add a durable application-attempt/substate (or explicit `APPLYING`/`PARTIALLY_APPLIED`) that records intent and each landed operation before APPLIED. Cancellation/abandon logic must inspect landed operations, not the top-level status, and compensate any landed set. Define retry, rollback, regeneration, and release behavior for that state and make APPLIED mean the complete required operation set verified—not merely that at least something landed.

### 7. `athlete-m` is still not an exact fixture and contains contradictory expectations

> “golden expectation sets”

> “blockers exactly `{FTP_ESTIMATED, RACE_STALE, COURSE_UNRESOLVED, WEEKS_MISMATCH} ∪ whatever the seeded plan violates structurally`”

> “required confirmation for the schedule overlap”

“Exactly ... plus whatever” is not a golden set. The fixture names only one structural seed, yet the observed pinned generator can also omit race day, make a thin race week, and duplicate a field test. No frozen generated plan/PlanIR seed, race date, exact course list, per-day plan output, or RNG/determinism input says which of those rules must fire.

The schedule expectation is contradictory on its face: long-ride days Mon/Tue/Sun and interval days Wed/Thu are disjoint, while C2 says the required confirmation is for a v1 day-list overlap. If the intended conflict is generated intervals landing on a long-ride-available day, that is a different rule and needs an exact generated schedule.

The weeks expectation is also ambiguous: `WEEKS_MISMATCH` is expected, but the same paragraph says fueling labels match “the 7 generated weeks.” F6 excludes lead-in from the comparison; the fixture must say explicitly whether the seed is six paid-plan weeks plus W00 or seven paid-plan weeks.

Finally, the claimed exact input does not name the device JSON field. At the pinned ref, the rich intake schema reads `powerOrHr` but has no device key, and the markdown adapter hardcodes the device line:

```text
$ git show origin/main:webhook/app.py | nl -ba | sed -n '1248,1275p;1485,1488p'
  1248  profile = {
...
  1259      'power_or_hr': intake_data.get('powerOrHr', ''),
...
  1269  'weekly_schedule': {
...
  1485  ## Equipment
  1486  - Indoor Trainer: ...
  1487  - Devices: power meter, HR strap
```

**Required change:** specify byte-addressable fixture files and exact JSON schemas/keys, a frozen race date and course array, deterministic plan-date/session seed (including W00), and literal ordered expected blocker/confirmation sets for each phase—no open union. Clarify the schedule rule and six-plus-lead-in week arithmetic. Name the new production device field and assert it traverses JSON → markdown → parser. Add negative expectations for every structural rule that must *not* fire.

### 8. Manual confirmation evidence still does not bind the content sent

> `manual_attestation: {channel, recipient, sent_at, revision, content_digest?, reason_not_verified}`

The optional `content_digest` and absence of attachment digests allow CONFIRMED to record only that some message was allegedly sent to a recipient at a revision. It cannot answer whether the approved body or sealed guide was sent. This is the exact integrity property the typed evidence change was supposed to close.

Provider evidence is stronger because the server fetches Gmail and compares the guide attachment, but manual fallback must remain honest **and** content-specific. “Google is down” prevents provider verification; it does not prevent the system from recording the expected generated body/attachment digests or the coach from attesting whether those exact artifacts were used.

**Required change:** require the expected draft/body digest and complete attachment inventory/digests in manual evidence, plus an explicit disposition for changed body, omitted attachment, or non-email channel. Store the actual coach-attested content snapshot/digests and compare them to the sealed release component; if they differ, record the difference and require an explicit reviewed override rather than silently confirming the sealed message.

### 9. Schema-v1 migration cannot recover the immutable order identity it promises

> “`SCHEMA_VERSION` → 2, with migration for v1 files.”

> “New immutable fields: `order_id` ... State lives at an order-keyed path.”

The pinned v1 file contains `athlete_id` and revision but no order reference, and the authority is stored only by athlete slug:

```text
$ git show origin/main:webhook/fulfillment_state.py | nl -ba | sed -n '124,148p'
   124  def write_generation(... athlete_id: str, ...):
...
   135      state = {
   136          "schema_version": SCHEMA_VERSION,
   137          "athlete_id": athlete_id,
   138          "generation_revision": revision,
```

```text
$ git show origin/main:webhook/app.py | nl -ba | sed -n '2367,2368p'
  2367  def _fulfillment_status_path(athlete_id: str) -> Path:
  2368      return Path(DELIVERIES_DIR) / athlete_id / 'fulfillment_status.json'
```

A repeat athlete can have multiple ledger orders, so looking up athlete slug in `.processed_orders.json` cannot prove which order the v1 approval/application belonged to. Guessing would recreate the cross-order authority flaw S1 is designed to eliminate.

**Required change:** define a fail-closed migration policy. Legacy files without a provable unique order link must receive a new opaque `legacy_order_id`, lose inherited approval/application authority (or enter a quarantined legacy status), and require authenticated manual binding with preserved original evidence. Specify collision/multiple-ledger behavior, path move atomicity/recovery, and whether old tokens/routes are revoked. Do not infer an order from athlete slug alone.

## Implementation-gated items — no further spec text can close these

These become legitimate build/live-verification work **after** the nine blockers above are repaired:

1. **TrainingPeaks live protocol:** whether the SPA currently accepts and faithfully reads back HR/LTHR/HRmax/RPE structures; searchable external markers; exact create/update/delete behavior; singleton CAS feasibility; ambiguity after network timeout; and session-token refresh behavior. These require a controlled canary and captured protocol evidence.
2. **Worker operation:** browser login/TOTP/session survival, SPA drift detection, coaching-relationship checks, fenced lease behavior, durable operation-journal recovery, rate/egress enforcement, and redacted audit output. The worker does not exist at the pinned commit.
3. **Apply-contract implementation parity:** actual per-kind projections and fake-server/live-canary parity for workouts, notes, attachments, mental tasks, entitlements, thresholds, and zones; then safe JS-driver retirement.
4. **Fixture execution:** checking in `athlete-m`, HR/LTHR/HRmax/RPE fixtures, deterministic generation, and proving the exact goldens. The real Monika intake must not be copied from Railway.
5. **Gmail behavior:** OAuth consent/refresh, sender-alias enforcement, draft/message ID relationships, sent-state lookup, MIME/body canonicalization, and attachment-byte verification.
6. **Guide release:** deterministic PDF rendering with pinned fonts/container, private delivery or the safe ZIP-only default, publish verification, and cache/revocation behavior.
7. **Endure capability:** whether Endure can suppress platform invitations, provide readback and rollback, and avoid silent TP fallback. It must remain disabled until those live facts pass; deferral is safe.
8. **Course schema/matching:** implementing `courses[]`, backfilling events, and proving non-headline course selection. The interim non-waivable blocker is now adequate.
9. **Other-repository polyline copy:** changing and testing the `gravel-god-training-plans` copy at a pinned external ref.
10. **Terms-of-service/business risk:** r3 records browser automation as accepted risk; technical review cannot prove contractual acceptability.

## Non-blocking findings

1. **All requested new/changed Appendix 2 anchors are accurate at `origin/main` @ `af284c2`:**

   - Endure: `webhook/app.py:1918-1926` says the helper never raises/fails the order, and `:2000-2009` performs the pre-approval push with TP fallback language.
   - Device source: `webhook/app.py:1487` and `tp-skus/generate_skus.py:82` hardcode `power meter, HR strap`.
   - Generation order: `generate_athlete_package.py:2989-3052, 3124-3131` loads the profile/data, emits ZWO first, then guide, then advisory PlanIR.
   - Guide carb figures: `training_guide_builder.py:1367, 1668-1776, 2939-2941` contains the cited recovery, per-hour, duration-table, gel/timeline, and women-specific/general-guidance figures.
   - Synthesized rest days: `plan_ir.py:455-464, 500-503` creates `type="rest"`, `tp_kind="day_off"` for calendar days without a rendered ZWO.

   The remaining Appendix 2 anchors were also rechecked and remain accurate. One wording nuance: “profile→ZWO→guide→IR” means profile/data **load** at `2989`, not profile generation in that function.

2. **The dependency-graph rewrite is substantive.** Phase 1 no longer depends on D0, Phase 3 no longer waits on a write canary, and automated platform identity is scoped to delivery mode. This closes r2 blocker 1 rather than renaming it.

3. **S3/S4 are strong foundations.** Value-bearing catalog snapshots plus server-owned waivability directly close two of the highest-risk r2 defects. Implementation should keep the catalog and namespaced blocker merge in the same post-render finalization transaction so they cannot diverge.

4. **D2 now has real semantics.** In particular, `use-tp-value` regenerates instead of pretending a review-page choice changed already-rendered content, and singleton updates have an inspection before-image.

5. **D4's safe disposition is sufficient for convergence if Endure stays off.** Re-enabling it would require a platform-specific apply contract/capability/readback amendment; choosing “defer” does not block the TrainingPeaks/manual pipeline.

6. **F7 is now implementable without another product decision.** The chosen 720-hour bound implies multi-month reads, which r3 explicitly covers.

7. **`CANCELLED` from any state should preserve terminal facts.** Even after new blocker 6 is fixed, implementation should retain approval/application/confirmation and compensation history rather than treating cancellation as erasure.

8. **Review-link identity remains honestly credential identity.** r3 does not overclaim that possession proves a named human; `review-link:<kid>:<jti-issued-to>` is the right provenance level for the settled one-coach model.

## Could not verify

1. I could not verify any live TrainingPeaks request/response behavior, stable marker, remote ID, HR/RPE target, singleton update, delete, rollback, or idempotency guarantee. No controlled live fixture/captured protocol exists at the pinned commit.
2. I could not verify worker security, lease fencing, capability persistence, browser session/TOTP, or SPA behavior because the worker is specification-only.
3. I could not verify `apply_contract/v1`, state schema v2, review pages, typed tokens, blocker merge, seal calculation, release components, or an outbox because none is implemented at `origin/main`.
4. I could not execute `athlete-m`; its named files do not exist yet. I did not access or reproduce the real customer's Railway intake.
5. I could not verify Gmail draft/sent-message evidence, aliases, OAuth, attachment fidelity, or deterministic MIME hashing.
6. I could not verify deterministic PDF publishing, private guide hosting, revocation/cache behavior, or Pages deployment.
7. I could not verify live Endure apply/readback/rollback/invitation behavior. Pinned code proves only that the current webhook invokes it before approval and suppresses its failure.
8. I could not verify the external `gravel-god-training-plans` polyline copy because r3 still supplies no repository URL/ref accessible from this review.
9. I could not verify production course matching against `courses[]`; the updated ticket is design context, not implementation.
10. I could not verify TrainingPeaks terms-of-service acceptability.

## Convergence assessment

r3 has separated most true implementation unknowns from design obligations, and the items in the implementation-gated section should **not** cause another speculative spec rewrite. However, the content-seal cycle, false outbox atomicity, capability lifecycle, incomplete apply schema, cross-revision identity, partial-apply cancellation leak, non-exact fixture, unbound manual evidence, and unsafe legacy migration are all decidable in text now.

Under the team's rule—converge only when every remaining item can be closed only by building—this draft is **not converged**. A narrowly scoped r4 that closes those nine contracts could plausibly be the final spec round; after that, the remaining uncertainty is appropriately implementation/live-verification gated.

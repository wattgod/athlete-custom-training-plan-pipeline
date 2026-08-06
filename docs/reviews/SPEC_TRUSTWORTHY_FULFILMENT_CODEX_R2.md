# Verdict: NO-GO

**Convergence:** r2 is materially better, but only 10 of the 22 r1 blockers are fully resolved; 10 are partial, 2 remain unresolved, and r2 introduces 15 new blockers at the review/release, state, worker, validator, and platform boundaries.

## Review basis

I read the r1 review first, then r2, the handoff and Monika findings, the race-course ticket, and the prior TrainingPeaks ticket. All code evidence is from the required ref, never the dirty working tree:

```text
$ git rev-parse origin/main
af284c2647b20388c7bb57678fc123780f6a6660
```

I inspected every Appendix 2 code anchor through `git show origin/main:<path>`. Representative hashes:

```text
$ for p in athletes/scripts/intake_to_plan.py athletes/scripts/fueling_policy.py \
    athletes/scripts/calculate_fueling.py athletes/scripts/tp_polyline.py \
    athletes/scripts/training_guide_builder.py athletes/scripts/plan_ir.py \
    athletes/scripts/fulfillment_manifest.py delivery/trainingpeaks/adapter.py \
    tools/tp_apply_order.py webhook/app.py webhook/fulfillment_state.py; do
    git show "origin/main:$p" | shasum -a 256 | awk -v path="$p" '{print path, $1}'
  done
athletes/scripts/intake_to_plan.py 83501dd3cc9842a7cfde0d13b1647025e5e50516f283c68c2108a9c90633e2cf
athletes/scripts/fueling_policy.py ea694191d9048cfc6682b05208b50d12ae3c4212e1a6b97c47aa7619c6cf0e76
athletes/scripts/calculate_fueling.py 5e5258234100f34e7fb9cd3963e8586aa664b185fc7770a7cc7b152b7e0ec8ca
athletes/scripts/tp_polyline.py 268e35a06c7a536331e6f6191a6bde5417eca500fe6e444e329aa8c4c39856bf
athletes/scripts/training_guide_builder.py d7302e4b1bee2560ecbbfdf96a24a4623f56d9ff998822eaddc94d44ecaba4c7
athletes/scripts/plan_ir.py 82c8d72b6659193a7a33083e6a8c470ebbeffc3a16b575db752454a5db7b7719
athletes/scripts/fulfillment_manifest.py 62e8a3bc678517742202ef3fd02f7e0b1f4be74d9a9714d6535ff9a9c905c838
delivery/trainingpeaks/adapter.py 028f6c1be93b1f58d6e5c133a7f1b8f465aefad5cc0d106634e579cd39cbc393
tools/tp_apply_order.py e20f3e9470695190b6c50a0bc38c801d8da2dafa285c8fac634b07bb375d42ee
webhook/app.py c5b7621fa89a2b4d5aceb4136a0e961802b6081ffeff92f8af5c641f4c020053
webhook/fulfillment_state.py aac7f0762d92333f5299e877b963d46c541fdd47b02f924a81bb60e52444c5b9
```

## R1 blocker dispositions

| R1 blocker | R2 status | One-line justification |
|---|---|---|
| 1. Adapter idempotency unproven | **PARTIALLY RESOLVED** | D3 retracts the false guarantee and adds intent plus lookup recovery, but it still lacks a per-athlete mutation lease, persisted remote object IDs, and complete ambiguity rules (new blocker 6). |
| 2. Two manifests/apply paths | **PARTIALLY RESOLVED** | D0 chooses one owner and retires the JS authority, but `apply_contract/v1` is a name and feature list, not a schema or parity-complete cutover contract (new blocker 5). |
| 3. No source model for HR/RPE | **PARTIALLY RESOLVED** | A1.1 supplies the required metric-neutral model and fixtures, but its apply-payload and worker-canary gates are scheduled before D0/D1 exist (new blocker 1). |
| 4. Fueling re-fabricates FTP | **RESOLVED** | A1.3 explicitly removes watt inference/serialization in null-power mode and requires zero-watt cross-artifact assertions and corrected guide copy. |
| 5. Full package bypasses the gate | **RESOLVED** | B1 withholds ZWO/apply payload/customer artifacts from pre-approval coach access and provides only a non-executable review bundle. The missing content seal is a separate new defect (new blocker 2). |
| 6. Structural rules at the wrong gate | **PARTIALLY RESOLVED** | C2 moves them post-render, but Phase 1 lacks its apply-contract input and two rule definitions still fail against the pinned final model (new blockers 1 and 14). |
| 7. Schedule rule overreaches v1 input | **RESOLVED** | C2 correctly makes v1 overlap a required confirmation and reserves blocking for explicit prohibitions/fixed constraints. |
| 8. Confirmations cannot be stored | **PARTIALLY RESOLVED** | C3 versions the endpoint/state and adds a confirmation snapshot, but stores only a digest where I5 requires the confirmed values (new blocker 3). |
| 9. Signed-link possession is not named-human identity | **RESOLVED** | C4 honestly records the approving credential, uses server-side POST actions, and specifies CSRF, scanner-safe GET, expiry, revocation, cache/referrer, and log controls. |
| 10. Download-token privilege escalation/lifetime | **PARTIALLY RESOLVED** | B3 fixes type/audience/expiry/key scoping, but tokens, state, and `/review/<athlete_id>` omit the order identity, so distinct orders for the same athlete share one authority (new blocker 12). |
| 11. Different-email TP identity cannot resolve | **RESOLVED** | D2 adds a distinct TP email, coach selection, explicit resolution states, durable TP ID binding, and write-time revalidation. |
| 12. Target-affecting TP thresholds are soft | **PARTIALLY RESOLVED** | D2 makes them required and defines choices, but no choice is propagated back into the canonical plan/release revision (new blocker 4). |
| 13. Worker security design incomplete | **PARTIALLY RESOLVED** | D1 removes `get_token` and adds isolation, separate caller credentials, action authorization, rotation, redaction, limits, and egress controls, but never defines how the separate worker obtains authoritative state or prevents replay (new blocker 6). |
| 14. Guide publishes outside release state | **RESOLVED** | E1 gates publication on APPLIED, defines a safe no-public-URL default, records revision, and requires regeneration/cancellation revocation. Release-failure state remains a new cross-workstream defect (new blocker 8). |
| 15. Two athlete-facing emails | **RESOLVED** | E2 settles Gmail draft as the sole athlete message and removes the automated customer send from `/api/confirm`. |
| 16. Monika replay unsafe/non-reproducible | **PARTIALLY RESOLVED** | `athlete-m` is synthetic and names frozen classes/inputs, but no exact checked-in fixture, generated-week count, device answer, or exact structural seed/expected set is specified. |
| 17. Hardcoded fueling phase table omitted | **RESOLVED** | F2 names the code, derives labels from actual weeks, requires one canonical prescription, and adds replay/cross-artifact assertions. The implementation inventory is larger than the named table (non-blocking finding 2). |
| 18. Polyline overshoot omitted | **RESOLVED** | F3 specifies unrounded cumulative time, bounds, monotonicity, golden replacement, and property tests. |
| 19. `intel-stats` fixed window omitted | **PARTIALLY RESOLVED** | F7 adds authorization, bounds/validation, and deterministic ordering, but does not choose `hours` vs `limit`, specify caps/pagination, or require tests. |
| 20. Altitude assertion omitted | **RESOLVED** | F1/C2 require a post-render semantic failure when a qualifying frozen race snapshot does not produce the altitude section. |
| 21. Course mismatch remains soft | **NOT RESOLVED** | C2 calls it a hard blocker, but C1 gives every blocker a waiver and the unchanged transition semantics approve any exactly waived set; omission of unresolved facts is deferred to the separate ticket (new blocker 15). |
| 22. Whole-flow decisions deferred despite Phase 5 | **NOT RESOLVED** | F6 is concrete and F5 is directional, but F4 still says to define transitions later; it supplies no cancellation/refund/regeneration states, legal transitions, or compensation contract, and D3 cannot roll back all operation types (new blockers 7 and 8). |

## New blockers

### 1. The rollout schedules consumers before their prerequisites exist

> “A validator over PlanIR + the apply contract ...”

> “Phase 1 ... the post-render validator ...”

> “must be proven ... via the worker canary (§D1) before Phase 3 exits.”

> “Phase 4 — worker, read-only. D1 ... + D2 ...”

> “Phase 5 — ... D0 migration ...”

There are three dependency inversions:

1. Phase 1's validator requires the D0 apply contract, but D0 lands in Phase 5.
2. Phase 2 requires `platform_identity` before approval, but the D2 mechanism that creates it lands in Phase 4.
3. Phase 3 requires apply payload fixtures and a worker canary, while the apply contract lands in Phase 5 and the worker first lands in Phase 4.

The pinned generator still emits the two old contracts, and the CLI still delegates the TP-native one to the browser driver:

```text
$ git show origin/main:athletes/scripts/generate_athlete_package.py | nl -ba | sed -n '3142,3151p'
  3142            build_plan_ir(athlete_id)  # PlanIR's fulfillment projection follows the gate.
...
  3144        from fulfillment_manifest import build_fulfillment_manifest
  3145        build_fulfillment_manifest(athlete_dir)
  3146        detail("Saved: fulfillment_manifest.json")
  3147        # Architecture rule #1: tp_manifest is a versioned PROJECTION ...
  3149        from plan_ir import build_tp_manifest
  3150        build_tp_manifest(athlete_id)
  3151        detail("Saved: tp_manifest.json")

$ git show origin/main:tools/tp_apply_order.py | nl -ba | sed -n '4,17p;50,51p'
     4  Architecture: this CLI *prepares and validates only*. It never talks to
     5  TrainingPeaks itself — ``tp_apply_driver.js`` executes inside a logged-in TP
...
     9    1. loads + validates ``tp_manifest.json`` from a package (dir or zip),
...
    50  MANIFEST_FILENAME = "tp_manifest.json"
```

**Required change:** publish a dependency graph and reorder the rollout. Either land D0's schema/projection before the Phase 1 validator and Phase 3 fixtures, or make those phases validate a named transitional internal artifact. Move identity binding before any Phase 2 approval gate, or explicitly exempt non-TP/manual orders with a testable delivery-mode rule. A write-capable canary harness must exist before it can gate Phase 3.

### 2. Approval is not bound to the content reviewed, so B1 creates a review/release TOCTOU gap

> “Release artifacts are built (or exposed ... ) on transition to APPROVED.”

> “Review precedes application.”

> “approval gains `confirmations` ... `{item_id, value_digest, ... revision}`”

The coach reviews summaries and an unpublished guide, then executable artifacts may be built later. Nothing in state binds approval to a canonical-model digest, review-bundle digest, apply-contract digest, or release-file digest. A nondeterministic rebuild or same-revision file mutation can therefore release/apply content the coach never reviewed. Revision-bound URLs do not help if content changes without `write_generation`.

The current revision record has no artifact seal, and transition merely changes state:

```text
$ git show origin/main:webhook/fulfillment_state.py | nl -ba | sed -n '135,148p;183,211p'
   135        state = {
   136            "schema_version": SCHEMA_VERSION,
   137            "athlete_id": athlete_id,
   138            "generation_revision": revision,
   139            "status": BLOCKED_REVIEW if issues else GENERATED,
   140            "blocking_issues": issues,
   141            "approval": None,
   142            "waiver": None,
   143            "application": None,
   144            "confirmation": None,
...
   183        if to == APPROVED:
...
   185                state["approval"] = {"coach": coach.strip(), "at": now_iso()}
...
   208        state["status"] = to
   209        _history(state, "TRANSITION", from_status=current, to_status=to,
   210                 coach=coach.strip(), **(metadata or {}))
   211        _atomic_write(state_path, state)
```

**Required change:** seal each generation with a canonical content digest covering the workout model, review summaries, guide source, apply contract, and customer artifact inventory. Store that digest in the review items and approval. Generate release projections deterministically from the sealed model; store their digests; make downloads and the worker reject any artifact/contract whose revision and digest do not match approval. Any content-changing correction must call `write_generation` and require re-review.

### 3. State schema v2 still cannot answer “what was confirmed (with values)”

> “what it confirmed (with values) ... from the state file alone.”

> “`approval` gains `confirmations`: ... `{item_id, value_digest, disposition: ... revision}`”

A one-way digest can prove equality to a value supplied later; it cannot recover the confirmed value from the state file. The target schema therefore still violates I5 by construction. It also does not say where the server-authoritative review-item catalog and exact value snapshot live, so unknown/stale ID validation has no defined source.

The pinned schema confirms why a real v2 extension is necessary:

```text
$ git show origin/main:webhook/fulfillment_state.py | nl -ba | sed -n '183,210p'
   183        if to == APPROVED:
   184            if current == GENERATED:
   185                state["approval"] = {"coach": coach.strip(), "at": now_iso()}
...
   209        _history(state, "TRANSITION", from_status=current, to_status=to,
   210                 coach=coach.strip(), **(metadata or {}))
```

**Required change:** define a server-generated, revisioned review-item catalog in state and snapshot the typed canonical value (plus display unit/source/basis), disposition, credential, and revision into approval. If sensitive values must not be duplicated, embed an encrypted or access-controlled value snapshot in the same state authority; a digest alone requires weakening I5.

### 4. D2's threshold/account choices do not change the plan they are supposed to authorize

> “no plan editing in the browser.”

> “explicit resolutions: `use-tp-value` / `update-from-intake` / `manually-corrected` / `cannot-resolve`”

> “for an HR-anchored plan, TP's threshold is what turns `%LTHR` into a prescription.”

The plan and guide are generated from intake/profile values before review. Selecting `use-tp-value` can therefore approve a plan whose guide, zones, descriptions, and canonical targets were rendered from a different intake value. `manually-corrected` has the same problem unless the correction is read back and fed into a new generation. C3 records the choice but D2 defines no write-back, re-projection, revision bump, or second review.

Pinned generation order:

```text
$ git show origin/main:athletes/scripts/generate_athlete_package.py | nl -ba | sed -n '2989,3052p;3124,3131p'
  2989    # Load all athlete data
  2990    step(1, "Loading athlete data...")
  2991    profile = load_yaml(athlete_dir / 'profile.yaml')
...
  3044    # Generate ZWO workout files FIRST ...
  3046    zwo_files = generate_zwo_files(..., profile, fueling)
...
  3049    # Generate training guide AFTER workouts ...
  3052    generate_training_guide(athlete_id, output_path=guide_path)
...
  3124    # G0 reflection only: aggregate the artifacts just generated.
...
  3129        from plan_ir import build_plan_ir
  3130        build_plan_ir(athlete_id)
```

**Required change:** define each resolution as a state-changing command. `use-tp-value` must copy the inspected value/provenance into canonical inputs; `update-from-intake` must bind the exact intake value to the account mutation; `manually-corrected` must read back the corrected value. Any choice that changes an anchor must bump revision, regenerate all projections, and return to review. Approval is allowed only when the sealed plan value and inspected TP value satisfy the chosen resolution.

### 5. `apply_contract/v1` is not a schema and the migration can silently lose existing operation classes

> “one canonical apply contract, versioned (`apply_contract/v1`)”

> “It carries: workout upserts ... calendar notes, threshold/zone update operations ... expected-readback digests, and rollback identifiers.”

No field-level schema, operation union, required/optional fields, canonical digest encoding, external-ID construction/version behavior, operation ordering, or compatibility rule is given. The migration list also omits current attachment and course-entitlement operations, and it does not disposition `mental_training_tasks` or the TP-native strength/race/day-off semantics. “The adapter is migrated” cannot be implemented or parity-tested from this contract.

Pinned contracts demonstrate the missing parity inventory:

```text
$ git show origin/main:athletes/scripts/fulfillment_manifest.py | nl -ba | sed -n '67,80p'
    67    return {
    68        'schema_version': MANIFEST_VERSION,
    69        'athlete_id': ir['athlete']['id'],
    70        'workouts': workouts,
    71        'calendar_dates': dates,
    72        'native_notes': notes,
    73        'attachments': attachments,
    74        'mental_training_tasks': tasks,
    75        'course_entitlement': entitlement,
    76        'verification_expectations': {

$ git show origin/main:delivery/trainingpeaks/adapter.py | nl -ba | sed -n '79,94p'
    79    for index, note in enumerate(manifest.get('native_notes', []), 1):
...
    84    for index, attachment in enumerate(manifest.get('attachments', []), 1):
...
    89    entitlement = manifest.get('course_entitlement')
    90    if entitlement:
...
    93                                f'/fitness/v1/athletes/{athlete_id}/entitlements',
```

**Required change:** include a normative JSON Schema (or equivalent typed definition) for an operation union and envelope. Specify stable ID construction across revisions, content-digest canonicalization, threshold/zone before-images, workout/strength/race/day-off/note/attachment/entitlement disposition, ordering and dependency rules, readback expectations, and rollback data. Add migration parity tests proving each retained feature and explicitly retire any intentionally dropped feature before deleting either old authority.

### 6. The separate broker has no defined source of authorization truth or replay defense

> “the worker is a separate service”

> “every operation authorized per-action and bound to `{athlete_id, generation_revision}` from the state file”

> “distinct rotating secret for worker-API callers”

The spec never says whether the worker mounts the Railway delivery volume, queries the webhook, or validates a signed capability. A caller secret authenticates a client, but does not prove that this athlete/revision is APPROVED or that this contract is the approved one. No request nonce/idempotency record prevents replay of an old `apply` or `rollback` request while its caller credential remains valid. Nor is there a per-TP-athlete lease: two authorized apply requests can both list an empty window, persist separate intents, and POST the same workout before either can reconcile. Lookup-before-write is not mutual exclusion.

D3 also says the stable remote marker is “to be established by canary” but does not require the returned TP object ID to be persisted. If a user edit removes or changes the embedded marker, later verification and rollback have no authoritative remote handle; if lookup finds multiple matches, no stop/repair rule is defined.

The pinned authority is a webhook-local file behind a separate authenticated endpoint:

```text
$ git show origin/main:webhook/app.py | nl -ba | sed -n '2367,2368p;2414,2423p'
  2367 def _fulfillment_status_path(athlete_id: str) -> Path:
  2368     return Path(DELIVERIES_DIR) / athlete_id / 'fulfillment_status.json'
...
  2414 secret = request.headers.get('X-Cron-Secret', '')
  2415 if not secret or not hmac.compare_digest(secret, os.environ.get('CRON_SECRET', '')):
  2416     return jsonify({'error': 'Unauthorized'}), 401
...
  2421     state = load_fulfillment_state(_fulfillment_status_path(norm_id))
```

**Required change:** choose one trust mechanism. Prefer a webhook-issued, short-lived, single-action capability containing athlete/order, TP athlete ID, revision, approved contract digest, action, caller/audience, expiry, and nonce. The worker must validate it and persist nonce consumption before mutation; rollback gets a separate capability. Alternatively, specify shared authoritative storage and its locking/security semantics. Add a durable lease keyed by TP athlete ID, with fencing/expiry and a same-revision idempotent result. Persist every remote object ID after lookup/POST, and fail closed on zero-after-ambiguous-write or multiple matches. Read-only probe credentials must not authorize writes.

### 7. D3 reconciles calendar POSTs but not threshold/zone mutations or manual applications

> “including threshold/zone resolutions”

> “`rollback` (delete-by-external-id)”

> “Manual fallback is permanent: ‘I imported manually’ records APPLIED with typed evidence.”

> “refund after APPLIED triggers calendar rollback (D3)”

Thresholds/zones are mutable account singletons, not external-ID-keyed calendar objects. Delete-by-external-ID cannot restore them. D3 does not require a before-image, compare-and-swap, account-setting readback, operation ordering, or compensation. It also does not require a manual import to record remote IDs or pass the same verify step, yet F4 promises rollback for every APPLIED plan. Manual objects may have no embedded external ID at all.

The pinned adapter has no such primitives:

```text
$ git show origin/main:delivery/trainingpeaks/adapter.py | \
    rg -n '\b(threshold|zone|delete|rollback|intent|PUT|PATCH)\b' || \
    echo '[no threshold/zone/delete/rollback/intent/PUT/PATCH implementation]'
[no threshold/zone/delete/rollback/intent/PUT/PATCH implementation]
```

The only current mutations are blind POST upserts:

```text
$ git show origin/main:delivery/trainingpeaks/adapter.py | nl -ba | sed -n '67,94p'
    67 def apply(self, athlete_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
...
    77     created += self._upsert(...,
    78                             f'/fitness/v6/athletes/{athlete_id}/workouts', payload)
...
    81     created += self._upsert(...,
    82                             f'/fitness/v1/athletes/{athlete_id}/calendarNote', ...)
```

**Required change:** specify reconciliation per operation type. For calendar objects define absent/one/multiple and same/different-digest behavior. For threshold/zone changes persist a before-image and intended after-image before write, use compare-and-swap where possible, verify exact values, and restore only if the current value still matches this operation's after-image. A manual APPLIED transition must carry a typed object inventory plus clean readback; otherwise label it non-reconcilable and exclude it from automated rollback promises.

### 8. APPLIED cannot atomically represent calendar success plus guide/draft release success

> “the fulfillment state machine ... is sound and kept as the spine ... it does not redesign the transitions.”

> “Publishing ... happens on the APPLIED transition (with the draft, §E2)”

> “After APPLIED + verify, the worker creates a Gmail draft”

Publishing and draft creation are independent external side effects. The calendar can be correctly APPLIED while Pages or Gmail fails. R2 supplies no release substate, retry/outbox record, structured failure field, or rule for whether APPLIED is committed before or after those operations. Committing first violates I6's “never reports success” for release; committing after falsely says the calendar is merely APPROVED and invites a reconciliation retry of an already-applied plan.

The pinned transition has one application record and immediately commits APPLIED:

```text
$ git show origin/main:webhook/fulfillment_state.py | nl -ba | sed -n '199,211p'
   199        elif to == APPLIED:
   200            if current != APPROVED:
   201                raise FulfillmentStateError("application requires APPROVED status")
   202            if not str(platform).strip() or not str(evidence).strip():
   203                raise FulfillmentStateError("platform and nonempty evidence are required")
   204            state["application"] = {"coach": coach.strip(), "at": now_iso(),
   205                                    "platform": platform.strip(), "evidence": evidence.strip()}
...
   208        state["status"] = to
...
   211        _atomic_write(state_path, state)
```

**Required change:** keep APPLIED as the calendar fact and add explicit, revisioned release components/substates (for example `guide_release` and `draft`) with `pending|succeeded|failed`, attempt IDs, evidence, and retry history, or add legal top-level release states. Use a durable outbox so transition and job creation are atomic. Phase 5 success requires all required components succeeded; failures remain loud without falsifying calendar state.

### 9. E2 accepts an arbitrary message ID and contradicts itself when Gmail integration is unavailable

> “evidence: the Gmail message id of the sent draft”

> “`send` becoming an evidence check”

> “If the Gmail integration is down, the coach sends manually and records the same evidence by hand — the state machine does not depend on Google.”

The target does not define what the evidence check checks. A message ID alone does not bind recipient, sender/brand, athlete/order, generation revision, reviewed guide attachment, message body, or sent state. If Google is unavailable, the server cannot perform the claimed check; if the coach uses another channel, there may be no Gmail ID. “Same evidence” and “does not depend on Google” are not the same contract.

The pinned exactly-once primitive accepts only a Boolean callback and arbitrary metadata, so r2 must define the missing server validation rather than inherit it:

```text
$ git show origin/main:webhook/fulfillment_state.py | nl -ba | sed -n '215,233p'
   215 def confirm_after_send(path: os.PathLike[str] | str,
   216                        send: Callable[[], bool], metadata: Optional[Dict[str, Any]] = None) ...
...
   225        if state["status"] == CONFIRMED:
   226            return "idempotent", copy.deepcopy(state)
...
   229        if not send():
   230            raise RuntimeError("confirmation email failed")
   231        state["status"] = CONFIRMED
   232        state["confirmation"] = {"at": now_iso(), **(metadata or {})}
```

**Required change:** define a typed evidence union. Provider-verified evidence must include provider/message/draft IDs, from/to, sent timestamp, revision, body/attachment digests, and server verification. Manual evidence must be an explicit authenticated attestation with channel, recipient, sent time, revision, content/attachment digests, and reason it could not be provider-verified. Reject arbitrary, wrong-recipient, unsent, and stale-revision IDs. Describe the primitive as exactly-once state recording, not exactly-once human sending.

### 10. B2 specifies APPROVED/APPLIED emails but no transition invokes them

> “`APPROVED` | Apply step ...”

> “`APPLIED` | Draft-ready notice ...”

The pinned notification is built and sent once, immediately after generation. The transition endpoint mutates state and returns JSON; it does not enqueue or send a new notification. Merely making the template state-aware cannot produce APPROVED or APPLIED emails.

```text
$ git show origin/main:webhook/app.py | nl -ba | sed -n '1990,2021p;2393,2401p'
  1990 result = run_pipeline(...)
...
  2011 details = _build_plan_notification_details(order_data, result, ...)
...
  2017 if result['success']:
  2018     details['download_token'] = _generate_download_token(athlete_id)
  2019     _notify_new_order('training_plan', details)
  2020     _update_job(athlete_id, status='succeeded', ...)
...
  2393 state = transition_fulfillment(...)
...
  2400 return jsonify({'athlete_id': norm_id, 'status': state['status'],
  2401                 'generation_revision': state['generation_revision']}), 200
```

**Required change:** name notification-producing transition events and implement them through a durable outbox keyed by athlete/revision/status/template version. Define retry/deduplication and record failed notification delivery without rolling back a valid state transition. If APPROVED/APPLIED email is not actually desired because the review page is the control surface, remove those rows instead of specifying unreachable behavior.

### 11. The existing Endure delivery path bypasses the entire r2 state machine

> “No executable deliverable, customer download, published guide, or athlete-calendar write exists outside the fulfillment state machine.”

> “Nothing touches an athlete's calendar before an authenticated approval.”

R2 is written as though TrainingPeaks/manual import are the only delivery paths; `Endure` and `delivery_target` do not appear anywhere in it. At the pinned commit, however, an Endure-target order is pushed immediately after successful generation, before state-aware notification or approval. That helper explicitly “NEVER raises, never fails the order”; on failure the job still succeeds and falls back to TrainingPeaks. This violates I2, I3, and I6, and it can also violate I4 because the Endure flow owns invitation mail outside E2.

```text
$ rg -ni 'endure|delivery_target' docs/SPEC_TRUSTWORTHY_FULFILMENT.md || echo '[no Endure/delivery_target disposition]'
[no Endure/delivery_target disposition]

$ git show origin/main:webhook/app.py | nl -ba | sed -n '1918,1926p;1990,2021p'
  1918  def _attempt_endure_delivery(athlete_id: str, order_data: dict,
  1920      """Push a generated plan to Endure. NEVER raises, never fails the order.
...
  1990      result = run_pipeline(athlete_id, deliver=True,
...
  2000      # Phase 4b: push to Endure when this order opted in.
  2002      # guarantee). A failed push never fails the order ...
  2006      if (result['success']
  2007              and order_data.get('delivery_target') == 'endure'):
  2008          endure_record = _attempt_endure_delivery(
  2009              athlete_id, order_data, intake_data or None)
...
  2017      if result['success']:
  2019          _notify_new_order('training_plan', details)
  2020          _update_job(athlete_id, status='succeeded', ...)
```

**Required change:** make delivery platform an order-scoped state field and bring every platform adapter under the same approval, content seal, apply evidence, readback, rollback, release, and failure rules. Disable the current pre-approval Endure push before Phase 1 exits, or explicitly remove Endure from production. Add athlete-m and cross-brand fixtures for both `trainingpeaks` and `endure`, including failure-without-TP-fallback unless the coach authorizes that fallback.

### 12. “One page per order” and typed tokens still have no order identity

> “One page per order at `/review/<athlete_id>`”

> “every token carries signed claims `{athlete_id, generation_revision, artifact, audience, iat, exp, kid}`”

Athlete ID plus a counter in one athlete-named state file is not an order identity. A returning athlete, two concurrent purchases, or two people who normalize to the same athlete slug share the same review URL, state path, revision counter, tokens, artifacts, approval, and platform binding. A later `write_generation` replaces the earlier order's live state and invalidates its actions. R1 explicitly required athlete/order binding; r2 silently dropped `order_id` from the token and schema.

```text
$ git show origin/main:webhook/fulfillment_state.py | nl -ba | sed -n '124,148p'
   124  def write_generation(path: ..., athlete_id: str, ...):
...
   135      state = {
   136          "schema_version": SCHEMA_VERSION,
   137          "athlete_id": athlete_id,
   138          "generation_revision": revision,
...

$ git show origin/main:webhook/app.py | nl -ba | sed -n '2367,2368p;2380,2387p'
  2367  def _fulfillment_status_path(athlete_id: str) -> Path:
  2368      return Path(DELIVERIES_DIR) / athlete_id / 'fulfillment_status.json'
...
  2380  @app.route('/api/fulfillment/<athlete_id>/transition', methods=['POST'])
```

**Required change:** add immutable `order_id` (and delivery platform) to schema v2, review routes, storage keys, token/capability claims, artifact paths, contract external IDs, audit records, and every transition. Use an opaque order/review identifier rather than an athlete slug as the primary authority. Add tests for repeat customers, simultaneous orders for one TP athlete, slug collisions, cross-order token reuse, and regeneration of one order without affecting another.

### 13. The post-render validator is wired to a replace operation while the spec says “append”

> “Validator failures append blockers via `set_generation_blockers`”

The pinned function does not append. It replaces the complete blocker list. If the new validator passes only its own findings—as the quoted instruction naturally says—it erases `FTP_ESTIMATED`, `RACE_STALE`, `COURSE_UNRESOLVED`, availability, brand, and quality blockers. A concurrent read/merge/write in the caller would still be prone to lost updates unless the merge occurs under the state lock with a revision precondition.

```text
$ git show origin/main:webhook/fulfillment_state.py | nl -ba | sed -n '153,165p'
   153  def set_generation_blockers(..., blocking_issues: list[Dict[str, Any]]) ...:
...
   157      with locked_state(path) as (state_path, state):
...
   162          state["blocking_issues"] = issues
   163          state["status"] = BLOCKED_REVIEW if issues else GENERATED
   164          _history(state, "BLOCKERS_UPDATED", blocker_ids=[x["id"] for x in issues])
```

**Required change:** either state explicitly that one final orchestrator supplies the complete deduplicated blocker set, or add an atomic `merge_generation_blockers(expected_revision, source, issues)` operation that merges/removes only that validator's namespace under the lock. Tests must start with intake/provenance blockers, add post-render blockers, rerun one validator cleanly, and prove unrelated blockers are never dropped.

### 14. Two post-render rule definitions still cannot catch the observed defects

> “`THIN_RACE_WEEK` — race week has < 3 scheduled entries, where notes and strength do not count and the race-day entry does”

> “`SESSION_PREDATES_ORDER` — any dated session earlier than `order_created_at` (delivery date used only for reporting).”

First, PlanIR synthesizes a dated `day_off` for every unrendered calendar day. R2 never excludes `rest`/`day_off`, so a literal count sees a full week even when there is only a race entry. Second, the observed defect was “in the past at delivery time”: the order was purchased August 4, delivered August 6, and an August 5 workout is after order creation but already stale at delivery. The new rule deliberately legalizes it. PlanIR dates are date-only strings, while `order_created_at` is a timestamp, so timezone/same-day comparison is also undefined.

```text
$ git show origin/main:athletes/scripts/plan_ir.py | nl -ba | sed -n '455,468p;490,503p'
   455  def _rest_session(date: Optional[str]) -> Session:
...
   460      type="rest",
...
   464      tp_kind="day_off",
...
   490  for week_data in plan_dates.get("weeks", []):
   492      for day in week_data.get("days", []):
...
   500          else:
   501              # Calendar days without a rendered ZWO are real rest days ...
   503              week.sessions.append(_rest_session(day.get('date')))

$ nl -ba docs/MONIKA_RENK_PIPELINE_FINDINGS.md | sed -n '72,81p'
    72  ### 5. Structural holes in a 6-week plan
...
    77  - Two W00 workouts dated 08-04 and 08-05 — **in the past at delivery time**.
...
    81  "plan has a race day" and "no session is dated before delivery" are not in it.
```

**Required change:** define counted kinds exhaustively and exclude at least `rest`/`day_off` and notes from thin-week counts; add fixtures with seven synthesized rest entries. Replace or supplement the order rule with `SESSION_PREDATES_RELEASE`, comparing the session's local calendar date against an explicit release/delivery date and timezone. If pre-order and pre-release are both meaningful, make them separate rules with exact same-day semantics.

### 15. `COURSE_UNRESOLVED` and transitional fabricated FTP remain waivable safety failures

> “each [blocker] with a waive control requiring a reason”

> “`COURSE_UNRESOLVED` ... Hard blocker until the `courses[]` schema work lands”

> “No estimated or defaulted value may anchor an athlete-facing deliverable while presenting as measured.”

“Hard” is only a label here. The retained transition accepts any blocked plan once the waiver contains every blocker ID. Thus a coach can waive `COURSE_UNRESOLVED` without correcting/removing the 89-mile course facts, or waive Phase 1's `FTP_ESTIMATED` and release the fabricated-watt plan. The new course ticket's no-unresolved-facts acceptance criterion belongs to the future schema ticket; its own status says the interim blocker covers the gap. It does not change r2's interim renderer or waiver semantics.

```text
$ git show origin/main:webhook/fulfillment_state.py | nl -ba | sed -n '183,197p'
   183  if to == APPROVED:
...
   187      if not isinstance(waiver, dict):
   188          raise FulfillmentStateError("complete waiver is required for blocked review")
...
   191      blockers = {issue["id"] for issue in state["blocking_issues"]}
   192      if not isinstance(rule_ids, list) or not reason or set(rule_ids) != blockers:
   193          raise FulfillmentStateError("waiver must cover every blocking issue exactly")
...
   196      state["approval"] = {"coach": coach.strip(), "at": now_iso()}

$ nl -ba docs/followups/RACE_COURSES_SCHEMA_TICKET.md | sed -n '3,5p;35,40p'
     3  - Status: filed; blocks nothing in SPEC_TRUSTWORTHY_FULFILMENT (the interim
     4    `COURSE_UNRESOLVED` hard blocker covers the gap) ...
...
    40  - No course-specific fact reaches a plan or guide from an unresolved match.
```

**Required change:** add blocker policy to schema v2 (`waivable: true|false`, with server-owned policy by stable rule ID). Make fabricated target anchors, unresolved platform identity, unresolved target thresholds, state/validator failures, and unresolved course facts non-waivable. Approval must require remediation and a new generation/review, or the renderer must omit every unproven course/FTP-dependent fact. Add negative tests proving a complete waiver cannot approve these IDs.

## Non-blocking findings

1. **Appendix 2 anchor audit:** all listed pinned-code line claims were accurate, including the newly added fueling-policy, fueling-table, polyline, guide-trigger, intel-stats, apply-order, fulfillment-manifest, adapter, test, and day-list anchors. `origin/main` resolves to the stated full commit.

2. **F2 is broader than its named anchor.** `training_guide_builder.py` contains many independent fixed carbohydrate figures in addition to `GUT_TRAINING_PHASES` (for example lines 1668-1776 and 2939-2941). “All rendered carb numbers” therefore requires an explicit inventory and a distinction between personalized prescription, generic education, product examples, recovery nutrition, and daily g/kg—not only changing `calculate_fueling.py:94-116`.

   ```text
   $ git show origin/main:athletes/scripts/training_guide_builder.py | \
       rg -n '60-80g|70-75g|40-60g|60-90g|70-80g|g/hr' | sed -n '1,12p'
   1367:            recovery_line = "30g protein + 60-90g carbs within 30 minutes"
   1668:  <p>For any ride over 90 minutes at moderate-to-high intensity (Z3+), you need 60-80g of
   1671:  The target for most athletes is 70-75g per hour ...
   1679:      <tr><td><strong>Z2 Endurance</strong></td><td>2-4 hours</td><td>40-60g</td>
   1704:  <tr><td>4-8 hours</td><td>60-90g</td>...
   1776:      ... = 70-80g total.</td></tr>
   2941:      <p><strong>General guidance, not your target:</strong> 60-80g carbs per hour ...
   ```

3. **A2 must remove the source fabrication, not only repair tokenization.** The paid-order adapter itself inserts the hardcoded device answer; parser-only work would turn the fabricated string into better fabricated tokens.

   ```text
   $ git show origin/main:webhook/app.py | nl -ba | sed -n '1483,1490p'
     1485  ## Equipment
     1486  - Indoor Trainer: {intake_data.get('trainer_access', 'smart trainer')}
     1487  - Devices: power meter, HR strap

   $ git show origin/main:tp-skus/generate_skus.py | nl -ba | sed -n '79,85p'
       80  ## Equipment
       81  - Indoor Trainer: smart
       82  - Devices: power meter, HR strap
   ```

4. **Per-link revocation is not a `kid` blacklist.** Blacklisting a signing-key ID revokes every token under that key, not one nonce. Specify a nonce/JTI denylist or per-link credential record, scanner/session behavior, and whether first open consumes anything.

5. **F3's second copy is outside the pinned repository.** The local module says the second copy lives in `gravel-god-training-plans`, but r2 supplies no repository URL/ref, owner, or cross-repo acceptance gate. This should not silently make this repository's Phase 1 unfinishable.

6. **`athlete-m` needs an exact fixture contract.** Name the checked-in paths and exact device answer, ordered day lists, purchased and generated week counts, race courses/no-match, frozen times/timezone, session seed, worker responses, and exact expected blocker set by phase. “Structural rules as seeded” is not a golden expectation.

7. **F7 should choose an API.** Specify maximum/default `hours`, maximum/default `limit`, whether both may be supplied, cursor/order semantics, malformed/negative handling, and tests. Reading only current/previous monthly files also becomes wrong for a sufficiently large allowed window unless changed.

8. **A3's sensitivity field needs enforcement.** The review surface, notification, state history, logs, and audit output need explicit allow/redact rules for health/PII-bearing derived values; labeling sensitivity without constraining renderers does not protect it.

9. **The two follow-up documents occupy different refs in this dirty checkout.** The prior TP ticket is present at `origin/main` but absent from the working tree; the race-course ticket is present only in the working tree. This did not prevent review because I read the former with `git show` and the latter as the newly supplied spec context.

   ```text
   $ for p in docs/followups/AUTOMATED_TRAININGPEAKS_FULFILLMENT_TICKET.md \
       docs/followups/RACE_COURSES_SCHEMA_TICKET.md; do
       git cat-file -e "origin/main:$p" 2>/dev/null && echo "$p origin/main:PRESENT" || echo "$p origin/main:ABSENT"
       test -f "$p" && echo "$p working-tree:PRESENT" || echo "$p working-tree:ABSENT"
     done
   docs/followups/AUTOMATED_TRAININGPEAKS_FULFILLMENT_TICKET.md origin/main:PRESENT
   docs/followups/AUTOMATED_TRAININGPEAKS_FULFILLMENT_TICKET.md working-tree:ABSENT
   docs/followups/RACE_COURSES_SCHEMA_TICKET.md origin/main:ABSENT
   docs/followups/RACE_COURSES_SCHEMA_TICKET.md working-tree:PRESENT
   ```

## What I could not verify

1. I could not verify live TrainingPeaks acceptance or exact readback semantics for `percentOfThresholdHr`, `percentOfMaxHr`, RPE descriptions, threshold/zone updates, stable embedded external IDs, delete/rollback, or TP-side idempotency. No controlled live fixture or captured protocol exists in the pinned repository.

2. I could not verify that the browser worker can maintain coach sessions/TOTP, distinguish candidate athletes, enforce coaching relationships, survive SPA drift, or perform any broker operation. The worker does not exist at the pinned commit.

3. I could not verify the new `apply_contract/v1`, state schema v2 migration, review page, typed tokens, approval snapshot, release outbox, or credential model because they are specification-only.

4. I could not execute `athlete-m`; no such checked-in fixture exists yet. I also could not replay the real Monika input, which remains only on the Railway volume and must not be copied into this repository.

5. I could not verify deterministic PDF/Page publishing, guide revocation/cache behavior, Gmail OAuth/draft creation, sent-message verification, sender aliases, or attachment fidelity. None is implemented at the pinned commit, and no external credentials were available.

6. I could not verify the other vendored polyline copy in `gravel-god-training-plans`; it is outside this repository and r2 does not pin its ref.

7. I could not verify course-level production matching because the pinned race schema has no `courses[]`; the new ticket is design context, not implementation.

8. I could not verify TrainingPeaks terms-of-service acceptability. R2 records browser automation as an accepted business risk, but includes no contractual/legal evidence.

9. I could not verify the live Endure service's delivery, invitation-email, readback, rollback, or idempotency behavior. The pinned client and tests prove that the webhook invokes it before approval, not what the remote service ultimately mutates.

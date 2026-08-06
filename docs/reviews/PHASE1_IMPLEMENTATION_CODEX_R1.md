# Phase 1 implementation adversarial review — Codex R1

## Verdict: NO-GO

The implementation does not establish the Phase 1 invariant that blocked means
blocked. There are still live CLI and webhook paths that expose executable
artifacts or create a TrainingPeaks apply job without a seal-bound approval;
approval can be recorded after sealed bytes have changed; quarantined v1 state
can retain authority; a double persistence failure is reported as a successful
job; the validator does not validate the final `tp_manifest.json`; and the
athlete-m gate manufactures its expected plan rather than replaying production
generation. These are release blockers under S1/S2/S4, B1-B4, C2, and the Phase
1 rollout gate (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:107-190,207-224,336-452,1086-1099`).

Review basis: static review of `git diff 4812520..HEAD` and the resulting files.
I did not trust commit messages or
`docs/reviews/PHASE1_IMPLEMENTATION_NOTES.md`. I did not modify implementation
files and did not run the socket-based fake-TP tests.

## Phase 1 conformance matrix

| Phase 1 item | Disposition | Evidence |
|---|---|---|
| S1 order identity | **Partial / blocked** | Schema v2 requires order/platform identity (`webhook/fulfillment_state.py:21-35,107-139`), and order state/jobs have order-keyed paths (`webhook/app.py:1774-1800,2103-2141`). Manual generation still writes its authority at the athlete path (`athletes/scripts/generate_athlete_package.py:3095-3108`), and the v1 quarantine has authority leaks described in blocker 3. |
| S2 transitional seal | **Partial / blocked** | Artifact records, manifest sealing, and verification exist (`webhook/fulfillment_state.py:350-470`), but approval does not verify the current bytes, sealed revisions are replaceable, and serving has a verify/open race (blocker 2). |
| S4 blocker policy | **Partial / blocked** | The server owns a non-waivable set and recomputes `waivable` (`webhook/fulfillment_state.py:38-94`); approval rejects complete waivers containing a non-waivable id (`webhook/fulfillment_state.py:496-525`). `COURSE_UNRESOLVED` has no required remediation, and seal mismatch is never materialized into state (blockers 2 and 6). |
| S6 blocker merge | **Conforms statically** | Source-scoped replacement, preservation of other sources, and revision rejection are implemented (`webhook/fulfillment_state.py:300-347`) and used by intake/post-render (`athletes/scripts/intake_to_plan.py:3372-3376,3443-3448`). |
| B1 review/release split | **Fails** | The new ZIP split is correct in isolation (`webhook/app.py:1736-1764,1932-1973`), but old release/apply paths remain reachable (blocker 1). |
| B2 state-aware generation notice | **Partial** | The new email is review-only and reports blockers/waivability (`webhook/app.py:360-410`), and successful state-aware jobs select it (`webhook/app.py:413-439,2313-2324`). Legacy delivery email paths remain able to attach ZWOs and import instructions (blocker 1). |
| B3 endpoints and typed tokens | **Partial / blocked** | Claims bind order, athlete, revision, artifact, audience, time, jti, and kid (`webhook/download_tokens.py:86-125,141-190`); the route rejects caller-selected `type` and gates customer artifacts (`webhook/app.py:2531-2574`). Missing-key behavior and operational revocation are not fail-closed (blocker 8). |
| B4 state failure | **Fails** | A second persistence failure leaves `persisted` false but the job is still notified as success and marked `succeeded` (`webhook/app.py:2287-2326`); blocker 4. |
| D4 Endure pre-approval disable | **Conforms for the order path** | The Endure helper remains (`webhook/app.py:2208-2257`), but `_execute_plan_job` no longer invokes it (`webhook/app.py:2260-2332`). The focused test asserts an Endure target produces no POST (`webhook/tests/test_endure_delivery.py:637-652`). |
| Versioned PlanIR + `tp_manifest` post-render validator | **Fails** | A versioned envelope is present (`athletes/scripts/post_render_validator.py:19-74,195-208`), but the manifest is reduced to a count and both named inputs are rewritten after validation (blocker 5). |
| New blockers and confirmations | **Partial / blocked** | Intake adds FTP/course/weeks blockers (`athletes/scripts/intake_to_plan.py:3336-3371`); the validator implements race-week, duplicate test, dates, schedule, fueling and altitude IDs (`athletes/scripts/post_render_validator.py:212-322`); crashes merge a non-waivable blocker (`athletes/scripts/intake_to_plan.py:3457-3470`). Altitude cannot fire on the production schema, course remediation is absent, and seal mismatch never becomes a finding (blockers 2, 5, 6). |
| A2 device source and parsing | **Partial / blocked** | The webhook and SKU hardcodes are removed (`webhook/app.py:1572-1575`; `tp-skus/generate_skus.py:80-82`), and comma/newline parsing plus vocabulary mapping exist (`athletes/scripts/intake_to_plan.py:506-531`). Unknown tokens are neither verbatim nor confirmation items (blocker 7). |
| F2 fueling truth | **Conforms statically, with test limitation** | Fueling labels derive from actual `plan_dates.yaml`, including W00 (`athletes/scripts/calculate_fueling.py:303-401`), and the generated package realigns fueling before rebuilding the guide (`athletes/scripts/generate_athlete_package.py:3126-3135`). The guide labels its generic figures and marks one canonical personalized card (`athletes/scripts/training_guide_builder.py:1655-1676,1767-1776,4121-4172`). The test samples helpers rather than a complete rendered guide (`athletes/scripts/test_fueling_plan_alignment.py:46-62`). |
| F3 polyline, this repo | **Conforms statically** | Cumulative time remains unrounded between emissions, with clamping and monotonicity (`athletes/scripts/tp_polyline.py:52-67`). Goldens and fixed property-shaped cases exist (`athletes/scripts/test_tp_polyline.py:28-75`). The external copy is unverifiable here. |
| F6 weeks sold vs delivered | **Conforms statically** | `plan_weeks` is compared with purchased weeks and W00 is explicitly excluded from the message (`athletes/scripts/intake_to_plan.py:3358-3371`); policy leaves it waivable (`webhook/fulfillment_state.py:40-47,73-79`). |
| F7 intel stats | **Conforms statically** | `limit` is rejected, `hours` is bounded 1-720, all intersecting months are read, and results sort by timestamp/id (`webhook/app.py:4413-4440,4447-4495`). |
| Athlete-m literal fixture and gate | **Literal JSON matches; gate fails** | `tests/fixtures/athlete_m/expected/phase1.json:1-20` exactly matches the Phase 1 closed sets in the spec (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:1043-1068`). The test does not generate those outputs (blocker 9). |

## Blockers

1. **Executable release and apply bypasses remain live.** This violates B1's
   rule that release artifacts require APPROVED+ and seal verification, S2's
   requirement that every consumer verify the artifact and approval, and the
   Phase 1 “blocked means blocked” gate
   (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:150-190,338-352,1093-1099`).

   - A signed WooCommerce order queues a job with no intake
     (`webhook/app.py:3477-3520`). No intake selects
     `generate_full_package.py --deliver` (`webhook/app.py:1612-1629`). Its
     delivery step copies a guide to the hosting tree and ZWOs to Downloads
     before consulting any fulfillment state (`athletes/scripts/deliver_package.py:92-118`).
   - The same legacy delivery script can send the guide and workout ZIP to the
     athlete (`athletes/scripts/deliver_package.py:184-207`). The lower-level
     CLI independently loads an athlete-path guide/workout directory and sends
     it without any order, revision, approval, or seal check
     (`athletes/scripts/email_delivery.py:430-478`); its email explicitly gives
     `.zwo` import instructions and attaches a workout ZIP
     (`athletes/scripts/email_delivery.py:101-133,249-272,335-354`).
   - `tp_apply_order.py` has an explicit `--skip-approval-check` switch and
     proceeds without a server (`tools/tp_apply_order.py:201-230,504-520`). With
     a server it checks only `status == APPROVED`; it does not compare order,
     revision, athlete, model seal, release-manifest digest, or package digest
     to the supplied package (`tools/tp_apply_order.py:173-220,433-456`). The
     consumed `tp_manifest.json` carries none of order id, revision, or seal
     (`athletes/scripts/plan_ir.py:648-665`). Thus even the nominal server gate
     can authorize a stale or unrelated manifest, and skip mode can authorize a
     blocked one. The emitted driver runbook performs the real browser apply
     (`tools/tp_apply_order.py:407-425`; `tools/tp_apply_driver.js:496-527`).
   - The alternative adapter also accepts an arbitrary manifest and performs
     remote writes before its first state transition; it never verifies a seal
     or approval/manifest binding (`delivery/trainingpeaks/adapter.py:67-96,130-139`).

2. **The seal is detectable but not an enforced immutable approval boundary.**
   This violates S2's “nothing rewritten after being hashed,” immutable
   manifest, approval binding, fatal-consumer-verification, and
   `write_generation` correction rules
   (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:150-190`).

   - `transition(..., APPROVED)` checks only that two stored strings are
     nonempty, then copies them into approval; it never calls
     `verify_release_manifest` (`webhook/fulfillment_state.py:496-531`). A file
     can change after sealing and the approval endpoint still returns
     APPROVED. The existing mutation test proves failure only when verification
     is called explicitly (`webhook/tests/test_fulfillment_state.py:181-189`);
     there is no approval-after-mutation negative test.
   - `persist_deliverables` overwrites the authoritative order state from a
     source copy, deletes an existing `r<revision>` directory, and rebuilds it
     at the same revision (`webhook/app.py:1911-1924`). This can erase approval
     and replace already-sealed bytes without `write_generation`, precisely the
     same-revision mutation S2 forbids.
   - Download hashes the file and then returns its path to `send_file`
     (`webhook/fulfillment_state.py:458-470`; `webhook/app.py:2570-2584`). The
     file is reopened after verification, leaving a verify/open TOCTOU window.
   - Seal failures are logged and converted to 409 only
     (`webhook/app.py:2570-2574`). Although `SEAL_MISMATCH` is declared
     non-waivable (`webhook/fulfillment_state.py:40-47`), no producer merges
     that finding into state. State may remain APPROVED after a fatal mismatch,
     contrary to S4 and R9 condition 8.

3. **Schema-v1 quarantine is neither startup-complete nor authority-free.**
   This violates S1's requirements that every v1 file be migrated recoverably
   at startup and that prior approval/application grant no authority for new
   actions (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:114-127`).

   - Migration preserves the old status, approval, and application verbatim
     (`webhook/fulfillment_state.py:575-618`). The general transition function
     checks `legacy_binding` (`webhook/fulfillment_state.py:488-492`), but
     `confirm_after_send` does not (`webhook/fulfillment_state.py:552-572`). The
     `/api/confirm` route likewise gates only on the preserved status before it
     constructs an athlete send (`webhook/app.py:2800-2823,2873-2894`).
   - More directly, the authenticated status endpoint returns preserved
     APPROVED state without checking `legacy` or a seal
     (`webhook/app.py:2734-2769`). The old TP CLI then accepts that status alone
     (`tools/tp_apply_order.py:201-220`), so a migrated approval can authorize a
     new apply even without manual binding.
   - Migration is lazy inside `_resolve_order_id`, not a startup scan. It returns
     a single existing slug lookup before even examining the legacy file
     (`webhook/app.py:1804-1845`). A repeat customer with one v2 lookup can
     therefore leave the old v1 file unmigrated indefinitely. The tests cover
     an isolated lazy migration and rejection through `transition`, but not
     lookup shadowing, preserved APPLIED confirmation, or the status/apply
     consumer (`athletes/scripts/test_athlete_m_phase1.py:239-275`;
     `webhook/tests/test_fulfillment_state.py:192-212`).

4. **A total state/persistence failure is deliberately reported as success.**
   This directly violates B4 and the no-false-success invariant
   (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:397-402`). After both normal
   persistence and the `STATE_UNAVAILABLE` quarantine fail, `persisted` remains
   false (`webhook/app.py:2287-2311`), yet the code sends a successful training
   plan notice and marks the job `succeeded` (`webhook/app.py:2313-2326`). The
   regression test mocks `persist_deliverables` to return `None` and explicitly
   asserts `succeeded` (`webhook/tests/test_webhook.py:2982-3012`), so the test
   has enshrined the forbidden behavior rather than caught it.

5. **The post-render validator does not validate the final named transitional
   artifacts, and the altitude blocker uses a schema that production does not
   emit.** This violates C2's requirement to validate PlanIR **and**
   `tp_manifest.json`, plus F1 guide semantics
   (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:418-452,953-958`).

   - Every semantic check iterates PlanIR sessions
     (`athletes/scripts/post_render_validator.py:90-95,212-301`). The manifest
     is checked only for version and equal session count
     (`athletes/scripts/post_render_validator.py:201-208,319-322`). A stale or
     malicious manifest with the same count passes even though that manifest is
     what the live browser apply CLI consumes.
   - The pipeline validates, merges the resulting state, and then rewrites both
     PlanIR and `tp_manifest.json` without validating the rewritten files
     (`athletes/scripts/intake_to_plan.py:3441-3453`). Consequently the exact
     named bytes later sealed are not the bytes that passed validation.
   - Altitude validation reads
     `target_race.start_elevation_asl_ft/average_elevation_asl_ft`
     (`athletes/scripts/post_render_validator.py:303-317`). Production intake
     stores `target_race.elevation_ft` (`athletes/scripts/intake_to_plan.py:957-975`),
     while the guide's authoritative trigger reads
     `race_metadata.avg_elevation_feet/start_elevation_feet`
     (`athletes/scripts/training_guide_builder.py:225-256`). The validator's
     fields are not either producer schema, so `ALTITUDE_SECTION_MISSING` does
     not protect qualifying production snapshots. No altitude test exists in
     `athletes/scripts/test_post_render_validator.py:64-112`.

6. **`COURSE_UNRESOLVED` has no facts-omitted recovery and still carries the
   headline course facts into the plan model.** S4/C2 require non-waivable
   `COURSE_UNRESOLVED` to be recoverable by regenerating from athlete-supplied
   facts only (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:214-218,420-425`). The code
   first copies the matched race's headline elevation and other record fields
   into `target_race`, then merely adds `course_unresolved`
   (`athletes/scripts/intake_to_plan.py:943-984`). The only runtime use of the
   rule is to append a blocker (`athletes/scripts/intake_to_plan.py:3350-3357`);
   there is no facts-omitted projection/regeneration path. The follow-up ticket
   itself says no course-specific fact may reach plan/guide for an unresolved
   match (`docs/followups/RACE_COURSES_SCHEMA_TICKET.md:23-42`), which the
   current assignment of `elevation_ft` violates.

7. **A2 does not preserve unknown device tokens verbatim as confirmation
   items.** A2 requires comma/newline-only splitting, vocabulary mapping, and
   unknown tokens verbatim as confirmations
   (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:309-322`). The parser lowercases and
   whitespace-normalizes every unknown token, then inserts it directly into the
   profile (`athletes/scripts/intake_to_plan.py:506-531,1473-1476`). No device
   confirmation producer exists. The new test calls this “preserves unknowns”
   while expecting the lowercased profile token, and never checks a confirmation
   (`athletes/scripts/test_intake_to_plan.py:63-79`).

8. **Typed token key handling fails open, and revocation is not wired to an
   operational action.** This violates B3 and R9 condition 8's fail-closed token
   and revocation requirement
   (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:375-395`;
   `docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R9.md:114-119`). If no token
   key or secret is configured, `_keyring` silently derives both audience keys
   from the public literal `dev-secret` (`webhook/download_tokens.py:43-60`), so
   the service can issue forgeable production capabilities instead of refusing
   to start/issue. `revoke_download_token` exists
   (`webhook/download_tokens.py:193-223`), and verification reads the denylist
   (`webhook/app.py:2024-2033`), but there is no application caller or
   authenticated endpoint that can add a real issued jti/kid; only the unit
   test calls it (`webhook/tests/test_download_tokens.py:81-91`). Tests also
   force valid keys for every case (`webhook/tests/test_download_tokens.py:13-20`),
   masking the insecure default, and contain no legacy-token rejection case.

9. **The athlete-m “golden” is self-fulfilling rather than a deterministic
   production replay.** This fails the Phase 1 gate and R9 conditions 1 and 7
   (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:1035-1068,1093-1099`;
   `docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R9.md:71-75,109-113`). The
   fixture's literal expected closed sets are correct
   (`tests/fixtures/athlete_m/expected/phase1.json:1-20`), but:

   - `_rendered_replay` reads `expected/plan_dates.json` as input and fabricates
     PlanIR, `tp_manifest`, fueling, and guide HTML
     (`athletes/scripts/test_athlete_m_phase1.py:67-110`). It never calls the
     production date calculator or package generator.
   - `_intake_issues` manually returns the exact four desired intake blockers,
     including a hardcoded weeks-mismatch message
     (`athletes/scripts/test_athlete_m_phase1.py:113-123`). It never runs the
     production blocker assembly.
   - The test writes a one-line fake ZWO and handcrafted artifacts before
     testing persistence (`athletes/scripts/test_athlete_m_phase1.py:126-171`).
     It therefore proves that the expected JSON agrees with itself, not that
     fixed-clock production generation produces the golden schedule, exact
     blockers/confirmations, or valid artifacts.

## R9 implementation-gated conditions

| R9 condition | Phase 1 disposition |
|---|---|
| 1 — dependency rollout and every phase gate | **Not honored.** Athlete-m is not a production replay (blocker 9). |
| 2-6 — D0 schema, migration parity, kill points, worker protocol, live TP proof | Not Phase 1; scheduled for Phases 3-5. The retained Phase 1 browser apply bypass must not be mistaken for satisfying them (blocker 1). |
| 7 — deterministic fixtures | **Not honored for athlete-m Phase 1.** The literal file exists, but the test synthesizes it (blocker 9). HR/RPE and D0 positional fixtures are later-phase. |
| 8 — state, token, seal, outbox failure behavior | **Not honored for the Phase 1 subset.** Migration, state failure, token keys/revocation, and seal enforcement fail closed only partially (blockers 2-4 and 8). Outbox is Phase 5. |
| 9-10 — Gmail evidence and deterministic/revocable guide release | Not Phase 1. |
| 11 — platform prerequisites; Endure off | **Honored only as the Phase 1 disable:** the normal order path does not call Endure. Later re-enable prerequisites are not implemented and must remain off. |
| 12 — controlled end-to-end evidence | Production end-to-end proof is Phase 5. Its Phase 1 course safeguard is **not honored** because facts-omitted regeneration is absent (blocker 6). The external polyline-copy follow-up is not verifiable here. |

## Non-blocking findings

1. **No test file was deleted, but test selection was broadened in ways that can
   inflate a green run.** The archetype suite now skips wholesale when a
   white-paper sentinel is absent (`tests/archetypes/test_regression.py:8-13`),
   and the complete webapp test module is skipped when `flask_wtf` is absent
   (`webapp/tests/test_webapp.py:20-27`). These changes are unrelated to the
   Phase 1 gate and should be accounted for in any reported pass/skip totals.

2. **The Endure test change hides stale later-phase behavior.** Entire legacy
   execution and confirm test classes are skipped
   (`webhook/tests/test_endure_delivery.py:543-544,753-754`) and only the
   no-preapproval-POST check replaces the main flow. Disabling the push is
   correct for Phase 1, but stale fallback/invitation branches and the callable
   helper remain in production code (`webhook/app.py:2208-2257,2896-2977`).
   They should not be represented as tested behavior.

3. **Several critical negative cases are missing.** There is no test for
   approval after sealed-byte mutation, same-revision persistence replacement,
   migrated APPLIED confirmation/status consumption, semantic manifest drift
   with equal counts, production-schema altitude, missing token secrets,
   application-level revocation, or legacy token rejection. The relevant test
   files stop at explicit seal verification, isolated migration, count-based
   validator fixtures, and library-only revocation
   (`webhook/tests/test_fulfillment_state.py:181-212`;
   `athletes/scripts/test_post_render_validator.py:64-112`;
   `webhook/tests/test_download_tokens.py:44-96`).

4. **F3's “property tests” are a short fixed table, not broad generated
   properties.** The implementation appears correct, but the test covers only
   four duration vectors (`athletes/scripts/test_tp_polyline.py:55-75`). This is
   weaker than the property-test wording in F3
   (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:968-973`).

5. **Later-phase statuses leaked into schema without transition support.**
   `APPLYING`, `APPLIED_ATTESTED`, and `CANCELLED` are accepted as top-level
   values (`webhook/fulfillment_state.py:21-35`), while `transition` implements
   only APPROVED and APPLIED and rejects every other destination
   (`webhook/fulfillment_state.py:496-542`). This is premature Phase 5 surface
   area and can mislead consumers, though it is not itself a Phase 1 release
   blocker.

6. **The local manual pipeline remains athlete-keyed.** It creates an opaque
   order id inside `athletes/<slug>/fulfillment_status.json` rather than moving
   state to `deliveries/orders/<order_id>`
   (`athletes/scripts/generate_athlete_package.py:3095-3108`). Production
   webhook persistence is order-keyed, but S1's manual-order claim is therefore
   not universally true. This becomes blocking if that CLI is considered an
   authoritative manual-order workflow rather than a generation-only tool.

## Items I could not verify

1. I did not run the fake-TrainingPeaks/socket tests because the review sandbox
   cannot run them, per the task constraint. I therefore make no claim that the
   full suite passes, fails, or has the reported pass/skip counts.
2. I did not exercise live WooCommerce, SMTP/SendGrid, Railway, Endure, or
   TrainingPeaks. The bypass findings are based on reachable static call graphs
   and explicit CLI behavior, not a production mutation.
3. I could not verify deployment-time filesystem permissions or whether an
   external process currently rewrites sealed revision directories. The code
   itself neither makes them immutable nor prevents replacement.
4. I could not verify production token environment variables. Regardless of
   current configuration, the checked-in fallback remains fail-open if those
   variables are absent.
5. I could not inspect or compare the vendored `gravel-god-training-plans`
   polyline copy because that repository/ref is outside this review scope. This
   does not gate this repository's Phase 1 under F3.

In summary, the verdict is **NO-GO**: useful artifacts and real apply tooling
still bypass the gate, seal and v1 authority are not enforced at every
consumer, state failure can be called success, key validator rules do not cover
the artifacts/schema they claim to cover, and the mandatory athlete-m gate is
not an honest end-to-end replay. Phase 1 should not be released until all nine
blockers have regression tests that exercise the production paths and the
literal athlete-m golden is produced by fixed-clock generation rather than
constructed from its own expected files.

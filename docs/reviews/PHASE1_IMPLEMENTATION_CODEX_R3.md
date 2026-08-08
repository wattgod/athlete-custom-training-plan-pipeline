# Phase 1 implementation adversarial review — Codex R3

## Verdict: NO-GO

Six of the seven carried R2 items are fixed. Confirm now verifies the complete
sealed release and materializes mismatches, the validator covers all TP
projection fields, facts-omitted survives the production guide path, the
athlete-m calendar golden is the complete emitted structure, missing-intake
orders become durable non-waivable quarantines, and PlanIR is sealed. The
remaining B1 residual is release-blocking: the server capability authenticates
the sealed `tp_manifest.json`, but the browser executes a different, mutable
`apply_job.json` whose operation bytes and target TP athlete are not covered by
the capability. The final gate check also has a check/write race. In addition,
an APPROVED Endure order can still be moved to APPLIED with arbitrary nonempty
evidence and then CONFIRMED through the TrainingPeaks-specific customer email,
despite Endure being required to remain disabled until Phase 5.

Review basis: static inspection of commits `6c30547`, `7847c6a`, `067259a`,
`2d3de32`, and `d1c9cb1` after R2 baseline `d3106d7`, plus the resulting
production call paths and regressions. The implementation notes were treated
as claims, not evidence. Per the task constraint I did not run the suite. The
human-reported `2357 passed, 86 skipped, 0 failed` result is recorded only as
externally supplied.

## Carried-item dispositions

| Item | Disposition | Code evidence | Production-path regression evidence |
|---|---|---|---|
| **B1 + N3 — executable release/apply bypass and platform binding** | **PARTIAL** | N3's direct cross-platform holes are closed: the CLI requires a TP order and exact order/athlete/revision/seal/manifest binding (`tools/tp_apply_order.py:211-255`), the emitted job carries those fields (`:301-367`), the status endpoint issues a gate only for an authorized APPROVED TP release (`webhook/app.py:2862-2929`), the live gate re-verifies the release and all claims (`:2932-3006`), and APPLIED compares the caller platform to immutable state (`webhook/fulfillment_state.py:652-681`). But the token binds only release metadata and `tp_manifest_sha256` (`webhook/app.py:2785-2806`). It does not bind a digest of `apply_job.json`. The driver checks only those envelope fields (`tools/tp_apply_driver.js:90-125`) while executing mutable `plan_title`, `workouts`, strength documents, `athlete_tp_id`, and apply-date fields (`:193-206,232-288,327-400,470-500`). It checks the live gate and then performs the first POST as separate operations (`:535-553`). See release blocker 1. | Regressions prove revocation *before* a gate request, post-emission sealed-manifest mutation, and cross-platform rejection (`athletes/scripts/test_phase1_bypass_gates.py:178-290`), plus missing binding and a refused gate before any TP request (`tools/test_tp_apply_order.py:520-587`). None mutates executable job fields while retaining the valid envelope, nor changes state after a successful final gate response but before the first write. |
| **B2 — APPLIED/confirm seal enforcement** | **FIXED** | APPLIED verifies the entire release under the state transition lock and durably creates non-waivable `SEAL_MISMATCH` on failure (`webhook/fulfillment_state.py:652-681`). Confirm first verifies approval-to-release equality and every manifest artifact (`webhook/app.py:3068-3076`), reads the email, intake backup, and selected guide through verified open descriptors (`:3078-3108`), sends the captured attachment bytes (`:3207-3210`), and records mismatches before returning 409 (`:3109-3116`). Because `verify_release_manifest` hashes every record before any selected attachment is read (`webhook/fulfillment_state.py:416-456`), PDF, HTML, and every other sealed attachment are covered, not just the two directly named by the route. | The state regression mutates a sealed artifact after approval and proves APPLIED is refused with durable non-waivable mismatch (`webhook/tests/test_fulfillment_state.py:211-231`). The real confirm route is parameterized over `personal_email.md` and `training_guide.html` and asserts 409, zero send, and durable quarantine (`athletes/scripts/test_phase1_bypass_gates.py:293-339`). |
| **B5 — complete final TP projection validation** | **FIXED** | The validator derives and compares `plan_title`, `athlete`, and the complete `race` object, then every ordered session projection field and exact counts (`athletes/scripts/post_render_validator.py:105-165`). Intake rebuilds both named projections and validates the final on-disk bytes (`athletes/scripts/intake_to_plan.py:3559-3586`). | The parameterized test mutates all five top-level leaves—title, athlete, race name/date/priority—without changing counts and requires rejection (`athletes/scripts/test_post_render_validator.py:149-166`); equal-count session drift is also rejected (`:141-146`). |
| **B6 — facts-omitted remediation** | **FIXED** for the production order path | Multi-course omission retains athlete-stated name/date/distance, avoids DB fallbacks, and uses a discipline only when athlete-stated (`athletes/scripts/intake_to_plan.py:962-975,1008-1091`). The shipping builder recognizes the omission, skips both race-data resolution and date cross-reference, and constructs race data only from retained athlete distance (`athletes/scripts/training_guide_builder.py:3973-3997`). | The regression invokes real `webhook.run_pipeline`, seeds distinctive forbidden snapshot and guide-database facts, and proves they are absent from both the generated profile and shipping guide (`athletes/scripts/test_athlete_m_phase1.py:170-246`). A retired helper remains; see non-blocking finding 1. |
| **B9 — full-fidelity athlete-m calendar golden** | **FIXED** | The production run reads the emitted `plan_dates.yaml` and compares the entire parsed YAML object to a 328-line YAML golden; there is no selected-field projection (`athletes/scripts/test_athlete_m_phase1.py:33-77`; `tests/fixtures/athlete_m/expected/plan_dates.yaml`). The opt-in updater copies the raw emitted file bytes (`test_athlete_m_phase1.py:74-76`). Parsing YAML for semantic equality is not the former lossy transform. | `test_athlete_m_phase1_golden` runs real `webhook.run_pipeline` before the complete comparison and separately pins field test, race day, race-week density, VO2 placement, blockers, confirmations, and fueling (`athletes/scripts/test_athlete_m_phase1.py:52-167`). |
| **N1 — paid missing-intake durable quarantine** | **FIXED** | Missing intake returns state-unavailable without invoking the legacy deliver path (`webhook/app.py:1622-1637`). `_execute_plan_job` treats that result as persistence-required even when generation failed, writes an order-scoped `STATE_UNAVAILABLE` revision, treats only the durable quarantine as workflow success, emits the normal state-aware coach notice, and fails the job if both persistence attempts fail (`:2253-2355`). `STATE_UNAVAILABLE` is server-owned and non-waivable (`webhook/fulfillment_state.py:37-46`), so the quarantine cannot be approved (`:607-628`). The normal customer status endpoint reads the same state and grants no download without approval and seal verification (`webhook/app.py:2626-2690`); the quarantine is therefore real, not an orphan. | Real Woo and Stripe handler tests assert order-scoped BLOCKED_REVIEW plus non-waivable `STATE_UNAVAILABLE` (`webhook/tests/test_webhook.py:284-320,372-410,836-874`); the latter also asserts the durable-workflow job is `succeeded`. The athlete-m gate proves a blocked state has no customer download and cannot be confirmed/waived through approval (`athletes/scripts/test_athlete_m_phase1.py:144-167`). |
| **N2 — PlanIR included in the release seal** | **FIXED** | `plan_ir.json` is a private deliverable (`webhook/app.py:1761-1774`), is copied before release finalization (`:2011-2043`), and `_artifact_records` seals every file under the revision except the state/manifest machinery itself (`webhook/fulfillment_state.py:349-413`). | The production athlete-m persistence test reads the actual release manifest and requires both `artifacts/plan_ir.json` and `artifacts/tp_manifest.json` (`athletes/scripts/test_athlete_m_phase1.py:110-123`). |

## Remaining release blocker

### 1. B1 remains open: the capability authorizes a sealed source, not the executable job

The status/token path has real value. A token cannot be forged without
`CRON_SECRET`: it is HMAC-SHA256 signed (`webhook/app.py:2770-2806`), and the
consumer checks the signature, audience, expiry, and maximum lifetime
(`:2809-2826`). Regeneration before the gate request changes status/revision and
is rejected; sealed-byte mutation is rejected and materialized; and non-TP
orders do not receive a token (`:2882-2929,2932-3006`).

That authorization is nevertheless spent on different bytes. The CLI hashes
the actual `tp_manifest.json` (`tools/tp_apply_order.py:605-614`) and then emits
an unsealed `apply_job.json` containing operator-supplied `athlete_tp_id` and
target-date/start-type plus transformed workout and strength payloads
(`:301-367,477-518`). Neither the server claims nor the browser gate contain an
apply-job digest. An emitted job can therefore be edited after authorization—for
example, change `athlete_tp_id`, plan title, workout bodies/dates, strength docs,
or target date while leaving the seven checked binding fields intact. The live
gate still returns 200, and the driver uses those altered fields in its POSTs
(`tools/tp_apply_driver.js:193-206,232-288,327-400,470-500`). This violates I3
(what was reviewed is what is applied), Phase 1 S2 byte binding, and B1's rule
that driver inputs are release artifacts
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:83-96,172-190,338-352`). It also conflicts
with R9 conditions 1 and 3: a write-capable old driver remains exposed before
the later parity/worker gates
(`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R9.md:71-85`).

There is also no atomic final authorization boundary. The driver awaits the
second gate response and only then calls stage 1's POST
(`tools/tp_apply_driver.js:535-553`). Regeneration, revocation, or sealed-byte
mutation after the response but before that POST cannot stop the write. Within
the endpoint, current state is loaded before release verification and is not
held under one state lock through the authorization response
(`webhook/app.py:2942-3006`), so a concurrent regeneration after the load can
also leave the endpoint authorizing its stale snapshot. The regressions mutate
before calling the gate, not at either race boundary.

Finally, receipt acceptance does not repair the provenance. It validates only
terminal fields and aggregate kind counts against the local manifest
(`tools/tp_apply_order.py:387-430`), then posts a reduced evidence object
(`:522-567`). The server accepts any nonempty evidence string after seal
verification (`webhook/fulfillment_state.py:652-681`); it never verifies a job
digest or receipt binding. Thus APPLIED does not prove which job bytes or TP
athlete consumed the authorization.

Phase 1 does not need Phase 4/5 lease machinery to close this finding. A
conformant Phase 1 closure can hard-disable the live driver/apply transition, as
the other pre-worker delivery surfaces already do. If the transitional driver
is intentionally retained, the exact executable job and receipt must at least
be server-bound and the final check/write race must be removed before it can be
considered a release path.

## New blocker found in R3

### N4. Disabled Endure orders can be falsely advanced and customer-confirmed

The direct silent TrainingPeaks fallback from N3 is fixed, but the same-platform
case remains open. `transition_fulfillment` accepts APPLIED for every allowed
immutable platform—including `endure`—when `platform` matches and `evidence` is
merely nonempty (`webhook/fulfillment_state.py:33,652-681`). The authenticated
transition route exposes that primitive without a platform-specific evidence
validator (`webhook/app.py:2837-2859`). An operator can therefore approve a
clean Endure order and submit:

```json
{"to":"APPLIED","coach":"coach","platform":"endure","evidence":"x"}
```

No Endure apply or readback need have occurred. `/api/confirm` then accepts any
APPLIED state without checking `delivery_platform` (`webhook/app.py:3037-3066`)
and sends copy stating that the plan is live on TrainingPeaks
(`:3174-3205,3224-3265`) before marking CONFIRMED. The existing cross-platform
test proves only that an Endure order cannot claim `platform=trainingpeaks`; it
does not try the accepted `platform=endure` transition or confirm path
(`athletes/scripts/test_phase1_bypass_gates.py:265-290`).

This makes Endure's disabled state bypassable and can falsely tell a customer
that a platform delivery exists. It violates I2/I3/I6 and D4's requirement that
Endure re-enable only in Phase 5 with sealed content, apply evidence, readback,
rollback, and no platform email
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:83-96,875-893`), plus R9 condition 11's
explicit “Endure remains disabled” condition
(`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R9.md:131-136`). The Phase 1
closure is a platform check that refuses Endure APPLIED/confirm; no Phase 5
machinery is required now.

## Re-attack results and non-blocking findings

1. **A facts-rehydrating helper remains, but not on the production order
   path.** `training_guide_builder.generate_guide` still unconditionally calls
   `load_race_data` and the date cross-reference
   (`athletes/scripts/training_guide_builder.py:297-359`). Repository search
   finds no production caller; the shipping function is
   `generate_training_guide` (`:3788-3805`), called by
   `generate_athlete_package.py:3136,3216`, and that path honors omission. This
   is stale ambiguity worth deleting or making omission-aware, but it does not
   keep B6 open for Phase 1.
2. **The claimed Endure deletion is incomplete, though direct order-path push
   remains absent.** `webhook/endure_delivery.py:267-335` still contains the
   network-writing delivery function and `webhook/app.py:449-564` still contains
   old Endure success/fallback email branches; active tests still exercise those
   branches (`webhook/tests/test_endure_delivery.py:597-660`). The webhook imports
   the module, but production `app.py` calls only its health telemetry
   (`webhook/app.py:2533-2539`), and the normal plan job always supplies state
   fields that select the Phase 1 email at `:442-447`. I found no direct
   production job caller to `deliver_purchased_plan`. This is misleading dead
   code, not an additional network bypass. N4 is the reachable Endure state/send
   surface.
3. **Apply-token negative-test and boundary hardening are incomplete.** No
   dedicated regression tampers with an apply token or proves its expiry. Static
   verification shows both are enforced, but `exp < now` accepts the exact
   expiration second (`webhook/app.py:2822`), and malformed base64 errors outside
   the caught exception set may return 500 rather than the intended 401. Neither
   issue grants authority, so these are non-blocking by themselves.
4. **Confirmation selects one guide attachment but verifies all of them.** The
   route prefers PDF and otherwise HTML (`webhook/app.py:3098-3108`); its prior
   full-manifest verification means an unselected sealed guide mutation still
   blocks. The current negative test names HTML but not PDF. This is a coverage
   gap, not a code gap.
5. **The N1 quarantine is integrated with normal operations.** It uses the same
   order-scoped state, state-aware coach notification, status endpoint, download
   gate, and transition policy as generated orders. Minimal notification is
   acceptable in Phase 1; authority is durable and non-waivable.

## No-regression check

| Prior item | R3 result |
|---|---|
| **R1 B3 — schema-v1 quarantine** | **No regression.** Migration remains write-new/verify/tombstone-old, legacy state grants no release authority, and transition/confirm reject it even after binding (`webhook/fulfillment_state.py:600-603,685-709,712-795`; `webhook/tests/test_fulfillment_state.py:263-288`). |
| **R1 B4 — persistence failure false success** | **No regression.** No durable return forces pipeline/job failure, while only a successfully persisted quarantine becomes workflow success (`webhook/app.py:2281-2355`; `webhook/tests/test_webhook.py:3013-3042`). |
| **R1 B7 — unknown device tokens** | **No regression.** The parser retains unknown tokens verbatim and creates required confirmations (`athletes/scripts/intake_to_plan.py:536-575,3172-3180`). |
| **R1 B8 — download-token fail-closed/revocation** | **No regression.** Issue and verify still require audience-specific configured keys with no `CRON_SECRET` fallback, and durable jti/kid revocation remains enforced (`webhook/download_tokens.py:43-92,95-232`; `webhook/tests/test_download_tokens.py:44-137`). |
| **S6 source-scoped blocker merge** | **Conforms.** Merge still preserves other sources and rejects stale revisions (`webhook/fulfillment_state.py:299-346`); intake and post-render use distinct namespaces (`athletes/scripts/intake_to_plan.py:3564-3569`). |
| **D4 pre-approval Endure network disable** | **No regression in the normal generation job.** `_execute_plan_job` makes no Endure delivery call, and the production orchestration regression asserts zero POST (`webhook/tests/test_endure_delivery.py:545-566`). N4 is a separate post-approval state/confirmation bypass. |
| **F2 fueling truth / F3 polyline / F6 weeks mismatch / F7 intel stats** | **No static regression found.** Athlete-m still traverses production fueling and guide assertions (`athletes/scripts/test_athlete_m_phase1.py:52-167`); F3's implementation remains untouched; final intake still emits the weeks mismatch; and the bounded/deterministically sorted intel route was not changed by the R2-closure commits. |

No archetype ID, race mapping, plan-catalog, methodology, or workout-catalog
contract was changed by these commits.

## Unverifiable items

1. I did not execute the full or socket-dependent suite and make no independent
   pass/skip claim. The supplied 2357/86/0 result cannot prove absent adversarial
   cases.
2. I did not execute the browser driver or any live TrainingPeaks, Endure,
   Stripe, WooCommerce, Railway, Resend, or SMTP action. The driver findings
   follow its explicit data flow and request ordering.
3. I could not dynamically force regeneration or seal mutation in the
   gate-response/first-write interval. The race is statically present because
   authorization response and remote write are distinct awaits with no lease or
   lock spanning them.
4. I did not verify deployed `CRON_SECRET`, download-token keyrings, token
   revocation-store durability, CORS/proxy behavior, or filesystem permissions.
   Checked-in missing-secret behavior is fail-closed.
5. I did not validate live TP receipt semantics or whether TP APIs provide a
   server-side idempotency primitive. Those are later-phase/live-proof concerns;
   Phase 1 can close safely by keeping the driver disabled.

## Summary

The R2 remediation closes B2, B5, B6, B9, N1, N2, and the direct N3 platform
confusion, but the Phase 1 gate is still **NO-GO**. “Blocked means blocked” is
durable for intake/validator/seal blockers and customer downloads, yet it is not
an end-to-end invariant across every reachable release surface: the TP browser
driver can apply mutable, unsealed job bytes after a release-only gate and can
race revocation, while Endure can be falsely advanced and customer-confirmed
despite being disabled. Hard-disabling those pre-worker apply/confirm surfaces
is a Phase 1-conformant closure; otherwise their exact executable bytes,
platform evidence, and final authorization boundary require production-path
negative proof.

# Phase 3 implementation adversarial review — Codex R1

Date: 2026-08-08  
Branch reviewed: `build/trustworthy-phase3` at `3af452e`  
Comparison base: `build/trustworthy-phase2` at `6952021` (the second parent of `d8cb3e1`)

## Verdict

**NO-GO.** The implementation has **9 blockers**. The normal suite is green, and the
power-plan ZWOs are byte-identical to fresh Phase 2 output, but those facts do not
close the Phase 3 contract. The persisted “canonical” model is still compiled from
ZWO, null-power intake mishandles numeric edge cases, the preview applies power-IF
math to HR/RPE targets, sensitive approved values escape through a non-review API,
and `apply_contract/v1` cannot consume the normative effective-inventory shape it is
specified to diff.

The implementation notes are therefore not reliable as release evidence. In
particular, the claims at `docs/reviews/PHASE3_IMPLEMENTATION_NOTES.md:16-19`,
`:48-50`, `:61-64`, `:78-85`, and `:279-293` are contradicted by the shipped code or
tests.

## Blockers

### 1. The canonical training model is downstream of ZWO and is not the upstream authority for all rendering

**Claim.** A1.1 requires a metric-neutral model upstream of ZWO, PlanIR, preview,
apply-contract, guide, and polyline. The implementation instead authors ZWO first,
reflects it through PlanIR, and only then writes the canonical model. The guide also
does not consume the canonical model.

**Evidence.** `athletes/scripts/generate_athlete_package.py:3140-3167` calls
`generate_zwo_files()` before `build_canonical_model()`. The latter explicitly says
it bootstraps through the authored workout shape and calls PlanIR with
`prefer_canonical=False` (`athletes/scripts/canonical_training_model.py:240-258`).
PlanIR still describes itself as a non-authoring aggregation that is not an input to
ZWO, guide, or fueling (`athletes/scripts/plan_ir.py:1-6`). The guide is rendered
after canonicalization, but `training_guide_builder.py:384-435` reads profile,
derived, schedule, and plan configuration rather than the canonical artifact; its
only Phase 3 hook is a regex-based text rewrite at
`athletes/scripts/training_guide_builder.py:4176-4185`.

The canonical validator is also not an exact discriminated-union validator. It
checks only the `type` discriminator and that some additional key exists
(`athletes/scripts/canonical_training_model.py:390-406`); mixed or forbidden target
members are accepted. No negative test asserts one exact target shape per segment.

**Why it blocks.** A1.1 calls this architecture a prerequisite. A reflected artifact
cannot establish that ZWO and guide are projections of a single metric-neutral
authority. The current arrangement can preserve legacy bytes, but it cannot prevent
the published source and the purported canonical source from diverging.

**Minimal fix.** Create/finalize the metric-neutral session model before publication,
render ZWO and guide from that object, and validate targets with an exact per-type
union (including forbidden fields). Add round-trip tests proving every published
projection is derived solely from the same canonical input.

### 2. Numeric FTP edge cases either kill a recoverable paid order or fabricate a measured anchor

**Claim.** The null-FTP path works for a short allowlist of strings such as
`unknown`, but not for classic numeric edge cases.

**Evidence.** `parse_watts()` extracts any unsigned digit run
(`athletes/scripts/intake_to_plan.py:465-470`). Consequently `-200` becomes positive
`200`; this behavior is positively pinned by
`athletes/scripts/test_intake_to_plan.py:1142-1146`. A supplied `0` becomes
`ftp_watts: 0` and `power_basis: measured` because basis selection uses `is not None`
(`athletes/scripts/intake_to_plan.py:905-916`), then the sanity gate exits the whole
order for being below 50 W (`athletes/scripts/intake_to_plan.py:177-200` and
`:3594-3600`). Meanwhile downstream control selection uses truthiness for the same
anchor (`athletes/scripts/canonical_training_model.py:44-70`). Tests cover named
unknown strings and ordinary positive numbers, but not `0`, signed, malformed, or
out-of-range intake through the paid-order path
(`athletes/scripts/test_intake_to_plan.py:2134-2168`).

**Why it blocks.** `-200` is presented as a measured 200 W fact, violating I1 and
A1.2. `0` hard-fails a field that can safely become `None`, violating the repository's
paid-order safety rule and A1.2's required no-power confirmation path.

**Minimal fix.** Parse the whole signed numeric token, accept only a plausible
positive measured anchor, and degrade invalid/zero/out-of-range values to
`ftp_watts: null`, `power_basis: none`, plus coach-visible confirmation/provenance.
Add paid-order tests for `0`, negative, malformed, and implausible values.

### 3. The zone-accounting repair applies power IF thresholds to HR and RPE targets

**Claim.** The b74826d calculation is defensible for legacy power-plan parity, but it
is not one truthful definition “for every order and control metric,” as the notes
claim.

**Evidence.** `_canonical_intensity_factor()` fourth-power-weights raw power, LTHR,
HRmax, and scaled-RPE ratios identically (`athletes/scripts/generate_plan_preview.py:50-100`),
then `_if_to_zone()` applies power IF thresholds to all of them (`:34-47`, `:148-158`).
For a conventional endurance source segment of 55-75% FTP, the LTHR projection is
68-83% LTHR (`athletes/scripts/canonical_training_model.py:94-101`, `:118-159`). The
preview takes the mean, 0.755, and labels it power zone Z3 because the Z2 cutoff is
0.75. I reproduced exactly:

```text
target {'type': 'pct_lthr', 'low': 0.68, 'high': 0.83}
preview_effort 0.755 preview_zone Z3
```

The new regression test proves only power ZWO/IF equivalence
(`athletes/scripts/test_plan_preview.py:120-143`). It has no LTHR, HRmax, or RPE
classification case. The resulting zone is used by the release-facing methodology
check (`athletes/scripts/generate_plan_preview.py:337-383`).

**Why it blocks.** Percent LTHR, percent HRmax, RPE, and normalized power IF are not
interchangeable physiological scales. This can turn easy LTHR sessions into hard
sessions and create false PASS/WARN/FAIL review signals for the exact null-power
athletes Phase 3 introduces.

**Minimal fix.** Define metric-specific effort normalization/zone classification
against the canonical target type (or compare a truly metric-neutral authored zone),
then add LTHR, HRmax, RPE, free-ride, ramp, and interval regressions. Retain the
duration-weighted whole-session unit only if the methodology target is explicitly in
that same unit.

### 4. The required HR/LTHR, HRmax, and RPE “every artifact” fixtures do not exist

**Claim.** A1.1 explicitly requires each offline no-power fixture to assert zero watt
figures in every artifact, the appropriate Week 1 field test, and a re-anchor point.
The three fixtures exercise only canonical JSON, PlanIR, and TP manifest.

**Evidence.** `athletes/scripts/test_truthful_power.py:36-60` creates a profile,
fueling stub, dates, and one temporary ZWO. The test then serializes only canonical,
PlanIR, and TP objects for the watt grep (`:63-89`). It never generates or inspects
the training guide, preview, coaching brief, plan summary, release manifest, review
bundle, or customer bundle. Athlete M does grep generated JSON/YAML/HTML/Markdown
artifacts (`athletes/scripts/test_athlete_m_phase1.py:73-124`), but it is only the
pending-HR/RPE fallback case; it is not the LTHR and HRmax fixture required by A1.1.

**Why it blocks.** This is an explicit normative acceptance condition, and the most
likely watt-leak surfaces—the legacy guide and preview—are precisely the surfaces the
three control fixtures omit.

**Minimal fix.** Run all three control cases through production package generation,
sealing, review/customer bundle construction, and all textual/PDF-extractable
artifacts; assert zero numeric watts/%FTP, the exact field-test type, and serialized
re-anchor evidence in every relevant output.

### 5. The derived-value registry is neither complete nor revisioned at its source

**Claim.** A3 and I1 require every derived value to carry provenance and the current
revision. Only a small hand-picked subset is registered, and source entries silently
default to revision 1.

**Evidence.** `derived_registry.entry()` defaults every entry to revision 1
(`athletes/scripts/derived_registry.py:36-56`). `registry_document(revision=...)`
sets only the document revision and does not update entry revisions (`:93-100`); its
test requests document revision 3 but never checks the entry revision
(`athletes/scripts/test_derived_registry.py:22-28`). Production callers do not pass a
revision—for example intake at `intake_to_plan.py:1756-1829`, fueling at
`calculate_fueling.py:555-584`, and canonical at
`canonical_training_model.py:355-379`. The server later overwrites only its
materialized state copies (`webhook/fulfillment_state.py:576-590`), leaving the
owning artifact's `_derived` record at revision 1.

Completeness is also absent. Fueling derives calories, carbohydrate ranges, weekly
gut progression, timeline, hydration, and recommendations
(`athletes/scripts/calculate_fueling.py:470-548`) but registers only duration,
hourly carbs, and total carbs (`:555-584`). The review-bundle plan summary derives
plan dates, methodology score/tier, ability, and fueling summaries with no `_derived`
registry at all (`athletes/scripts/generate_athlete_package.py:3184-3216`; inclusion
in the review bundle is `webhook/app.py:1798-1805`). No coverage test inventories
derived output fields against registry entries.

**Why it blocks.** This directly violates A3's revision requirement and I1's “every
derived value” invariant. A coach cannot review the basis/source of numerous
athlete-facing computed values, and a regenerated source artifact can falsely claim
revision 1 while state claims revision 2+.

**Minimal fix.** Make the generation revision mandatory at registry construction,
stamp it into every source entry, enumerate all computed athlete/review-facing
fields, and add a coverage test that fails when a derived output lacks an exact
field/basis/input/sensitivity record.

### 6. Sensitive derived values leak through the post-approval status API

**Claim.** A3 permits sensitive typed values only in the authenticated review page
and server-side state. The non-review status API redacts live review items but returns
their unredacted approval snapshots.

**Evidence.** Derived values become typed review items with their value and
sensitivity (`webhook/fulfillment_state.py:278-298`). Approval copies every complete
review item, including `value`, into `approval.confirmations`
(`webhook/fulfillment_state.py:1144-1200`). The status endpoint correctly redacts
`review_items`, blockers, and confirmations, but returns `state['approval']` raw
(`webhook/app.py:3242-3263`). `redact_sensitive_review_items()` handles only a list
of directly sensitive items and is not applied recursively to approval evidence
(`webhook/fulfillment_state.py:113-121`). Existing A3 tests cover the helper and a
notification, not an approved status response
(`webhook/tests/test_phase3_derived_catalog.py:37-58`).

**Why it blocks.** After approval, weight, FTP, W/kg, carbohydrate targets, and other
sensitive verified facts can be returned outside the authenticated review page. This
is the exact boundary A3 says MUST be enforced, not decorated.

**Minimal fix.** Build one recursive external-state projection that redacts sensitive
values in live and archived approval/waiver/application evidence, and test the real
post-approval status response with a seeded secret.

### 7. `apply_contract/v1` cannot consume the normative effective-inventory schema

**Claim.** D0's exact inventory entry contains `payload_snapshot_ref`, not an inline
`payload`. The contract builder ignores the reference and requires a non-normative
inline payload for dated updates and deletes.

**Evidence.** The binding schema is
`{remote_id, desired_digest, payload_snapshot_ref, kind, last_op_id}`
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:603-615`). The builder reads
`inventory_record.get('payload')` for update/delete compensation and throws when it
is absent (`athletes/scripts/apply_contract.py:317-322`, `:350-359`). There is no
production resolver for `payload_snapshot_ref`. The supersession test masks the
problem by adding illegal inline `payload` fields to both inventory entries
(`athletes/scripts/test_apply_contract.py:120-141`). A direct probe using the exact
normative five-field inventory failed with:

```text
ApplyContractError: dated update requires copied prior payload
```

**Why it blocks.** A Phase 4 inventory produced exactly as specified cannot generate
the required update/delete contract or embed `prior_payload`; supersession fails
before any apply is possible.

**Minimal fix.** Validate inventory records against the exact schema, resolve each
immutable `payload_snapshot_ref` through an explicit snapshot reader supplied to the
offline builder, copy the canonical payload into `prior_payload`, and delete support
for inline inventory payloads. Test both update and delete from exact inventory
records.

### 8. Attachment logical IDs violate D0's exact stable identity formula

**Claim.** D0 defines an attachment logical key as
`{parent_logical_key}:{filename}`. The implementation inserts the parent's full
logical ID into the child key and then prefixes the child again.

**Evidence.** `athletes/scripts/apply_contract.py:261-272` selects a full workout
`logical_id` as `parent`, forms `logical_key = f"{parent}:{filename}"`, then calls
`_logical_id()` again. The resulting probe value was:

```text
cs_phase3:attachment_upsert:cs_phase3:workout_upsert:2026-08-14#1:guide.html
```

The normative identity is
`cs_phase3:attachment_upsert:2026-08-14#1:guide.html`. The identity test asserts only
cross-revision stability and marker presence, not the per-kind exact key
(`athletes/scripts/test_apply_contract.py:60-71`). Semantic validation merely
reconstructs whatever suffix was already supplied and never validates per-kind key
grammar (`athletes/scripts/apply_contract.py:395-415`).

**Why it blocks.** `logical_id` is the reconciliation and supersession key. Using a
different public identity formula creates incompatible inventory and marker records
before the first apply.

**Minimal fix.** Carry `parent_logical_key` separately from
`parent_logical_id`; use the former in the attachment key and the latter only in the
payload. Add literal identity fixtures and per-kind logical-key validation.

### 9. The mandatory legacy-to-D0 remote-effect parity gate is not actually a parity test

**Claim.** D0 requires equivalent remote effects per legacy operation class. The
normal-suite test checks counts and one workout structure/description; the socket
test posts arbitrary JSON to list buckets and compares only selected fields.

**Evidence.** `athletes/scripts/test_apply_contract.py:144-164` compares class counts,
calendar dates, and one new payload to its source IR; it does not execute or normalize
legacy and new effects. The socket test's fake server accepts any JSON and deduplicates
only `external_id` (`athletes/scripts/test_trainingpeaks_adapter.py:21-52`). Its
assertions compare counts, workout dates, note titles, attachment filename, mental
text, and entitlement ID (`:128-151`), omitting the rest of each remote field set and
all update/delete/keep behavior. It is also skipped in this sandbox because loopback
sockets are forbidden.

For example, the tested legacy workout carries `workout_type`, `duration_s`,
`segments`, `sport`, and origin metadata, while D0 carries `tp_workout_type`,
`total_seconds`, TSS, description, and TP-native structure. The test never defines
and compares the normalized remote object those two projections are meant to create.

**Why it blocks.** The normative parity MUST is unproven. Shallow cardinality parity
cannot establish that no operation class or field semantics were lost during the
contract migration.

**Minimal fix.** Implement a field-aware fake remote model/adapters for both legacy
and D0 inputs; compare complete normalized remote state for every operation class,
including create/update/delete/keep, adopted positional resources, attachments, and
entitlements. Run the socket variant in a CI environment that permits loopback.

## Normative MUST inventory

The following table enumerates the Phase 3 MUSTs in A1, A3/I1, D0, and fueling. A
“pass” means I found both enforcement and a relevant test; “blocker” points to the
numbered release defect above.

| Normative requirement | Enforcement | Test/evidence | Result |
|---|---|---|---|
| Canonical metric-neutral model is upstream of every rendering/projection | `generate_athlete_package.py:3140-3177`, `canonical_training_model.py:233-275` | No upstream-authority test | **Blocker 1** |
| Exactly one typed target (`power_pct_ftp`, `pct_lthr`, `pct_hrmax`, `rpe`, `free`) per segment | `_segment_target`, `canonical_training_model.py:132-162`; weak validator at `:390-406` | Positive types only at `test_truthful_power.py:63-75` | **Blocker 1** |
| Plan control derives from power basis and HR markers | `canonical_training_model.py:42-80` | `test_truthful_power.py:63-75` | Pass, subject to Blocker 2 input handling |
| ZWO emitted only for measured-power control | `canonical_training_model.py:384-387`; temporary authoring at `generate_athlete_package.py:3148-3167` | `test_truthful_power.py:76`; athlete M `test_athlete_m_phase1.py:116` | Pass |
| LTHR/HRmax use TP-native target types; RPE is description-only | `canonical_training_model.py:415-455`; PlanIR projection | `test_truthful_power.py:78-89` | Pass offline |
| No Phase 3 worker/live TP acceptance claim | No worker added; offline contract module has no network imports | `test_apply_contract.py:167-171` plus manual diff | Pass |
| HR/LTHR, HRmax, RPE fixtures grep every artifact and prove field test/re-anchor | Partial fixtures only | `test_truthful_power.py:36-89` | **Blocker 4** |
| FTP estimation deleted; `power_basis` measured/none; FTP nullable | `intake_to_plan.py:905-916` | Unknown-string cases at `test_intake_to_plan.py:2134-2221` | **Blocker 2** for numeric invalids |
| Preview is null-safe | `generate_plan_preview.py:124-135` | Athlete M replay/full suite | Pass for `None`; metric truth fails under **Blocker 3** |
| `power_basis:none` is a confirmation, not a blocker | `intake_to_plan.py:3331-3345` | `test_athlete_m_phase1.py:161-163` | Pass |
| Null-power fueling uses duration/intensity/body-mass bounds only | `fueling_policy.py:93-155`; `calculate_fueling.py:480-542` | `test_athlete_m_phase1.py:109-115` | Pass |
| Null-power fueling computes/serializes no watts/work-rate/kJ and unsafe missing mass defers | `fueling_policy.py:124-155` | Athlete M null-power assertions | Pass for tested production fixture |
| No-power guide copy omits numeric watts | Regex guard at `canonical_training_model.py:177-192`, called by guide `:4176-4185` | One Athlete M grep, not all control fixtures | **Blocker 4** acceptance gap |
| `FTP_ESTIMATED` remains non-waivable | `webhook/fulfillment_state.py:47-70`, `intake_to_plan.py:3273-3285` | `test_fulfillment_state.py:197-205`, `test_review_surface.py:347-359` | Pass |
| Every derived value records field/class/basis/inputs/sensitivity/time/current revision and reaches review | Shape validation `derived_registry.py:36-90`; partial materialization | `test_derived_registry.py:22-36`, `test_phase3_derived_catalog.py:23-34` | **Blocker 5** |
| Sensitive values are absent from every non-review surface; checklist uses seeded secrets | Redaction helper `fulfillment_state.py:113-121` | Helper/email only at `test_phase3_derived_catalog.py:37-58` | **Blocker 6** |
| Checked JSON Schema is generated/equivalent and every contract validates | `apply_contract.py:155-207` | `test_apply_contract.py:50-57` | Pass |
| Exact envelope and unknown-reader rejection | Schema constants at `apply_contract.py:160-175` | Schema negative test/full suite | Pass |
| Exact stable logical ID, revision op ID, and kind-limited marker | `apply_contract.py:210-212`, `:370-376` | `test_apply_contract.py:60-71` | **Blocker 8** for attachment key |
| Exact common fields, kind/disposition matrix, payload schemas, digests, predecessors, rollback | Generated operation branches and `PAYLOAD_SCHEMAS`, `apply_contract.py:48-187`, `:295-377` | Schema/position/supersession tests | Pass for accepted inputs |
| Effective inventory has the exact five-field shape and supplies immutable prior-payload snapshots | No exact inventory validator/resolver; inline `payload` read at `apply_contract.py:317-359` | Test supplies non-normative inline payload | **Blocker 7** |
| Every inventory ID has exactly one operation and exact predecessor | `apply_contract.py:395-427`, `:460-486` | Subsequent singleton/entitlement tests | Pass only once non-normative inventory is accepted; **Blocker 7** prevents dated supersession |
| Ordering: singleton; supersession; dated dependency order; entitlement last | `_sort_key`, `apply_contract.py:380-392` | Contract tests/full suite | Pass for generated fixtures |
| Supersession embeds prior payload and never dereferences an earlier contract at apply time | `_operation`, `apply_contract.py:303-377` | `test_apply_contract.py:120-141` | **Blocker 7** |
| All pinned legacy operation classes retained with equivalent fake-server effects | D0 emits seven kinds | Shallow count/selected-field tests only | **Blocker 9** |
| First/subsequent adopted singleton and pre-existing entitlement branches covered | Contract builder and schema | `test_apply_contract.py:74-117` | Pass |
| JS driver remains review-excluded until parity; no live execution surface | Top-level JS throw, Python job/runbook hard fail, adapter unconditional raise | `tools/test_tp_apply_order.py:422-434`, `test_trainingpeaks_adapter.py:71-79` | Pass |

## Non-blocking findings

1. **The “no golden plan content changed” claim is correct.** I generated Phase 2
   from a fresh `git archive build/trustworthy-phase2`, ran the same acceptance
   generator, and compared relative path plus SHA-256 for every ZWO. Phase 2 and
   Phase 3 were byte-identical for all four orders: gravel-fullgym 89, masters 77,
   roadie-fondo 41, roadie-climber 46; **253/253 files identical**, with no added or
   removed paths. Commit b74826d itself changes only preview code/tests. For power
   plans, its duration-weighted fourth-power session calculation is defensible as a
   projection matching the former ZWO parser and is covered by
   `test_plan_preview.py:120-143`. The notes become wrong when they generalize that
   power-calibrated definition to every control metric; that part is Blocker 3.

2. **No live TrainingPeaks path was re-enabled on this branch.** The three named
   driver files have no diff from Phase 2. `tools/tp_apply_driver.js:1-6` throws
   before installing globals or networking; `tools/tp_apply_order.py:225-229`,
   `:313-322` refuses job/runbook/job-mode construction; and
   `delivery/trainingpeaks/adapter.py:71-76` raises before historical code. The new
   `athletes/scripts/apply_contract.py:1-18` imports no HTTP/browser library and has
   no execution entry point. I made no live TP, browser-session, worker, email,
   Stripe, or external-network call.

3. **Phase 1/2 release invariants did not regress in the inspected paths.** Approval
   requires a sealed release (`webhook/fulfillment_state.py:1083-1097`) and rechecks
   the release bytes before recording approval (`:1182-1200`). The customer download
   rejects unapproved state (`webhook/app.py:2870-2919`); the review bundle contains
   only the non-executable allowlist (`webhook/app.py:1798-1805`, `:2084-2090`).
   Download tokens bind order, athlete, revision, artifact, and audience
   (`webhook/download_tokens.py:96-145`, `:169-221`). The focused invariant suite was
   66/66 passing.

4. **I did not find numeric watt leakage in the Athlete M production replay or a
   watts/work-rate/kJ input in its null-power fueling.** The production null branch
   in `fueling_policy.py:124-155` does not compute watts. The `ftp or 200.0` at
   `plan_ir.py:415-424` is used only by the historical ratio-only ZWO metrics parser
   and is not serialized as an athlete fact. It is still evidence of why canonical
   authoring should not depend on ZWO, but it is not itself a fabricated published
   FTP.

5. **The sensitivity labels on the entries that do exist are generally conservative.**
   Weight, FTP, W/kg, control basis with raw HR markers, and fueling targets are
   labeled `sensitive`; I did not find a clearly under-labeled registered entry. The
   defects are incomplete coverage (Blocker 5) and broken external projection
   enforcement (Blocker 6), not an obviously wrong label on the small registered set.

6. **The implementation notes' verification count before the acceptance fixes is
   stale, but the closure count is reproducible.** The current normal suite is 2,419
   passed / 87 skipped, matching `PHASE3_IMPLEMENTATION_NOTES.md:240`, not the earlier
   2,416 claim at `:160-163`.

## What I verified and how

### Repository and diff

- Read `CLAUDE.md`, `.claude/skills/order-safety/SKILL.md`,
  `.claude/skills/generator-conventions/SKILL.md`, and
  `.claude/skills/archetype-and-catalog/SKILL.md` before reviewing the paid-order,
  generator, and catalog paths.
- Reviewed every file in `git diff build/trustworthy-phase2...HEAD`, including the
  post-merge commits b74826d, dcd9efb, and 3af452e.
- `git diff --check build/trustworthy-phase2...HEAD` — pass.
- `python3 -m compileall -q athletes/scripts delivery tools webhook` — pass.

### Test commands and results

From repository root:

```text
python3 -m pytest -q --disable-warnings --maxfail=25
```

Result: **2,419 passed, 87 skipped, 21 warnings, 0 failed** in 20.13 s.

Focused Phase 3 suite, from `athletes/scripts`:

```text
python3 -m pytest test_truthful_power.py test_apply_contract.py \
  test_derived_registry.py test_trainingpeaks_adapter.py \
  ../../webhook/tests/test_phase3_derived_catalog.py -q -rs
```

Result: **20 passed, 1 skipped**. The skip is the loopback fake-TP test.

Focused Phase 1/2 state/review/token regression suite, from repository root:

```text
python3 -m pytest webhook/tests/test_fulfillment_state.py \
  webhook/tests/test_review_surface.py webhook/tests/test_download_tokens.py -q
```

Result: **66 passed, 0 skipped, 0 failed**.

Required acceptance command, from `athletes/scripts`, with a writable HOME and the
original user site preserved so pytest/MarkupSafe remain importable:

```text
review_home=$(mktemp -d /private/tmp/gg-phase3-home-rs.XXXXXX)
HOME="$review_home" \
PYTHONPATH="/Users/mattirowe/Library/Python/3.14/lib/python/site-packages${PYTHONPATH:+:$PYTHONPATH}" \
GG_RUN_ACCEPTANCE=1 python3 -m pytest test_order_acceptance.py -q -rs
```

Result: **36 passed, 4 skipped, 4 failed** in 10.77 s. Two skips are the expected
Roadie-only package contract cases; two are PDF-optional cases. All four failures are
the two mandatory-PDF existence/structure assertions for gravel-fullgym and masters.
Chrome was found, but the sandbox killed headless Chrome with exit 134 before it
could emit a PDF. The same four PDF-only failures occurred when running the freshly
archived Phase 2 tree (**36 passed, 4 skipped, 4 failed**), so this does not show a
Phase 3 regression, but those four acceptance assertions are not verified here.

### Independent ZWO identity check

I did not reuse the notes as authority. I created a fresh tree with:

```text
phase2_dir=$(mktemp -d /private/tmp/gg-phase2-r1.XXXXXX)
git archive build/trustworthy-phase2 | tar -x -C "$phase2_dir"
```

I ran Phase 2's acceptance generator there, then built maps of
`relative ZWO path -> SHA-256` for the four Phase 2 and Phase 3 athlete directories.
Results:

| Fixture | Phase 2 ZWOs | Phase 3 ZWOs | Added/removed/changed |
|---|---:|---:|---:|
| `acc-gravelrider` | 89 | 89 | 0 / 0 / 0 |
| `acc-mastersrider` | 77 | 77 | 0 / 0 / 0 |
| `acc-roadiefondo` | 41 | 41 | 0 / 0 / 0 |
| `acc-roadieclimber` | 46 | 46 | 0 / 0 / 0 |
| **Total** | **253** | **253** | **0 / 0 / 0** |

### Adversarial probes

- Built revision 2 from an exact five-field normative dated inventory entry with a
  `payload_snapshot_ref` and no inline payload: reproduced
  `ApplyContractError: dated update requires copied prior payload`.
- Printed the emitted attachment identity: reproduced the nested parent full-ID
  defect in Blocker 8.
- Projected a 55-75% endurance segment to LTHR, ran the canonical preview classifier,
  and reproduced 68-83% LTHR -> 0.755 -> Z3.
- Compared the three TP driver paths against Phase 2: no branch diff; manually
  inspected each hard-stop before unreachable historical network code.

## What I could not verify in this sandbox

1. **Four mandatory PDF acceptance assertions.** Headless Chrome/Chromium exits 134
   under the managed sandbox's process/Mach restrictions. A writable HOME did not
   overcome that restriction, and WeasyPrint/wkhtmltopdf are not installed. I did
   not fake PDFs or weaken the test. Phase 2 fails the same four assertions here.
2. **The loopback fake-TP parity test.** Binding `127.0.0.1` is forbidden, so pytest
   skips `test_trainingpeaks_adapter.py:82`. Independently, Blocker 9 shows that its
   assertions would still be too shallow to meet normative remote-effect parity.
3. **Any live TrainingPeaks behavior.** Phase 3 is required to remain offline, so I
   intentionally did not attempt identity binding, live HR/RPE acceptance, marker
   round-trip, apply, readback, rollback, or worker canary checks.
4. **The already-pending Phase 2 human live-page gate.** It is outside this code-only
   Phase 3 review and remains a separate release prerequisite.

## Final disposition

**NO-GO — 9 blockers.**

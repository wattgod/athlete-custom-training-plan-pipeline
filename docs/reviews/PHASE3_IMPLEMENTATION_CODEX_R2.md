# Phase 3 implementation adversarial review — Codex R2

Date: 2026-08-08
Branch reviewed: `build/trustworthy-phase3` at `21b5c0f`
Round-1 baseline: `cd85db5`
Phase-2 comparison: `build/trustworthy-phase2`

## Verdict

**NO-GO. Five blockers remain.**

The four fix commits materially improve the implementation. The canonical model is
now finalized before any ZWO is published, invalid numeric FTP inputs degrade to the
truthful no-power path, LTHR/HRmax/RPE targets are normalized on their own scales,
the production no-power fixtures traverse both bundles, the exact five-field
inventory can resolve update/delete snapshots, the emitted attachment ID is now
literal-contract correct, and the post-approval status response recursively redacts
the seeded sensitive value.

Those fixes do not close the whole R9 contract. The derived registry still covers
only a caller-declared subset and omits entire production-derived artifacts; failure
notifications still emit sensitive FTP/weight values; inventory validation accepts
a dated record with the snapshot reference that D0 forbids from being null;
attachment identity validation does not bind the key to the payload; and the new
parity model still does not model the legacy adapter's real remote effects.

## R1 blocker closure

| R1 blocker | Status | Evidence |
|---|---|---|
| 1. Canonical model was downstream of published ZWO | **Closed** | Production authors into a private temporary directory, builds and validates the canonical model, and only then publishes ZWO (`athletes/scripts/generate_athlete_package.py:3145-3177`). Canonical construction consumes the in-memory document inventory (`athletes/scripts/canonical_training_model.py:396-441`), exact target-union validation is at `:592-636`, and ZWO bytes are rendered solely from canonical sessions at `:658-747`. PlanIR loads canonical at `athletes/scripts/plan_ir.py:672-674`; preview loads canonical at `athletes/scripts/generate_plan_preview.py:139-164`; the guide receives canonical explicitly at `athletes/scripts/training_guide_builder.py:3917-3931,4193-4200`. The round-trip regression is `athletes/scripts/test_truthful_power.py:133-203`. The compiler input is still XML-shaped, but it is private and pre-publication; poisoning/deleting a published ZWO no longer changes any session projection. |
| 2. Numeric FTP edges killed/fabricated orders | **Closed** | Whole-token signed parsing and finite/bounded acceptance are at `athletes/scripts/intake_to_plan.py:466-487`. The paid-order `0`, `-200`, partial, and implausible cases assert null FTP, no W/kg, valid sanity, and `POWER_BASIS_NONE_CONFIRM` at `athletes/scripts/test_intake_to_plan.py:2167-2180`. |
| 3. Power IF thresholds were applied directly to HR/RPE | **Closed** | Per-target normalization is at `athletes/scripts/canonical_training_model.py:119-147`; preview normalizes before duration/fourth-power weighting at `athletes/scripts/generate_plan_preview.py:50-100`. LTHR, HRmax, RPE, ramp, interval, and free regressions are at `athletes/scripts/test_plan_preview.py:145-180`. The R1 LTHR probe now returns `0.68-0.83 -> 0.65 -> Z2`. Power behavior remains pinned by `test_plan_preview.py:120-143` and the independent ZWO manifest below. |
| 4. No production every-artifact HR/LTHR, HRmax, RPE fixtures | **Closed, except sandbox PDF execution** | The three cases run the webhook subprocess, persistence/sealing, review ZIP, and customer ZIP at `athletes/scripts/test_metric_neutral_packages.py:64-122`; they assert field-test/re-anchor identity and no customer ZWOs at `:124-139`. I reran all three and independently scanned 141 retained textual artifacts: no numeric watts or `%FTP` match. PDF text is conditional at `:52-57`; this sandbox could not create the mandatory PDFs. |
| 5. Derived registry incomplete and source revisions stale | **Not closed** | Entry revision is now mandatory (`athletes/scripts/derived_registry.py:36-58`) and normal paid-order execution stamps its prospective revision (`athletes/scripts/intake_to_plan.py:3612-3627`). However, coverage trusts the caller's own `required_fields` list and ignores every undeclared output (`derived_registry.py:108-133`). Entire computed documents remain unregistered (`derive_classifications.py:338-375`; `select_methodology.py:520-533`), and state materialization includes only profile/fueling/summary/canonical (`generate_athlete_package.py:3333-3343`). See Blocker 1. |
| 6. Sensitive values leaked through post-approval status | **Partially closed** | The specific R1 status leak is closed: status includes archived evidence then projects the full response recursively (`webhook/app.py:3242-3276`); the recursive policy is `webhook/fulfillment_state.py:113-149`; the real seeded post-approval endpoint test is `webhook/tests/test_phase3_derived_catalog.py:69-103`. The authenticated review page continues to consume raw server state, so it is not over-redacted. But production failure notification/log fallback still emits sensitive FTP and weight. See Blocker 2. |
| 7. D0 could not consume the normative five-field inventory | **Partially closed** | Exact key-set validation is at `athletes/scripts/apply_contract.py:317-340`; dated update/delete snapshot resolution, schema validation, and digest verification are at `:343-360`; exact update/delete tests are `athletes/scripts/test_apply_contract.py:139-187`. The verbatim R1 five-field update/delete probe passes. The validator nevertheless accepts a forbidden null dated snapshot on a keep. See Blocker 3. |
| 8. Attachment logical identity was nested incorrectly | **Partially closed** | Builder output is now exactly `order:attachment_upsert:date#ordinal:filename`, with parent key and ID carried separately and checked during construction (`athletes/scripts/apply_contract.py:266-286`); the literal fixture is `athletes/scripts/test_apply_contract.py:61-90`. The emitted R1 identity defect no longer reproduces. Loaded-contract validation checks only key regex and payload digest, however, not attachment key/payload correspondence (`apply_contract.py:466-499`). See Blocker 4. |
| 9. Legacy-to-D0 parity was shallow sampling | **Not closed** | The new fake model is field-aware only over a synthetic field set (`athletes/scripts/fake_remote_parity.py:24-61,78-103`). It does not model the disabled legacy adapter's actual payload or supported operations (`delivery/trainingpeaks/adapter.py:78-108`). See Blocker 5. |

## Blocking findings

### 1. A3 coverage remains self-declared and omits production-derived artifacts

**Claim.** The new coverage helper does not detect a newly added derived output
unless the same caller also remembers to add that output to `required_fields`.
Several production artifacts made entirely of computed values carry no `_derived`
registry at all.

**Evidence.** `assert_registry_covers()` compares records only to the supplied
`required_fields`; it never derives the inventory from the document schema or
rejects undeclared document fields (`athletes/scripts/derived_registry.py:108-133`).
This direct probe passed:

```text
document = {'x': 1, 'new_computed_output': 8675309}
required_fields = ['x']
result: undeclared_computed_output_accepted
```

The production classification artifact computes tier, plan weeks, starting phase,
strength frequency, equipment tier, risks, exclusions, and candidate days with no
registry (`athletes/scripts/derive_classifications.py:338-375`). Methodology likewise
computes selection, score, confidence, configuration, and alternatives, then writes
the unregistered document (`athletes/scripts/select_methodology.py:520-533,576-582`).
The production state catalog materializes only profile, fueling, plan summary, and
canonical records (`athletes/scripts/generate_athlete_package.py:3333-3343`), omitting
`derived.yaml`, `methodology.yaml`, `plan_dates.yaml`, and
`weekly_structure.yaml`. A fresh acceptance package confirmed all four have no
`_derived` registry.

The test called “fails when a derived output lacks provenance” manually puts the
missing field into `required_fields` (`athletes/scripts/test_derived_registry.py:43-49`),
so it does not exercise the actual omission failure mode.

**Why it blocks.** A3 and I1 require every derived value to have reviewable basis,
inputs, sensitivity, time, and current revision. The current catalog still cannot
explain multiple values that shape the plan, guide, preview, and coaching brief.
The claimed enforcement gate can silently miss future additions.

**Minimal fix.** Establish an authoritative per-artifact derived-field schema that
the coverage gate itself enumerates; register the computed fields in the derived,
methodology, calendar, and schedule owners; materialize them into the review
catalog; and add a negative test that adds a computed output without editing any
coverage list and fails.

### 2. Failure notifications and their log fallback still expose sensitive values

**Claim.** Recursive status projection fixed one API, but the A3 external boundary
does not cover every notification/log path.

**Evidence.** Production notification details copy raw FTP and body weight
(`webhook/app.py:992-1005`). The successful Phase-1 notice returns early through the
redacted review-only builder, but the failure branch renders those values directly
in HTML (`webhook/app.py:563-570,651-680`) and plain text (`:682-708`). If email is
unconfigured or sending fails, the same body is written to the critical log
(`webhook/app.py:832-852`). Both FTP and weight are labeled `sensitive` by the
registry (`athletes/scripts/intake_to_plan.py:1800-1807,1846-1862`).

A direct seeded probe returned:

```text
failure_notification_secret_in_text True
failure_notification_secret_in_html True
```

The added test covers only a sensitive blocker passed to the successful generation
email (`webhook/tests/test_phase3_derived_catalog.py:106-115`), not the failure
notification or log fallback. The standalone fueling CLI also still prints
carbohydrate target ranges labeled sensitive (`athletes/scripts/calculate_fueling.py:797-809`).

**Why it blocks.** A3 explicitly requires sensitive values to be absent from
notifications and logs outside the authenticated review page/server state. Failure
paths are first-class production paths in this repository.

**Minimal fix.** Project the complete notification data through a typed external
projection before every success/failure renderer and log fallback, or omit sensitive
facts from those messages entirely. Add seeded tests for the failed-order email,
unconfigured-email critical log, send-failure log, and CLI/export surfaces.

### 3. The “exact” effective-inventory validator accepts an impossible dated record

**Claim.** `_validate_inventory()` enforces the five property names but not D0's
per-kind value constraints.

**Evidence.** The R9 schema permits `payload_snapshot_ref: null` only for keeps of
never-written positional resources (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:609-615`).
The validator accepts null for every kind (`athletes/scripts/apply_contract.py:317-340`).
When a desired dated resource has the same digest, `_operation()` emits a keep
without resolving a snapshot (`:410-414`). This exact probe succeeded without a
snapshot reader:

```text
dated_null_snapshot_accepted keep
predecessor = {'op_id': '...@r1', 'remote_id': 'w-1'}
```

The same validator also permits non-null `remote_id` on positional records even
though positional predecessors normalize it to null (`apply_contract.py:309-340`).

**Why it blocks.** An invalid materialized remote state can be blessed as complete,
then the next content-changing revision cannot produce the mandatory compensable
update because its prior payload was never stored. D0's inventory is the
supersession authority, not a best-effort hint.

**Minimal fix.** Validate inventory values by kind: dated records require non-empty
`remote_id` and `payload_snapshot_ref`; written singleton records require a payload
snapshot and null remote ID; only adopted positional keeps may have both null.
Add first/subsequent keep and later-update tests starting from each allowed inventory
branch.

### 4. Attachment identity validation is not bound to the attachment payload

**Claim.** The builder now emits the correct attachment identity, but the contract
validator accepts a logical key whose parent and filename disagree with the payload.

**Evidence.** Builder-time checking is correct
(`athletes/scripts/apply_contract.py:266-286`). Loaded-contract validation later
checks only the logical-key regex, revision ID, marker containment, and payload
digest (`:466-499`). I changed a valid operation from `guide.html` to
`different.html`, changed `parent_logical_id` to a different workout, recomputed the
payload digest, and `validate_contract()` accepted:

```text
logical_id: cs_probe:attachment_upsert:2026-08-14#1:guide.html
payload.parent_logical_id: cs_probe:workout_upsert:2099-01-01#1
payload.filename: different.html
result: accepted
```

**Why it blocks.** D0 defines attachment identity exactly as
`{parent_logical_key}:{filename}`. A reader trusting this validator can reconcile,
read back, or compensate the wrong attachment/parent while the document still
claims schema validity.

**Minimal fix.** In semantic validation, split the attachment logical key, require
`payload.filename` to equal its filename component, require
`payload.parent_logical_id` to equal the order's workout logical ID built from the
parent-key component, and require the named parent workout operation/inventory
identity to exist. Add tampered loaded-contract negatives.

### 5. The new parity gate still invents legacy behavior instead of comparing it

**Claim.** The socket-free and loopback tests compare D0 with a synthetic
“legacy desired state,” not with the remote effects of the actual legacy adapter.

**Evidence.** The actual disabled adapter's workout request contains
`external_id`, `title`, `date`, `duration`, `sportType`, and `segments`
(`delivery/trainingpeaks/adapter.py:81-90`). The new legacy normalizer ignores those
remote fields and instead selects D0-shaped fields added to the manifest:
`description`, `tp_workout_type`, `total_seconds`, `tss_planned`, and `structure`
(`athletes/scripts/fake_remote_parity.py:24-39`; fields were added at
`athletes/scripts/fulfillment_manifest.py:44-50`). My direct comparison produced:

```text
actual legacy workout keys:
  date, duration, external_id, segments, sportType, title
parity model “legacy” keys:
  date, description, structure, title, total_seconds, tp_workout_type, tss_planned
```

The mismatch is deeper than naming. The real adapter never loops over
`mental_training_tasks` (`delivery/trainingpeaks/adapter.py:81-108`), while the fake
legacy model installs them (`fake_remote_parity.py:46-51`). The real adapter has no
delete operation and skips any already-done key; the fake `reconcile_legacy()`
deletes absent dated resources and overwrites all desired resources
(`fake_remote_parity.py:78-85`). The round-2 test then compares D0 against those
invented effects (`athletes/scripts/test_apply_contract.py:213-290`). The loopback
variant uses the same model and therefore cannot repair the semantic gap.

**Why it blocks.** D0 requires equivalent normalized remote effects for every
legacy operation class before migration. This test can remain green while remote
workout structure changes, mental tasks appear for the first time, and
update/delete/keep semantics differ from the legacy path.

**Minimal fix.** Extract or faithfully reproduce the exact unreachable legacy
request builders and operation support, apply those requests to a field-complete
fake remote, independently apply D0 operations, and compare normalized final remote
state. Differences that are intentional—such as newly adding mental tasks or
deletes—need an explicit spec/migration disposition, not a parity assertion.

## Non-blocking findings

1. The canonical-authority rework is real at the publication boundary. The mature
   generator still produces a private XML-shaped compiler document first, but a
   published ZWO is no longer read by canonicalization, and the final ZWO is
   recreated from the validated canonical session. I do not classify that internal
   compiler representation as the R1 reflection defect.
2. Source registry entry construction now requires a revision, and the normal paid
   order path computes the prospective revision before `build_profile()`
   (`athletes/scripts/intake_to_plan.py:3612-3627`). Defaults remain in
   `registry_document(revision=1)` and several owner lookups use `or 1`
   (`derived_registry.py:95`; `canonical_training_model.py:535-538`;
   `calculate_fueling.py:552-557`; `generate_athlete_package.py:3236-3241`). I found
   no normal webhook correction path that bypasses the prospective stamp, but the
   complete revision-2 production artifact path lacks a dedicated end-to-end test.
3. The recursive projection is not applied to the authenticated review page; that
   page continues to render authoritative raw state. The 66-test review/state/token
   suite remained green, so I found no over-redaction regression there.
4. `git diff --check cd85db5..HEAD` passes. The broader Phase-2-to-HEAD check reports
   only the two trailing-space lines already committed in the R1 review document,
   not an implementation defect.

## Verification performed

### R1 adversarial probes

- Exact five-field normative inventory, with `payload_snapshot_ref` and no inline
  payload: update and delete now resolve, schema-check, digest-check, and copy the
  prior payload. Inline payload is rejected. The focused probe passed.
- Attachment identity emission: now exactly
  `cs_phase3:attachment_upsert:2026-08-14#1:guide.html`, with parent
  `cs_phase3:workout_upsert:2026-08-14#1`. The focused probe passed.
- LTHR endurance segment: `{'type':'pct_lthr','low':0.68,'high':0.83}` now produces
  normalized effort `0.65` and `Z2`, not `Z3`.
- Real post-approval status response with seeded sensitive value: the seed is absent
  from both live and approval-snapshot output. The focused endpoint probe passed.

The exact focused command for those tests returned **7 passed**.

### Test execution

```text
python3 -m pytest -q --disable-warnings --maxfail=25
```

Result: **2,452 passed, 87 skipped, 21 warnings, 0 failed** in 21.49 s.

Focused Phase-3 changed-test suite (the nine Phase-3/R1 test files):
**346 passed, 30 skipped, 0 failed** in 7.51 s. Twenty-nine skips are the repository's
optional `/tmp/nicholas-intake.md` cases; one is the loopback fake-TP test.

Production every-artifact non-power package suite with a retained temporary base:
**3 passed**. I additionally grepped all 141 retained textual artifacts for numeric
watts and `%FTP`; no match.

Phase-1/2 state, review, and download-token invariant suite:
**66 passed, 0 skipped, 0 failed**.

Required opt-in acceptance command, from `athletes/scripts`, with a writable HOME and
the user site preserved:

```text
review_home=$(mktemp -d /private/tmp/gg-phase3-r2-home.XXXXXX)
HOME="$review_home" \
PYTHONPATH="/Users/mattirowe/Library/Python/3.14/lib/python/site-packages${PYTHONPATH:+:$PYTHONPATH}" \
GG_RUN_ACCEPTANCE=1 python3 -m pytest test_order_acceptance.py -q -rs
```

Result: **36 passed, 4 skipped, 4 failed** in 11.59 s. The four failures are the
mandatory PDF presence/structure assertions for gravel-fullgym and masters. The two
Roadie PDF cases skip under their HTML-fallback contract; two other skips are the
expected Roadie-only package cases. A fresh archived Phase-2 tree produced the same
**36 passed, 4 skipped, 4 failed**, so this is not a Phase-3 regression.

`python3 -m compileall -q athletes/scripts delivery tools webhook` passed.

### Independent power-plan ZWO identity

I generated all four acceptance orders in a fresh `git archive
build/trustworthy-phase2`, generated the same orders at HEAD, and compared a sorted
manifest whose lines are `<sha256><two spaces><athlete-relative-path>`.

| Fixture | Phase 2 | Phase 3 | Added / removed / changed |
|---|---:|---:|---:|
| `acc-gravelrider` | 89 | 89 | 0 / 0 / 0 |
| `acc-mastersrider` | 77 | 77 | 0 / 0 / 0 |
| `acc-roadiefondo` | 41 | 41 | 0 / 0 / 0 |
| `acc-roadieclimber` | 46 | 46 | 0 / 0 / 0 |
| **Total** | **253** | **253** | **0 / 0 / 0** |

The independent manifest diff was empty. Both manifests hash to
`a639fc3f54d09e3de6e278511d44894b573e6f252f1b054c1ad27a532ef90ada`
under the line format above. This is an independently generated manifest; its digest
need not equal the notes' differently serialized manifest digest.

### Phase 1/2 and TrainingPeaks execution checks

- Approval/release sealing, non-executable review bundles, and download token
  binding remained green in the 66-test invariant subset and the full suite.
- No TrainingPeaks execution path was enabled. The three historical execution files
  have no diff from Phase 2. `delivery/trainingpeaks/adapter.py:71-76` raises before
  its historical request loop; `tools/tp_apply_order.py:225-229,313-322` refuses job
  construction/execution; `tools/tp_apply_driver.js:1-6` throws before its body can
  install globals or call the network.
- `athletes/scripts/apply_contract.py` and `fake_remote_parity.py` contain no HTTP,
  browser, credential, or execution entry point.
- I made no live TrainingPeaks, browser-session, Stripe, email, worker, or external
  network call.

## What I could not verify in this sandbox

1. **Loopback fake-TP transport test.** Binding `127.0.0.1` is forbidden here, so
   `test_trainingpeaks_adapter.py::test_phase3_contract_has_fake_server_effect_parity_with_legacy_manifest`
   skipped. The repository reports it green outside the sandbox. Its shared semantic
   model is still insufficient for Blocker 5, irrespective of transport.
2. **Four mandatory PDF acceptance assertions.** No usable PDF engine was available
   under this managed sandbox, so gravel-fullgym and masters could not create PDFs.
   I did not fake a PDF or weaken assertions. These are reported green outside the
   sandbox; I personally did not execute them successfully.
3. **PDF text assertions for the LTHR/HRmax/RPE fixtures.** They run only when a PDF
   exists and `pdftotext` can consume it. I verified every retained textual artifact
   and both ZIPs, but not generated PDF text.
4. **Live TrainingPeaks acceptance/readback.** Phase 3 must remain offline. I did not
   attempt HR/RPE acceptance, identity binding, marker round-trip, mutation,
   readback, rollback, or canary checks; those remain Phase 4/5 gates.
5. **The pending Phase-2 human live-page gate.** It remains outside this code-only
   Phase-3 review.

## Final disposition

**NO-GO — 5 blockers.**

# COACHING-LOOP — Rolling Athlete Calendar Orchestration

**Status:** v5 ACCEPTED (Matti, 2026-07-24) — adversarial convergence: sol r1
(6B/8M/2m) → luna r1 (1B/10M/1m) → sol r2 (2B/9M/1m) → luna r2 (0B/9M/2m),
all folded; final certification round waived by coach decision (blocker count
had reached zero; residual findings were bookkeeping-grade and folded).
Nothing executes until Matti approves CL-T0a dispatch and answers the open
questions.
**Repo home:** `athlete-custom-training-plan-pipeline` (references Endure MS-B01)

## Thesis

A **new rolling orchestration layer** — persistent per-athlete season state,
weekly context resolution, engine adapters, a formal proposal IR, gated review,
receipted placement — over engines that are plan-shaped today.

| Reused as-is | Needs an adapter (new code) | Does not exist (new) |
|---|---|---|
| RUN-LIB assets (v1.1) | block-builder `build_calendar_week` (hydration adapter; SeriesTracker serialization is NEW code) | TP READ data plane; season resolver; ProposalIR; engine-state store + loop journal; orchestrator/isolation runner; review surface; approvals protocol; single-week placement protocol |
| GG bike/strength TP libraries | `dual_sport_dispatch` (v1.1) | |
| Dampened-adaptation philosophy; guardrail/gate patterns | PlanIR conventions inform; NOT the proposal IR | |

## v1.0 scope

**Bike + strength slots, 5 pilot athletes, coach-AUTHORED dossiers,
proposal-only.** Machine-enforced: ProposalIR header carries
`capability_profile: "v1.0-proposal-only"`; schema validation REJECTS any
`tp_op` other than `add` under that profile (sol r2 f12). Deferred to v1.1+:
RUN-LIB/dual-sport adapter, bootstrap compiler, Endure/QMD axes, placement
(CL-T7). Endure/QMD format design is v1.1 planning and does NOT gate CL-T0a.

## Hard scope boundaries

- **Exclusion (technical):** `coaching_loop/exclusions.py` →
  `EXCLUDED_ATHLETE_IDS: frozenset[int] = {418209}` (Anthony, Matti standing
  instruction 2026-07-23). `normalize_athlete_id() -> int` at every module
  boundary (non-coercible → error). Checked (raise) in fetch, resolve,
  propose, brief, approvals parsing, placement. Lands in CL-T0a. Removal
  requires a Matti-authored commit.
- No auto-place tier exists in any v1.x schema.
- No medical reasoning. Lexicon hits → BLOCKING exception (below).
- **Comment privacy (sol r2 f10):** raw comment text never persists outside
  the fetch step. Snapshots store a derived form only:
  `{comment_id, workout_id, lexicon: {version, hits: [term_ids]}, length}`.
  A3 replay consumes the derived form (deterministic given lexicon version).
  The ledger ExceptionRecord stores the derived form plus an excerpt of AT
  MOST 8 words centered on the lexicon hit — this bounded excerpt is the ONE
  sanctioned persistence of comment text, stated explicitly (luna r2 f9).
  CL-T0a comment fixtures are SYNTHETIC, never real athlete text.
- TP transport = coach's logged-in browser session; weekly run is
  semi-attended. No cron promises.

## Data contracts

### C1 Hash discipline (acyclic — sol r2 f1)
`canonical_json`: UTF-8, sorted keys, no whitespace, integral floats as ints.
Every hash is over an explicitly named **view** (versioned projection), and no
view contains any field derived from its own hash. Construction order:

1. `dossier_rev = H(dossier-view)` — dossier file minus nothing (pure content).
2. `engine_state_hash = H(base-state-view)` — see C3; the stored `state_rev`
   field is set to this value and is NOT part of the view.
3. `snapshot_hash = H(snapshot-view)`.
4. `content_hash = H(proposal-content-view)` = {schema_version,
   capability_profile, athlete_id, week_start, sessions[] WITHOUT session_ids,
   adaptation_decisions, flags, exceptions, coverage_report, load_summary,
   engine_state_next (base-state-view form — contains NO proposal/journal
   references, see C3)}. Excluded by definition: proposal_id, session_ids,
   status, revision, input_manifest.
5. Derived ids: `proposal_id = "prop-" + H(athlete_id|week_start|content_hash)
   [:16]`; `session_content_hash = H(session-view)` per C2; `session_id =
   "sess-" + H(session_content_hash|ordinal)[:12]` (ordinal disambiguates
   identical sessions within a week).
6. `input_manifest_hash = H(input-manifest-view)` where the manifest =
   {snapshot_hash, dossier_rev, engine_state_hash, code_manifest, lexicon:
   {version, content_sha}}.
7. `approval_hash = H(content_hash | input_manifest_hash)` — what an approval
   binds to.

`code_manifest` (sol r2 f6, luna r2 f1): git SHA + dirty-tree guard scoped to
SOURCE paths only (`*.py`, `athletes/config/**`, schema files). Machine-owned
runtime paths — `athletes/roster/*/journal.jsonl`, `engine_state.yaml`,
`runs/**`, approvals/WAL files — are `.gitignore`d working data, excluded from
both the dirty check and code_manifest, so the loop's own writes never block
the next run or shift the manifest. Hash algorithm everywhere: SHA-256.
Canonical JSON adds: NFC-normalized strings; non-integral floats rounded to 6
decimals. The pure-function signature of proposal generation is
`(snapshot, dossier, base_engine_state, code_manifest, lexicon)` — nothing
else may be read.

### C2 `ProposalIR` v1 (JSON Schema in CL-T0a)
Header: schema_version, capability_profile, proposal_id, content_hash,
athlete_id (int), week_start (athlete-tz ISO Monday), revision (journal
metadata — NOT in content-view; replay identity is content_hash equality),
status (proposed|approved|edited_superseded|rejected|expired), input_manifest.
Sessions: {session_id, session_content_hash, day, sport, slot, source,
library_item_id?, structure?, description, duration_hours, tss_est, tp_op}.
`session_content_hash = H(session-view: day|sport|slot|source|library_item_id|
structure|description|duration_hours|tss_est)`; `session_id` derives from it
(luna r2 f5 — per-session identity for edit-magnitude matching). Header also
carries `origin: engine|coach_edit` (luna r2 f4). v1.0: tp_op={op:add}
only (profile-enforced). Full op grammar (v1.1+, specified now): add |
replace{target_workout_id, target_fingerprint} | delete{...}; order
deletes→replaces→adds; targets must be loop-owned and preflight-verified.
Plus: adaptation_decisions (rule, window, evidence, action), flags,
exceptions (typed; `blocking` is DERIVED at emission from the canonical
`EXCEPTION_CLASS` code map — type → blocking|overridable — and re-validated
at approvals parsing, mismatch → reject; luna r2 f6), coverage_report,
load_summary, engine_state_next (base-state-view).

### C3 Engine state: base state vs loop journal (sol r2 f1+f2 resolution)
**Base engine state** (`engine_state.yaml`, machine-owned): season =
{active_goal_id, phase_calendar (block/week table with date bounds),
resolution_input_hash}; cursor = {block_number, week_in_block}; bike series
levels; ownership registry; `recent_races: [{date, sport, priority}]`
(rolling 28-day window, refreshed on APPROVE from the approved week's races —
the W-1 lookback source; luna r2 f8). NOTHING about proposals/approvals lives
here.
**Loop journal** (`athletes/roster/<slug>/journal.jsonl`, append-only).
Journal record schemas (all with run_id, ts): PROPOSED {week_start, revision,
proposal_id, content_hash, input_manifest_hash, origin}, REPLAY {week_start,
revision_ref, proposal_id} (identical content regenerated — no new revision),
REPROPOSED_UNCHANGED {as REPLAY, but after a REJECT — flagged in the brief:
the engine re-proposed content the coach already rejected}, APPROVED
{approval_hash, operator}, EDITED_SUPERSEDED {old_proposal_id,
new_proposal_id, operator}, REJECTED, EXPIRED, STATE_APPLIED {state_hash
before, after} (luna r2 f3).

Transitions: **PROPOSE** appends a journal record and mutates NOTHING else —
base state unchanged, so the proposal's own CAS stays valid. `revision` =
1 + max(prior revisions for that week_start); identical-content regeneration
→ REPLAY (post-rejection: REPROPOSED_UNCHANGED). **Apply-time lifecycle rule
(luna r2 f3): an approval is valid only if the proposal's latest journal
record is PROPOSED or REPLAY — REJECTED/EXPIRED/EDITED_SUPERSEDED proposals
are unapprovable regardless of hash match.**
**APPROVE** = C4 CAS passes → atomically: apply engine_state_next to
engine_state.yaml, append APPROVED + STATE_APPLIED, cursor advances.
**REJECT/EXPIRE** → journal only; cursor unchanged; next run regenerates at
revision+1. **MISSED WEEK** → next run proposes the current week; journal
notes the gap; no back-fill. **GOAL/DOSSIER CHANGE** →
resolution_input_hash mismatch → season re-resolved, cursor re-anchored,
flagged. The season resolver is loop-owned code operating on persisted inputs
only (never wall-clock phase logic; calculate_plan_dates is not called).

### C4 Approvals protocol (crash-safe CAS — sol r2 f2/f3/f4/f5)
Entry: {proposal_id, approval_hash, action: approve|reject|
override_approve {exception_ids, rationale (hashed into the entry)}}.
**There is no `edit` action.** A coach edit happens BEFORE approval: the
coach edits SESSIONS ONLY; the edit pipeline re-derives `engine_state_next`
from the CURRENT base state + edited sessions (never hand-carried — the state
transition is always machine-generated; luna r2 f4), re-runs schema + W-gate
validation, and emits a NEW proposal (origin: coach_edit, revision+1, journal
EDITED_SUPERSEDED with old→new ids); approval targets the new approval_hash.
Exception classes are re-derived at emission — an edit cannot reclassify a
blocking exception (luna r2 f6). Edits can never bypass gates.

Staleness authority per manifest component (sol r2 f4): dossier_rev,
engine_state_hash, lexicon, code_manifest are repo-local — re-computed and
compared at apply time (no TP access needed). snapshot_hash is NOT re-checked
at approval: in v1.0 (proposal-only) TP currency carries no risk; in v1.1+
TP currency is the PLACEMENT PREFLIGHT's job (place step is itself a
semi-attended fetch that re-reads the calendar fingerprint and aborts on
drift). This split is by design; approval CAS = repo-local inputs only.

Crash safety (sol r2 f5, luna r2 f2): apply runs under a lockfile. WAL intent
record = {apply_id, entries, hashes, PRIOR engine_state bytes (backup)}.
Commit order: write intent (fsync) → write new state to temp file (fsync) →
atomic rename over engine_state.yaml → append journal line (single line,
fsync; startup scan truncates any partial trailing line) → clear intent.
Recovery: intent present with rename not yet durable → restore backup and
retry or roll back; duplicate apply_id → no-op. Rationale text for overrides
is stored verbatim in the ledger AND hashed into the approval entry (minor
ambiguity resolved: both).

### C5 Snapshots & hermetic replay
Run bundle: run_manifest {run_id, operator, code_manifest, lexicon, roster
slice, per-athlete envelopes} + per-athlete tp_snapshot (comments in derived
form only). Replay: same (snapshot, dossier, base state, code_manifest,
lexicon) → identical content_hash — CI golden-replay test on pilot bundles.

### C6 Per-athlete isolation
Result envelopes ok|failed|skipped; one athlete's failure marks the run
`partial`, surfaces as a brief exception, never blocks other athletes.

## Weekly flow (v1.0)

1 Fetch (semi-attended; per-athlete checkpoints; resume after re-auth;
partial → partial run). 2 Resolve WeekContext. 3 Propose (bike adapter +
strength slotting). 4 Adapt. 5 Gate. 6 Review (brief: failures/blocking
exceptions first; approvals per C4). 7 Measure (ledger/metrics).

### Adaptation rules (fully pinned — sol r2 f7)
Defaults live here; dossier may override per athlete. All rules are pure
functions of WeekContext; every firing records evidence.
- **A1 completion**: ratio = Σ completed_hours / Σ planned_hours over
  loop-owned sessions in the 14 days ending the snapshot Saturday; no-op if
  planned sessions < 3. ratio < 0.60 → the Tuesday-slot quality session drops
  one level (floor: level 1) AND the optional session's duration is set to
  the dossier `optional_floor_min` (default 20). If no Tuesday-slot quality
  session exists, the highest-level quality session is reduced; if none, A1
  no-ops (logged).
- **A2 readiness**: least-squares slope over the last 7 calendar days' values;
  x = calendar-day index 0..6, missing days omitted (min 5 points else no-op);
  slope < −0.5 units/day (default) → each quality session is replaced by the
  Z2 library item per mapping table `z2_map_v1` (versioned, in
  library_manifest) over duration buckets [<45, 45–59, 60–74, 75–89, ≥90] min,
  flagged. A4 applies BEFORE A2; A2 rewrites only non-overlay sessions
  (luna r2 f7).
- **A3 lexicon**: derived-form hit → BLOCKING exception + progression freeze
  (levels held at engine_state values).
- **A4 new race ≤28d**: deterministic overlay — race day becomes a race slot;
  day-before becomes the openers library item of the dossier's openers
  duration bucket; flagged.
Precedence A3 > A2 > A1; A4 composes. All windowed; single-day events change
nothing.

### Gate: W-rules + exception classes (sol r2 f8)
W-1 no intensity ≤2 days post-race (lookback: engine_state prior races);
W-2 long ride present per week type; W-3 optional never RPE≥5; W-4 hours in
dossier band; W-5 series level +1 max; W-6 banned-pattern scan; W-7 exclusion
assert. **Blocking** (unapprovable; resolved only by dossier/proposal edit →
regeneration): W-6, W-7, A3 — per the canonical `EXCEPTION_CLASS` map; the
approvals parser rejects approve AND override_approve on any proposal
carrying a blocking exception. **Overridable** (W-1..W-5): `override_approve`
must name EXACTLY the set of overridable exception_ids on the proposal
(missing or unknown ids → reject) with a rationale hashed into the entry.
Blocking ones render red/topmost in the brief.

## Bad-week model

No run → athletes keep current calendars; missed_week journaled. Mid-run
interruption → checkpoints/partial. No manifest by cadence deadline →
Morning Intel reminder (advisory).

## Review economics

Green scan ~10s, exception ~4min (validated in pilot). 84-athlete ≤60min
holds only under ~13% exception rate; tripwire: sustained >15% → onboarding
pauses. Data failures + confirm-inferred-fields count as exceptions.

## Shadow pilot (v1.0 exit gate)

5 athletes, 4 weeks, ~20 proposals, proposal-only.
- **Approval gate**: ≥70% of engine-origin proposals receive approve (or
  override_approve) without coach_edit supersession.
- **Edit magnitude** (sol r2 f9): for each superseded proposal, magnitude =
  1 − |sessions shared by content-hash between engine and final| /
  max(#engine sessions, #final sessions). Gate: median ≤0.20 across
  superseded proposals; vacuously passes if none.
- **Anti-rubber-stamp**: 10% random re-review (self-disagreement target 0);
  rationale required on every override_approve (already structural) and on
  approvals of flagged proposals; week-4 blind re-programming check on 3
  sampled athlete-weeks.
- **Safety**: 0 false negatives on weekly injected synthetic guardrail +
  lexicon fixtures (precision also reported).
- **Determinism**: replay of every week reproduces identical content_hashes.
- **Timing**: p50 ≤3min, p90 ≤6min per athlete (instrumented).
Fail → revise, rerun once. Two failures → stop and rethink.

## Tickets (owners for every contract — sol r2 f11)

- **CL-T0a read-only spike (gates all):** real TP READ fixtures (browser
  session; comments captured ONLY in derived form) + schema tests;
  exclusions module; ProposalIR JSON Schema + C1 hash utils (acyclicity
  test: construct full artifact chain from fixtures); engine_state + journal
  schemas + season resolver spec; resolve Matti's open questions. No
  mutations. Output: T0a report appended here; Matti reads before T1+.
- CL-T1 dossier schema/validator (defaults table from this spec) + base-state
  validator + **season resolver implementation + state-machine tests** + 5
  hand-authored pilot dossiers (Matti approves).
- CL-T2a TP read adapters over T0a fixtures. **CL-T2c orchestrator: run
  bundles, checkpoints, isolation runner, run manifest, failure/restart
  tests** (owns C5/C6).
- CL-T3a bike rolling adapter (SeriesTracker serialize/hydrate; coherence
  tests). CL-T4 adaptation rules (pure; damping properties; injected
  fixtures). CL-T5 W-rules + guardrail compiler + blocking/overridable
  classes.
- CL-T3c composition + ProposalIR emission + goldens (generated only with
  T4+T5 in the path). CL-T6 brief + approvals (C4 incl. WAL/recovery tests)
  + edit-supersession flow + timing. CL-T9 ledger/metrics (edit-magnitude
  calc). CL-T10 runbook (STE).
- → SHADOW PILOT → (pass + Matti go) **CL-T0b live-mutation spike** (test
  athlete 5959039, explicit Matti authorization; notification-behavior probes;
  placement protocol report) → CL-T7 placement → v1.1 (T3b RUN-LIB adapter,
  T2b bootstrap compiler, Endure/QMD axes, T8 feedback ingestion).

Terra executes, Fable verifies/commits, sol gates each ticket.

## Open questions for Matti (block T0a completion, not start)

1. Pilot five (bike-focused). 2. Cadence anchor. 3. Dossier approval format.
4. Strength depth v1.0. 5. T0b authorization (pre-placement only).

## Convergence trail

- **sol r1: NO-GO 6B/8M/2m** — orchestration reframe; PlanIR ≠ proposal IR;
  no rolling phase oracle; no read plane; unenforced exclusion; unmeasurable
  pilot; underdetermined adaptation; dossier gaps; vacuous weekly compliance;
  review workload model; approvals safety; TP mutation maturity; lexicon
  state model. Folded in v2.
- **luna r1: fold-fidelity confirmed; NO-GO 1B/10M/1m** — "names not
  contracts": ProposalIR schema, engine-state machine, CAS, exclusion
  normalization, bad-week model, dossier-edit concurrency, placement/churn
  semantics, hermetic determinism, isolation, anti-rubber-stamp, T0 split,
  golden ordering, v1.0 scope cut (ADOPTED). Folded in v3.
- **sol r2: NOT CONVERGED 2B/9M/1m** — hash-graph circularity → C1 acyclic
  view order; PROPOSE-invalidates-own-CAS → C3 base-state/journal split;
  `edit` not a contract → edit-supersession flow; staleness unevaluable →
  repo-local CAS + placement-preflight split; WAL/crash-safe apply; dirty-tree
  guard + lexicon in pure signature; A1/A2/A4 rewrite functions pinned;
  blocking vs overridable exceptions; edit-magnitude metric defined; comment
  privacy via derived form; C5/C6/resolver ticket owners (T1/T2c);
  capability_profile enforcement + T0a gate slimmed. Folded in v4.

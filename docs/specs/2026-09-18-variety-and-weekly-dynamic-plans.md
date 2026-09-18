# Motoren: workout variety policy + weekly per-athlete dynamic plans

Status: PLAN OF RECORD (Matti, 2026-09-18: "weekly"). Not yet built. Sol review
before dispatch.

## A. Variety and progression (selector policy, no new content)

Evidence (2026-09-17 builds): library index 1,464 curated items / 754 families /
24 types; three blocks (Ed, Ari, Forest) used 40 distinct workouts; Descending-
Cadence Ladder 4x on Ed and 4x on Ari, High Cadence Intervals 3x each, plain
Endurance 7x on Ed; ~25% of sessions in a progression series. Deep pools skipped:
torque_stomps 98, sweet_spot_intervals 97, vo2_classic 94, durability_long_sims 77,
race_sim 76, endurance_with_work 74, tempo 60.

Rules to add to `library_selector.select` / `resolve_library_selections`:
1. **Block spread.** No curated item twice in a block; no family twice in a week.
   Extend `used_items` (already tracks item+week) with a family-per-week key.
2. **Progression first.** For an intensity slot at the start of a series, rank
   items that open a 2-3 rung ladder (a floor-qualified next rung exists,
   `_family_can_continue_above_floor`) above singletons; series length target
   2-3 rungs per block (AE-4.1 plus-one).
3. **Filler rotation.** The weekday filler role rotates through
   `endurance_with_work` -> `tempo` -> `skills`/cadence -> `endurance_z2_long`
   across the week/block instead of defaulting to cadence. Cadence stays
   guaranteed once per week (AE-3.7 dimension work), not every filler.
4. **Rotation seed widening.** `_rotate_index` currently converges on the same
   2-3 items per slot; seed by (athlete, plan_week, slot) so consecutive blocks
   for the same athlete draw different items from the same pool.
5. **Report.** `library_fallbacks.json` gains a `variety` block: distinct items,
   families, series count, pool utilisation per library_key -- so a build can be
   judged on spread at a glance (and sol can grade it).
Gates unchanged: AE-2.7 floor, AE-3.1 dose window, R1-R20, role ceilings.

### A — as built (2026-09-18)

`library_selector.select` / `generate_athlete_package.resolve_library_selections`;
tests `test_variety_policy.py`. `GG_LIBRARY_VARIETY=0` switches the policy off
for a before/after grade; `GG_LIBRARY_TRACE=1` prints one line per decision.

Deviations from the rules above, with reasons:
- **Block = coaching mesocycle**, not the engine's `block_number` (which only
  advances at a phase change, so a 12-week base would be one block and a
  4-week coached block spanning a phase edge two). A new meso opens on the
  first load week after a recovery week; taper/race weeks stay in the meso
  before them.
- **Rule 1 split hard/soft.** Item-per-block is hard (same shape as the
  same-week ban; a loud D9 fallback beats a silent repeat). Family-per-week
  and family-per-block are soft preferences so small libraries still resolve.
- **Added: family start cap** — a family is freshly *started* at most twice
  per plan (series continuations exempt). Without it Ed's first rebuild still
  drew Descending-Cadence Ladder fresh in four blocks.
- **Rule 3 (series length)**: intensity series close after 3 rungs, filler
  pairs after 2; the slot restarts on a different family.
- **Rule 3 tempo**: NOT in the easy-day rotation — the ratified filler IF
  ceiling (Q-B .72) excludes every tempo item and the ceiling was not relaxed.
  Rotation is `endurance_with_work` → `skills` → Z2 by (plan_week + filler
  ordinal).
- **Rule 2 ranking** counts only rungs the series could actually advance onto
  (floor, day cap, role/AE-3.1 ceiling, exclusions). Counting duration alone
  ranked a 30/30 family whose next rung failed the dose gate.
- **Rule 5 report** is a sibling `library_variety.json`, not a block inside
  `library_fallbacks.json` (intake_to_plan and the integration tests read that
  file as a plain list).

Measured on the three 2026-09-17 athletes (test rebuilds only; committed
packages restored, nothing republished):

| athlete | committed curated / distinct | policy on curated / distinct | fallbacks |
|---|---|---|---|
| Ed (7 wk) | 25 / 18 | 25 / 21 | 4 → 4 |
| Ari (7 wk) | 22 / 17 | 22 / 19 | 1 → 1 |
| Forest (4 wk, under the floor) | policy off 12 / 8 | 9 / 9 | 1 → 1 |

Counts are bike sessions with a `library_item_id` in `plan_ir.json` (the
shipped calendar). `library_variety.json` counts more: it reads every
block-builder day with a resolution, including days the payload later drops
or locks, so its `distinct_families` can exceed the shipped distinct-item
count (Forest: 11 vs 9).

Adversarial review (Claude Opus stand-in, Codex out of credits, 2026-09-18)
folded in: item-per-block is hard for intensity / long-ride slots and softens
to "prefer" for a filler slot whose duration window holds nothing else (a
repeated easy hour beats a synthetic render of it); the post-trim recovery
rebalance now shares the selector's memory and the report is rebuilt after it;
series closed by the rung cap still count in the report; the overflowing head
line is word-cut, never dropped; every "<TIER> FUEL" tag is accepted;
`GG_LIBRARY_VARIETY=0` restores the pre-policy floor-continuation check.
Known, accepted: the 3-rung cap can restart on the same family when no other
family fits (3+3 with a title reset); rule 2's depth count does not apply the
±15% budget window the continuation path also checks.

Latent bugs the new picks surfaced (fixed in the same change): a compiler-
appended `RPE guide:` line fell past the 180-word athlete-copy cap and
`validate_canonical_model` killed the build; the `[HIGH FUEL: …]` tag
(fueling_policy's quality tier) was unknown to the sanitizer and the apply
contract and read as an internal token.

## B. Weekly per-athlete dynamic plan (DRAFT in the TP library, never the live calendar)

Trigger: Matti's weekly review (Sunday/Monday). One run per active athlete.

Inputs, folded into ONE athlete master profile (`athletes/<id>/profile.yaml` +
`coaching_history.md`, the Forest pattern):
- questionnaire / intake (pipeline data), Drive "Athlete Reviews_<name>" workbook
  (goals, schedule, latest weekly review row), TP athlete comments + coach
  comments since last run, TP settings (FTP, HR), completed-load reality
  (fitness/v6 pull: last 6 weeks hours/TSS, CTL model), calendar commitments
  (life_calendar when shared), and the latest review verdict.
- A `profile_refresh.py` step writes the profile diff to `coaching_history.md`
  with sources cited (Drive row / TP comment id / email id) -- nothing inferred
  silently; contradictions land under "Standing contradictions".

Build: `generate_full_package.py <id>` -> `build_tp_plan_payload.py` -> athlete
layer (per-athlete rules file, e.g. Forest's OPTIONAL/duration titles) -> sol
review -> DRAFT dynamic plan in the library titled
`DRAFT · <Athlete> · <block name> · <weeks>wk` (existing apply_plan.js recipe:
plans/v1/plans POST -> workouts -> calendarNote -> isDynamic flip). Re-runs
UPDATE the same DRAFT plan in place (delete+repost its items), so each athlete
has exactly one standing draft. Live calendars are never written by this loop;
Matti copies across with the dual calendar.

Review surface: one page per run (artifact or Drive doc): what changed in the
profile since last week, the block shape (weekly TSS/hours vs demonstrated),
the variety block from A.5, lint + sol verdict, and the 3 lines Matti would
tell the athlete. If nothing changed in the inputs, the plan is not rebuilt and
the page says so.

Roster: TP `users/v3/user` athletes filtered to real coached athletes (the
holiday-plan linked set is the current "active" list; tests and self-loggers
excluded). ~30 athletes -> ~30 builds/week, minutes of compute.

## Order and estimate
1. A (selector policy + variety report): ~1 day incl. sol + golden updates.
2. B.1 profile refresh from the four sources: ~2 days (Drive + TP readers exist
   in pieces from this week; the join and the citation discipline are the work).
3. B.2 draft-plan upsert + review page + weekly scheduler: ~1 day.
Nothing here writes to an athlete calendar.

## B — implementation plan (2026-09-18, lead with what changes)

What exists and is reused, not rebuilt: the `endure-coaching-ops` plugin
(`~/plugins/endure-coaching-ops`) — `coaching-reviews` builds per-athlete
evidence packets (`packets/<athlete>.json`: ftp_tp, pmc, workouts, next_week,
self_review, wellness, events, gmail); `tp-dynamic-plan-builder` holds the
proven plan-library transport (create → workouts → notes → isDynamic; rebuild-
in-place); private `plan-builds/<athlete>/apply_plan.js` scripts are working
instances of it. `coaching_loop/` (ProposalIR, v5.1) is a different, heavier
design and is NOT touched; Part B is the thin weekly loop Matti ratified.

### Decisions most likely to change
1. **Master profile stays `athletes/<id>/profile.yaml`.** `profile_refresh.py`
   writes ONLY a whitelist: `fitness_markers.ftp_watts` (from TP settings),
   `recent_training.demonstrated_hours_6wk` / `_tss_6wk` / `ctl` (from PMC,
   never overwriting the athlete's stated target), `a_events`/`b_events`
   (add TP events that are missing, never delete), `coached_block.window_start`
   /`window_end` (rolls to next Monday, 4 weeks or race-bound),
   `life_calendar.commitments` (append). Everything else — self-review text,
   comments, Drive rows — goes to `coaching_history.md` as a dated section
   with a source citation per line (packet path, note id, message id).
   Contradictions (stated hours vs demonstrated, FTP change > 5%, race date
   mismatch) never write the profile; they land under "Standing
   contradictions" in the history AND in `refresh_diff.json`.
2. **Per-athlete rules are data, not code.** `plan-builds/<athlete>/rules.yaml`
   (private dir, outside the repo) replaces the bespoke `athlete_layer.py`
   scripts: `title_format: duration_lead|plain`, `optional_intensity:
   {enabled, text}`, `strip_sentences: [regex]`, `guardrails: [{title_match,
   text}]`, `commitment_notes: [{date, title, description}]`,
   `drop_rest_on_locked_days: bool`, `note_prefix: {week_titles_regex, text}`.
   `tools/athlete_layer.py` applies them; Forest/Ed/Ari rules are ported from
   their existing scripts and must reproduce today's `*_final.json` byte-for-
   byte (golden test). Race-card tailoring stays an engine gap.
3. **One standing DRAFT per athlete**, title `DRAFT · <Name> · <block> · <N>wk`,
   upserted in place (delete workouts+notes, re-POST, isDynamic re-confirmed)
   via a generic `plan-builds/_shared/upsert_draft_plan.js` (parameterised by
   `window.__DRAFT_TITLE__`; finds the plan by exact title or creates it).
   Live athlete calendars are never written by this loop.
4. **Skip-if-unchanged.** `weekly_draft_state.json` per athlete stores the
   SHA-256 of (profile.yaml, rules.yaml, packet fields used, engine commit).
   Same hash → no rebuild; the review page says so.
5. **Runner = a Claude session on this Mac**, not a cron script: the TP reads
   need the logged-in Chrome (playwriter) and the Drive workbook needs the
   Drive MCP. Skill `weekly-drafts` is the runbook (packets → refresh → build
   → review page → upsert). A Monday 06:00 Claude cron is added only after
   the first manual run is clean.

### Pilot roster
Athletes with a profile AND a coached block today: Forest Hietpas, Edward
Shapiro, Ari Shapiro, Judd Pulley. Mike Wallace joins when the other session's
Arrowhead build lands. Everyone else needs a profile first (onboarding skill).

### Code (new, tested; nothing existing is rewritten)
- `athletes/scripts/profile_refresh.py` — `refresh(athlete_dir, packet,
  workbook_rows=None, commitments=None, today=...) -> RefreshDiff`; CLI writes
  profile.yaml (whitelist), coaching_history.md section, refresh_diff.json.
- `tools/athlete_layer.py` — rules.yaml → plan_payload_final.json /
  notes_payload_final.json; golden tests against the three shipped builds.
- `tools/weekly_draft_plan.py` — per-athlete orchestrator: refresh → 
  generate_full_package → build_tp_plan_payload → athlete_layer → lint summary
  + library_variety.json → run dir `plan-builds/<athlete>/weekly-<date>/` with
  `draft_manifest.json` {title, plan_day_one, counts, lint, variety, diff};
  honours the inputs hash.
- `tools/weekly_review_page.py` — one HTML for the run: per athlete the
  profile diff, block shape (weekly hours/TSS vs 6-wk demonstrated + CTL),
  variety block, lint verdict, "3 lines to the athlete" drafted from block
  notes and marked DRAFT.
- `plan-builds/_shared/upsert_draft_plan.js` — from judd/steve apply_plan.js
  plus find-by-title, delete-all, isDynamic; receipt with content readback.
- Skill `weekly-drafts` (canonical in gravel-god-cycling/.claude/skills,
  mirrored in the pipeline repo).

### Order
1. profile_refresh + athlete_layer (parallel executors, isolated worktrees).
2. weekly_draft_plan + review page + upsert script.
3. Adversarial review of the code; first manual run on the pilot four,
   DRAFT plans upserted, review page published; then the cron.

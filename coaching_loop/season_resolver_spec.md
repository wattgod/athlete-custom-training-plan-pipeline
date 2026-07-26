# Season resolver — spec (CL-T0a spec-only; implementation is CL-T1)

Status: spec-only. No resolver code exists in `coaching_loop/` yet. This
file is the contract CL-T1 implements against, plus the state-machine
tests CL-T1 owns. See `docs/COACHING_LOOP_SPEC.md` C3 for the base-state
shape this resolver reads and writes, and `coaching_loop/schemas/
engine_state.schema.json` for the `season` object it produces.

## What the resolver is for

The loop keeps a persisted `season` block inside each athlete's base
engine state: `active_goal_id`, `phase_calendar` (a block/week table with
date bounds), and `resolution_input_hash`. The season resolver is the
only code allowed to write that block. Nothing else in the loop computes
phase or season boundaries.

## Hard rule: no wall-clock phase logic

"Never wall-clock phase logic" means the resolver never performs an
INTERNAL system-clock READ (`datetime.now()` or equivalent) to decide
anything. It does not mean the resolver is forbidden from knowing what
day it is at all -- re-anchoring a cursor after a goal change (below)
inherently needs to know where "now" falls in the new phase calendar.
The rule is satisfied by injection, not by omission: `today` is always
an explicit parameter the CALLER supplies, never a value the resolver
reads for itself. That keeps the function pure and deterministic --
same `(dossier, prior_engine_state, today)` in, same
`SeasonResolution` out, testable without mocking a clock -- which is
exactly the property the spec's "never wall-clock phase logic" line is
protecting. Two consequences:

- `datetime.now()` (or any wall-clock read) must not appear anywhere in
  the resolver's phase/cursor logic. `today` is used for BOTH the
  MISSED WEEK/regeneration bookkeeping AND the GOAL/DOSSIER CHANGE
  cursor re-anchoring algorithm below -- it is not restricted to one of
  those two uses.
- `athletes/scripts/calculate_plan_dates.py` is NOT called. That module
  computes a one-shot, backward-from-race-date plan for a fixed-length
  plan artifact. The rolling loop has no fixed plan length and must
  survive missed weeks, goal changes, and re-anchoring without
  recomputing a whole plan from scratch. Reusing it would reintroduce
  wall-clock-shaped, single-goal assumptions the rolling model is built
  to avoid.

## Inputs (pure function signature)

```
resolve_season(
    dossier: dict,            # goal, race calendar, phase preferences
    prior_engine_state: dict | None,  # None on first resolution for this athlete
    today: date,               # caller-supplied, never read from the system
                                # clock internally -- see "Hard rule" above
) -> SeasonResolution
```

`dossier` and `prior_engine_state` are the only content inputs. Nothing
about proposals, approvals, or the journal is read. This mirrors C1's
"pure-function signature of proposal generation is (snapshot, dossier,
base_engine_state, code_manifest, lexicon) — nothing else may be read":
the resolver has the same discipline, scoped to season data.

## Output: `SeasonResolution`

```
SeasonResolution = {
    "active_goal_id": str,
    "phase_calendar": [
        {
            "block_number": int,       # >= 1
            "week_in_block": int,      # >= 1
            "phase": str,              # e.g. "base", "build", "peak", "race", "recovery"
            "start_date": date,        # ISO, Monday
            "end_date": date,          # ISO, Sunday
        },
        ...
    ],
    "resolution_input_hash": str,      # H() over the exact dossier+prior-state
                                        # fields the resolution ran on
    "cursor": {"block_number": int, "week_in_block": int},  # re-anchored cursor
    "flagged": bool,                   # true when this call re-anchored an
                                        # existing season (goal/dossier change)
}
```

`resolution_input_hash` follows C1 hash discipline: it is `H(view)` over
an explicitly named, versioned projection of the resolver's own inputs
(the dossier fields that affect season shape, plus whatever prior-state
fields matter for continuity). This is the same value stored in
`engine_state.season.resolution_input_hash` and compared on every run to
decide whether re-resolution is needed.

## When the resolver runs

1. **First resolution for an athlete.** `prior_engine_state` is `None`.
   The resolver builds `phase_calendar` and `cursor` from the dossier
   alone, cursor starts at `{block_number: 1, week_in_block: 1}`,
   `flagged: false`.
2. **Every subsequent run, before Propose.** The caller re-computes
   `resolution_input_hash` from the current dossier + prior engine
   state and compares it to the stored value.
   - **Match:** the resolver is not re-run at all; `season` and `cursor`
     carry over unchanged. This is the common case — most weeks, most
     athletes.
   - **Mismatch (GOAL/DOSSIER CHANGE):** the resolver re-runs. It
     produces a new `phase_calendar`, re-anchors `cursor` so the athlete
     lands in the phase/week that matches `today`'s actual elapsed
     training relative to the new goal (not a restart at week 1), and
     sets `flagged: true`. The caller surfaces this flag in the next
     brief.
3. **MISSED WEEK.** The resolver is not involved. Per C3: "next run
   proposes the current week; journal notes the gap; no back-fill."
   `cursor` still advances by the resolver's normal week-over-week rule
   (unchanged season), it just skips the gap week's proposal.

## Cursor re-anchoring algorithm (GOAL/DOSSIER CHANGE)

On a resolution_input_hash mismatch:

1. Build the new `phase_calendar` from the new dossier goal/race-calendar
   fields, same shape as first resolution.
2. Find the `phase_calendar` row whose `[start_date, end_date]` window
   contains `today`.
3. Set `cursor` to that row's `{block_number, week_in_block}`.
4. If `today` falls before the new calendar's first row (goal moved
   further out) or after its last row (goal moved closer than remaining
   weeks allow), clamp `cursor` to the nearest boundary row and set
   `flagged: true` regardless of the hash-mismatch flag, so the brief
   calls out the clamp explicitly (this is a coach-visible edge case,
   not a silent clamp).

## State-machine properties CL-T1's tests must cover

- **Determinism:** same `(dossier, prior_engine_state, today)` in →
  same `SeasonResolution` out, every time (no wall-clock, no randomness).
- **Idempotence on match:** if `resolution_input_hash` matches, calling
  the resolver again (rather than skipping it) must return a
  `SeasonResolution` identical to the stored `season`/`cursor` — the
  resolver is a pure function of its inputs, so this should hold
  automatically, but it is exactly the property a caller depends on for
  "skip re-resolution when the hash matches" to be a safe optimization.
- **Re-anchoring correctness:** for every synthetic goal-change fixture,
  the re-anchored cursor's phase row contains `today`.
  Reference: `coaching_loop.hashing.base_state_view` treats `season` as
  part of the hashed engine state, so a resolver bug here shows up as an
  unexpected `engine_state_hash` change in CL-T1's golden tests too.
- **No back-fill on MISSED WEEK:** verify the journal gains a gap note
  and the cursor advances past the missed week without a proposal for it.
- **Boundary clamp:** goal moved outside the new calendar's date range on
  both ends (too early, too far past); both must clamp and flag.

## Explicitly out of scope for this spec

- The concrete algorithm for building `phase_calendar` rows from a
  dossier's goal/race-calendar fields (periodization model, block
  lengths). That is CL-T1 implementation detail, not a T0a contract.
- Any code. This file has none on purpose.

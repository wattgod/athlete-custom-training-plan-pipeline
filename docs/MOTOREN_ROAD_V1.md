# Motoren Road v1

Status: implementation contract  
Owner: canonical Motoren engine  
Consumer: Roadie Labs public plan preview and paid road-plan pipeline  
Profile version: `road/v1`

## Decision

Roadie Labs does not get a fork of Motoren. It gets a road-native profile
inside the canonical engine. Shared physiology, progression, recovery,
strength, fueling, taper, voice, and TrainingPeaks projection remain common.
Road event format changes only the road-specific secondary quality session,
long-ride signature, and athlete-facing road strategy.

This preserves one source of truth while preventing a criterium, hill climb,
time trial, stage race, and gran fondo from collapsing into the same plan.

## Public request contract

`training-plan-preview-request/v2` accepts an optional
`race.event_format` when `race.discipline == "road"`.

Allowed canonical values:

| Event format | Meaning | Roadie editorial source |
| --- | --- | --- |
| `generic_road` | Mass-start road race with no narrower verified format | fallback only |
| `criterium` | Repeated corner exits, short surges, sprint under fatigue | future explicit Roadie records |
| `hill_climb` | One sustained uphill effort or uphill TT | `hillclimb` |
| `time_trial` | Individual sustained aerodynamic effort | future explicit Roadie records |
| `stage_race` | Consecutive competitive stages | `multi_stage` |
| `fondo` | Gran fondo, sportive, or century | `gran_fondo`, `sportive`, `century` |

The field is rejected for non-road requests and rejected when it is not one
of the canonical values. It participates in the normalized request and cache
key. The public response echoes it in `race.event_format`; no internal
selection metadata is exposed.

## Resolution precedence

1. A valid explicit `race.event_format` from the consumer.
2. A conservative single match from the verified race name.
3. `generic_road`, marked for review inside the paid intake path.

Roadie Labs must use its structured `fondo_rating.discipline` mapping and
send the explicit value. Race-name inference is a compatibility fallback,
not the normal public-site path. Ambiguous names never guess.

## Engine behavior

Motoren passes the resolved format through the existing calendar block chain
to `workout_selector.select_workouts_for_week`. The format profile may replace
one secondary intensity workout and the long-ride signature for the current
phase. It may not displace the protected VO2 anchor or bypass global gates.

Format signatures are defined in `athletes/config/road_racing.yaml` and must
resolve to real, renderable workout-library names. Preview cards are built by
the same renderer and canonical TrainingPeaks projection as paid plans; no
workout title, structure, purpose, or strength block may be invented by the
site.

## Shared invariants

- The race demand vector, not a single difficulty score, drives emphasis
  (`AE-1.8`).
- Road-format dimension work is woven into normal specificity rather than
  bolted on as extra load (`AE-1.2`, `AE-3.7`).
- Hard-minute caps, per-day caps, intensity distribution, progression,
  recovery, VO2 maintenance, fueling, taper, and strength remain canonical
  (`AE-2.1`, `AE-2.2`, `AE-2.3`, `AE-2.6`, `AE-2.8`, `AE-3.1`, `AE-4.1`,
  `AE-6.1`, `AE-1.12`).
- Road VO2 anchors retain their real library workout but clamp to the
  library level range whose rendered T@VO2max remains inside AE-3.1's hard
  5–18 minute bounds.
- Discipline-specific copy and workouts cannot leak across sport or brand
  boundaries (`AE-3.15`).
- Event format never widens the selectable menu to an unrenderable workout.
- The same normalized request is deterministic for a given engine and voice
  version.
- Unknown or ambiguous formats fail conservatively to `generic_road`; invalid
  explicit values fail closed.

The six road profiles and their exact workout signatures are a
coach-approved house profile. The rules above constrain how those signatures
are selected; this document does not invent a new AE rule.

## Acceptance matrix

For a fixed athlete, availability, demand vector, dates, and phase:

| Format | Required distinguishing build signature |
| --- | --- |
| `generic_road` | `Race Simulation` secondary |
| `criterium` | `Microbursts` secondary |
| `hill_climb` | `Mixed Climbing Variations` secondary |
| `time_trial` | `Threshold Steady` secondary |
| `stage_race` | `Blended Endurance, Threshold, and Sprints` secondary |
| `fondo` | `Tempo with Accelerations` secondary |

Acceptance requires:

1. Contract tests for allowlisting, cache-key separation, invalid values, and
   non-road rejection.
2. Engine tests proving every format reaches the real renderer, preserves the
   VO2 anchor, and yields the expected distinguishing signature.
3. Cross-discipline leak tests across all reachable road rotations.
4. Roadie tests proving every corpus discipline maps deterministically and
   generated page configuration emits the explicit canonical value.
5. Full engine and Roadie regression suites.
6. Production checks against at least one fondo, hill climb, and stage-race
   request, with response echo and distinct workout signatures verified.

## Rollout and rollback

The contract field is optional, so old consumers remain valid. Deploy the
engine first, then deploy regenerated Roadie plan pages. If Roadie must roll
back, removing `race.event_format` returns previews to conservative name
inference or `generic_road` without changing the endpoint. If the engine must
roll back, old pages will receive a fail-closed contract error rather than a
plausible but wrong plan; Roadie already shows its explicit unavailable state.

# SPEC — Demand-Unit Simulation Composer

Coach mandate (Aug 17, 2026): rebuild the Act sim composer on the demand-unit
logic of the hand-built "Natty Specific" series. Direct quotes that govern
design:

- "I think you can make them super complicated, but simple is better."
- "One error people make in sim days is that they betray a lack of belief …
  they feel like they have to overdo the simulation and make the workout just
  as hard as the race. That's mostly not super productive … most people don't
  have the base (i.e. CTL) to absorb a 450+ day in training."
- "The Natty sim doesn't sim everything that's going to happen in the race —
  the interval structure replicates the general crux demands of the race
  spread out across a long ride."
- "Realize that I have other sims in the workout library, like Leather Bound
  (for Unbound, for example)." → curated race-matched sims take precedence.

## Ground truth (from the coach's own TP library, gg_tp_library_full.json)

**Natty Specific 2 (4hr, IF 0.74, TSS 217)** — climbing-race unit:
```
15:00 warm-up @55-75%
UNIT: 0:30 @120-127% (attack the base) + 4:30 @106-113% (sustain the climb)
      + 10:00 @83-88% (over-the-top tempo)
4 units total, separated by 30-45:00 @60-70% Z2
```
**Natty Specific 4 (5hr Dress Rehearsal, IF 0.75, TSS 283)** — same unit,
6 reps; the last two are spaced only 15:00 apart. Density converges toward the
race's (8 climbs/5hr) but never reaches it, and **unit intensity never
escalates across the series — only count and spacing change.**

**Unbound: Tempo Rhythm + Fat Max (IF 0.75)** — flat/rough-race unit:
```
UNIT: 4x[2:50 @76-90% + 0:10 @150-180%]  (12min tempo rhythm w/ micro-surges)
separated by 60:00 Z2 blocks; closes with a long 75-90% fatigue block
```
**Leather Bound 1-4 (IF 0.70-0.73)** — durability shape: 15:00 tempo blocks
between hour Z2 blocks, bookended by 4:00 @106-120% efforts.

Common design language: **one unit shape per race crux, repeated over a long
Z2 spine, whole-day IF 0.70-0.76.** Never a kitchen sink.

## What's wrong with the current composer

`act_race_sim.compose_act_simulation` builds three different demand types into
every sim (Part 1 attacks + 30/30s, Part 2 climbing grinds, Part 3 tired-legs
pyramids). That is the "lack of belief" failure mode the coach names: it tries
to sim everything. It is replaced wholesale. `compose_midweek_sim` inherits
the same fix, compressed.

## D1 — Demand unit derivation (SIMPLE: one table, keyed by existing facts)

`demand_unit(facts: RaceFacts) -> DemandUnit`, keyed on the existing
`climbing_emphasis` property (no new race-metadata plumbing):

| emphasis | unit (exact segments) | unit label |
|---|---|---|
| high (≥100 ft/mi) | 0:30 @1.23 + 4:30 @1.10 + 10:00 @0.85 | "climb set: attack the base, sustain, tempo over the top" |
| moderate (75-99) | 0:30 @1.20 + 3:00 @1.05 + 8:00 @0.85 | same language, shorter sustain |
| flat / unknown | 4x[2:50 @0.83 + 0:10 @1.65] | "tempo rhythm with surges — race-pace texture on rough roads" |

Descriptions print the coach's bands (e.g. "120-127%") plus watts from the
athlete's FTP at placement (both, e.g. "120-127% / 234-248w"). ZWO/structure
targets use the band midpoints above. `high_altitude` keeps its existing
behavior: an RPE-not-watts execution line, no power change.

## D2 — Density schedule (the convergence)

For Act k of N on a `duration_min` budget:
- `units(k) = 3 + k`, hard-capped by what fits with minimum spacing (below)
  and by 8.
- Z2 spacing between units: 40:00 for all acts, EXCEPT the final act
  (dress rehearsal) tightens the spacing of its last two units to 15:00 —
  exactly the Natty 4 move.
- Warm-up 15:00 @0.65, cooldown 10:00 @0.50, remaining budget is the Z2 spine
  @0.66; a single Z2 filler absorbs the remainder to keep the duration exact
  (whole minutes, same technique as today).

Unit power/duration NEVER changes with k. Only count and spacing do.

## D3 — The belief guard (intensity ceiling IS the load guard)

No CTL machinery. The guard is structural, stated in REPO-NP units: this
codebase computes IF as duration-weighted 4th-power mean over segments
(generate_plan_preview.py:99), which reads ~0.03 HIGHER than TP's authored
ifPlanned for the same composition (measured: real Natty 2 = 0.769 repo-NP
vs 0.74 authored; Natty 4 = 0.787 vs 0.75; the spec's 4hr/4-unit composition
= 0.769 repo-NP, byte-identical to real Natty 2's). Guard: composed-day
repo-NP IF must land in [0.68, 0.79]; if adding the next unit would exceed it
or spacing would drop below 15:00, the unit is not added. The final
(dress-rehearsal) act may reach 0.79; earlier acts must stay <= 0.77. TSS
honesty: after composing, the day's tss is recomputed from the composed
segments with the SAME repo-NP formula and written back onto the bb day
(replacing the old duration-ratio scaling at generate_athlete_package.py:1592,
which was tuned for the retired three-Act composer) — a 4hr sim lands ~235
TSS, a 5hr dress rehearsal ~290, structurally preventing the 450-TSS hero day.

## D4 — The Audible (every card)

One line, load-week wording:
"AUDIBLE: if the legs are gone after unit {n-1}, skip the remaining attacks
and ride the climbs at tempo — then finish the Z2. The spine of this ride is
the point."
Dress rehearsal appends: "Fueling practice continues at race rate no matter
what you audible."
(Flat-unit wording says "skip the remaining surges and ride the tempo blocks
steady" instead of climbs/attacks.)

## D5 — Description rewrite (product voice: professional, one wink max)

Structure: title line; THE UNIT (segments + why: "this is the crux demand of
{race name}: {one clause from emphasis}"); THE SHAPE ("{u} units across
{h}hr of Z2 — Act {k} of {N}. Each act packs them tighter; race day is the
only day you do the full count."); ALTITUDE line when applicable; AUDIBLE;
DRESS REHEARSAL block (existing kit/fuel copy) on the final act. Keep the
existing "Ride the units at their targets; ride the spine disciplined and
bored. Boredom is the skill." close. No invented terrain facts — same
fact-conservatism as today.

## D6 — Curated race-matched sims take precedence (DIRECT mapping, not the selector)

Adversarial review (Aug 17) verified the general selector CANNOT carry this:
"Natty Specific 1-4" do not parse into a family ladder (four singleton
name_bases in the index — no leading dash before the digit), and singleton
continuation would wander into unrelated race_sim items. Also, the standing
invariant "act_simulation days never reach the selector" (library_selector.py
:96-100, generate_athlete_package.py:944-947, :979-988) REMAINS TRUE — the
Aug 17 coach instruction ("realize that I have other sims in the workout
library, like Leather Bound for Unbound") supersedes the earlier scope ruling
but is implemented in the ACT PATH, not by re-scoping the selector:

- `RACE_SIM_SERIES: dict[race_id, list[canonical item name]]` — an explicit
  ORDERED list per race, seeded: `gravel_nationals: [Natty Specific 1..4]`,
  `black_canyon: [Race Sim - Black Canyon (Waffles) 1..4]`,
  `unbound_gravel_200: [Durability - Leather Bound 1..4]`. Data, no fuzzy
  matching.
- When the athlete's matched race_id has an entry, Act k of N resolves to
  entry `round(k * len(list) / N)` (last act = last entry). Placement is D4
  byte-verbatim for STRUCTURE + DESCRIPTION + authored TSS/IF (same carrier
  fields as library resolutions: library_tss / library_if_planned per
  generate_athlete_package.py:3394-3397). Duration guard: if the mapped
  item's authored duration exceeds the block-builder's day cap by >15%, fall
  back to the composer for that act and record it in the fallback report.
- TITLES stay pipeline-owned Act framing — "Race Simulation — Act k of N
  [— Dress Rehearsal]" — because delivery_notes.py:342-346 detects Act-class
  rehearsals by "act" in the display name and plan_ir's simulation pattern
  keys on title text. The curated item name is appended in the description's
  first line instead. The `act_simulation` day flag is NEVER stripped
  (block_chain.protect_post_simulation_recovery gates on it).
- Composer (D1-D3) is the path for every race without an entry and for
  unmatched races.
- A test validates every RACE_SIM_SERIES item name resolves to exactly one
  index item.

## D7 — Midweek sim

`compose_midweek_sim` becomes: warm-up + 2 units (same unit as the long-ride
acts) + Z2 spine + cooldown, same IF band, description says "same unit as
your long-ride simulations, compressed for a midweek slot." Existing sub-90min
budget handling (drop to 1 unit under 45min) mirrors today's tight-budget
guards.

## Out of scope

- No new race-metadata fields, no CTL/PMC integration, no per-athlete unit
  tuning beyond FTP-for-watts.
- Titles/series numbering unchanged ("Race Simulation — Act k of N — Dress
  Rehearsal") — briefing prose already graded A against them.
- Curated sim families are NOT edited; the alias map only routes to them.

## Tests

- Unit table totality over all emphasis values incl. unknown.
- Density monotone non-decreasing across acts; final-act tight spacing
  present; unit segments identical across acts (count/spacing only).
- Composed repo-NP IF in [0.68, 0.79] for budgets 150-330min across all
  emphases (final act may reach 0.79, earlier acts <= 0.77); duration exact
  to the second; day tss recomputed from composed segments.
- Audible present on every card; rehearsal fueling line only on final act.
- Watts render alongside %FTP for a known FTP.
- RACE_SIM_SERIES: every entry resolves to exactly one index item; mapped
  race places byte-verbatim structure/desc with authored TSS/IF and
  Act-framed title; oversize item falls back to composer + fallback report;
  unmapped race uses composer; act_simulation flag survives resolution
  (protect_post_simulation_recovery still fires).
- Compliance: R14 series-coherence does not fire on Act days (role
  long_ride, not intensity) — explicit test; full compliance gate green on
  a generated plan for both mapped and unmapped races.
- Midweek: 2 units, same unit shape as long-ride, tight-budget degradation.

## Rollout

Build behind the existing generation flow (no flag needed — composer is
already the only Act path; D6 routing gated by the alias map's presence).
Regenerate Sonja (Big Sugar ≈ flat band → rhythm unit; no alias entry →
composer path), place as v23, regrade loop until A. Then a second E2E on a
mapped race (gravel_nationals) to verify D6 places Natty Specific verbatim.

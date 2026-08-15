# Custom-plan quality tickets — from the Guillermo Romero order (2026-08-14)

Every item below is a defect the coach caught on a real paid order after the
pipeline's output passed every gate. The delivered calendar was rebuilt by hand
to the Monika-standard (reference capture:
`~/Downloads/guillermo-romero-delivery/monika_reference.json` — TP 2947583).
Ordered by how badly the raw pipeline output undersells the product.

## T1 — Archetype level selection ignores plan length
A 5-week plan starts every workout series at Level 1/6 ("Introduction to the
pattern") and has no runway to climb. Real consequence: the plan's ONLY
dedicated VO2 day shipped as 2x5min @110% in a 31-minute session for a
10+-year rider. The level ladder assumes 12 weeks. Level selection needs
plan-length and training-age context: short plans for experienced athletes
should enter at L2-L3, not L1.

## T2 — Race week has no sharpener and openers are on the wrong day
The generator emitted openers on Tuesday of race week and NOTHING the day
before the race. House standard (Monika, coach-built): Tuesday = short
anaerobic sharpener ("Stars In Your Eyes" 20/30/40s), Friday = Openers v1.1
the day before the race. Encode a race-week template: sharpener early week,
openers day-before, rest days as explicit Day Off entries.

## T3 — Taper week is 100% flat Z2
W4 emitted five identical single-block endurance rides. A taper needs
volume DOWN but stimulus ALIVE: 30/15s (high stimulus, low damage),
high-cadence work, alactic 6-second bursts inside endurance rides. Coach
ruling on this order: Wed = Thirty-Fifteens, Thu = Cadence Work, Sat =
endurance with 6s bursts every ~14min.

## T4 — "Race sims" are a monotone surge loop, blind to the race
Both 5-hour Saturdays emitted 21x(13min @70% + 7s @150%) — the same surge
pattern any race would get. The race record carries terrain demands (Mammoth:
long seated climbs, altitude, punchy start) and the sims should be built from
them. House shape = the Act structure (Act 1 punchy start / Act 2 long grind
with low-cadence climbing / Act 3 structured finale on tired legs), with the
second sim as full dress rehearsal at race fuelling rate. Generator should
compose sims from race_characteristics, not a fixed surge loop.

## T5 — Archetype names promise the terminal form at Level 1
"3x15 Tempo" at L1 contains 3x8. "Norwegian 4x8" at L1 contains 3x8. The
athlete-facing title must describe the emitted level's actual content
(render titles from the level spec, not the archetype name).

## T6 — The delivery layer does not exist in the pipeline
Everything the coach calls the product's floor was hand-placed this order:
- dimensioned titles ("{name} - {set} - {NN}min - RPE{n}") + ifPlanned
- explicit Day Off cards on every restday (no blank dates, ever)
- the note series: START HERE (guide link + account fixes + how the week
  works), weekly briefings, FUELLING ladder, ALTITUDE/heat, GRAVEL GRIT 1-4,
  CHECK-IN, REHEARSAL DEBRIEF, RACE WEEK, AFTER
- hosted guide at intake.gravelgodcoaching.com/guides/<athlete>/ (+PDF)
- NUTRITION/HYDRATION blocks on long rides (drink-to-thirst language)
Automate emission of this layer from the sealed plan + fueling.yaml, in the
Monika-standard voice. Until then, the pre-delivery checklist must list it.

## T7 — Fuelling is a flat rate, not a ladder
Every quality day shipped "[HIGH FUEL: 56g/hr]" flat; race day says 66. The
gut-training ladder (climbs with the long rides toward race rate, rehearsal
at race rate on the final sim) exists in the coach's hand-built plans and in
`fueling.yaml`'s numbers but the generator never emits it. Emit a dated
ladder note + per-ride slots; workouts must not quote numbers that disagree
with it.

## T8 — Plan end has no "what's next"
The last calendar entry the athlete sees should carry the nurture close
(race-notes ask + bridge/next-block/coaching offer in the email-sequence
voice). Currently the plan just stops.

Related: `MONIKA_RENK_PIPELINE_FINDINGS.md` (boundary failures),
`RACE_COURSES_SCHEMA_TICKET.md` (multi-course schema).

---

# Round 2 — from the Sonja Field synthetic end-to-end (2026-08-15)

A fully synthetic order (Big Sugar, 9 weeks, female 52) generated, placed on
the TP test athlete via apply_contract + shipped delivery_render only, then
independently graded by two reviewers against the Monika fixture. Consensus:
transport shell strong (calendar completeness A, titles B-/C), coaching
product failing (overall F as a customer deliverable). New defects:

## T9 — Strength answers silently dropped at intake parse
Questionnaire said `Strength Training: yes / Current Strength: 2x-week /
Strength Equipment: full-gym`; the built profile carries
`currently_training: false, include_in_plan: false, sessions_per_week: 0`
with NO flag, and the plan ships zero strength. Silent field loss is the
order-killer family: parse failures must surface as coach-visible flags,
never defaults masquerading as answers.

## T10 — "Long Ride vs Race Duration" preview check counts the race itself
The check passed at "140%" because max long ride = 560min — which IS the
race-day entry. Real longest training ride: 249min vs a 560min race (44%).
Exclude race-day entries from the max; the check exists precisely to catch
this athlete (longest-ever ride 4-5h, 9.3h race) and it self-certified.

## T11 — Fuel ladder exists but never reaches race rate on a long ride
Tags progress 46 -> 51 -> 56 g/hr, but every 4h+ ride stays at 46-51 and the
only session at race rate is a 61-minute "simulation". The final long ride
before taper must rehearse the race prescription (see delivery_render
build_fuel_ladder for the target algorithm).

## T12 — Race-day template still ships the prohibited hydration copy
"clear urine morning of race" + "Don't wait until thirsty" are generated
fresh on every order (hand-purged for Guillermo, regenerated for Sonja).
Replace at the template source with drink-to-thirst + sodium +
finish-lighter-never-heavier.

## T14 — The Anaerobic Test archetype is not a test, it's an hour of nothing
Coach-flagged on the live card: 62 minutes = 20min warmup + 29min @55% +
ONE 3-minute all-out + cooldown — 36 TSS, 95% soft-pedaling, a single
unmeasured effort with no repeatability component. The house 360 protocol's
anaerobic day is 10s sprint + 1min capacity + 20x30/30 repeatability with
explicit fade measurement. Replace the archetype's structure (and justify
the 29-minute 55% block or delete it); a "test" must produce numbers the
plan can use.

## T13 — Renderer nits from live grading
Surge rides title as "6s @150%" without the rep count (structure lists
repeats individually, so the 15x prefix is lost); day-off synthesized from
a rest ZWO can carry 1min/1TSS; identical endurance days are
indistinguishable ("Endurance - 70min - RPE3" x19 — consider varying by
week context once notes exist).

---

# Round 3 — from the Sonja v2 regrade (2026-08-15, delivery layer live)

Dual regrade after steps 1-3b + T9/T10/T12: overall F -> D (sol) / C+
(orchestrator). Delivery-layer dimensions all A/B; substance unchanged
(T1-T4/T14 in flight). New defects:

## T15 — Strength track is placeholder programming
12 sessions landed but not consistently 2/week (weeks 1 and 4 got one), and
"full-gym" athletes receive unloaded jumps/hops/lunges and push-up/row
mobility circuits with no load prescriptions. strength_periodization must
respect the athlete's stated frequency and equipment tier (full-gym ->
loaded compound progressions with prescriptions), and title-case its names.

## T16 — Notes must cross-check the calendar they describe
The Sep 14 briefing led with the surge ride instead of Thursday's key
session, and the rehearsal debrief pointed at a "rehearsal" that is (until
T4 lands) a generic surge ride. Weekly-briefing key sessions should order
weekday quality first, and a consistency pass (future delivery_lint rule)
must verify every note reference (session names, ladder rungs, rehearsal
dates) against the placed calendar. Also: ladder note rounds to 5 while
workout tags carry raw prescription values (45/50/55 vs 46/51/56) — one
authoritative ladder, one rounding rule (Task I in flight); long rides
must carry the per-ride fuel/hydration description blocks; day-off cards
synthesized from rest ZWOs still carry 1min/1TSS; race-day card TSS 394 vs
description 393.

## T17 — Race-day pacing must match the goal and the day's length
A 52-year-old finisher facing ~9.3 hours was told to hit 88-94% FTP on
climbs and "increase effort as others fade." Race-day copy needs goal-type
and duration dispatch: finisher/long-day copy caps climb intensity, leads
with the ceiling decision rule, and frames the final third as holding
form, not attacking.

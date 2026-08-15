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

# Training Algorithm Evidence — Ratified Rules

**Status: RATIFIED by Matti Rowe 2026-08-23** (ruling record in §9).
Adversarially reviewed by GPT-5.6-sol 2026-08-23 (15 findings — 5 blockers,
9 major, 1 minor — all verified against live code and folded in before
commit; full findings: `docs/evidence/2026-08-23-sol-review-findings.md`).
This document is the canonical evidence-backed rule set for the plan- and
workout-generation algorithms. Any agent changing plan structure, workout
selection, progression, testing, fueling, or compliance logic MUST read this
file first and MUST cite the rule ID it is implementing. Full mining reports
with claim-level citations live in `docs/evidence/`.

Governing constraints (do not relax):

- WKO-proprietary metrics (mFTP, FRC, dFRC, TTE-as-metric, iLevels, stamina
  score, TIS) never surface in our product. Open analogues only (§7).
- Rules marked OPEN are not implemented until Matti rules.
- Contradictions with this document are surfaced, never silently resolved.
- Evidence tiers: `[P]` peer-reviewed · `[E]` expert-opinion (named coach on
  record) · `[H]` coaching heuristic · `[A]` anecdote · `[M]` model-derived.
- Citation keys: `R#` = WKO/Cusick store mining · `A1–J4` = Couzens/Seiler
  corpus mining · `WG-#` = wider-graph sweep (Matti-authored + Buchheit-Laursen
  FUNDAMENTALS + whitepapers). See `docs/evidence/2026-08-23-*.md`.

---

## 1. Plan shape (`calculate_plan_dates`, `block_chain`)

**AE-1.1 — Never fill the runway.** [M][E][H] A long runway produces a later
start plus a stabilization block, never longer phases. Base 12–16 weeks max;
peak 3–6 weeks, front-loaded. (R10, R41, R42, R112; H2; WG load-stabilization)

**AE-1.2 — Stabilization phase.** [M][E] Insert a hold-load phase between
Build and Peak for 12+ week preps: weekly TSS flat, specificity rising.
Peak CTL lands 8–12 weeks BEFORE race day; load flat-lines after. Basis:
a workout returns ~50% of its benefit at 30 days, +25% at 60, +12% at 90;
fatigue steady-states ~21 d while fitness compounds to ~126 d; constant-load
sim beats continuous ramp by ~6% peak fitness on ~4% less work. (H2, R10)
**Ruling Q7 addendum (Matti):** dimension work (position/cadence/terrain) is
woven into the stabilization phase, not just endurance fillers.

**AE-1.3 — Residual stacking.** [P] Sequence qualities by residual duration;
the gap between a quality's last block and race day must be shorter than its
residual: aerobic endurance 30±5 d, max strength 30±5 d, VO2max 18±4 d,
anaerobic glycolytic 18±4 d, max speed 5±3 d (Issurin 2008). Speed/alactic
work therefore belongs IN race week; VO2 touch inside the final ~2 weeks.
(R47; WG residual-training-effects)

**AE-1.4 — Ramp rate (ratified reconciliation, ruling Q1).** [E] Two caps,
both enforced: ≤8 CTL/week inside a loading block (2–4 weeks max before a
rest week) AND ≤10 CTL/month net after recovery weeks — the Couzens verbatim
is a hard +10/month (B1); the ratified Q1 wording allowed "10–12", so
implementers gate at 10 and treat 10–12 as a WARN band that is coach
override, not evidence. Halve both above CTL 100; treat CTL 135–165 as a
wall. Discount 15–20% for run-dominant athletes. Decelerate the ramp as
phase intensity rises: TSS scales as IF², so the week-budget multiplier
shrinks as the phase's IF climbs (session TSS >300 lingers ~2 days, >450
multi-day). Mechanism note: inflated FTP → inflated zones → inflated TSS
makes aggressive ramps look survivable — see AE-5.2. (R1, R2, R3, R4; B1,
E4; WG FUNDAMENTALS lever 10)

**AE-1.5 — CTL bands by training age, never age or FTP.** [E] Half-open
intervals: 1≤y<2 yr: <40/41–75/≥76 · 2≤y<5 yr: <60/61–95/≥96 · y≥5 yr:
<80/81–115/≥116. Subtract ~10 over age 50. Feasibility cap first: the hour
budget bounds the achievable CTL (6–8 h/wk ⇒ CTL ~75 ceiling) — never
prescribe a CTL target the hours cannot reach. Annual hours are the
classification primitive over any 2–3-week weekly sample: ~800 h/yr ≈
serious age-grouper tier, ~1,000 h/yr ≈ top tier. (R5, R6, R79; A1)

**AE-1.6 — Macrocycle length shrinks as intensity rises.** [E] Early base
3–5 wks; mid-late base 2–3; peak 2–3. Modality arc: HVLI → pyramidal →
polarized; polarized is effective ~6–10 weeks only — reserve for build/peak.
(R40)

**AE-1.7 — Gravel specificity (coach override of R45).** [E→ratified Matti
2026-08-23] Base/peak stays pyramidal for gravel/ultra (volume matters), BUT
race specificity is delivered through the race-sim workout class, pace-change
and dimension work, and aggressive in-ride carb practice — NOT through raw Z2
volume alone. Cusick's "volume is the specificity" is the floor, not the
method. Long Z1–Z2 rides carry an explicit fueling-practice objective. ~8-week
specific-prep window before the A race. (R45 as amended; R115; Matti ruling)

**AE-1.8 — Event-class plan-length gate + demand-vector selection.** [E]
Ultra-class events get 4–9 month preps; warn on (or refuse) sub-16-week
ultra requests. The existing 14-dimension race demand vector (7 course + 7
editorial, 1–5 each, across the 757-race database) drives the
archetype-category mix for the specific-prep window — a single "difficulty"
number never selects sessions. (WG ultra whitepaper;
gravel-guide-content.json ch2)

**AE-1.9 — Race calendar validation.** [E] 1–2 true peaks/year; warn at 3+
A-races. B/C races get no taper WEEK/PHASE — raced as hard training days
with athlete buy-in; C races one distance down. The existing 2-day B-race
overlay (easy day at −2, openers at −1; `calculate_plan_dates.py:592`,
`generate_athlete_package.py:3871`, spec overlay IDs) is explicitly
retained — it is race-day logistics, not a taper, and is NOT removed by
this rule. Mid-season reset pattern available. (R49, R50, R59; H6) —
annual-macro features beyond a single prep are PARKED for the coaching
ladder (ruling Q11).

**AE-1.10 — Short-runway and novice branches.** [E][H] <12 h/wk: sweet-spot
substitutes for LSD earlier; extra base period, never an extra build. Novice /
returning (training age <1 yr): Seiler onboarding state machine — 6 weeks
frequency only, 6 weeks duration, intensity only after a conversational
90-min ride (ruling Q10: also surfaces as a note in the plan). (R51; F1)

**AE-1.11 — Camps and doubles.** [E][H] Camp = 7–10 day overload landing 3–5
weeks pre-race, short rest after (extended rest gives the gain back). ≤5
continuous loading days (2-1-2 shape). Doubles: Base 1/2 only, disciplined
athletes, never late evening. (R52, R111; B4, I4)

**AE-1.12 — Taper shape (ruling Q8).** [A→ratified] Rest begins 10–14 days
out; then a reload of 2–3 hard efforts before the event so the athlete
doesn't arrive flat. Every reload effort stays inside the ratified taper
hard-content caps (no ≥92%-FTP rep >120 s — ramps counted by their ≥92%
excursion, not their average — and ≤15 min/900 s total ≥92% work per
session). In peak/race weeks manage ATL as the active lever; CTL is a
lagging result. Weakest evidence tier in this doc (anecdote), adopted
because it formalizes what openers already do. (R57, R58)

## 2. Intensity budget & distribution (`block_compliance`)

**AE-2.1 — Hard-minutes floor + hard-days cap (ruling Q2).** [Matti-authored]
90–120 min of genuinely hard work per week, minimum, for any athlete training
≥6 h/wk; below ~90 cumulative hard minutes VO2max gains are "small and
inconsistent". Day cap is maturity-conditional: novices 2, mature (≥1–2 yr)
3, VO2-focused blocks 2–2.5 (defined as ≤5 hard days per rolling 2-week
window). Floor and cap enforce together. **Precedence:** AE-2.1 applies only
after an athlete passes AE-1.10's intensity-graduation gate — true novices
inside the onboarding state machine are exempt from the hard-minutes floor.
**Migration:** active registry rule R05 currently permits novices 1–3
intensity sessions (`block_compliance.py:237`, SPEC_EARNED_SELECTION R05);
implementing this rule requires an R05 revision (owner review + version
bump per registry rules). ("The 80/20 Trap"; R19; F3)

**AE-2.2 — Volume-scaled ratio.** [Matti-authored] Intensity share scales
inversely with hours: ~70/30 at 7 h/wk → 75/25 at 10 h → 80/20 only at
12–15 h. One fixed ratio across volume tiers is wrong by house position.
**Accounting unit:** this split is measured by TIME-IN-ZONE (low = Z1–Z2
time; "hard" = everything above), computed per AE-2.3's declared ruler —
never by session count. (WG "80/20 Trap", "Peter Attia" draft; D4
reconciled by tier)

**AE-2.3 — TID shape must match the declared phase.** [E] Compute the week's
actual distribution; a "base" week whose computed shape is threshold-modality
(e.g. from hard group rides) fails. Polarized ≈ 1–2 hard days, 20–30% hard;
pyramidal ≈ 2–3, 40–50%; accounting unit declared explicitly (80/20 by
session count ≈ 90/10 by time-in-zone — same distribution, two rulers).
(R86; F4; J1)

**AE-2.4 — Anti-monotony set.** [E][H] No monotonic CTL climbs — every
mesocycle chain shows a visible dip. In Peak: volume slope ≤0 while intensity
slope >0. Consistency enforced at week scale, forbidden at day scale. No
single session format >3–5 weeks running. At least one load channel trending
up outside planned rest. Plans design for 60–70% adherence and carry a
first-class downgrade path. (R8, R43, R103, R104, R105; F6, J3)

**AE-2.5 — Weekly TIZ ceilings (caps, never additive minima).** [H] These
are per-band CEILINGS inside whatever "hard" budget AE-2.2 allows — they
are not requirements and are never summed: extensive (sweet-spot/tempo)
≤20–30% of weekly volume, hard ceiling 40%, >30% mature athletes only;
intensive (threshold+) ≤10–15%. Both bands cannot sit at their maxima in
the same week without violating AE-2.2, which governs. Sweet-spot ≤3
days/week — fewer, fuller sessions. (R15, R18)

**AE-2.7 — Session floors (ruling Q5).** [ratified] 45-min session floor;
recovery rides, openers, and the AE-1.10 novice branch are exempt. Sessions
tagged aerobic-development carry a 90-min floor (adaptations switch on
between 45 and 90 min — F7). Time-crunched sessions are complete on their
own at the floor, with "add Z2 / extend the warm-up if you have more time"
in the description (Workout Standards v1.0). (F7, J4; R17/R37 operate at
the interval layer beneath this)

**AE-2.8 — Endurance load-rate cap (ruling Q6).** [ratified] Endurance-
classified sessions ≤50 TSS/hr, enforced as a COMPUTED gate (planned TSS ÷
planned hours), not an authoring convention. Known offenders to fix:
`endurance_surges` L6 (58.5) and `tempo_3x15` (52.5–56). Pairs with the
ratified endurance IF band .60–.70 scaled down with duration (AE-5.6).
(R83, C1 finding; Workout Standards v1.0)

**AE-2.6 — Base keeps a pulse.** [H] One maintenance-intensity hard day per
8–14 workouts even in early base; ≥1 long near-LT1 ride/week in early base.
VO2 maintenance every 14 days stands (ruling Q12: residual-backed, R47) —
distinct from the 2–3-hard-days budget, which governs everything else.
(R36, R54)

## 3. Workout design & selection (`workout_selector`, renderer)

**AE-3.1 — Physiology gates on every generated/selected workout.** [P][M]
- VO2max sessions, T@VO2max gate with exact intervals: **FAIL <5 min or
  >18 min · WARN 5–8 min or >14–18 min · PASS 8–14 min.** (~12–30 min
  prescribed ≈ 15 min banked.) Computation: until a duration-matched %CP
  model ships, T@VO2max = seconds ≥106% FTP (the existing
  `GGTP/engine/physiology.py` proxy — over-counts short reps; compare
  designs, not truth). AE-3.4's per-category session ceilings DEFER to
  this gate for VO2-classified sessions. Under-execution floor: <50%
  W′ depletion = under-cooked (target ~2/3 drain).
- Threshold/anaerobic: W′bal nadir 0–6 kJ (CP = FTP/0.96, W′ = 20 kJ,
  Skiba differential; use differential model for micro-intervals).
- Sweet spot / G-Spot: expect near-zero W′ drawdown; sustained drain = the
  athlete rode hot.
- Good sets drain slightly deeper each rep; tank empty only at the end.
(WG FUNDAMENTALS + scorecard; R14, R93, R94, R95)

**AE-3.2 — Rep-length physics.** [P] VO2 on-ramp is 1:20–2:20, so VO2 reps
≥ ~2 min (Seiler 4×8 beat 4×4 and 4×16 — progress duration before watts).
SST reps ≥15 min; threshold reps ≥10 min. Micro-intervals: on ≤40 s, rest
≤15–20 s (30/15 default). Float ("on-off" recovery) optimum ≈70% of
vVO2max for short HIIT; over/under "overs" ≤110% or the session becomes
VO2 work. Zone-blend rule, precisely: do not TARGET a physiological
crossover within one work STEP ("best of both" single-step designs);
explicitly alternating over/under steps and multi-zone sessions (Float
Sets, Criss-Cross, Over-Unders) remain legitimate registered designs —
they are governed by the W′bal gate in AE-3.1 instead. (WG FUNDAMENTALS;
R17, R28, R35)

**AE-3.3 — Rest intervals are specified, not implied.** [H] Default ~1:1
timed from end of effort. Recovery power: ≤50 W for power-building sets;
50–60% FTP for capacity-building sets; always below FTP or the tank never
refills. Relief <2–3 min is passive. +1–2 min adaptive mid-set rest allowed
on max-aerobic repeats when power drops at rep 3–4. (R26, R27, R93)

**AE-3.4 — TIZ is the selection currency.** [H] Select and dose sessions by
accumulated time-in-zone against the session purpose; reps/watts/rest are
interchangeable levers to hit it. Session TIZ ceilings by category (tempo:
rec ~60 / cat 60–180 / pro 180+ min · SST: rec ≤45 / 45–80 by cat ·
max-aerobic ~15, rarely >20 min all levels). Terminate on elapsed TIZ vs
purpose — never on a fixed %-power-drop rule. (R13, R29, R36, R37)

**AE-3.5 — Targets from history, rendered as floors.** [H] Seed a new
interval target from the athlete's last ~3 similar-duration efforts; numeric
targets on reps 1–2 only, "match that feel" after. Rendered wattage ranges
are floors, not ceilings. Rep count from demonstrated capability (3–8
usable), never from the model. L5–L7 prescribed in watts only. (R32, R33,
R34; WG FUNDAMENTALS)

**AE-3.6 — Failure branches.** [H] Power on-target but duration fails
(fatigue ruled out) → shorten the rep, keep the watts. Completes once but
cannot repeat 2–3× → durability limiter: keep the wattage, build
repeatability. Consistently under target → add frequency before lowering the
target. (R30, R31, R88)

**AE-3.7 — Cadence and dimension work.** [E][ratified] Prescribe explicit
cadence spread (e.g. 65/85/105 rpm); early-base hard days biased 95–100+
rpm. Cadence is a programmed target where execution-critical (SFR/torque/
cadence work), description-level everywhere else (Workout Standards v1.0).
Low-cadence floors <60 rpm gate behind a knee-history flag (+29%
patellofemoral load at 70 vs 90 rpm). (R110; WG FUNDAMENTALS lever 7)

**AE-3.8 — Bounded athlete discretion in workout notes.** [H] Phase-gated
"feels great" rules rendered into workout copy: base → extend duration at
same power; peak → one watt harder, never add reps; failed set → resume
after 5–10 min only if early reps weren't already a struggle. (R106)

**AE-3.9 — Gravel archetype set.** [E] Long "TAN" tempo (rolling, seated,
natural surges, ~85% by average power, progresses past 60 min). Lactate-
stacking surge repeatability (Golich). Post-fatigue intervals phase-gated to
build/peak. Race-sim class per AE-1.7 (design interview with Matti pending).
(R25, R89, R96)

**AE-3.10 — Vocabulary cap.** [E] Variation serves physiology, not
entertainment; top pros run ~6–10 unique workout types/year. No novelty
rotation. (R39; WG "No One Cares If You're Bored")

**AE-3.11 — FatMax: name purged, mechanism retained (ruling Q3).**
[ratified] No workout, archetype, or copy may carry the FatMax name (or a
fasted variant — AE-6.3). The underlying mechanism — maximal fat oxidation
sits in Z2 near LT1 — is RETAINED as the documented physiological rationale
for the .60–.70 endurance band and its "ride the bottom-middle, not the
ceiling" prescription; without it the guide's Z2 justification is orphaned.
(C2 finding; "Sweet Spot Isn't that Sweet", "How To Do Workouts"; E3)

## 4. Progression (`series progression`)

**AE-4.1 — Plus-one, outcome-gated, one lever.** [H][E] Step each hard
session's TIZ +45 s to +1 min over the last comparable session. Advance only
after the current dose is reported manageable; repeat unchanged at most once
— never a third time ("Always Be Pushing", Coggan). Move exactly one of
{power, TIZ, rest}. Never progress volume and intensity in the same block.
**Supersession:** this replaces the current mechanical level-per-load-week
advance (`series_tracker.py:112`) and requires a registry R15 revision
(level deltas 0/1/2) — named migration in workstream 3; until that
migration lands, R15 remains the enforced rule. (R21, R22; B2; WG 11-lever
ontology)

**AE-4.2 — Direction of sub-threshold progression.** [E] Toward one longer
continuous effort: 1×30 → 2×20 → 1×45 → 2×30 → 1×60. Named error: 2×20 →
3×15 → 6×10. Extensive intervals: add reps at fixed duration, then cut rest
toward continuous. Micro-burst archetypes progress reps → then SETS → then
sessions/week (Rønnestad). (R23, R24; WG FUNDAMENTALS)

**AE-4.3 — Durability ratchet.** [E] Daily binary: extend or intensify,
never both. A duration held for ~6 weeks is maintenance; only a longer
session develops. Prefatigue ladder dosed in kJ (normalized /kg): fresh →
~1000–1500 → ~2000 → ~2500–3000+; bridge segment is intensity-specified.
Under fatigue de-rate VO2/anaerobic targets −10–20%, threshold near-normal;
fueling mandatory; not for novices. (I2; WG FUNDAMENTALS lever 8 —
Maunder 2021, Spragg 2024)

**AE-4.4 — Phase-conditional "more left" rule.** [H] Base/capacity: athlete
has more → add a rep. Final 4–5-week peak: go harder on the last rep
instead. (R78)

**AE-4.5 — Expect the dip.** [P] After an aggressive volume ramp, 3–5 weeks
of performance decline precede gains (Banister τ1 ≈ 40–42 d; 95%
steady-state ≈ 126 d). Do not insert corrective blocks inside the window;
set expectations in plan copy. (R9; WG delayed-training-effect)

## 5. Testing (`testing protocol`)

**AE-5.1 — Data gates before model-derived numbers.** [E] ≥30 days history
(90 preferred) with real max efforts short, medium, AND long before any
CP/W′-derived prescription ships; lead with the gap otherwise. WKO's ±5%/
±7.5 residual-trust bands are their calibration — derive our own. (R62)

**AE-5.2 — Never derive zones from an early-season FTP test.** [E] Best
20-min values come early, fresh, and anaerobically inflated; assume stated
FTP inflated 5–10%. This is the documented rationale for the G-Spot at
86–92% (vs sweet spot 88–94%) and feeds the ramp-rate mechanism in AE-1.4.
(E4; WG "Sweet Spot Isn't that Sweet")

**AE-5.3 — Baseline battery.** [E] 4–6 days, one max effort per day (5-min ·
long test · 1-min · recovery · sprints). Long-test duration by phenotype:
~20 min diesel / ~25 all-rounder / ~30 pursuit; hard cap 30. Match test
environment to training environment (≥75% indoor → test indoor). Round
displayed thresholds up to nearest 5 W, present as a range. Frame every test
as training. (R63, R64, R69, R71, R72)

**AE-5.4 — Testing blends into training after baseline.** [E] Near-max
efforts every 4–6 weeks (6–8 early base), steered by the stalest duration,
placed in week 2 of a cycle right after the rest week. Test after rest but
not cold (1–2 moderate days if fully off). Backfill the 1-min max for
frequent racers. Full re-baseline annually at the same calendar point. The
360 Testing Week protocol satisfies the battery (TP 230732). (R65–R68, R70)

**AE-5.5 — Aerobic benchmark is the phase-transition trigger (ruling Q9:
adopted, plus fix offenders).** [E] Every 4–8 weeks: 10 min @140 bpm + 10
min @150 bpm continuous; record power and EF (power/HR). EF ~1.4 = starting
age-grouper, ~2.0 = elite; reference improvement +60–80 W over six months of
base. When the benchmark plateaus while load rises: stop ramping, change
block intent. Cusick's variant gate: exit base when FTP ≈ 80–85% of power-
at-VO2max (open proxy: best recent 3–5 min power). CTL is never the
transition trigger and is never reported to the athlete as "fitness".
(D1, D2; R48; H3)

**AE-5.6 — LT1 field calibration as athlete-facing copy (ruling Q9).** [E]
Ship the field test in endurance workout copy: HR flat for 45+ min = below
LT1; drift beginning at 15–20 min = above it; talk test (full sentences =
Z2). NEVER hard-code an LT1 formula — all candidate formulas are disputed.
Endurance band stays IF .60–.70; LT1-adjacent work is the deliberate top of
the band, not the default. Long-duration tests are house policy (MLSS is
30–70 min; the "20-minute revolution" under-developed long capacity).
(D3, E2, E6; R73, R87)

**AE-5.7 — Durability probes.** [H] 2–3×/year, end of a training cycle,
separate from FTP retests: power-curve comparison before vs after a fixed
kJ split (~1000/1500/2000 kJ by race demand). This replaces WKO "stamina".
(R91; I1)

## 6. Fueling (`calculate_fueling`, workout copy)

**AE-6.1 — The bracket table is canon.** [Matti-authored, 38 refs] Carbs
DOWN as duration goes up: 2–4 h 80–100 g/hr · 4–8 h 60–80 · 8–12 h 50–70 ·
12–16 h 40–60 · 16+ h 30–50; positioned within bracket by W/kg (the exact
positioning/interpolation function is an OPEN implementation detail — the
methodology's exponent-1.4 note is not yet an executable formula and must
be specified and sol-reviewed before code); gut ceiling ~90–120 g/hr;
brackets absorb Jensen's-inequality error on variable gravel power. Amateur
racing: 70–90 g/hr is plenty. **Migration:** the live implementation
(`athletes/scripts/fueling_policy.py` — absolute-work formula
`48 + .055·(FTP·IF) + .10·(kg−60) + goal`, 90 g/hr ceiling through 8 h)
predates this table and differs from it; reconciling them is a named
workstream item requiring a `POLICY_VERSION` bump, not a silent edit.
Race-sim and gravel long rides push carb practice hard per AE-1.7. (WG
fueling-methodology; "The 120 Trap")

**AE-6.2 — Gut training is a schedulable block.** [P] 8–10 weeks pre-race;
+16% exogenous oxidation over 28 days; up to −60% GI symptoms; start in the
lower bracket third for a first major event. (WG fueling-methodology)

**AE-6.3 — Fasted rides stay purged.** [E] All-or-nothing protocol (near-
daily 8–10 weeks) or zero benefit — the watered-down version has no
defenders. (R113; Workout Standards v1.0)

**AE-6.4 — OPEN (ruling Q4 = "Maybe?"): race-page fueling copy.** The
Transcontinental page prescribes 80–100 g/hr where the methodology says
30–50 for 16 h+. Do NOT change race pages until Matti confirms; flag any
new race-page fueling copy against AE-6.1 in the meantime.

**AE-6.5 — Hydration.** [H] Start sessions 100% hydrated; sodium by sweat-
salt phenotype: clean bibs ~500 mg/bottle · kinda salty 750–1000 · really
salty 1500. (WG hydration article)

## 7. WKO-proprietary gate (hard constraints)

| WKO construct | Status | Open substitute |
|---|---|---|
| stamina 0–100 | BANNED | kJ-split power-decay probe (AE-5.7) |
| population phenotype %, strengths charts | BANNED | self-relative PD-curve shape only |
| TIS badges/targets | numbers BANNED | structure may inspire a home-grown TIZ dose metric |
| WKO residual bands ±5%/±7.5 | BANNED | derive our own |
| mFTP/FRC/dFRC/TTE/iLevels | analogues OK | CP, W′, differential W′bal (Skiba/Froncioni-Clarke), t=W′/(P−CP), duration-matched %CP |
| Couzens ln(volume) regression | NOT IN CORPUS | concave-returns shape usable; NEVER fabricate coefficients |

## 8. Masters & classification (`athlete classification`)

**AE-8.1 — Masters keep the top end.** [E] LT1 declines only ~5% from 40→65;
VO2max (~11–12%) is what decays. Preserve the VO2 stimulus, pay with
spacing. The "exactly 3 intense sessions/week, one per discipline,
rotating" prescription is scoped to **60+ MULTISPORT athletes** (its source
is triathlon coaching). Cycling-only masters follow AE-2.1's day caps with
extended inter-session spacing (and AE-1.10 precedence for novices).
Shorter reps (30–60 s at 1:2), micro-intervals preferred, hills for run
VO2. Tendon caution on intensity re-entry. (G1, G2)

**AE-8.2 — Masters volume is start-point-dependent.** [E] Low lifetime
volume → volume goes UP (decline is ~1%/yr only if already training to
potential); 15–18 h/wk into upper 50s → hold or trim; never below 10–12
without cause. Consistency beats periodized peaks for masters. (G3, G4, G6;
WG masters article)

**AE-8.3 — Phenotype, self-relative.** [E] Classify from the shape of the
athlete's own %FTP-normalized PD curve vs their history. Assessment scatter
= consistency diagnostic. Higher anaerobic bias → longer, lower-power
max-aerobic reps. Peak entry: capacity-vs-power quadrant, prioritize exactly
one. Limiter selection cross-checks event demand — "room to grow" ≠
"potential to grow". (R74–R77, R80)

**AE-8.4 — Strength scheduling.** [P for injury data] Masters strength is
protected and fresh (4–6 reps × 3 sets, 1–2 in reserve, ≥1.5 g/kg protein);
never off the back of / day after VO2 work (morning-before OK as primer).
Durability blocks in younger high-volume athletes may deliberately place
strength after accumulated fatigue. Never the day before a key session.
Full 4-phase periodization in the Matti-authored strength program. (G5, I3;
WG strength 2nd ed.)

**AE-8.5 — Readiness gating (plan-side contract).** [E; HRV-guided ≈+6%
VO2max in Finnish replications] The plan is the prior; readiness only
adjusts it (Altini constraint). The gate is a COMPOSITE — chest-strap HRV
against a 7-day rolling baseline and personal normal range, plus resting
HR, plus two 1–10 subjective scales (fatigue, life stress) — never a
scalar score. Named inversion: high HRV + unusually low RHR + low arousal
= FATIGUED, suppress the hard session. Sleep overrides the stack via the
graded downgrade ladder, encoded as first-class session metadata: (1)
attempt the session's aerobic volume with intervals dropped → (2) 1 h
recovery ride → (3) abort, reassess tomorrow. In peak phase yesterday's
subjective report outranks any power-derived metric. Plan-side scope:
every hard session carries its downgrade ladder; live gating executes in
Endure/coaching, not in static plan generation. (C2–C7, R108; aligns with
dampened-adaptation doctrine — trends, not events)

## 9. Ruling record (Matti, 2026-08-23, "Algo responses")

| Q | Subject | Ruling |
|---|---|---|
| Q1 | Ramp rate | **Agree** — dual-timescale caps (AE-1.4) |
| Q2 | Hard-minutes floor + maturity day cap | **Yes** (AE-2.1) |
| Q3 | FatMax name/mechanism split | **Yes** — purge name; mechanism documented as the .60–.70 rationale |
| Q4 | Race-page fueling fix | **"Maybe?" → OPEN** (AE-6.4) — no race-page edits yet |
| Q5 | 45-min floor refinements | **Agree** — keep 45 floor; 90-min floor for aerobic-development-tagged sessions |
| Q6 | 50 TSS/hr cap enforcement | **Yes** — computed gate + fix the two offending archetypes |
| Q7 | Plan-shape redesign | **Yes, plus dimension work woven in** (AE-1.2) |
| Q8 | Taper reload | **Yes** — rest 10–14 d out, then 2–3 hard efforts inside ratified hard-content caps |
| Q9 | LT1 anchoring | **Yes, and fix** offenders (zone-derivation from early-season FTP; copy) (AE-5.5/5.6) |
| Q10 | Novice onboarding state machine | **Yes; also add as a note in training plans** (AE-1.10) |
| Q11 | Annual-scale features | **Yes** — cheap parts now (A-race validation, B/C no-taper); annual macro parked |
| Q12 | VO2 14-day cadence | *(no answer)* — recommendation stood: no change, documented distinction (AE-2.6) |

**Additional coach ruling (same date):** Cusick R45 ("volume is the
specificity" for gravel) is overridden per AE-1.7 — race-sim + pace-change/
dimension work + hard carb practice is the house specificity method, on a
pyramidal base.

## 9b. Hook → module map

The section-heading hook names are conceptual; the concrete modules (all
under `athletes/scripts/` unless noted) are:

| Hook (as used above) | Module(s) |
|---|---|
| calculate_plan_dates / plan shape | `calculate_plan_dates.py` |
| block_chain | `calculate_plan_dates.py` + block assembly in `generate_athlete_package.py` |
| workout_selector / renderer | `workout_selector.py`, `library_selector.py`, `workout_mapper.py`, `generate_athlete_package.py`, `nate_workout_generator.py` |
| series progression | `series_tracker.py` (+ level semantics in `generate_athlete_package.py`) |
| block_compliance / gates | `block_compliance.py`, `post_render_validator.py`, `validate_plan_package.py`; physiology scoring: `gravel-god-training-plans/engine/physiology.py` + `tools/validate_physiology.py` |
| testing protocol / athlete classification | intake + `generate_athlete_package.py` (no single module yet — new code lands here) |
| fueling | `fueling_policy.py` |

Curated TP selection (`library_selector.py`) runs BEFORE compliance inside
`generate_athlete_package.py` — selection-time rules must live in the
selector, not only in post-hoc gates.

## 10. Workstreams (execution scope, in order)

1. **Library fixes** — the 79/234 gate failures + purge list. The scored
   library is `experimental-workout-library/` in the MAIN pipeline checkout
   (scorecard: `experimental-workout-library/_ENRICHMENT_SCORECARD.md`;
   absent from worktrees until merged). The native archetype catalog (100
   archetypes × 6 levels) and the TP-curated library are DIFFERENT corpora
   and must be independently re-scored under the AE-3.1 gates
   (mechanical, cheap executors).
2. **Gates** — AE-3.1 physiology gates + AE-2.x compliance rules into
   `block_compliance` / `post_render_validator`.
3. **Progression core** — AE-4.1/4.2 into series progression;
   AE-2.1/2.2 budget.
4. **Plan-shape redesign** — AE-1.1…1.5 into `calculate_plan_dates` /
   `block_chain` (largest change; own spec + sol review).
5. **Standard training plans** — apply to master plans, published TP plans,
   and plan guides (gravel-god-training-plans).
6. **Coached-athlete builder** — same rules into the coaching intake/build
   path; correct recent athlete plans (audit in progress).
7. **Evidence expansion** — That Triathlon Show / Fast Talk Labs / Empirical
   Cycling mining → addenda to this doc after Matti review.

Landmines for implementers: the Couzens `distilled/*.json` files contain
confirmed mis-paraphrases (e.g. "10 CTL/month" → "10 percent") — implement
from classified verbatims only. Sol adversarial review is mandatory before
dispatch on every workstream above (house rule).

---

## 11. Round 2 — PENDING, NOT RATIFIED (mined 2026-08-23, awaiting Matti)

Sources: `docs/evidence/2026-08-23-empirical-cycling-mining.md` (Kolie
Moore, web-sourced — several claims UNVERIFIED) and
`docs/evidence/2026-08-23-triathlon-fasttalk-mining.md` (That Triathlon
Show + Fast Talk Labs, verbatim-sourced). NOTHING in this section may be
implemented until it moves into §1–§8 with a ruling.

Round-2 ruling queue:

- **Q13 — Density blocks vs ramp caps (HIGH).** Moore deliberately clusters
  4 consecutive hard days → 3 easy → 3 SST (documented case: +29 W FTP in 2
  weeks) to break plateaus. A strict within-block ramp cap (AE-1.4) and the
  2–3-hard-days cap would forbid the structure. Sanction a bounded
  "density block" archetype as an explicit exception, or reject?
- **Q14 — VO2 anchoring (HIGH, well-corroborated).** Anchor VO2max interval
  targets to 5-min mean-max power, not %FTP (Henderson/Connor worked case:
  same %FTP target trivial for one athlete, failed two national champions;
  Eriksson's duration-offset table: 3–4 min reps ≈ 95% of 5-min power,
  ±2–3 %-points per minute of rep-duration change). Threshold anchors to
  the 30–60-min power band, not a point FTP.
- **Q15 — FTP derivation & TTE testing.** FTP is not 95% of 20-min power
  (phenotype range 86–96%); TTE at FTP is individual (30–70 min). Adopt
  Moore's TTE-anchored progressive test protocols as a testing option
  alongside the baseline battery? Hunter Allen corroborates the failure
  mode: ~50–60% of athletes historically set threshold too high.
- **Q16 — Endurance floor vs low LT1.** Moore: some athletes' LT1 sits at
  50–55% FTP — a hard .60 IF floor would push them above LT1 on "easy"
  days. Allow a tested-LT1 override below the .60 floor?
- **Q17 — 45-min floor: frequency-training exemption.** Tipper (Ben
  Healy's coach) and Byrn prescribe 20–30-min frequency sessions as real
  training for time-crunched athletes; Eriksson's novice plans run shorter
  still. Add a "frequency/combo session" exemption class (alongside
  recovery/openers) plus an explicit novice exemption?
- **Q18 — TSS/CTL validity cross-check (architectural).** Eriksson:
  TSS/CTL invalid across triathlon disciplines and terrain; recommends
  rolling 6-week/3-month volume averages as the primary load lens. Moore
  implies the same. Add a volume-based cross-check layer beside CTL?
- **Q19 — Recovery-week band edge.** Peter Leo's running guidance ≈67% of
  peak volume (don't dump chronic volume) sits just above the ratified
  50–65%. Widen to 50–70% for run volume, or hold?
- **Q20 — Twitch-profile conditioning.** Fast-twitch athletes get more
  rest per rep (threshold 3:1→2:1 vs 4:1→3:1) and are killed by constant
  70–75% FTP riding and long threshold volume; slow-twitch tolerate long
  reps happily. Encode profile-conditional recovery ratios and endurance
  ceilings?
- **Q21 — Concurrent-training spacing (clean addition).** Moore: same-day
  strength+endurance = endurance first with ≥3 h gap; otherwise 24–48 h
  separation; >2–3 h rides or >80% FTP intervals on strength days risk the
  hypertrophy signal; heavy leg day depletes glycogen ~38% (days to
  refill). Adopt into strength scheduling?
- **Q22 — Cheap adds bundle.** (a) 90-min sub-threshold drift test as a
  second durability probe (Zanini: weekly >90-min long runs cut economy
  drift ~50%); (b) heat-acclimation block: ~10 × 1-h sessions across ~2
  weeks pre-race for hot events; (c) novice template: 4 weeks easy-only
  before any intensity, first hard session 5×1min, year-one long-run cap
  45–60 min; (d) post-A-race immune gate (~10 days). Adopt all?

Clarification (no ruling needed): the triathlon miner flagged "VO2 every
14 days" as contradicted by weekly in-season VO2 practice — misread. The
ratified rule is a MAINTENANCE FLOOR (sparsest allowed spacing, base
included), not a prescription cadence; build/peak frequency is governed by
AE-2.1. Wording in Workout Standards to be clarified accordingly.

Verification debts (round 2): Moore's W′bal critique NOT found (expected
but unlocated — needs podcast transcripts); hard-start VO2 claims
UNVERIFIED (blocked fetches); ramp-test critique rationale is community
paraphrase only. None of these may be cited as Moore's position.

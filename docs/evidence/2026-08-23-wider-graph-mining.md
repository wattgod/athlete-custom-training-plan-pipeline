Sweep complete. Findings below, grouped by pipeline hook.

---

# EVIDENCE SWEEP — plan/workout generation, outside `knowledge/sport-science/`

**Stores actually productive:** `writing-graph` (Matti-authored, richest), the interval-manipulation whitepaper + scorecard, `endure-labs-graph/knowledge/*.md` (3 root notes), `gravel-race-automation/docs/whitepapers/`, gravel-god fueling methodology.
**Stores that came up dry:** `endure-labs-graph/pitfalls/` (all engineering), `endure-labs-graph/memory/` (product/process only — one relevant note), `endure-labs-graph/research/` (FIT parsing only), `training-plans` collection (5,899 docs are per-athlete generated output — `methodology.yaml`, no rationale/research docs at all).

---

## 1. WORKOUT SELECTION

**CLAIM** A workout is 11 orthogonal levers, not one difficulty knob; progress ONE and hold the rest so you know what drove the adaptation.
· **NUMBERS** 9 Buchheit-Laursen variables + dose + modality; 6 acute response types; 4 formats (long 2–4 min / short <45 s / repeated-sprint ≤10 s / SIT 20–30 s)
· **SOURCE** `/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/experimental-workout-library/FUNDAMENTALS_interval-manipulation.md` (Buchheit & Laursen, Sports Med 2013 I & II)
· **RELEVANCE** This is the missing selection *ontology*. `workout_selector.py` currently picks by name; this lets it pick by physiological target and justify the pick.

**CLAIM** Aerobic sessions should be scored on T@VO₂max (~10 min/session target); threshold/anaerobic on W′bal nadir (small positive on the final rep).
· **NUMBERS** T@VO₂max band 8–14 min = pass; W′bal nadir band 0–6 kJ = pass, seed W′ 20 kJ; CP ≈ FTP/0.96
· **SOURCE** same file + `_ENRICHMENT_SCORECARD.md`
· **RELEVANCE** Two computable acceptance gates for every generated workout. Directly implementable as a compliance rule #12/#13.

**CLAIM** The house library, when scored against those gates, fails 1 in 3 combos — and the failures are systematic by archetype, not random.
· **NUMBERS** 234 archetype×level combos: **155 PASS / 79 FAIL**. Whole-archetype failures: `vo2_5x3_classic` (all 6, T@VO₂max 16–31 min = way over), `ronnestad_40_20` L2–L6 (15–23 min), `float_sets` (all 6, W′ never drains: nadir 20.0 kJ), `criss_cross` (all 6, nadir 18.8–19.1 kJ — the "overs" don't bite), `gspot_criss_cross` (all 6), `wprime_depletion` L2–L6 (nadir −0.9 → **−26.4 kJ**, physiologically impossible), `descending_vo2_pyramid` L5–L6 (nadir −0.9, −3.8), `tired_30_30` (T@VO₂max stuck at 6.0 min across all 6 levels — the progression axis does nothing)
· **SOURCE** `_ENRICHMENT_SCORECARD.md` (same dir)
· **RELEVANCE** A ready-made audit of which library entries are mis-dosed. `tired_30_30` progressing 75→175 min with zero change in T@VO₂max is a pure duration-inflation bug.

**CLAIM** Rep length must clear VO₂ kinetics or the session under-delivers; but too long collapses intensity.
· **NUMBERS** VO₂ takes **1:20–2:20** to reach max; 1-min reps → ~82% peak VO₂ vs ~92% at 2 min. Seiler 4×4/4×8/4×16 = 94/90/88% HRpeak, 13.2/9.6/4.9 mM lactate — **4×8 won with ~2× the gain**. Progress duration before watts.
· **SOURCE** FUNDAMENTALS (Seiler 2013)
· **RELEVANCE** Level-ladder axis policy: the default progression axis for VO2 archetypes should be `work_duration`, not `reps`.

**CLAIM** Recovery-interval duration has a floor of benefit at ~2 min; below/above that you lose either power or nothing.
· **NUMBERS** Velocity in 4-min bouts rises 1→2 min recovery but **not** 2→4 min; athletes self-select ~118 s. For relief <2–3 min keep it **passive**. BL optimum float ≈ **70% vVO₂max** for short HIIT.
· **SOURCE** FUNDAMENTALS (Seiler & Hetlelid 2005)
· **RELEVANCE** Hard bounds for the `recovery_duration`/`recovery_intensity` axes in the ZWO renderer.

**CLAIM** Splitting reps into series *reduces* total T@VO₂max but buys quality — so series count is a quality lever, not a volume lever.
· **NUMBERS** Rønnestad canonical: **3 series × (13 × 30s @ MAP / 15s @ 50%), 3 min between**; progress reps 12→13, then series 3→5, then sessions/week; ~3× the VO₂max gain of effort-matched 4×5-min
· **SOURCE** FUNDAMENTALS (Rønnestad 2015/2020)
· **RELEVANCE** Correct progression ordering for micro-burst archetypes; the STATUS file flags that L5–L6 currently grow reps (Billat L6 ≈ 3×11) when they should grow sets.

**CLAIM** Prescribe L5–L7 in **watts only** — HR and RPE lag or fail at those intensities.
· **SOURCE** FUNDAMENTALS, "Safety gates to encode"
· **RELEVANCE** Renderer rule for ZWO text events / guide copy.

---

## 2. WEEK & PHASE SEQUENCING

**CLAIM** Phases should be stacked by *residual decay rate*, most durable first — the current Base→Build→Peak calculator treats phases as independent.
· **NUMBERS** Issurin 2008 residuals: aerobic endurance **30 ± 5 d**, max strength **30 ± 5 d**, aerobic power/VO₂max **18 ± 4 d**, anaerobic glycolytic **18 ± 4 d**, max speed **5 ± 3 d**
· **SOURCE** `/Users/mattirowe/endure-labs-graph/knowledge/residual-training-effects.md` (★★★★☆)
· **RELEVANCE** Independently justifies the 14-day VO2 rule (18 ± 4 d residual → 14 d spacing sits safely inside the lower bound) and says race-specific speed/alactic work belongs in the last ~5 days, i.e. taper and race week — which is exactly where recovery-week strides live.

**CLAIM** There is a missing phase between Build and Peak: **Load Stabilization** — hold weekly TSS constant, raise specificity, let fitness compound while fatigue plateaus.
· **NUMBERS** With CTL_TC=42 / ATL_TC=7: fatigue steady-state ~21 d (3×7), fitness ~126 d (3×42) → a **21–126 day window** where fatigue is flat and fitness still climbing. Model sim (τ₁=40, τ₂=10, k₁=0.2, k₂=0.35): constant load vs continuous ramp = **~6% higher peak fitness on ~4% less total work**. Maps to Issurin Accumulation→Transmutation→Realization. Caveat: model predictions, not measurements; τ₁ varies ~30–60 d across athletes; applies to 12+ week preps.
· **SOURCE** `/Users/mattirowe/endure-labs-graph/knowledge/load-stabilization-phase.md`
· **RELEVANCE** Highest-leverage sequencing change available. Explicitly names the failure mode "phase-calculator fills all available time with a continuous ramp" — which is what `calculate_plan_dates.py` does.

**CLAIM** Adaptation is delayed by weeks-to-months; impatient athletes mistake the delay for a deficit and add stimulus, interrupting the adaptation already underway.
· **NUMBERS** Banister τ₁ ≈ **40–42 days**; time to 95% of fitness steady state ≈ 3τ₁ ≈ **126 days**
· **SOURCE** `/Users/mattirowe/endure-labs-graph/knowledge/delayed-training-effect.md` (★★★★★) · echoed Matti-authored in "How To Do Workouts The Right Way" ("fitness is a lagging outcome… if you do a VO2max workout today you're not going to wake up tomorrow with a better VO2max")
· **RELEVANCE** Justifies damping the plan's response to any single week and setting expectation copy in the guide.

**CLAIM** *Frequency* is a first-class load variable — spacing beats cramming at equal volume.
· **SOURCE** "The Big Three: Frequency, Duration, and Intensity" (**Matti-authored**, 2026-02-13) — `writing-graph/inbox/gravel-god/the-big-three-frequency-duration-and-intensity.md`
· **RELEVANCE** Names **density** ("how closely spaced high-effort workouts are") as a design axis distinct from dose. Also: "long endurance sessions stress your autonomic nervous system similarly to high-intensity work, potentially requiring less total recovery" — relevant to whether a long ride counts against the intensity budget.

---

## 3. PROGRESSION & INTENSITY DISTRIBUTION

**CLAIM (contradicts a flat 80/20)** Polarized ratios must scale *inversely* with volume — the low-volume athlete needs MORE intensity per hour, not less.
· **NUMBERS** **At 7 h/wk → ~70/30. At 10 h → ~75/25. At 12–15 h → 80/20 becomes correct.** Floor: **90–120 min of genuinely hard work per week**, minimum; below ~90 min cumulative hard time, VO₂max improvement is "small and inconsistent." 20% of 7 h = 1 h 24 min = "six minutes below the minimum effective dose." Pogačar rides 28–32 h/wk → 20% = 6 h of real intensity weekly.
· **SOURCE** "The 80/20 Trap" (**Matti-authored**, v2 draft) — `/Users/mattirowe/Desktop/Projects/writing-graph/drafts/the-80-20-trap-v2.md`
· **RELEVANCE** Directly parameterizes the intensity budget by weekly hours. Cross-check: 2–3 intensity days/week at ~30 min work each ≈ 60–90 min — **may sit below Matti's own stated floor for the 6–9 h athlete.**

**CLAIM (same, restated)** "If you only have 8 hours a week, you need proportionally more intensity, not less. The cult tells you the opposite."
· **NUMBERS** The "Pogačar is 85% Zone 2" number = 25 h Z2 **and 4.5 h/wk of VO₂max/threshold/above-LT2**. Survivorship bias: he built the engine on hard efforts as a teenager, then settled into 85/15 to *maintain* it.
· **SOURCE** "Peter Attia Stole Your Training Plan" (**Matti-authored** draft)
· **RELEVANCE** Guide copy + methodology-scoring rationale for why low-hours athletes don't get MAF/pure-polarized.

**CLAIM** Ramp rate should *decelerate* as intensity is added, because TSS scales as IF².
· **NUMBERS** TSS = IF²·hrs·100. Session TSS **>300 lingers ~2 days, >450 multi-day**. TSS under-weights neuromuscular and durability work.
· **SOURCE** FUNDAMENTALS lever 10
· **RELEVANCE** Week-budget logic (`load = hours×1.10`) is duration-linear; this says the multiplier should shrink as the phase's IF rises.

**CLAIM** TSS is a useful single-dimension collapse but blind to *kind* of stress.
· **SOURCE** "Keep Trusting TSS Blindly" + "Sweet Spot Isn't that Sweet" §TSS (**Matti-authored**) — `writing-graph/inbox/gravel-god/sweet-spot-training-cycling.md`
· **RELEVANCE** Supports the FUNDAMENTALS position that dose gates must sit *alongside* T@VO₂max/W′bal gates, not replace them.

---

## 4. TAPER

**CLAIM** A taper that is all-intensity is a build week in disguise — exactly 1 opener, rest easy.
· **SOURCE** `athlete-custom-training-plan-pipeline/CLAUDE.md`, "Taper phase is NOT all-intensity" pitfall (already ratified, listed for completeness)

**CLAIM** For long-horizon events, taper is a *consolidation* window in which nothing new enters — no new gear, no new fueling, no new route theory.
· **NUMBERS** Final **4–8 weeks** for a 6–9 month ultra build
· **SOURCE** `/Users/mattirowe/Documents/GravelGod/gravel-race-automation/docs/whitepapers/ultra-bikepacking-training-white-paper.md` §4.4
· **RELEVANCE** Taper-week workout notes should carry a "nothing new" constraint block; distinct from the current TSS-reduction-only taper.

**CLAIM** Residual decay says what to keep alive through taper: aerobic base needs no maintenance (30 d), VO₂max needs a touch (18 d), speed decays in 5 d so alactic work must be *in* the final week.
· **SOURCE** `endure-labs-graph/knowledge/residual-training-effects.md`
· **RELEVANCE** Gives a principled taper composition rather than a percentage cut. **Corroborates** the ratified "recovery weeks = Z2 + drills + alactic strides" pattern and extends it to race week.

---

## 5. TESTING & ASSESSMENT

**CLAIM (Matti-authored, load-bearing)** Athletes' stated FTP is systematically inflated **5–10%**, so any %FTP prescription is really a higher-zone prescription — the whole basis of the Sweet Spot critique.
· **NUMBERS** Worked example: tested 250 W (via the standard 95%-of-20-min, or FasCat's 93%), true 60-min ≈ 235 W. A 3×20 @ 235 W drifts to 107% of momentary threshold by interval 2 and **109% by interval 3**. Sweet Spot 88–94% therefore lands *above* threshold most of the time.
· **SOURCE** "Sweet Spot Isn't that Sweet" (**Matti-authored**)
· **RELEVANCE** Argues for a conservative FTP derivation coefficient in the pipeline and for zone bands that assume inflation.

**CLAIM (Matti-authored)** The **G-Spot = 86–92% FTP** — deliberately shifted down from Sweet Spot's 88–94% so that an athlete with an inflated FTP is still genuinely sub-threshold.
· **SOURCE** "Sweet Spot Isn't that Sweet," closing section
· **RELEVANCE** This is the canonical definition and the *reason* for the offset. The pipeline has a `G_Spot` category and the experimental engine has `gspot_intervals` / `gspot_progressive` / `gspot_criss_cross` — the last of which **fails the W′bal gate at all 6 levels** (nadir 20.0 kJ at L1–L4 = the criss-cross never drains W′; it's a steady-state block with cosmetic crosses).

**CLAIM** Power meters disagree with each other AND with themselves; single-workout numbers are not evidence.
· **NUMBERS** Same effort read 500/460/480 W across SRM/Stages/PowerTap; day-to-day drift on one meter 230–258 W for a nominal 250 W
· **SOURCE** "5 Ways to Become a Power Meter Clown" (**Matti-authored**)
· **RELEVANCE** Testing cadence and how the guide frames test-to-test deltas; supports trend-based rather than event-based adaptation.

**CLAIM** Free field test beats the lactate meter for zone placement: full sentence = Z2, full paragraph = low Z2, single words = past LT1.
· **SOURCE** "The 80/20 Trap" (**Matti-authored**)
· **RELEVANCE** RPE/talk-test calibration language for every endurance workout description — and the ultra whitepaper says RPE calibration matters *more* than power benchmarks for long events.

**CLAIM** Warm-up floor before any test or hard session: **at least 10 min, ideally 15**, Z1→Z2 lift at high cadence.
· **SOURCE** "How To Do Workouts The Right Way" (**Matti-authored**)
· **RELEVANCE** Matches the experimental engine's decision #10 (aerobic work gets a 10-min Z1→Z2 lift only; only hard work gets a real primer).

---

## 6. DURABILITY / FATIGUE RESISTANCE

**CLAIM** Durability is the deterioration of the power profile over a long ride, **independent of fresh fitness** — two riders with equal fresh FTP can differ hugely at hour 3.
· **NUMBERS** Pros' 5/12-min power declines around **1000–3000 kJ** (U23 collapse ~1500, elite ~2500 — van Erp). 2025 review: **10–20% decline after high-intensity prior work**. It is the **intensity of the bridge work, not kJ total**, that drives the decline (Spragg): **W′ and sprint power fall while CP holds.**
· **SOURCE** FUNDAMENTALS lever 8 (Maunder 2021; Spragg 2024; van Erp)
· **RELEVANCE** Prefatigue should be dosed in **kJ·kg⁻¹**, and the bridge segment must be *intensity*-specified, not just long. Current Durability archetypes specify duration.

**CLAIM** Under fatigue, **de-rate VO₂/anaerobic targets 10–20%; keep threshold near-normal.** Fueling mandatory. Not for novices.
· **NUMBERS** Prefatigue ladder: fresh → ~1000–1500 → ~2000 → ~2500–3000+ kJ
· **SOURCE** FUNDAMENTALS lever 8 + "Safety gates to encode"
· **RELEVANCE** A concrete, encodable rule the pipeline does not currently have. `tired_30_30` in the experimental library appears NOT to de-rate (T@VO₂max frozen at 6.0 min across all levels while duration inflates 75→175 min).

**CLAIM** For ultra-length demand, durability stops being one quality among several and becomes *the organizing quality*; the long ride progresses in **state**, not just duration.
· **NUMBERS** Progression: long rides fed normally → long rides at the back half of big weeks → back-to-back long days → 2–4 day loaded simulation with full race systems
· **SOURCE** ultra-bikepacking whitepaper §2, §4.2–4.3
· **RELEVANCE** A named 3-rung "state" ladder for the long-ride slot that generalizes below ultra distance.

---

## 7. FUELING

**CLAIM (contradicts the "more is better" default)** Carb needs go **DOWN** as race duration goes up, because intensity drops and fat oxidation rises.
· **NUMBERS** Brackets: **2–4 h → 80–100 g/hr · 4–8 h → 60–80 · 8–12 h → 50–70 · 12–16 h → 40–60 · 16+ h → 30–50.** W/kg positions within bracket (exponent 1.4). Gut ceiling ~90–120 g/hr absolute. Worked: 95 kg/220 W/2.3 W/kg, 6.5 h → **63 g/hr**; 70 kg/280 W/4.0 W/kg, 6.5 h → **75 g/hr**.
· **SOURCE** `writing-graph/inbox/gravel-god/fueling-methodology.md` (Gravel God house methodology, 38 refs)
· **RELEVANCE** This is the canonical fueling formula and it is *bracket-bounded on purpose* (see Jensen's inequality below). `calculate_fueling.py` should be checked against it.

**CLAIM (Matti-authored)** 120 g/hr is a workload number, not a status number — amateurs should eat what their wattage oxidizes.
· **NUMBERS** Pogačar at 350–420 W for 5 h burns 150–175 g CHO/hr, so 120 g/hr is a *deficit* for him. Amateur at 180 W for 3 h: ~550 kcal/hr, CHO 40–50% of that = **55–70 g/hr**; at 120 g/hr, 50–65 g is unabsorbed osmotic load. **70–90 g/hr is plenty for amateur racing.** Gut training raises *tolerance*, never *oxidation* beyond muscular demand. 120 becomes right only at genuine 6h+ Unbound race pace, 700–800 kcal/hr → 100–130 g/hr.
· **SOURCE** "The 120 Trap" v2 + "120 Grams of Bullshit" (**Matti-authored** drafts)
· **RELEVANCE** Fuel-tag copy on every workout. Note the *internal* consistency: this agrees with the bracket table.

**CLAIM** Averaging power to compute fuel is mathematically wrong for gravel.
· **NUMBERS** Jensen's Inequality — fat oxidation computed from average power vs over variable power differed by an **83% overestimate** in one analysis. Gravel: nominal 180 W avg oscillating 110–250 W.
· **SOURCE** fueling-methodology.md §"Why Averages Lie"
· **RELEVANCE** Why the bracket approach (not a point estimate) is the correct architecture.

**CLAIM** Phenotype (VLaMax) predicts carb burn at the same watts.
· **NUMBERS** Diesel 0.25–0.3 mmol/L/s → 60–80 g/hr, glycogen 12+ h · All-rounder 0.4–0.5 → 90–120 g/hr, 10–15 h · Glycolytic 0.6–0.7 → **120–150 g/hr, only 5–6 h**
· **SOURCE** fueling-methodology.md
· **RELEVANCE** A phenotype input would meaningfully move the fueling output — currently unused.

**CLAIM** Sex-specific: women burn ~7% more fat at the same relative intensity, crossover ~58% vs ~50% VO₂max, use **25–50% less muscle glycogen**; the performance gap narrows beyond 200 miles.
· **SOURCE** fueling-methodology.md
· **RELEVANCE** The guide already has a women-specific conditional; this gives it numbers.

**CLAIM** Gut training is an 8–10 week pre-race protocol with a measurable effect size.
· **NUMBERS** ~**16% increase in exogenous carb oxidation over 28 days**; GI symptoms cut **up to 60%**. Start in the lower third of your bracket for a first major event. Real food after hour 8.
· **SOURCE** fueling-methodology.md §"What To Do About It"
· **RELEVANCE** A datable, schedulable protocol block — currently the plan has fuel tags but no gut-training progression.

**CLAIM** Hydration: start every session 100% hydrated; sodium by sweat-salt phenotype.
· **NUMBERS** ~30% of athletes start workouts dehydrated. Clean bibs → **500 mg** Na/bottle; kinda salty → **750–1000 mg**; really salty → **1500 mg**.
· **SOURCE** "How to Hydrate So You Don't Die in Your Gravel Race" (**Matti-authored**)

---

## 8. RECOVERY WEEKS & RECOVERY GENERALLY

**CLAIM** Cap hard days at **2–3/week** — series/reps accumulation is bounded by this, not by dose.
· **SOURCE** FUNDAMENTALS levers 5 + safety gates. **Independently corroborates ratified rule #5.**

**CLAIM** Fatigue plateaus in ~21 days while fitness keeps rising for ~126 — so the correct response to a fatigue plateau is to *hold*, not to cut and re-ramp.
· **SOURCE** `load-stabilization-phase.md`
· **RELEVANCE** Suggests recovery-week frequency should be a function of ATL trajectory, not a fixed 3-week rhythm.

**CLAIM (Matti-authored)** "Recovery makes you fast"; overtraining isn't a badge; no individual workout defines fitness — "you are your body of work."
· **NUMBERS** Same athlete: 300 W for 10 min one day, 270 W the next. Real-world progression benchmark ("The Great Dane"): **+50 W FTP and −20 lb**, over years.
· **SOURCE** "How To Do Workouts The Right Way" (**Matti-authored**, 2022)
· **RELEVANCE** Recovery-week and post-test copy; sets the expectation horizon in the guide.

**CLAIM (Matti-authored)** Boredom tolerance is a trainable competitive advantage, not a problem to design around.
· **SOURCE** "No One Cares If You're Bored" (**Matti-authored**) + `writing-graph/themes/boredom-as-competitive-advantage.md`
· **RELEVANCE** **Directly relevant to variety-driven workout rotation.** The house position is that variation exists to serve physiology, not to entertain — "all you need is the same five workouts… except they'd get too bored." A generator that rotates archetypes purely for novelty is arguing against its own brand.

---

## 9. RACE-SPECIFIC / DEMAND-DRIVEN

**CLAIM** Race demand is 14 scored dimensions, 7 course + 7 editorial, each 1–5, normalized 0–100, across 757 races — and a single "difficulty" number cannot drive session selection.
· **NUMBERS** Course dims: Length (<40 mi → 150+ mi/multi-day), Technicality, Elevation (<2,000 ft → 10,000+ ft), Climate, Altitude (<3,000 ft → sustained >8,000 ft), Logistics, Adventure
· **SOURCE** `gravel-god/guide/gravel-guide-content.json` ch2
· **RELEVANCE** A structured demand vector already exists per race. This is the natural input to a demand→archetype-category selector; `gravel-god/scripts/generate-race-pack-previews.py` already filters up to 7 categories for ultra (VO2max, Race_Simulation, Gravel_Specific, Critical_Power, Anaerobic, Sprint, Norwegian).

**CLAIM** Gravel's signature demand is constant power change, not steady output — "surge over the rough stuff, settle on the smooth."
· **SOURCE** race-pack workout context strings across `gravel-god/output/*.html`; guide ch1 "sustainable output for extended duration… not peak power"
· **RELEVANCE** Justifies Terrain Microbursts / Gravel_Specific / endurance-with-surges as the discipline-extra slot.

**CLAIM** For ultras the demand inverts: intensity ceilings compress, volume is capped for everyone including winners, and recovery becomes an *in-race* skill.
· **NUMBERS** Sustainable training tops out ~**25–30 h/wk** for anyone. TCR winner Allegaert ~20,000 km/7 months (~25–28 h/wk); typical TCR finishers 5,000–10,000 km in final 6 months (~8–15 h/wk). Race demands **70–100 riding h/wk** — everyone races in deficit. Tour Divide 24-day target = **~100 mi + 5,500 ft/day, loaded, every day**. No credible vendor sells a 12-week ultra prep; formats are 4- and 6-month plans, 6-month coaching minimums, 9 months recommended for Tour Divide.
· **SOURCE** ultra-bikepacking whitepaper §2–3
· **RELEVANCE** Hard gate: plan length must scale with event class, and the pipeline should refuse (or warn on) sub-16-week ultra requests.

**CLAIM** Masters decline is ~1%/yr *only if you're already training to potential* — most amateurs aren't, so volume increase beats age decline.
· **NUMBERS** 330 W at 30 → 300 W at 40 = 10% over 10 yr. Pro floor is **750 h/yr (15 h/wk)**; US domestic pro 17–20 h/wk = 850–1,000 h/yr. An amateur at 200 h/yr has enormous headroom.
· **SOURCE** "How to Beat People 20 Years Younger Than You" (**Matti-authored**)
· **RELEVANCE** Masters conditional in the guide; argues against reflexively de-loading masters athletes.

---

## 10. STRENGTH (adjacent but load-bearing on scheduling)

**CLAIM** Strength placement is a calendar problem, not a willpower problem: after ride days or on easy days, **never the day before a key session.**
· **NUMBERS** Four phases: **Foundation** 4–6 wk, 2–3×/wk, 30 min · **Build** 8 wk, 2×/wk, 35–40 min, 3×5 @ RPE 7–8, week-4 written deload · **Sharpen** 4–6 wk, 1–2 gym + on-bike seated low-cadence 40–60 rpm, 2×8 min → 3×15 · **Hold** race season 1×/wk, 20–25 min, isometrics swap on heavy race weeks. Every set at 2–3 RIR (RPE 6–8). Session cap ~40 min or it gets abandoned. Masters: Foundation doubles, ≥72 h spacing, year-round floor rises to 2×/wk, **intensity target unchanged**.
· **SOURCE** "Strength for Gravel Cyclists — 2nd Edition (July 2026)" and "…The Philosophy Behind the Program" (**Matti-authored**) — `writing-graph/inbox/gravel-god/`
· **RELEVANCE** Cited evidence: road cyclists **7× more likely** to have osteopenia (Rector 2008); strength improves TT performance/efficiency with **no VO₂max effect** (Llanos-Lagos 2025); injury risk cut **up to two-thirds** (Lauersen 2018); concurrent block adds **~1 kg** (Van Hooren 2024); only ~⅓ of male pros keep lifting in-season; only **8.0% of male pros** do any upper body.

---

# CONTRADICTIONS WITH THE RATIFIED STANDARDS

| # | Standard | Contradicting evidence | Source |
|---|---|---|---|
| **C1** | **50 TSS/hr cap on endurance** | Two archetypes classified `endurance` in the experimental engine exceed it: `endurance_surges` L6 = 78 TSS / 80 min = **58.5 TSS/hr**; `tempo_3x15` L6 = 103 TSS / 110 min = **56 TSS/hr** (L1 already 52.5). Both scored PASS on the dose gate — the gate only checks non-regression, never a rate cap. | `_ENRICHMENT_SCORECARD.md` |
| **C2** | **Purge FatMax** | A `fatmax` archetype ("FatMax Development", 6 levels, 100→200 min, all PASS) is a first-class entry in the experimental library. Separately, **Matti-authored** copy endorses the *concept* twice: "The intensity where you actually maximize fat burning — FatMax — sits well below sweet spot, typically Zone 2 around 2 mmol/L" (Sweet Spot article) and "The point of Zone 2 rides is primarily metabolic — to increase fat burning… if all of your Zone 2 rides are at the ceiling of Zone 2 or above, your ability to burn fat will be limited" (How To Do Workouts). **Recommendation:** purge the *archetype name*, keep the *mechanism* as the rationale for the .60–.70 IF band — otherwise the guide's own Z2 justification is orphaned. |
| **C3** | **Purge structured-fartlek** | `structured_fartlek` is a live 6-level archetype (60 min flat, TSS 46→55, axis=`reps`) scoring all-PASS. Note its progression is nearly inert (9 TSS across 6 levels) — an independent reason to cut it. | `_ENRICHMENT_SCORECARD.md` |
| **C4** | **2–3 intensity days/week (as sufficient)** | **Matti-authored:** the 6–9 h/wk athlete needs **90–120 min minimum of genuinely hard work weekly**, and below ~90 min cumulative, VO₂max gains are "small and inconsistent." 2–3 sessions at typical archetype work-durations can land under that. The rule caps hard days correctly but sets no *floor on hard minutes*. | "The 80/20 Trap" (Matti) |
| **C5** | **Implicit fixed polarized distribution** | **Matti-authored:** distribution must scale with volume — 70/30 at 7 h, 75/25 at 10 h, 80/20 only at 12–15 h. Any methodology that applies one ratio across all volume tiers contradicts the house position. | "The 80/20 Trap", "Peter Attia Stole Your Training Plan" (Matti) |
| **C6** | **Fueling (in-plan vs. race-page copy)** | Race-page pack copy tells Transcontinental (3,100 mi, multi-week) riders **"80–100 g carbs/hour from mile 1."** The house fueling methodology puts 16+ h events at **30–50 g/hr** and 12–16 h at 40–60. The race-page generator is roughly 2× the methodology for the longest events. | `gravel-god/wordpress/output/transcontinental-race.html` vs `fueling-methodology.md` |
| **C7** | **45-min floor** | No contradiction found — lowest ridable entries are 50 min (`loaded_recovery_vo2`, `above_cp_90s` L6). Clean. |
| **C8** | **VO2 every 14 days** | No contradiction — actively *supported* by Issurin's 18 ± 4 d VO₂max residual. Clean. |

---

# TOP 10 HIGHEST-VALUE ADDITIONS NOT COVERED BY THE RATIFIED STANDARDS

1. **T@VO₂max and W′bal as generation-time acceptance gates** (aerobic → 8–14 min T@VO₂max; threshold/anaerobic → W′bal nadir 0–6 kJ, seed 20 kJ, CP = FTP/0.96). Two computable rules that catch mis-dosed sessions the current 11 rules cannot see — and 79/234 of the existing library already fails them. *(FUNDAMENTALS + scorecard)*

2. **Volume-scaled intensity ratio: 70/30 @ 7 h → 75/25 @ 10 h → 80/20 @ 12–15 h, with a hard floor of 90–120 min hard work/week.** Turns the intensity budget from a day-count into a minute-count that respects the minimum effective dose. *(Matti-authored, "The 80/20 Trap")*

3. **A Load Stabilization phase between Build and Peak** — hold weekly TSS constant, raise specificity, exploit the 21–126 day window where fatigue is flat and fitness still rises (~6% higher peak fitness on ~4% less work in model sim). The single biggest structural change available to `calculate_plan_dates.py`. *(endure-labs `load-stabilization-phase.md`)*

4. **Residual-decay-driven phase sequencing** (aerobic 30 ± 5 d → VO₂max/glycolytic 18 ± 4 d → speed 5 ± 3 d). Gives a *principled* taper composition and independently ratifies both the 14-day VO2 spacing and the alactic-strides-in-recovery-weeks pattern. *(endure-labs `residual-training-effects.md`)*

5. **Durability dosed in kJ with an intensity-specified bridge, plus a fatigue de-rate rule: −10–20% on VO₂/anaerobic targets, threshold near-normal.** Ladder fresh → 1000–1500 → 2000 → 2500–3000+ kJ, normalized per kg. Turns Durability from "long ride with intervals" into a parameterized axis. *(FUNDAMENTALS lever 8; Maunder 2021 / Spragg 2024)*

6. **Duration-bracketed fueling that goes DOWN with race length** (80–100 → 60–80 → 50–70 → 40–60 → 30–50 g/hr across 2–4/4–8/8–12/12–16/16+ h), W/kg positioning within bracket, bracket-bounded specifically to absorb Jensen's-inequality error on variable gravel power. Plus the 8–10 week gut-training protocol (+16% oxidation over 28 d, −60% GI symptoms). *(fueling-methodology.md; "The 120 Trap")*

7. **Interval-design bounds as renderer constraints:** rep length ≥ ~2 min for VO₂ work (VO₂ kinetics 1:20–2:20); relief ~2 min optimum, passive when <2–3 min; float ~70% vVO₂max; overs ≤110% or they become VO₂ work; progress duration before watts; L5–L7 prescribed in **watts only**; series grow before reps at the top of a ladder. *(FUNDAMENTALS levers 1–6, 9)*

8. **Ramp-rate deceleration as intensity enters the plan**, because TSS scales as IF² and session TSS >300 lingers ~2 days / >450 multi-day. The week-budget multipliers are currently duration-linear and blind to this. *(FUNDAMENTALS lever 10)*

9. **FTP inflation as a modeled assumption (5–10%), with the G-Spot at 86–92% FTP as the deliberate compensating offset.** Makes the house zone table defensible and explains, in the athlete's own guide, why the target sits below Sweet Spot. Immediate action item: `gspot_criss_cross` fails the W′bal gate at all 6 levels — it isn't doing what its name claims. *(Matti-authored, "Sweet Spot Isn't that Sweet")*

10. **Demand-vector-driven archetype selection off the existing 14-dimension race score** (Length / Technicality / Elevation / Climate / Altitude / Logistics / Adventure, each 1–5, over 757 races), with an event-class gate on plan length — ultras get 4–9 months or a refusal, never 12 weeks. The data already exists and the race-pack preview script already does a crude version of this. *(gravel-guide-content.json; ultra-bikepacking whitepaper)*

---

**Honorable mention (not in the top 10 but cheap to encode):** cadence lever gating — low cadence at *moderate* intensity builds little (Kristoffersen 2014 null), but carried *into* VO₂/HIIT reps it improves VO₂max/Pmax (Hebisz 2024) and sprint power (Paton 2009); patellofemoral load is **+29% at 70 vs 90 rpm**, so any cadence floor below ~60 rpm should be gated behind a knee-history flag. *(FUNDAMENTALS lever 7)*
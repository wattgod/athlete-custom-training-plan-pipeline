# That Triathlon Show + Fast Talk Labs Corpus Mining — 2026-08-23

Miner: Explore agent over ~/endure-labs-graph/scripts/voice-extraction/classified/ scientific-triathlon (30 files) + fast-talk-labs (29) + bonk-bros skim (30). Verbatim-sourced; distilled/ files avoided.

STATUS: PENDING — awaiting Matti rulings (see ALGORITHM_EVIDENCE.md §11).

---

# Coaching-Evidence Mining Report — Training-Plan/Workout Generation Rules

**Corpus mined:** `scripts/voice-extraction/classified/` at `/Users/mattirowe/endure-labs-graph/`
**Channels:** `scientific-triathlon/` (all 30 files except previously-touched 40qAOUskyA8.json, B4OusQAVnPc.json — those two were re-mined here too since only "ramp_rate content" was distilled from them previously, not the full file), `fast-talk-labs/` (all 29 files except iuySslpWGTM.json), `bonk-bros/` (all 30 files, skim pass)
**Method:** Programmatic keyword-tight filter (percentages, watts, zone/Z-numbers, CTL/ATL/TSS/FTP, VO2, mmol, taper, recovery week, polarized/pyramidal/sweet-spot, durations, threshold, lactate) applied to `is_coaching=true` segments, then full verbatim read of every matched segment (~2,900 lines scientific-triathlon, ~1,245 lines fast-talk-labs, ~140 lines bonk-bros). All quotes below are verbatim from `original_text`, not `key_phrase` or distilled files.

---

## A. TESTING / ATHLETE PROFILING / CLASSIFICATION

**RULE:** Profile athletes on fast-twitch/slow-twitch spectrum via peak lactate, 20-second sprint power vs. 5-min vs. 20-min power spread, and workout preference (long threshold-reps tolerance = slow-twitch tell); use this to set recovery ratios and endurance-IF ceilings differently per profile.
NUMBERS: fast-twitch → threshold-to-rest 3:1→2:1 (vs 4:1→3:1 for sweet spot); "riding at 70–75% of FTP all the time can really kill" a fast-twitch athlete; slow-twitch tolerate 8–10 min threshold reps happily.
WHO: Nathan/guest physiologist on B4OusQAVnPc.json (Physiological Profiling episode).
SOURCE: B4OusQAVnPc.json idx 0,1,2,3,4,8,11,12,14,15,16,17.
HOOK: athlete classification / workout_selector individualization.

**RULE:** Run a critical-power/critical-speed test as 3 sub-maximal-duration efforts, discard any test result where a shorter-duration result is lower than a longer one (physiologically invalid), and use the remaining two.
NUMBERS: bike 3-min + 5-min + 20-min (or 3/6/12); run 200/400/800; critical-speed test validity requires longest test ≤20 min (literature configs: 3/6/12 min or 2/4/8/15 min).
WHO: unnamed guest coach (3LszuOxRyT4), Mikael Eriksson (1aVYgLQsILE), B4OusQAVnPc coach.
SOURCE: 3LszuOxRyT4.json idx 6,7; 1aVYgLQsILE.json idx 19; B4OusQAVnPc.json idx 12.
HOOK: testing.

**RULE:** Build an individualized performance/power-duration profile from 5 key anchor durations rather than a single FTP number; re-test only every 8–12 weeks once profile is established.
NUMBERS: anchor durations 5 min, 30 min, 60 min + 1–2 goal-race-relevant durations; retest cadence 8–10 or 8–12 weeks.
WHO: Mikael Eriksson.
SOURCE: 1aVYgLQsILE.json idx 8 (numbered "13" in dump), 14 ("power-duration-curve"), 13("8 to 10 weeks or 8 to 12 weeks").
HOOK: testing / workout_selector intensity anchoring.

**RULE:** Anchor VO2max interval targets to 5-min mean-max power (not %FTP); anchor threshold-interval targets to the 30–60 min power range (30-min ≈ upper/critical-power end, 60-min ≈ lower/MLSS end).
NUMBERS: 3–4 min intervals ≈ 95% of 5-min power; 2-min intervals ≈ 97–98%; 5–6 min intervals ≈ 92–93%; add/remove 2–3 percentage points per minute of duration change away from the 4-min anchor.
WHO: Mikael Eriksson.
SOURCE: 1aVYgLQsILE.json idx 4,5 ("209"–"212"), 14 ("229"), 15 ("232").
HOOK: workout_selector.

**RULE:** For race-specific power targets on long events, use the power associated with a duration ~20–25% shorter than the actual race-leg duration (not a flat %FTP).
NUMBERS: 5-hr IM bike split → target power from best 3:45–4:00 hr efforts; 2:30 70.3 bike → target from 1:52–2:00 hr efforts (20–25% shorter = 75–80% of original duration).
WHO: Mikael Eriksson.
SOURCE: 1aVYgLQsILE.json idx 11, 13.
HOOK: workout_selector / race pacing.

**RULE:** Trainability/potential-ceiling is best assessed as threshold-as-%-of-VO2max (fractional utilization): a big gap between VO2max and threshold = high remaining trainability; a threshold very close to VO2max = near-ceiling.
NUMBERS: none exact given, qualitative gap assessment.
WHO: Stephen Barrett (WorldTour coach, coach of Felix Gall).
SOURCE: MjJ3x3ZRaZ4.json idx 18.
HOOK: athlete classification / block_chain emphasis selection.

**RULE:** For durability testing, prescribe a fixed-duration sub-threshold test (~90 min at first lactate threshold / ~80% VO2max) and track drift in running economy from start to finish as the durability metric — not a single-point steady-state test.
NUMBERS: 90-min protocol at LT1 (~80% VO2max); trained-with-long-runs group drifted only 3% in economy vs 6% for group without long runs (50% relative difference); elite/world-record-level durability (Magnus Ditlev IM sim) drifted only 1.8%.
WHO: Michele Zanini (physiologist/durability researcher guest).
SOURCE: Rw4Hk-Hn114.json idx 12,13,14,15,16,17,2,3,4,5,6.
HOOK: testing / durability.

**RULE:** Heavy strength + plyometric training (10 weeks) measurably improves durability — reduces economy drift and extends time-to-exhaustion in a fatigued state.
NUMBERS: 10-week block, reduced drift in economy, enhanced time-to-exertion (no exact % given).
WHO: Michele Zanini.
SOURCE: Rw4Hk-Hn114.json idx 18.
HOOK: strength scheduling / durability.

**RULE:** For fast-twitch-dominant profiles, VO2max training matters more than for slow-twitch amateurs (their VO2max is often already near-ceiling from pro-level training history) — amateurs should chase VO2max gains, not just threshold-as-%-VO2max.
WHO: B4OusQAVnPc guest.
SOURCE: B4OusQAVnPc.json idx 6,7.
HOOK: athlete classification.

---

## B. PHASE SEQUENCING / PERIODIZATION / calculate_plan_dates

**RULE:** Structure marathon (and by extension long-endurance) periodization as three phases working backward from race day: General (broad speed spectrum) → Supportive (90–110% of race pace) → Specific (95–105% of race pace).
NUMBERS: Supportive phase = race-pace ±10%; Specific phase = 95–105% race pace; 18-week flagship plan (12-week compressed version also offered); peak-mileage low/high band per plan (e.g., "Breeze" plan 40 vs 50 mi/wk peak).
WHO: John Davis (running coach/author).
SOURCE: IW-VV39Nv0o.json idx 1,16,17,18,0.
HOOK: calculate_plan_dates / block_chain.

**RULE:** Build long workouts by working backward from the single hardest goal-specific workout the athlete must be able to execute, then reverse-engineer 2–3-week progressions of volume/intensity leading up to it (never introduce the full target session "out of nowhere").
NUMBERS: example marathon-pace progression: 25k @ 90% MP (5k chunks) → 28k → 32k @ 95% MP, roughly a month out; repeats progression: 1k+1k float → 2k+1k → 3k+1k → 4k+1k @ MP, 3 weeks out.
WHO: John Davis.
SOURCE: IW-VV39Nv0o.json idx 10,11,12,13,14,15.
HOOK: block_chain / series progression.

**RULE:** For an Ironman build, plan roughly 9–12 weeks of "specific" training leading into the race (some coaches: 6–8 weeks fully IM-specific after a 6–8 week pre-specific/supportive block), preceded by a base/general phase; VO2max/intensity block(s) occur ~6 months out to "raise the ceiling" before reverse-periodizing toward specificity.
NUMBERS: 9–12 weeks specific (From1_Skw7M); 12 weeks total incl. 2-wk taper, or as little as 6 weeks specific prep if athlete has already done a 70.3 (WmEiytCXR2g); 14–6-week pre-specific block, 6–8-week specific block (WmEiytCXR2g).
WHO: Melanie McQuaid (From1_Skw7M), unnamed ST coach guest (WmEiytCXR2g).
SOURCE: From1_Skw7M.json idx 6,1,2; WmEiytCXR2g.json idx 17,18,3,4,8,10.
HOOK: calculate_plan_dates.

**RULE:** In base phase, deliberately vary the block emphasis (endurance block / speed block / strength block / threshold block clustering) rather than trying to develop everything simultaneously every week.
WHO: Peter Leo (Jayco-AlUla coach).
SOURCE: -zgLbMNYLHY.json idx 3(idx=3 "block_grade").
HOOK: block_chain.

**RULE:** WorldTour cycling model: wave periodization alternating multi-week blocks of polarized (VO2max + zone-2 endurance) training with blocks of "blockization" (race-specific intensity work); transition periods blend the two.
NUMBERS: 2–3-week waves.
WHO: Stephen Barrett.
SOURCE: MjJ3x3ZRaZ4.json idx 17,19.
HOOK: block_chain / phase_transition.

**RULE:** Reverse-periodize (shorter/faster intervals first → longer/lower intervals later) for longer-distance goal races; use classic linear periodization (long/low→short/high) for shorter goal races.
WHO: Mikael Eriksson.
SOURCE: 1aVYgLQsILE.json idx 0.
HOOK: block_chain / series progression.

**RULE:** Base training is ~95% of season success (general aerobic capacity — VO2max, fractional utilization/threshold, economy, durability), specific preparation is ~5%; don't confuse base phase with "just easy training + a bit of threshold."
NUMBERS: "95% ... 5%"; base phase includes deliberate threshold/VO2max work, not just Z1–2.
WHO: unnamed ST guest coach.
SOURCE: 6-9o4PwLWAs.json idx 16,17,19,5.
HOOK: block_chain / calculate_plan_dates.

**RULE:** For older/lower-training-history athletes returning to structure, sequence: (1) baseline zone-1/zone-2 conditioning first, (2) short high-intensity reps (30–60s work, 1:2 work:rest, <10 min total work) to teach "changing pace," (3) then progress to standard threshold/VO2max sessions once the pacing sensation is established.
NUMBERS: 30–60s reps, 1:2 work:rest, total work 5–10 min.
WHO: unnamed guest coach.
SOURCE: 40qAOUskyA8.json idx 2,3,5.
HOOK: series progression / novice conditioning.

---

## C. BLOCK_CHAIN / RAMP RATE / LOAD PROGRESSION

**RULE:** Progress running volume by an absolute 5 minutes-per-run-per-week for typical athletes (up to 10 min/run/wk for very injury-resistant, high-training-history athletes) rather than a percentage-of-volume rule; explicitly reject the classic "10% rule" as not well-founded epidemiologically.
NUMBERS: +5 min/run/week (default); +10 min/run/week (experienced, low injury risk); 10% rule called "not at all good" / "not really well founded in the data."
WHO: Mikael Eriksson (three separate episodes reiterate this), John Davis (independently corroborates 10%-rule rejection).
SOURCE: 6-9o4PwLWAs.json idx 13; NPwc2VB2Piw.json idx 9,10; XtJOy1TNECI.json idx 0; IW-VV39Nv0o.json idx 5.
HOOK: block_chain ramp logic. **NOTE:** this is an alternative mental model (absolute-minutes ramp, not CTL-%) to the ratified ≤8 CTL/wk rule — flagged in contradictions table below.

**RULE:** Peter Leo (British Journal of Sports Medicine citation): increasing running mileage >10% substantially raises injury hazard in a large amateur-runner cohort — supports conservative running-volume progression specifically (distinct from Davis/Eriksson's rejection of the same 10% heuristic — direct disagreement between ST guests, noted below).
WHO: Peter Leo.
SOURCE: -zgLbMNYLHY.json idx 0.
HOOK: block_chain ramp logic (running).

**RULE:** Don't jump straight from moderate to maximal sustainable volume in one step (e.g., finishing school and suddenly training 30 hrs/wk); saturate more slowly by stepping volume up ~2–3 hrs/year rather than doubling immediately — you get the same fitness gain either way but preserve headroom and reduce burnout/injury risk.
NUMBERS: 15–20 hrs → 22–23 hrs → 24–25 hrs (year-over-year steps), vs. jumping straight to 30 hrs.
WHO: Jacob Tipper (coach of Ben Healy).
SOURCE: E_djkYB36Tw.json idx 3,5,6,7,8,11,12,13.
HOOK: block_chain / ramp_rate (long-horizon, year-over-year — complements CTL/wk within-block rule).

**RULE:** For deload/recovery weeks in running, don't cut volume too aggressively (e.g., 60k→20k/week) — that "chronic volume" is hard to regain; prefer maintaining ~65–70% of peak volume with reduced intensity instead of dropping volume the same amount as intensity.
NUMBERS: 60 km/wk peak → recovery week ~40 km/wk (≈67%), not 20 km/wk (≈33%).
WHO: Peter Leo.
SOURCE: -zgLbMNYLHY.json idx 2.
HOOK: block_compliance / recovery week composition. **NOTE:** ~67% is slightly above ratified 50–65% band — flagged.

**RULE:** Progressing V2max torque/threshold interval reps: beginner caps at 8×4min, intermediate 10–12×4min, elite up to 15×4min (60 min total threshold work) — only after demonstrated chronic training load and gradual progression; never start an athlete at the top of this range.
NUMBERS: 8×4min (beginner) → 10–12×4min (intermediate) → 15×4min/60min total (elite), 3:1 work:rest ratio (1min20s rest per 4min).
WHO: Jack Hutchins/Mikael Eriksson (co-hosts, "5 Essential Bike Workouts" ep).
SOURCE: HRBk3X8EB0o.json idx 16,17,15,14.
HOOK: series progression / workout_selector.

**RULE:** Progress a threshold-block interval series by extending rep duration while holding the same work:rest ratio, not just adding reps: 10×4min → 7×6min → 5×8min → 4×10min, always ~3:1 work:rest.
WHO: Mikael Eriksson.
SOURCE: HRBk3X8EB0o.json idx 17.
HOOK: series progression.

**RULE:** Early-in-block cadence/torque-manipulation and cadence-variation work belongs in a genuine 3-week preparation block (1–2×/week within it), not scattered continuously between races — becomes "overstimulation" if maintained in-season.
NUMBERS: 3-week block, 1–2 cadence sessions/week within it.
WHO: Peter Leo.
SOURCE: -zgLbMNYLHY.json idx 9,11.
HOOK: block_chain.

---

## D. WORKOUT_SELECTOR — INTERVAL DESIGN NUMBERS BY TYPE

### VO2max
**RULE:** Classify VO2max work by two distinct mechanisms — (1) sustained "long" reps eliciting near-max oxygen consumption (3–5 min @ ~92–98% of 5-min power) and (2) "micro-interval" sets (20–60s on, limited/incomplete recovery ~2:1 work:rest) that accumulate 10–20 min of near-VO2max time without the same lactate/acidosis cost. Choose based on athlete profile: slow-twitch profiles do well with steady long reps; micro-intervals preferable for triathletes/those who can't tolerate high glycolytic load.
NUMBERS: micro-intervals ≥20s, target power ≈120% FTP ballpark (individualized to 5-min power, NOT fixed %FTP); accumulate 10–20 min total (build from 10 min early season to 15–20 min); 2:1 effort:recovery ratio empirically shown to maximize time >90% VO2max; intermediate intervals 90s–3min at ~1:1 rest ratio, don't go below 1:1 (want max total output, avoid big fade); classic long reps 3–5 min just below-100–108% max aerobic power (individualized, can be as low as 108–112% for well-trained, ballpark 120% commonly cited but wrong for high-FTP athletes — must use 5-min power not %FTP: a 16yo with FTP 320W at 140% = ~450W matched a pro's actual VO2max power, but 140% of the pro's FTP 370W overshot their true VO2max power and caused early failure).
WHO: Neal Henderson & Trevor Connor (co-hosts, dedicated VO2max-intervals episode).
SOURCE: lCJ_mkfKJsk.json idx 17,18,19,0,11,12,13,14,15,16,2,3,15,16,18,19,0,1,2,12.
HOOK: workout_selector (critical — this directly informs interval-dosing algorithm; strongly recommend anchoring VO2max targets to 5-min mean-max power rather than %FTP).

**RULE:** For elite/high-anaerobic-capacity athletes, avoid the classic 4x4 protocol at altitude/sea-level generically — break the same total "time under load" into shorter pieces (e.g., 3030s) for better tolerance and gains; a controlled study found 30/30s produced significantly better gains than 4×4 in one comparison cited.
WHO: Neal Henderson.
SOURCE: lCJ_mkfKJsk.json idx 0,1.
HOOK: workout_selector.

**RULE:** VO2max micro-interval example set: 3 sets of 13×30s @ ~115–120% FTP / 15s @ ~60% FTP (Ronnestad protocol), scaled down for amateurs to 30/30s or 40/20s.
NUMBERS: 13×30/15, 3 sets, 3 min between sets; scaled: 30/30 or 40/20.
WHO: Jack Hutchins.
SOURCE: HRBk3X8EB0o.json idx 6,7.
HOOK: workout_selector.

**RULE:** "4x5min-consists-of-3x40/60" fractionated VO2max design: 4 reps of 5 min, each rep = 3×(40s @ 115–120% FTP / 60s @ 100–105% FTP) — sustains high lactate without full clearance ("just barely stopping the rapid fatigue accumulation"), harder-feeling but shorter total duration than long-rep alternative.
WHO: Jack Hutchins/Mikael Eriksson.
SOURCE: HRBk3X8EB0o.json idx 9,10,11.
HOOK: workout_selector.

### Threshold / Sweet Spot
**RULE:** Standard threshold interval design: 3:1 work:rest ratio (e.g., 10×4min @ 95–100% FTP with 1min20s rest is the "straight" version); progress interval duration while holding ratio; use "Norwegian style" longer threshold reps (6×10min @ 88–92% FTP, slightly lower power/longer duration to still allow lactate stabilization) as an alternative shorter-progression variant, up to 80–90 min total for elite.
NUMBERS: 10×4min @95–100% FTP, 1:20 rest (3:1); 6×10min @88–92% FTP up to 80–90 min elite.
WHO: Jack Hutchins/Mikael Eriksson.
SOURCE: HRBk3X8EB0o.json idx 15,16,17,13,14.
HOOK: workout_selector.

**RULE:** Long threshold session design for run: work backwards from threshold pace, start reps 10–15 sec/km slower than threshold and progress through the session to threshold pace if feeling good; typical: 8×4min (starting point) progressing to 8–12×4min; longer variant 4–8×8min (240s = 3:1 active jog rest).
NUMBERS: start 10–15 sec/km (or 15 sec/mile) slower than threshold; 8×4min typical start; 8–12×4min sweet spot for most; 4–8×8min longer variant, 3:1 active rest (240s).
WHO: Mikael Eriksson.
SOURCE: gqvOnZKCxK8.json idx 0,1,2,13,14.
HOOK: workout_selector.

**RULE:** LT2/threshold-progression set design (build lactate then hold): 2 sets of 3k→2k→1k with short recovery within a set, full recovery between sets — intensity builds from just-below-LT2 for the 3k to just-above for the 1k; use sparingly, after a decent base with threshold work already established, in build phase.
WHO: Mikael Eriksson.
SOURCE: gqvOnZKCxK8.json idx 2,3,4.
HOOK: workout_selector.

**RULE:** Sweet spot defined operationally as "high zone 3 / low zone 4" — the lowest intensity considered a useful stimulus for an advanced athlete in general prep (below that, prefer pure zone 2 volume); for beginners, 75–80% FTP is a sufficient stimulus.
NUMBERS: high Z3/low Z4 (advanced); 75–80% FTP (beginner).
WHO: Ambrose (time-efficient-training episode guest).
SOURCE: wLXLpNGB5Dg.json idx 0.
HOOK: workout_selector / athlete classification (novice vs advanced intensity floor).

**RULE:** Threshold range should be treated as a band, not a single FTP number: 30-min mean-max power ≈ upper end/critical power; 60-min mean-max power ≈ lower end/MLSS; prescribe intervals anywhere in that range depending on periodization goal (shorter reps at upper end, longer reps + more total duration at lower end).
WHO: Mikael Eriksson.
SOURCE: 1aVYgLQsILE.json idx 18, 0-3 ("phase_context/workout_preview" cluster).
HOOK: workout_selector.

### Torque / Low-Cadence & Strength-Endurance
**RULE:** Low-cadence/high-torque bike reps should be capped at 2–5 min per rep in early-season prep (longer than that requires reducing power output too much to be effective for fiber-type stimulus); more classic torque protocols use 4–8min reps at high torque/low cadence but coaches disagree on evidence strength and recommend a slower progression, tagged onto the front of classic threshold sessions.
NUMBERS: 2–5 min ideal rep range; 4–8-min traditional torque reps (evidence "not clearcut"); typical low-cadence example: 8×4min high-torque @ 2–3min rest, 50 RPM.
WHO: Peter Leo; Jack Hutchins.
SOURCE: -zgLbMNYLHY.json idx 0,16,19; 6-9o4PwLWAs.json idx 5; HRBk3X8EB0o.json idx 0,1,2,6.
HOOK: workout_selector / strength scheduling.

**RULE:** Endurance-ride sprint-injection protocol ("Ronnestad/Almquist endurance ride"): every hour of a long ride, insert 3×20s all-out seated sprints with 4-min recovery between; scale sprint duration/count down for longer (4–5hr) rides (2 sprints/hr instead of 3, or shorten to 15s) since triathletes have lower W' (anaerobic capacity) than pure cyclists so 30s original-protocol sprints are too taxing.
NUMBERS: min 2 hrs ride length (research base 3–4 hrs), 3×20s sprints/hour, 4-min recovery between sprints; scale to 2×15s/hr for 4–5hr rides.
WHO: Mikael Eriksson.
SOURCE: HRBk3X8EB0o.json idx 15,16,17,18.
HOOK: workout_selector / durability.

### Race-Pace / Marathon-Specific
**RULE:** Marathon-pace "over/under" session (Canova-derived): rolling 5km blocks of 1km @ MP-10s/km, 1km @ MP+30–45s (steady, not easy), 1km @ MP-10s/km, 1km @ MP+30–45s, repeat 3–5 rounds (12–20km total); variability keeps it mentally manageable and prevents athletes over-fixating on hitting exact MP for every km.
NUMBERS: 1km segments; ±10s/km faster/slower blocks; steady segment = MP+30–45s/km (45–70s/mile); 3–5 rounds = 12–20km.
WHO: Mikael Eriksson.
SOURCE: gqvOnZKCxK8.json idx 11,12,15,18,19,2.
HOOK: workout_selector.

**RULE:** Iron Man specific brick design (weekend): Saturday swim (10×400 IM-effort) + long ride with 3×1hr IM-intensity blocks within a 5hr ride; Sunday shorter bike-to-run brick with a long run containing IM-pace blocks (e.g., 3×30min or 2×30+2×20min within a 2–2.5hr run).
NUMBERS: 10×400m swim; 5hr ride w/ 3×1hr @ IM intensity; peak run 2–2.5hr with 20–30min IM-pace blocks (not 40–60min, closer to race).
WHO: unnamed ST guest coach.
SOURCE: WmEiytCXR2g.json idx 0,14,15,10,11.
HOOK: workout_selector.

### Swim-Specific
**RULE:** Swim threshold-set volume caps scale with critical speed: CS ≥145 sec/100m (slower) → cap total threshold volume at 2,000m; CS 125–145 → cap ~2,600m; CS <125 (faster) → higher volume allowed.
WHO: Mikael Eriksson.
SOURCE: ocySuP6CXLg.json idx 19,18,17.
HOOK: workout_selector (swim-specific series volume caps).

**RULE:** Build-to-threshold swim design (rather than starting at threshold) is preferable because the upper body produces more lactate and is easy to overcook: e.g., 3 sets of 8×100 building each set's send-off from ~10–15s above critical-speed-pace down toward critical speed itself; classic pure threshold set = 12×200 @ ~30s rest (4:1–5:1 work:rest), given nearly weekly.
NUMBERS: turnaround starts 10–15s > critical-speed pace; 8×100 ×3 sets; 12×200 @ 30s rest.
WHO: Mikael Eriksson.
SOURCE: ocySuP6CXLg.json idx 9,10,12,1,2,3,4.
HOOK: workout_selector / series progression.

**RULE:** Progress swim threshold-set fitness gain by increasing total interval distance (200→250→300m) rather than expecting pace to progress week-to-week — threshold pace improvement is slow/long-term.
WHO: Mikael Eriksson.
SOURCE: ocySuP6CXLg.json idx 3 (idx duplicated in dump — "workout_preview/load_trajectory" cluster near end).
HOOK: series progression.

---

## E. INTENSITY DISTRIBUTION / LOAD MONOTONY

**RULE:** Intensity distribution scales with total training volume: at 6–8 hrs/week ~70% low-intensity; at 20 hrs/week ~90–98% low-intensity (larger low-intensity "chunk" the higher the volume) — the classic fixed 80/20 doesn't hold constant across volume levels.
NUMBERS: 6–8 hrs/wk ≈ 70% Z1–2; ~14 hrs/wk (mid) ≈ 80%; 20 hrs/wk ≈ 90–98% Z1–2, remainder mostly Z3–4 with very little true Z5 (session-time-at-intensity in Z5 is inherently low).
WHO: unnamed guest coach (base-training/strength episode).
SOURCE: 3LszuOxRyT4.json idx 2,4,5.
HOOK: intensity distribution model (calculate_plan_dates / block_chain input).

**RULE:** Ultra-distance-specialist model: ~98% of training volume below first threshold (LT1), remaining ~2% is VO2max work (deliberately avoid threshold-intensity training entirely) — extreme polarization at the very-long-duration end of the spectrum.
NUMBERS: 98%/2%.
WHO: 58Oso90NK8c.json guest (unnamed).
SOURCE: 58Oso90NK8c.json idx 6,9.
HOOK: intensity distribution (ultra-distance / durability-specialist edge case).

**RULE:** WorldTour cyclist annual training hours cluster at 800–1,100 (average ~900–1,000), not the popularly-imagined 20–25 hrs/week; real total including off-bike conditioning work is 30–40 hrs/wk.
NUMBERS: 800–1,100 hrs/yr on-bike (avg 900–1,000); 30–40 hrs/wk total including 10–15 hrs/wk off-bike conditioning.
WHO: Stephen Barrett; SNFnH6IXiZw guest (fast-talk-labs).
SOURCE: MjJ3x3ZRaZ4.json idx 10,7,8,9; SNFnH6IXiZw.json idx 18.
HOOK: athlete classification / expectation calibration for pro-level plans.

**RULE:** Sub-threshold ("floating just below FTP") range for WorldTour-level triathlon coaching is defined as 94–99% of threshold — narrower and higher than typical amateur "endurance IF" prescriptions; used deliberately for cardiovascular-development sessions several times per week, distinct from long runs (which are prescribed purely for fatigue resistance, always easy).
NUMBERS: 94–99% of threshold; example: 15×800m @ 99% threshold on track; 6×5k at lower end of that range in a specific VO2/CV block 5–6 weeks pre-race.
WHO: Rob Cheetham (coach of Leon Chevalier).
SOURCE: vZI1qtPSyVI.json idx 17,18,3,4,9,11,12,13,14,2.
HOOK: workout_selector — **flag vs. ratified endurance-IF cap (see contradictions table)**.

---

## F. RECOVERY WEEK / TAPER / RACE-COUNTDOWN

**RULE:** Ironman taper volume reduction: week 2 out ≈ 40% down from peak (i.e., ~60% of peak volume) to as much as 50% down (50% of peak) at coach discretion; race week ≤50% of peak, "as little as you want" in final days; maintain intensity via short "activation" sessions rather than dropping intensity proportionally.
NUMBERS: 2 wks out: 60–75% of peak volume (one coach: "75%", another: "at least 40% down = 60% remaining", flexible to 50% down); race week: ≤50% of peak.
WHO: unnamed ST coaches (WmEiytCXR2g episode, two coaches comparing notes); Rob Cheetham (vZI1qtPSyVI).
SOURCE: WmEiytCXR2g.json idx 8; vZI1qtPSyVI.json idx 4.
HOOK: taper.

**RULE:** Taper activation sessions should stay at or below threshold intensity but can include a slightly-faster-than-usual opening interval to "sharpen" — e.g., activation bike session: 5min @ ~90% FTP then 3×5min @ IM race pace; keep total hard time very limited (this is deliberately sub-threshold, not a hard workout).
NUMBERS: 5min @ 90% FTP + 3×5min @ IM pace.
WHO: unnamed ST coach.
SOURCE: WmEiytCXR2g.json idx 14,15,11,12.
HOOK: taper.

**RULE:** For Ironman, do NOT do a classic "long aggressive taper" (large mileage cutback) if the athlete has been executing marathon/IM-specific workouts well in the specific phase — this produces flat/lethargic race-day feeling; instead treat race day as "a particularly big long weekend session" and taper only modestly, with the last real hard workout ~10 days out (never do a workout so hard you're not recovered 2 weeks later).
NUMBERS: last major workout ≥10 days before race day.
WHO: John Davis.
SOURCE: IW-VV39Nv0o.json idx 8,9,10,12,14.
HOOK: taper.

**RULE:** Heat-acclimation protocol timing before race: ~2 weeks / ~10 specific heat sessions of ~1hr each is generally sufficient for the "pure heat prep" component (distinct from blood-volume/hemoglobin adaptations which need longer). Arriving 4 days before a hot race without prior heat prep is a real disadvantage; arriving 10 days out with sessions already done in the preceding week is close to sufficient.
NUMBERS: ~2 weeks / ~5 exposures/week × 1hr each (2-week protocol from IW-VV39Nv0o); "10 specific sessions" ~2 weeks (WmEiytCXR2g); 4 days pre-race arrival = disadvantage; 10 days pre-race arrival with sessions already done = adequate.
WHO: John Davis; unnamed ST coach.
SOURCE: IW-VV39Nv0o.json idx 2; WmEiytCXR2g.json idx 0,2.
HOOK: taper / readiness gating (environmental).

**RULE:** Elite heat-adaptation daily dose example: ~40–60 min heat exposure/day (mix of sauna + indoor riding with extra clothing), 2 dedicated sauna sessions/week ~40 min each, with individualized core-temperature targets.
WHO: Kasper Pedersen (coach of Magnus Ditlev).
SOURCE: Uz-8eWiaAew.json idx 6,8.
HOOK: readiness / durability.

---

## G. READINESS GATING / RECOVERY PROTOCOL / OVERREACH

**RULE:** Gate intensity-session execution in real time: if heart rate for a prescribed intensity (e.g., threshold) doesn't reach the expected zone at the prescribed power, direct the athlete to raise power within the session rather than "banking" a wasted session at the wrong physiological target; the reverse also applies — if HR is already elevated for an easy-zone target, back off to true easy that day.
WHO: Sarah Piampiano / co-host (5UOjgSc5r1c, wLXLpNGB5Dg).
SOURCE: 5UOjgSc5r1c.json idx 16; wLXLpNGB5Dg.json idx 15,16,17,18.
HOOK: readiness gating / gate_failure.

**RULE:** The single biggest data-driven barrier to improvement identified by a WKO/power-analytics expert: athletes set their threshold/FTP too high, leading to (a) chronic under-recovery/fatigue accumulation, and (b) repeated failed intervals they rationalize as "bad days" instead of correcting the number. Estimated ~50–60% (historically, "less now") of athletes have threshold mis-set too high.
NUMBERS: ~60% (a couple years prior)/lower now, of athletes; even a 10–15W overshoot on threshold materially changes training response.
WHO: Hunter Allen (WKO/TrainingPeaks co-creator, guest).
SOURCE: WrY1gBuD69Q.json idx 4,5,6,10.
HOOK: readiness gating / testing.

**RULE:** Masters/older-athlete intensity-session cap: 2–3 intense sessions/week maximum for 50+ athletes; drop to 3 total intense sessions/week (1 swim/1 bike/1 run) at 60+, often dropping to 1 intense run/week specifically even at 50+.
NUMBERS: "two to three really is the max for athletes 50 plus"; "at 60 plus... stick to three. One swim, one bike, one run."
WHO: unnamed masters-specialist coach.
SOURCE: 40qAOUskyA8.json idx 13,15.
HOOK: readiness gating / masters conditioning — **compatible with ratified 2–3 intensity-days/week cap.**

**RULE:** Older athletes need MORE recovery spacing between hard sessions than younger athletes doing the same weekly hard-session pattern (e.g., can no longer do hard track Tuesday + hard swim Thursday + hard ride Saturday back-to-back-to-back the way they used to); don't stop doing intense sessions, but increase inter-session recovery.
WHO: unnamed masters-specialist coach.
SOURCE: 40qAOUskyA8.json idx 8.
HOOK: readiness gating / masters conditioning.

**RULE:** A subjective "recovery/freshness score" (1–5 scale) tracked weekly is a useful compliance/readiness proxy — target ~80–85% of training weeks scoring a "3" (moderate fatigue, sustainable), with occasional 4s and rare 1s/5s; coach must actively challenge athlete self-scoring since athletes systematically under-report fatigue (a "3" reported is often really a "1").
NUMBERS: 1–5 scale; ~80–85% of weeks should be "3."
WHO: Rob/Trevor (d7lPSkYTF2o).
SOURCE: d7lPSkYTF2o.json idx 3,7,14.
HOOK: readiness gating / block_compliance.

**RULE:** Cardiac-drift-based readiness check for steady-state threshold sessions: heart rate should rise and level off within the first 1–2 minutes and then hold flat for the rest of a steady-wattage threshold effort; if HR keeps climbing continuously instead of leveling, the athlete is above true threshold and power should be reduced.
WHO: unnamed physiologist (moP46q5KCgw).
SOURCE: moP46q5KCgw.json idx 3,4,9,10.
HOOK: readiness gating / workout execution validation.

**RULE:** For long lower-intensity rides, prescribe/monitor by heart rate rather than fixed wattage — cardiac drift means a steady-wattage ride pushes HR into a higher zone (threshold-adjacent) by the back half of the ride, even when starting correctly in zone 2.
WHO: Trevor Connor.
SOURCE: moP46q5KCgw.json idx 9,10.
HOOK: readiness gating / workout_selector for long endurance sessions.

---

## H. DURABILITY

**RULE:** Durability (resistance to fatigue-related decay of economy/power over long durations) is distinguishable from raw threshold/VO2max/economy at a fresh state, and is trainable via long runs specifically: one long run/week >90 min duration produced 50% less economy-drift over a 90-min test than a matched group capped at ≤70-min sessions (3% vs 6% drift).
WHO: Michele Zanini.
SOURCE: Rw4Hk-Hn114.json idx 12–17.
HOOK: durability / series progression (long-session inclusion rule).

**RULE:** Durability is developed primarily through volume, not intensity, for pro cyclists — "the closer those two [fresh vs. fatigued power] numbers are, the better your performance" and "how you develop it... it's just volume."
WHO: Stephen Barrett.
SOURCE: MjJ3x3ZRaZ4.json idx 19.
HOOK: durability.

**RULE:** Shoe rotation (2+ pairs alternated) reduces running-related injury risk by 39% per a cited study, via variable internal/external loading forces.
NUMBERS: 39% reduction.
WHO: guest physical therapist (c8FIyNRYSv0.json).
SOURCE: c8FIyNRYSv0.json idx 15.
HOOK: durability / injury mitigation.

**RULE:** Roughly 50% of the metabolic energy cost of distance running comes from the calf/Achilles complex — prioritize calf-specific strength/isometric loading, especially for masters runners who lose calf capacity that isn't compensated by other muscle groups.
NUMBERS: ~50% (Hamner & Delp study cited).
WHO: guest physical therapist.
SOURCE: c8FIyNRYSv0.json idx 3.
HOOK: durability / strength scheduling / masters conditioning.

**RULE:** Tendon-loading protocol for injury rehab/prevention: isometric holds 5–15s (up to 30s), high contraction intensity (70–90% of 1RM, or the "Berlin method" 4×4-sec holds at 90% MVIC); heavy low-rep strength work (2 reps in reserve) trains the neural/central system ("software"), not hypertrophy ("hardware").
NUMBERS: 5–15s holds (up to 30s); 70–90% 1RM; Berlin method 4 reps × 4s at 90% MVIC; heavy-lift target = 2 reps left in reserve.
WHO: guest physical therapist (c8FIyNRYSv0); SNFnH6IXiZw guest.
SOURCE: c8FIyNRYSv0.json idx 12,16,0,1,2,4; SNFnH6IXiZw.json idx 12.
HOOK: strength scheduling / durability.

---

## I. FUELING

**RULE:** Carbohydrate fueling threshold by duration: for exercise <1 hr, small CHO amounts still measurably improve perceived effort/performance; for 2–3+ hrs, CHO becomes the actual fuel source and must be actively fed to prevent hypoglycemia/bonking. General guideline for performance-focused sessions: 30–90g CHO/hr depending on goal, with pro/elite athletes tolerating well above 90g/hr (historic "60g/hr ceiling" belief has been shown wrong — modern ceiling is roughly double).
NUMBERS: <1hr: small amounts help; 2–3hr+: full CHO-fuel mechanism kicks in; general range 30–90g/hr; historic 60g/hr belief now "doubled and some"; elite intake reported up to 120g/hr.
WHO: B8V3HnPxLhc guests (sports nutritionists); Stephen Barrett.
SOURCE: B8V3HnPxLhc.json idx 9,10,17,16; MjJ3x3ZRaZ4.json idx 15.
HOOK: fueling.

**RULE:** Body-weight-relative fueling: intake targets should scale to body mass — the practical example given is that "one extra bottle" is ~1% of body weight for an 80kg athlete vs. ~2% for a 50kg athlete, meaningfully different relative loads.
NUMBERS: extra bottle ≈1% BW (80kg) vs ≈2% BW (50kg).
WHO: unnamed ST coach guest.
SOURCE: uQmyBRf2tr4.json idx 3.
HOOK: fueling.

**RULE:** ~70–80% of ingested carbohydrate during exercise is immediately oxidized; the remaining ~20% is stored as muscle glycogen rather than causing metabolic harm — supports aggressive in-race fueling without weight-gain concern.
NUMBERS: 70–80% oxidized, ~20% stored.
WHO: B8V3HnPxLhc guests.
SOURCE: B8V3HnPxLhc.json idx 13,14.
HOOK: fueling.

**RULE:** Above-threshold ("severe domain") training relies almost completely on carbohydrate; low-carb dietary approaches can impair the body's ability to use carbohydrate even after re-introducing it — avoid restrictive low-carb approaches for athletes doing regular above-threshold work.
WHO: unnamed nutritionist (moP46q5KCgw).
SOURCE: moP46q5KCgw.json idx 3.
HOOK: fueling / nutrition_compliance.

**RULE:** For high-fructose sports products, note the body absorbs glucose:fructose at ~4:1 ratio — products with near-equal glucose/fructose ratios (e.g., HFCS at 45:55) mismatch physiological absorption capacity; multi-transportable-carb (glucose+fructose) products should respect that ratio for higher hourly CHO delivery.
NUMBERS: 4:1 glucose:fructose absorption ratio.
WHO: B8V3HnPxLhc guest.
SOURCE: B8V3HnPxLhc.json idx 1.
HOOK: fueling.

**RULE (DURABILITY/RECOVERY, not headline-worthy but flagging):** High-intensity exercise (e.g., a half-Ironman) can downregulate T-regulatory immune cells for at least 10 days post-event — a relevant post-race/post-A-race immune-recovery signal, potentially informing a "no hard training for X days post-A-race" gate.
NUMBERS: T-reg downregulation still present 10 days post-event.
WHO: B8V3HnPxLhc guest.
SOURCE: B8V3HnPxLhc.json idx 5.
HOOK: readiness gating (post-race).

---

## J. MASTERS / NOVICE CONDITIONING

**RULE:** Novice/beginner sprint-triathlon running plan structure: 4 weeks of pure easy running before any intensity is introduced; first intensity session = 5×1min moderately-hard + 2min easy jog; long run builds gradually from 35 min to 45 min (holds at 45 min for the back half of an 8-week plan) — 45 min is "more than enough" for a first sprint triathlon and minimizes overuse-injury risk.
NUMBERS: 4 weeks easy-only before intensity; first hard session 5×1min/2min jog; long run 35→45min over 8 weeks, capped at 45min.
WHO: Mikael Eriksson.
SOURCE: NPwc2VB2Piw.json idx 12,13,14.
HOOK: novice conditioning / calculate_plan_dates / series progression.

**RULE:** First-year runners (regardless of triathlon distance ≤Olympic) should cap the long run at 60 minutes to maximize consistency and minimize injury risk — don't chase longer long-runs in year one even if race distance nominally exceeds that duration in time.
NUMBERS: 60-min cap, year one.
WHO: Mikael Eriksson.
SOURCE: NPwc2VB2Piw.json idx 15,18.
HOOK: novice conditioning.

**RULE:** Novice-training subjective gate: training should generally leave a beginner feeling more energized than exhausted — beginners have a "low threshold" for eliciting a good training stimulus, so err toward under-dosing rather than over-dosing intensity/volume.
WHO: Mikael Eriksson.
SOURCE: NPwc2VB2Piw.json idx 19.
HOOK: novice conditioning / readiness gating.

**RULE:** Masters (50s–60s) triathletes: threshold/economy are the "easiest to maintain" of the three big physiological markers as age advances, VO2max declines the most; running declines earliest/fastest (~1%/yr from mid-30s to mid-50s, then steepens), swimming declines later (~0.5–0.9%/yr until 60s-early 70s), cycling is easiest to maintain of the three. Training-volume decision for masters should depend on training history: low-lifetime-volume athletes can still increase volume in their 50s; high-lifetime-volume athletes (10–12 hrs: maintain; 15–18 hrs: consider decreasing) should maintain or taper down slightly, adding high-intensity + strength to offset sarcopenia.
NUMBERS: running decline ~1%/yr (mid-30s–mid-50s, steepens after); swimming decline ~0.5–0.9%/yr (until 60s/early-70s); 10–12hrs/wk → don't decrease; 15–18hrs/wk → consider decreasing, upper-50s+.
WHO: masters-specialist guest coach.
SOURCE: 40qAOUskyA8.json idx 4,5,11,13,12,14,15.
HOOK: masters conditioning / athlete classification.

**RULE:** For fast-twitch-dominant amateurs, the recommendation is to avoid excess volume of threshold/heavy-domain work (where high total volumes accumulate) and to be extra careful about doing endurance work too intensely — this profile "burns out" via long threshold sessions specifically, not via VO2max work.
WHO: B4OusQAVnPc guest.
SOURCE: B4OusQAVnPc.json idx 0,1,2,11.
HOOK: athlete classification → workout_selector guardrail.

---

## K. STRENGTH SCHEDULING

**RULE:** Strength-training frequency/dose should taper down (not disappear) as race proximity increases: ~6 weeks out from an Ironman, strength drops to ~1×/week plus daily "movement snacks" (brief non-fatiguing mobility/activation work throughout the day) rather than full sessions.
NUMBERS: 6 weeks pre-race → 1×/week strength + daily movement snacks.
WHO: guest physical therapist.
SOURCE: c8FIyNRYSv0.json idx 4.
HOOK: strength scheduling.

**RULE:** In-season maintenance strength dose: 1 heavy-load/low-rep session per week (or even every 10 days) is sufficient to maintain strength gains built off-season with a twice-weekly protocol — don't need to sustain 2×/week year-round.
WHO: SNFnH6IXiZw guest.
SOURCE: SNFnH6IXiZw.json idx 17.
HOOK: strength scheduling.

**RULE:** Strength session dose for age-group triathletes: ~2×/week, 30–50 min average (45 min typical), minimal periodization required — mostly rotate exercise selection ~monthly rather than progress load/rep schemes on a formal cycle.
NUMBERS: 2×/week, 30–50min (avg 45min); don't repeat identical exercise selection for 52 weeks straight.
WHO: unnamed guest coach.
SOURCE: 3LszuOxRyT4.json idx 12,18.
HOOK: strength scheduling.

**RULE:** Strength training injury-recurrence management: for chronic-injury-prone athletes, strength training resolves the underlying issue in the majority of cases (coach's estimate: "90% of athletes... it's strength training that resolves the issue").
NUMBERS: ~90% (subjective coach estimate, not a study).
WHO: unnamed guest coach.
SOURCE: 3LszuOxRyT4.json idx 12.
HOOK: strength scheduling / durability.

**RULE:** Weight-work soreness planning: schedule heavy lifting with an easy/recovery day the day after, since DOMS peaks 48–72 hrs post-session; a single heavy session's protective effect against soreness lasts ~6–7 months.
NUMBERS: 48–72 hr soreness window; protective effect lasts 6–7 months.
WHO: Trevor Connor.
SOURCE: moP46q5KCgw.json idx 9.
HOOK: strength scheduling / readiness gating.

---

## L. BONK-BROS — LOW-YIELD SKIM (as instructed, terse)

This channel is entertainment/gossip-format (bike-race rankings, gear talk, banter) — only 540 of ~5,000+ total segments flagged as coaching-relevant, and of those only ~23 contained genuinely quantified claims. Nothing here rises to formal "rule" quality, but a few anecdotal data points are worth flagging for cross-reference/pattern-matching rather than direct rule extraction:
- Repeated anecdotal pattern: several named pro/elite riders described as performing *better* in retirement/reduced-training states than during peak WorldTour volume ("he's been training about 70% of what he normally trains," "puts out better numbers now... rides like 10 hours a week") — consistent with the durability/overreach literature above but purely anecdotal (38ts6rYmTL0.json idx 7,8,9).
- "Overtrained" used loosely/frequently as a lived-experience descriptor for large one-off volume spikes (e.g., 30-hr week after a low-volume period → self-reported overtraining) (HYRj6c9QaXg.json idx 2) — anecdotal support for the ramp-rate caution already covered above, not a new number.
- No usable numeric rules on interval dosing, phase sequencing, taper, or fueling were found with sufficient rigor to extract; recommend deprioritizing this channel for any future re-mining pass.

---

## (a) TOP-10 HIGHEST-VALUE FINDINGS

1. **VO2max targets should anchor to 5-min mean-max power, not %FTP** — directly prevents the interval-dosing failure mode demonstrated in the Taylor Finney vs. pro-athlete case (same %FTP target caused one athlete to sail through and two national champions to fail on rep 4). (lCJ_mkfKJsk.json)
2. **Durability is trainable and measurable via a 90-min sub-threshold economy-drift test; long runs (>90 min, weekly) cut drift by ~50%.** Directly actionable for series_progression/long-session inclusion logic. (Rw4Hk-Hn114.json)
3. **Ramp-rate model dispute:** multiple credentialed coaches explicitly reject the "10% rule" in favor of absolute-minute progression (+5 min/run/week default, +10 min/run/week for resilient athletes) — while one other ST guest cites BJSM evidence *for* the 10% rule. This is a live disagreement worth encoding as a configurable ramp strategy rather than a single hard rule. (multiple files)
4. **Sub-threshold training band for elite/WorldTour-style triathlon prescription is 94–99% of FTP** — materially higher/narrower than a generic "endurance" zone, and worth checking against the ratified endurance-IF cap (see contradictions). (vZI1qtPSyVI.json)
5. **Intensity distribution is volume-dependent, not fixed 80/20**: 70% low-intensity at 6–8 hrs/wk scaling up to 90–98% at 20 hrs/wk. Should directly parameterize the intensity-distribution model by weekly hour target. (3LszuOxRyT4.json)
6. **Athlete-profile-based recovery ratios**: fast-twitch profiles get MORE recovery relative to work (3:1→2:1 for threshold, 4:1→3:1 for sweet spot) than slow-twitch; directly actionable in workout_selector individualization. (B4OusQAVnPc.json)
7. **VO2max micro-interval protocol specifics**: 2:1 effort:recovery empirically maximizes time-at->90%-VO2max; don't attempt micro-interval sets shorter than 5-min total accumulated work; build to 10–20 min accumulated VO2max time across the season. (lCJ_mkfKJsk.json)
8. **Taper contradiction candidates found**: multiple ST/fast-talk coaches explicitly prescribe sub-45-min sessions as legitimate (not recovery/opener) training — directly conflicts with the ratified 45-min floor. (E_djkYB36Tw.json, OWMG7soxNy8.json)
9. **Novice conditioning specifics**: 4 weeks pure easy before intensity, first hard session 5×1min/2min jog, long-run cap 45–60 min in year one — a full novice progression template not previously captured. (NPwc2VB2Piw.json)
10. **Recovery-week volume band evidence point**: Peter Leo's running recovery-week guidance (~67% of peak volume) sits just above the ratified 50–65% band — worth checking whether the standard should widen slightly or whether this is an outlier. (-zgLbMNYLHY.json)

---

## (b) CONTRADICTIONS TABLE (vs. ratified standards)

| # | Ratified Standard | Contradicting Evidence | Source | Severity |
|---|---|---|---|---|
| 1 | 45-min session floor (recovery/openers exempt) | Jacob Tipper explicitly prescribes 20–30 min runs and "jog to pool, swim 2K, jog home" as legitimate frequency-building *training* volume, not recovery/openers, for time-crunched age-groupers. Gordo Byrn's "30 for 30" protocol (30×30-min runs in 30 days) is prescribed as a core training method, not recovery. | E_djkYB36Tw.json idx 18,19,0,1,2 ("frequency training"); OWMG7soxNy8.json idx 0,19 | **High** — direct, repeated, from named credible coaches (Ben Healy's coach; elite masters IM racer/author). Recommend adding a "frequency/combo-session" exemption category alongside recovery/openers. |
| 2 | 45-min session floor | Novice sprint-triathlon plan (Eriksson) prescribes run sessions as short as 1min run/1min walk building to 5min run/30s walk, and beginner strength sessions of "20 minutes, that's perfect" — clearly under 45 min and not "recovery." | NPwc2VB2Piw.json idx 18,19,9 | **Medium** — plausibly covered by a "true novice" exemption not currently specified in the ratified rule; recommend clarifying novice exemption explicitly. |
| 3 | VO2max every 14 days | WorldTour cycling model (Stephen Barrett) and dedicated VO2max episode (Henderson/Connor) both describe VO2max stimulus recurring multiple times per week during build/race-specific blocks (2–3 structured intensity sessions/week, some VO2max, plus additional "spiked" VO2max exposure layered into endurance rides). No evidence found for a 14-day VO2max cadence anywhere in either corpus — every coach who specifies cadence describes weekly or near-weekly VO2max/near-VO2max stimulus in-season. | MjJ3x3ZRaZ4.json idx 13,14,15; lCJ_mkfKJsk.json (throughout); OKLOIpfWvFY.json idx 7,9,10 | **High** — this is the most load-bearing contradiction found; recommend re-examining whether the 14-day rule should be phase-dependent (e.g., wider spacing only in base, weekly in build/peak). |
| 4 | Ramp ≤8 CTL/wk within-block | No coach in either corpus frames ramp rate in CTL/week terms at all — every quantified ramp-rate rule uses absolute minutes/week (+5–10 min/run/wk) or year-over-year hour steps (2–3 hrs/yr), or rejects %-based rules outright. Not a direct numeric contradiction (no CTL evidence either way) but flags that CTL/week may not be the mental model practicing coaches actually use — worth validating the CTL metric choice itself given wkzwlBfJwxY.json's explicit critique of TSS/CTL validity (item below). | Multiple (section C above) | **Medium** — model-choice flag, not a number conflict. |
| 5 | (Implicit, TSS/CTL as core metrics generally) | Mikael Eriksson explicitly argues TSS/CTL are "not valid" in a triathlon context: stochastic swim sessions with wetsuit/pull-buoy inflate TSS falsely; cross-discipline transferability is "extremely poor"; TSS doesn't account for terrain (hilly run vs flat); recommends 3-month/6-week rolling volume averages instead of TSS/CTL as the primary load metric. | wkzwlBfJwxY.json idx 0,1,3,4,5,6 | **High (architectural)** — if calculate_plan_dates/block_chain leans on CTL/TSS as core scalars, this is a direct credible challenge to that metric choice from a named, well-regarded ST host; recommend at minimum a volume-based cross-check layer. |
| 6 | Recovery week = 50–65% of load-week TSS | Peter Leo's running-specific recovery-week guidance is ~67% of peak volume (40k from a 60k peak) — narrowly above the ratified band. | -zgLbMNYLHY.json idx 2 | **Low** — small deviation, single data point, running-specific. |
| 7 | Endurance IF 0.60–0.70 scaled down with duration | Rob Cheetham's WorldTour-adjacent long-course model defines "sub-threshold" cardiovascular-development work at 94–99% of FTP — well above the 0.60–0.70 endurance band, though this is explicitly *not* their endurance/Z2 category (their long runs are described separately as "always easy," 6min/km pace). Flagging because if any downstream logic maps "sub-threshold" generically to the endurance-IF band, this WorldTour usage of "sub-threshold" would violate it. | vZI1qtPSyVI.json idx 17,18,2,3,4,11,12,13 | **Medium** — likely a terminology/category mismatch (their "sub-threshold CV session" ≠ our "endurance" bucket) rather than a true contradiction; recommend confirming the workout-type taxonomy separates these. |
| 8 | 2–3 intensity days/week + 90–120 hard-min/week floor | OKLOIpfWvFY (Sam Proctor, pro coach) describes a week with "two hard swims, two hard bikes, one hard run" (up to 5 hard sessions across disciplines) for a professional triathlete — could exceed a literal 2–3-intensity-*days*/week cap if hard sessions land on different calendar days, though likely compatible if some are doubled on the same day. | OKLOIpfWvFY.json idx 12 | **Low** — probably resolvable via same-day stacking; flag for triathlon multi-discipline nuance rather than true conflict. |

---

## (c) DUPLICATE MATERIAL (already covered by Couzens/Seiler/Cusick pass — one line each, not expanded)

- General 80/20 polarized-intensity principle and its rationale (mT-X13K0-eI.json, multiple ST files) — DUPLICATE.
- FTP/threshold definition as ~1-hr maximal sustainable power / MLSS proxy (mT-X13K0-eI.json, WrY1gBuD69Q.json, moP46q5KCgw.json) — DUPLICATE.
- Taper reduces volume while maintaining intensity; avoid a "miracle taper" mentality (IW-VV39Nv0o.json, vZI1qtPSyVI.json) — DUPLICATE.
- General base→build→peak linear periodization structure (mT-X13K0-eI.json idx 3) — DUPLICATE.
- Aerobic capacity / anaerobic threshold / economy as the "big three" physiological determinants (Joyner & Coyle 2008 citation) (mT-X13K0-eI.json idx 2) — DUPLICATE.
- Cardiac drift / heart-rate-vs-power divergence on long steady efforts (moP46q5KCgw.json, ZsXTprligCY.json) — DUPLICATE.
- Recovery day = full rest or very-low-intensity active recovery, keep exposure/volume very low (MjJ3x3ZRaZ4.json idx 17,18) — DUPLICATE.
- General carbohydrate-per-hour fueling guidance framing (30–90g/hr) as a starting principle (B8V3HnPxLhc.json, HGR-roV57iA.json) — DUPLICATE (though the specific 4:1 glucose:fructose ratio and 70–80%-oxidation figures above are novel enough to keep).
- VO2max as the physiological marker that peaks/adapts fastest in an athlete's career (lCJ_mkfKJsk.json idx 0) — DUPLICATE.
- Zone-2/easy-day intensity control importance and "most training should be easy" framing generally (numerous files) — DUPLICATE (the *quantified volume-dependent scaling* in section E above is the novel contribution, not the general principle).

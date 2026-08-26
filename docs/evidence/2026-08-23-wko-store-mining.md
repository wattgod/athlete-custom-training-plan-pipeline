# WKO/Cusick Store Mining — 2026-08-23

Miner: Explore agent over ~/endure-labs-graph/knowledge/sport-science/ (8 atomic + 8 reference + 4 root notes). Rule IDs R1-R118 cited from docs/ALGORITHM_EVIDENCE.md.

---

Read all 8 atomic notes, all 8 reference notes, and the 4 root notes. Below is the extraction.

## Path legend (all absolute)

| Key | File |
|---|---|
| `REF/interval-design` | `/Users/mattirowe/endure-labs-graph/knowledge/sport-science/reference/interval-design.md` |
| `REF/training-load` | `/Users/mattirowe/endure-labs-graph/knowledge/sport-science/reference/training-load-and-ramp.md` |
| `REF/annual` | `/Users/mattirowe/endure-labs-graph/knowledge/sport-science/reference/annual-planning.md` |
| `REF/fatigue` | `/Users/mattirowe/endure-labs-graph/knowledge/sport-science/reference/fatigue-resistance.md` |
| `REF/testing` | `/Users/mattirowe/endure-labs-graph/knowledge/sport-science/reference/testing-protocol.md` |
| `REF/zones` | `/Users/mattirowe/endure-labs-graph/knowledge/sport-science/reference/zones-and-thresholds.md` |
| `REF/pd-model` | `/Users/mattirowe/endure-labs-graph/knowledge/sport-science/reference/power-duration-model.md` |
| `REF/coaching` | `/Users/mattirowe/endure-labs-graph/knowledge/sport-science/reference/coaching-practice.md` |
| `ROOT/residual` | `/Users/mattirowe/endure-labs-graph/knowledge/residual-training-effects.md` |
| `ROOT/delayed` | `/Users/mattirowe/endure-labs-graph/knowledge/delayed-training-effect.md` |
| `ROOT/stabilization` | `/Users/mattirowe/endure-labs-graph/knowledge/load-stabilization-phase.md` |
| `ROOT/fit` | `/Users/mattirowe/endure-labs-graph/knowledge/fit-file-analysis.md` |
| `INDEX` | `/Users/mattirowe/endure-labs-graph/knowledge/sport-science/sport-science-index.md` |

**Store-wide caveat, stated by the store itself** (`INDEX`, Provenance): "No claim in this store has been lab-verified independently of the source webinars — every numeric threshold here is expert-opinion, coaching-heuristic, or anecdote by the reference notes' own confidence tags, not peer-reviewed population data." The only genuinely peer-reviewed anchors are in the 4 root notes (Banister 1975, Verkhoshansky 1977, Busso 2003, Issurin 2008, Zatsiorsky 2006) and the Marcora & Staiano study in `REF/fatigue`.

---

# A. Ramp rate / weekly load progression

**R1 — RULE:** Cap planned week-over-week CTL gain at 5–8 points, sustained no more than 2–4 consecutive weeks before a rest week.
NUMBERS: 5–8 CTL/wk; unbroken build window 14–28 days (3-on/1-off fits); high-responder exception ~9–10 CTL/wk (n=1, 23yo pro).
CONFIDENCE: expert-opinion (anecdote for the 9–10 exception).
SOURCE: `REF/training-load` §4.1, §8.3 — Cusick (C-vfC-CRkl5Kk-19, -27).
HOOK: block_chain/calculate_plan_dates + block_compliance (new R-rule: reject a generated block whose modeled CTL slope >8/wk).
WKO-GATE: none — PMC/CTL/ATL/TSB is open Coggan/Banister, explicitly not WKO-proprietary (`REF/training-load` "Open-literature analogue").

**R2 — RULE:** Decelerate the ramp-rate target as the plan adds intensity — never hold the base-phase ramp constant into sweet-spot/tempo blocks.
NUMBERS: no fixed number; direction only ("lighten the load of progression"). Pair with R3.
CONFIDENCE: expert-opinion.
SOURCE: `REF/training-load` §4.2 — Cusick (C-H9HA4cupIvg-08).
HOOK: series progression / block_chain.
WKO-GATE: none.

**R3 — RULE:** Below CTL 100 use the full 5–8/wk band; above CTL 100 halve the target; treat CTL 135–165 as a diminishing-returns wall and stop ramping.
NUMBERS: slowdown point ~CTL 100; diminishing returns 135–165; Grand Tour ceiling 180–200 (not convertible to peak form).
CONFIDENCE: expert-opinion.
SOURCE: `REF/training-load` §3.2, §3.3 — Cusick (C-qnCAlNgoDxM-11, C-vfC-CRkl5Kk-20, -30, -31).
HOOK: block_chain / physiology gate.
WKO-GATE: none.

**R4 — RULE:** Discount all ramp-rate ceilings by 15–20% for run-dominant athletes.
NUMBERS: −15–20% vs. cyclists. Injury-history screen: audit ramp in the 2–4 weeks pre-injury.
CONFIDENCE: expert-opinion (screen = coaching-heuristic).
SOURCE: `REF/training-load` §4.4, §4.5 — Cusick (C-vfC-CRkl5Kk-21, -22).
HOOK: block_chain (sport-conditional ramp cap).
WKO-GATE: none.

**R5 — RULE:** Set the athlete's absolute CTL band from training age, not age or FTP; subtract ~10 points for athletes over 50.
NUMBERS: 1–2 yr → low <40 / med 41–75 / high ≥76. 2–5 yr → <60 / 61–95 / ≥96 (runners mature faster). 5+ yr cycling or 3+ yr running → <80 / 81–115 / ≥116. Masters >50: −~10 on each threshold.
CONFIDENCE: expert-opinion (WKO user-base derived).
SOURCE: `REF/training-load` §3.1, §8.1 — Cusick (C-vfC-CRkl5Kk-13/-14/-15/-17).
HOOK: athlete classification (training age → target CTL band → plan volume).
WKO-GATE: none.

**R6 — RULE:** Cap achievable CTL by available weekly hours before assigning a band — do not prescribe a CTL target the hour budget cannot reach.
NUMBERS: 6–8 hrs/wk ⇒ CTL ~75 is a hard ceiling. Strength work counts at 25 TSS/30 min (~50 TSS/hr) on a separate track.
CONFIDENCE: expert-opinion / coaching-heuristic (strength proxy).
SOURCE: `REF/training-load` §2.2, §9.10 — Cusick (C-vfC-CRkl5Kk-16, -47).
HOOK: calculate_plan_dates (feasibility gate at plan-generation time).
WKO-GATE: none.

**R7 — RULE:** For a genuinely plateaued established athlete, step volume 20–25% rather than tweaking intensity.
NUMBERS: +20–25% volume. Multi-year escalation exemplars (do NOT average — two different athlete situations): new/young 50→100→120→140 CTL over 3 yrs; developing pro ~10–15 pts/yr, 115→125→135, ceiling ≈140–155.
CONFIDENCE: expert-opinion.
SOURCE: `REF/annual` §3 — Cusick (M_I3GwOtJKE-03, ldRCkYGaSvI-02, qnCAlNgoDxM-14, vfC-CRkl5Kk-29).
HOOK: block_chain (annual/seasonal escalation), athlete classification.
WKO-GATE: none.

**R8 — RULE:** Require every generated mesocycle chain to show a visible CTL dip; reject monotonic climbs.
NUMBERS: healthy PMC = cyclical overreach→recover, each cycle peaking higher. NFOR signature: ATL sustained > CTL, no rest breaks, subjective "tired every session."
CONFIDENCE: expert-opinion (§5.7) / anecdote (§5.1 case).
SOURCE: `REF/training-load` §5.1, §5.7 — Cusick (C-qnCAlNgoDxM-04, C-vfC-CRkl5Kk-35).
HOOK: block_compliance (new R-rule: "no rest-week gap >4 weeks; ATL>CTL for ≥3 consecutive weeks without a recovery week = fail").
WKO-GATE: none.

**R9 — RULE:** After an aggressive volume ramp, expect and schedule around 3–5 weeks of performance decline before gains appear; do not re-prescribe on the dip.
NUMBERS: 3–5 wks decline; fitness layers in over 4–8 wks (one source ~6–8). Banister τ₁ = 40–42 d; 95% of fitness steady-state ≈ 3τ ≈ 126 days.
CONFIDENCE: expert-opinion (Cusick); peer-reviewed/foundational for the Banister decay (★★★★★).
SOURCE: `REF/training-load` §4.6 — Cusick; `ROOT/delayed` — Verkhoshansky 1977, Banister 1975, Busso 2003.
HOOK: block_chain (do not insert a corrective block inside the 3–5 wk window); plan-narrative copy.
WKO-GATE: none.

**R10 — RULE:** Insert a load-stabilization block (constant weekly TSS, rising specificity) between build and peak instead of ramping to the race.
NUMBERS: fatigue steady-state ~21 d (3×ATL_TC 7); fitness steady-state ~126 d (3×CTL_TC 42) ⇒ 21–126 d window where fatigue is flat and fitness still rising. Model sim (τ₁=40, τ₂=10, k₁=0.2, k₂=0.35): constant load vs. continuous ramp = ~6% higher peak fitness on ~4% less total work.
CONFIDENCE: model-derived, explicitly "model predictions, not empirical measurements"; individual τ₁ 30–60 d.
SOURCE: `ROOT/stabilization` — Banister-model simulation, mapped to Issurin accumulation→transmutation→realization.
HOOK: block_chain/calculate_plan_dates (new phase type between Build and Peak; applies to 12+ wk A-race preps).
WKO-GATE: none.

**R11 — RULE:** Treat true overtraining as effectively impossible below ~10–12 hrs/wk — diagnose under-progression instead.
NUMBERS: ~10–12 hrs/wk threshold. Distinct from NFOR, which is possible at any volume.
CONFIDENCE: expert-opinion.
SOURCE: `REF/training-load` §5.4 — Cusick (C-my4Y0DulYTY-26).
HOOK: block_compliance (suppress "you're overtrained" flags below the hour threshold; flag flat progression instead).
WKO-GATE: none.

**R12 — RULE:** Reset training-age/ramp maturity after a long layoff, but flag the retention window as unresolved.
NUMBERS: Source A: maturity holds ~12–18 months, then resets to 1–3 yrs training age. Source B: maturity persists ~5 years and healing status, not ramp guidance, should govern return.
CONFIDENCE: expert-opinion vs. anecdote — flagged as a **direct contradiction** in the store; "David should not cite a specific maturity-retention window with confidence."
SOURCE: `REF/training-load` Contradictions — Cusick (C-qnCAlNgoDxM-12 vs. C-vfC-CRkl5Kk-43).
HOOK: athlete classification. **Use only as a soft prior, never a hard gate.**
WKO-GATE: none.

---

# B. Interval dosing — per-session and per-week time-at-intensity

**R13 — RULE:** Dose every interval session by accumulated time-in-zone, and treat reps/watts/work:rest as interchangeable levers to hit that TIZ target.
NUMBERS: worked equivalence 3×5min (15) ≈ 4×4min (16). Don't push TIZ meaningfully past the high end of the band (diminishing returns).
CONFIDENCE: coaching-heuristic / expert-opinion.
SOURCE: `REF/interval-design` §1 — Cusick (C-0Qm5fXPo09k-22, C-my4Y0DulYTY-13/-02, C-jtBW4CIGiEU-20).
HOOK: workout_selector (select by TIZ target, not by named workout); series progression.
WKO-GATE: TIS→ "session-level time-in-zone accumulation (minutes above X% of duration-matched CP power)."

**R14 — RULE:** Cap a single VO2max session at 15–18 min above ~95% of target power; if the athlete clears that ceiling twice in a row, switch the progression lever from duration to intensity.
NUMBERS: per-session ceiling 15–18 min >95%. Alternate framing: ~15 min at *true* VO2max is the effective target; total prescribed interval time to bank it ranges 12–30 min because athletes reach VO2max at different rates. Count TIZ above ~90% (tightened to ~95% in some framings). Worked example: 7×3min = ~21 min work but only ~11–12 min above 90–95%.
CONFIDENCE: expert-opinion / coaching-heuristic ("studied pretty well," no study named).
SOURCE: `REF/interval-design` §2, `REF/pd-model` §15 — Cusick (C-M_I3GwOtJKE-43, C-ldRCkYGaSvI-36/-37, C-RA52lI2WRrg-22, C-M_I3GwOtJKE-42).
HOOK: workout_selector + physiology gate (T@VO2max target band).
WKO-GATE: "time above 95% VO2max" → cumulative minutes above duration-matched %CP thresholds from FIT power streams.
**REINFORCEMENT + REFINEMENT of the ratified "under-VO2 <5min T@VO2max" gate: the store gives an upper bound too (15–18 min), and a prescribed-time-to-TIZ conversion factor (~12–30 min prescribed → ~15 min banked).**

**R15 — RULE:** Hold weekly sweet-spot/extensive TIZ to 20–30% of weekly volume (hard ceiling 40%, >30% for mature athletes only) and weekly threshold/intensive TIZ to 10–15% (trim for masters/less-trained).
NUMBERS: extensive 20–30%, ≤40%; intensive 10–15%.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/interval-design` numeric table — Cusick (C-t9cMtn3pe8A-26, -30).
HOOK: block_compliance (new R-rule: weekly TIZ-share bands by band type).
WKO-GATE: none (raw time-in-zone).

**R16 — RULE:** Size an end-of-phase block's total TIZ relative to the athlete's time-to-exhaustion at threshold.
NUMBERS: extensive block ≥200% of TTE; intensive block ≥150% of TTE; general FTP work 110–150% of TTE.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/interval-design` numeric table — Cusick (C-t9cMtn3pe8A-27, -31, -42).
HOOK: series progression (block TIZ budget).
WKO-GATE: **TTE → time-to-exhaustion at FTP from testing, or CP-model t = W′/(P−CP)** (`REF/testing` analogue table). Usable, but the store flags the CP-derived TTE will diverge from WKO's.

**R17 — RULE:** Never program a sweet-spot interval shorter than 15 min or a threshold interval shorter than 10 min.
NUMBERS: SST floor 15 min (15–20 acceptable); threshold floor 10 min. Sub-15-min "SST" reliably drifts into threshold effort.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/interval-design` §6, numeric table — Cusick (C-t9cMtn3pe8A-30, C-RjJ7PNu3sNg-39).
HOOK: workout_selector (rep-length floor by zone).
WKO-GATE: detection of the drift uses TIS → substitute W′bal drawdown (see R44) or measured %-of-CP time distribution.
**REINFORCEMENT of the ratified 45-min session floor, at the interval-length layer.**

**R18 — RULE:** Cap sweet-spot to ~3 days/week and prefer fewer, fuller sessions over more, thinner ones.
NUMBERS: ≤3 d/wk (4–6 d/wk "dulls the response"); 3×20 min × 3 days preferred over 2×20 min × 4 days.
CONFIDENCE: expert-opinion / coaching-heuristic.
SOURCE: `REF/interval-design` §7 — Cusick (C-H9HA4cupIvg-05/-06/-10/-11).
HOOK: workout_selector + block_compliance (frequency cap per zone).
WKO-GATE: none.

**R19 — RULE:** Cap hard interval days per week by training maturity: 2 for novices, up to 3 for mature athletes; in a VO2max-focused block cap at 2–2.5.
NUMBERS: novice ~2/wk; mature (1–2+ yrs) up to 3/wk; beyond 3 = ~1% more gain for ~5% more fatigue. Phase-3 VO2max block: ~2–2.5 hard days/wk, all other days easy/mid-to-low zone 2.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/annual` §4, `REF/training-load` §9.9 — Cusick (C-my4Y0DulYTY-24, C-t9cMtn3pe8A-49).
HOOK: block_compliance (new R-rule).
**CONTRADICTION with the ratified "2–3 intensity/load week": the store caps novices at 2 and only permits 3 for athletes ≥1–2 yrs training age, and drops to 2–2.5 in a VO2max block. Recommend making the ratified 2–3 maturity-conditional.**

**R20 — RULE:** Progress hard days by making them harder, never by adding hard days; let easy days get easier as hard days progress.
NUMBERS: qualitative. Implementation = the "plus-one" rule (R21).
CONFIDENCE: expert-opinion.
SOURCE: `REF/annual` §4 — Cusick (C-my4Y0DulYTY-28).
HOOK: series progression (level ramp semantics).
WKO-GATE: none.

**R21 — RULE:** Step each hard session's total time-in-target-zone modestly above the prior comparable session — "plus one," not mechanical rep escalation.
NUMBERS: illustrated steps +45 s, then +1 min of cumulative TIZ.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/training-load` §7.1 — Cusick (C-M_I3GwOtJKE-22, C-ldRCkYGaSvI-06/-07).
HOOK: series progression (concrete step size for level ramps — the store's most directly usable progression increment).
WKO-GATE: none.

**R22 — RULE:** Gate every progression step on outcome, not calendar: advance only after the current dose is reported manageable, and repeat an unchanged prescription at most once.
NUMBERS: repeat ≤1× before advancing; >3 unchanged repeats = under-progression flag; never repeat unchanged a 3rd time ("Always Be Pushing," credited to Coggan). Move exactly one of three levers: power, TIZ, or rest.
CONFIDENCE: coaching-heuristic / expert-opinion.
SOURCE: `REF/interval-design` §1, `REF/coaching` §7.1 — Cusick, attributing Coggan (C-my4Y0DulYTY-27/-25, C-H9HA4cupIvg-34).
HOOK: series progression + block_compliance (new R-rule: "no identical workout 3× in a chain").
WKO-GATE: none.

**R23 — RULE:** Progress sub-threshold work toward one longer continuous effort, not toward more/shorter pieces.
NUMBERS: correct direction 1×30 → 2×20 → 1×45 → 2×30 → 1×60. Named error: 2×20 → 3×15 → 6×10. Below threshold, 2×20 ≈ 1×40 physiologically.
CONFIDENCE: expert-opinion.
SOURCE: `REF/interval-design` §1 — Cusick (C-jtBW4CIGiEU-26, -27).
HOOK: series progression (sub-threshold ladder definition).
WKO-GATE: none.

**R24 — RULE:** Progress extensive intervals by adding reps at fixed duration until it plateaus, then cut rest toward a continuous effort.
NUMBERS: qualitative sequencing rule.
CONFIDENCE: expert-opinion.
SOURCE: `REF/interval-design` §8 — Cusick (C-t9cMtn3pe8A-28).
HOOK: series progression.
WKO-GATE: none.

**R25 — RULE:** Progress long tempo well past the common 45–60 min cap.
NUMBERS: 45 → 60 → 75 → 90 min typical; extreme pro cases 4 hr and 7 hr (the 7-hr case flagged as itself a problem). "TAN" tempo (rolling/technical, seated, natural surges) targeted at ~85% FTP by **average** power, not NP.
CONFIDENCE: anecdote / coaching-heuristic.
SOURCE: `REF/interval-design` §8 — Cusick (C-t9cMtn3pe8A-40, -41).
HOOK: series progression + workout_selector (gravel-relevant TAN tempo archetype).
WKO-GATE: none.

**R26 — RULE:** Set default work:rest at ~1:1 timed from end-of-effort; use 1:1–1:2 for extensive above-threshold work; give intensive/anaerobic work proportionally more rest.
NUMBERS: default ~1:1; extensive-FRC ~1:1–1:2 (the older 1:2–1:10 chart is explicitly disavowed by the author). Recovery power: ≤50 W for power-building sets; 50–60% of threshold for capacity-building sets (flats not hills, to force sustained recovery output).
CONFIDENCE: coaching-heuristic, self-hedged ("don't think about them as absolutes").
SOURCE: `REF/interval-design` §4, §8 — Cusick (C-my4Y0DulYTY-12/-19/-29, C-RA52lI2WRrg-23).
HOOK: workout_selector (rest-interval target power is currently a common blind spot).
WKO-GATE: none.

**R27 — RULE:** Allow +1–2 min extra mid-set rest on max-aerobic on/off repeats when power falls by rep 3–4, and shrink that allowance as fitness improves.
NUMBERS: +1–2 min.
CONFIDENCE: expert-opinion.
SOURCE: `REF/interval-design` §8 — Cusick (C-jtBW4CIGiEU-33).
HOOK: workout_selector (in-workout adaptive rest field).
WKO-GATE: none.

**R28 — RULE:** Constrain micro-interval design to rest ≤15–20 s and "on" ≤40 s.
NUMBERS: 20/10 (Tabata), 30/15 (author's default), 40/15–20. EPD variant: warm-up → 3×12 s sprints (24 s easy between) → straight into 16 min continuous SST, repeated.
CONFIDENCE: expert-consensus.
SOURCE: `REF/interval-design` §8 — Cusick (C-t9cMtn3pe8A-44, C-jtBW4CIGiEU-35).
HOOK: workout_selector.
WKO-GATE: none (but note `ROOT/fit`: use **differential W′bal** (Froncioni/Clarke) for micro-intervals — the integral model craters on them).

**R29 — RULE:** Never terminate an interval set on a fixed %-power-drop rule; terminate on elapsed TIZ against session purpose.
NUMBERS: 4% and 5% stop-rules both explicitly rejected across three talks; completion criterion e.g. ≥15 min for max-aerobic work.
CONFIDENCE: disputed (rejects a rule attributed to unnamed outside sources, not Coggan).
SOURCE: `REF/interval-design` §3 — Cusick (C-M_c_e-t9U7o-28, C-jtBW4CIGiEU-32, C-my4Y0DulYTY-36).
HOOK: workout_selector auto-termination logic / block_compliance.
WKO-GATE: none.

**R30 — RULE:** When power is on-target but duration fails and fatigue is ruled out, shorten the interval — do not lower the power.
NUMBERS: rationale — the curve fit already proves the athlete produced that power.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/interval-design` §3 — Cusick (C-RA52lI2WRrg-24).
HOOK: series progression (failure-response branch).
WKO-GATE: none.

**R31 — RULE:** Read consistent under-target interval power as insufficient *frequency*, not excessive intensity — add reps/sessions before lowering the target.
NUMBERS: qualitative; default read.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/interval-design` §1 — Cusick (C-wlWOb6Nn9Lw-26).
HOOK: series progression / workout_selector.
WKO-GATE: none.

**R32 — RULE:** Publish interval wattage targets as floors, not ceilings, for fast-improving athletes.
NUMBERS: worked case — athlete held prescribed 300–310 W when capable of 330–340 W that day (Goodhart's law).
CONFIDENCE: expert-opinion.
SOURCE: `REF/interval-design` §1 — Cusick (C-OEWJxhxM3TY-05).
HOOK: workout_selector (target-range rendering in the TrainingPeaks structured workout).
WKO-GATE: none.

**R33 — RULE:** Seed a new interval target from the average of the athlete's last ~3 similar-duration intervals, then validate against the model band.
NUMBERS: worked example 324/319/316 W → ~320 W target. Structure: rep 1 controlled/history-anchored, rep 2 "by feel," remaining reps held at that self-selected level. Set numeric targets for only the first 1–2 reps; coach the rest as "match or exceed that feel."
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/interval-design` §1, `REF/zones` M39 — Cusick (C-wlWOb6Nn9Lw-22/-23/-24, C-ldRCkYGaSvI-14).
HOOK: workout_selector (target generation from history rather than %FTP).
WKO-GATE: none — history-based.

**R34 — RULE:** Set rep count from the athlete's demonstrated capability, never from the model.
NUMBERS: usable range 3–8 reps. Add a rep if energy remained at the prescribed count; reduce if depleted before finishing.
CONFIDENCE: expert-opinion (Coggan: "however many you can do is however many you can do").
SOURCE: `REF/coaching` §7.5, `REF/interval-design` §4 — Cusick/Coggan (C-my4Y0DulYTY-10, C-HF_yh3rcX6Q-28).
HOOK: workout_selector.
WKO-GATE: rep count is explicitly **not** model output even in WKO — fully portable.

**R35 — RULE:** Never blend two zones in one interval to get "best of both."
NUMBERS: qualitative — targeting a crossover typically yields the worst of both.
CONFIDENCE: expert-opinion / coaching-heuristic.
SOURCE: `REF/interval-design` §8 — Cusick (C-my4Y0DulYTY-03/-04, C-0Qm5fXPo09k-25, C-RjJ7PNu3sNg-41).
HOOK: workout_selector (reject composite-zone archetypes).
WKO-GATE: none.

**R36 — RULE:** Cap max-aerobic time-in-zone per session at ~15 min (rarely >20 min) and include one such session every 7–14 workouts even in base.
NUMBERS: dose-response peaks ~15 min; ≤20 min; 1 per 7–14 workouts.
CONFIDENCE: expert-opinion (cites unverified research + Golich's influence).
SOURCE: `REF/zones` M55, M24 — Cusick/Golich (C-jtBW4CIGiEU-30, -24).
HOOK: workout_selector + block_compliance (a base-phase intensity-maintenance floor).
**REINFORCEMENT with tension: the ratified "VO2 every 14 days" sits at the sparse end of the store's 7–14-workout window.**

**R37 — RULE:** Bound single-session TIZ by rider category.
NUMBERS: Tempo — rec ~60 min / cat 3-5 & 1-2 60–180 min / pro 180+ min. SST — rec ≤45 / cat 3-5 45–60 / cat 1-2 60–80 / pro 60+ (personal cap ~80 min). Max-aerobic — ~15 min, occasionally 15–20, all levels.
CONFIDENCE: expert-opinion, explicitly non-fixed.
SOURCE: `REF/zones` M56 — Cusick (C-jtBW4CIGiEU-34).
HOOK: workout_selector (per-level TIZ ceilings), athlete classification.
WKO-GATE: none.

**R38 — RULE:** Prefer 5–6 sessions/week of ~1 hr over 2–3 sessions of ~3 hr at equal weekly hours.
NUMBERS: 5–6 d/wk × ~1 hr beats 2–3 d/wk × ~3 hr.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/coaching` §6.8 — Cusick (C-qnCAlNgoDxM-29).
HOOK: calculate_plan_dates (day-count allocation before duration allocation).
WKO-GATE: none.
**CONTRADICTION with the ratified 45-min session floor at the low end — the store's frequency argument favors sub-hour sessions where hours are constrained.**

**R39 — RULE:** Cap the workout vocabulary; don't chase novelty.
NUMBERS: top World Tour pros execute ~6–10 unique workout types/year. Importance hierarchy, targeting last: purpose/knowledge → consistency → progressive load → training rhythm → interval targeting (targeting matters only for the last 95%→100%).
CONFIDENCE: expert-opinion.
SOURCE: `REF/coaching` §6.9, §6.10 — Cusick (C-t9cMtn3pe8A-38, C-my4Y0DulYTY-01).
HOOK: workout_selector (library-size sanity check; deprioritize target-precision work).
WKO-GATE: none.

---

# C. Phase sequencing / annual shape

**R40 — RULE:** Sequence modality HVLI ("even") → pyramidal → polarized, and shorten macrocycle length as intensity rises.
NUMBERS: early base macrocycle 3–5 wks; mid-late base 2–3 wks; peak cycles 2–3 wks ("quality-managed"). Mid-late base pyramidal can run the full ~8 wks for a well-trained athlete. Polarized effective window ~6–10 wks before plateau/decline — reserve it for build/peak.
CONFIDENCE: expert-opinion / coaching-heuristic.
SOURCE: `REF/annual` §2 — Cusick (C-H9HA4cupIvg-24/-07/-23, C-qnCAlNgoDxM-21, C-ldRCkYGaSvI-11).
HOOK: block_chain/calculate_plan_dates (macrocycle length as a function of phase, not a constant).
WKO-GATE: none.

**R41 — RULE:** Hold base to 12–16 weeks; flag >16 weeks as a "perma-fit" risk, and never solve a plateau by stretching phase length.
NUMBERS: base 12–16 wks; >16 excessive. Named anti-pattern: base 12→20 wk and build 6→12 wk inside a fixed annual hour budget ⇒ flat CTL, never peaks.
CONFIDENCE: coaching-heuristic / expert-opinion.
SOURCE: `REF/annual` §4, §7 — Cusick (C-jtBW4CIGiEU-18, -16, -17).
HOOK: calculate_plan_dates (hard upper bound on base length; long runway should raise quality/depth, not stretch phases).
WKO-GATE: none.

**R42 — RULE:** Hold the peak window to 3–6 weeks (3–8 individualized) and front-load it.
NUMBERS: core 3–6 wks; most gain in first 3–5 wks; extending toward ~12 wks buys only ~1–2% more speed for meaningfully more fatigue. Cap the high-intensity portion of build at ≤~6 wks. Build-phase FRC/anaerobic work 1–3×/wk.
CONFIDENCE: expert-opinion / coaching-heuristic.
SOURCE: `REF/annual` §4 — Cusick (C-ldRCkYGaSvI-04, -05, C-jtBW4CIGiEU-37).
HOOK: calculate_plan_dates.
WKO-GATE: FRC-targeted work → W′-depleting intervals from the CP model.

**R43 — RULE:** Actively decrease volume as peak-phase intensity rises; flag any generated plan where both trend up in the same window.
NUMBERS: no ratio given — direction is the rule; named as "the most common peak-phase mistake." Peak intensity progression must be *more* aggressive than the prior build's volume progression. Peak-phase weekly high-intensity minutes shrink even as sessions get harder.
CONFIDENCE: expert-opinion.
SOURCE: `REF/annual` §7, `REF/training-load` §4.8, `REF/interval-design` §2 — Cusick (C-M_I3GwOtJKE-08/-06/-07, C-ldRCkYGaSvI-09).
HOOK: block_compliance (new R-rule: "volume slope ≤0 while intensity slope >0 in Peak").
WKO-GATE: none.

**R44 — RULE:** Set peak-phase session durations by system.
NUMBERS: VO2max sessions 25–30 min (total); anaerobic-capacity sessions 10–18 min. Peak = polarized, 2–3 hard days/wk, 2–3 wk cycles.
CONFIDENCE: expert-opinion.
SOURCE: `REF/interval-design` numeric table, §9 — Cusick (C-M_I3GwOtJKE-07/-09, C-ldRCkYGaSvI-08/-10).
HOOK: workout_selector (peak-phase session-length bands).
WKO-GATE: none.

**R45 — RULE:** For gravel/ultra/long-course events, keep the peak-relevant window **pyramidal**, not polarized — volume is the specificity.
NUMBERS: qualitative; "more zone 1–2 time builds muscular endurance, sustainable threshold, and fueling practice." For ultra/Ironman: weight extensive/fat-adapted volume, minimize threshold time, add TAN (surge) tempo variety. Reverse periodization rejected for standard road/gravel; ~8-week specific-prep window before target event.
CONFIDENCE: expert-opinion.
SOURCE: `REF/annual` §2 — Cusick (C-M_I3GwOtJKE-38, C-t9cMtn3pe8A-48, C-H9HA4cupIvg-40, C-qnCAlNgoDxM-05).
HOOK: block_chain (event-archetype-conditional TID shape). **Directly relevant to Gravel God's core event type.**
WKO-GATE: none.

**R46 — RULE:** Separate anaerobic-capacity and anaerobic-power stimuli into distinct ~2-week blocks with a rest week between; never blend them in one week.
NUMBERS: ~2 wk on / 1 wk off → ~5-week cycle.
CONFIDENCE: expert-opinion.
SOURCE: `REF/annual` §4 — Cusick (C-my4Y0DulYTY-35).
HOOK: block_chain.
WKO-GATE: none.

**R47 — RULE:** Stack phases by residual half-life: durable qualities first, shortest-residual qualities last and closest to the race.
NUMBERS: aerobic endurance 30±5 d; maximal strength 30±5 d; aerobic power/VO2max 18±4 d; anaerobic glycolytic 18±4 d; maximal speed 5±3 d.
CONFIDENCE: ★★★★☆ — "well-established in strength/power, broadly accepted in endurance with less controlled-trial evidence."
SOURCE: `ROOT/residual` — Issurin 2008, Zatsiorsky & Kraemer 2006.
HOOK: block_chain/calculate_plan_dates (spacing between a quality's last block and race day must be < its residual). **The store explicitly notes the phase-calculator doesn't currently encode this.**
WKO-GATE: none — fully open literature.

**R48 — RULE:** Set the base→build gate on the FTP-to-power-at-VO2max ratio, not the calendar.
NUMBERS: don't leave extensive/base until the ratio reaches ~80–81%; the ratio plateaus at 81–85% (also stated 84–85% and ~85% — treat as a fuzzy band, individualize against the athlete's own historical high). Up to ~20 weeks for a brand-new athlete. Once it flattens for 2–3 weeks, pivot to VO2max/anaerobic work.
CONFIDENCE: coaching-heuristic; the ceiling number itself "wobbles across sources."
SOURCE: `REF/annual` §6, `REF/pd-model` §8, `REF/training-load` §9.7 — Cusick (C-t9cMtn3pe8A-35/-34/-33, C-H9HA4cupIvg-13, C-M_I3GwOtJKE-39).
HOOK: physiology gate + block_chain (phase-transition trigger).
WKO-GATE: **mFTP-as-%-VO2max → FTP as % of best recent 3–5-min power** (open proxy stated in `REF/annual` analogue table). Usable, noisier session-to-session.

**R49 — RULE:** Allow at most 1–2 true peaks/year; flag calendars with 3+ A-races.
NUMBERS: 1–2 max; 4–5 A-events at full intent dilutes all. Alternatives: ~2 true tapers/year, or a sustained "perma-peak" ~3–7% below true peak (explicitly hedged: "five percent… or three… or seven") via short rebuild cycles spaced ~6–8 to 8–10 weeks.
CONFIDENCE: expert-opinion (deficit % explicitly hedged).
SOURCE: `REF/annual` §8 — Cusick (C-H9HA4cupIvg-39, C-M_I3GwOtJKE-35, C-ldRCkYGaSvI-23).
HOOK: calculate_plan_dates (A-race count validation at intake); athlete classification.
WKO-GATE: none.

**R50 — RULE:** Structure a full racing season around a mid-season reset.
NUMBERS: early-season peak → rest point ~6–10 wks into season → ~2-wk aerobic build → ~2-wk intensive block → resume racing.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/annual` §8 — Cusick (C-M_I3GwOtJKE-36).
HOOK: block_chain (in-season chain template).
WKO-GATE: none.

**R51 — RULE:** For athletes under ~12 hrs/week, substitute sweet-spot for LSD earlier, start the season earlier, and add an extra base period — never an extra build/peak.
NUMBERS: <12 hrs/wk threshold; time-limited base context 7–12 hrs/wk (added intensity helps but gains are capped). Condensed late start (mature athletes only): 5 wks to race → straight into a 4-week Base 2 block, then build/peak/race, skipping prep/base 1. Under-prepared athlete taken on ~5–6 wks out needs a foundational-reset conversation, not a rescue VO2max block.
CONFIDENCE: coaching-heuristic / expert-opinion.
SOURCE: `REF/annual` §10, `REF/coaching` §6.6 — Cusick (C-qnCAlNgoDxM-44/-45, C-Qr9UlkZKvO4-43, C-ldRCkYGaSvI-27).
HOOK: calculate_plan_dates (short-runway branch — a common Gravel God case).
WKO-GATE: none.

**R52 — RULE:** Schedule a training camp 3–5 weeks (outer bound 4–8) before the target race, and follow it with **short** rest, not extended rest.
NUMBERS: camp 7–10 days high-volume overreach; adaptation lands ~4–8 wks post-camp, more commonly ~3–5 wks; extended post-camp rest gives the gain back.
CONFIDENCE: expert-opinion / coaching-heuristic.
SOURCE: `REF/training-load` §6.1, §6.2 — Cusick (C-qnCAlNgoDxM-43, C-vfC-CRkl5Kk-23).
HOOK: block_chain (camp-block placement).
WKO-GATE: none.

**R53 — RULE:** After repeated poor execution inside a peak block, pull back, rest ~1 week, and restart the block rather than pushing through.
NUMBERS: ~1 week rest ("bad workout disease").
CONFIDENCE: expert-opinion / coaching-heuristic.
SOURCE: `REF/training-load` §6.4 — Cusick (C-M_I3GwOtJKE-20, C-ldRCkYGaSvI-28).
HOOK: block_compliance / plan-regeneration trigger.
WKO-GATE: none.

**R54 — RULE:** Keep some intensity in base at all times — maintenance-intensity hard day every 8–14 workouts, including early base.
NUMBERS: 1 per 8–14 workouts. Plus ≥1 long near-LT1 ride/week in early base (2/week better than 1). Cadence bias 95–100+ rpm on early-base hard days. Add 1–2 hrs/week of volume through mid-late base.
CONFIDENCE: coaching-heuristic / expert-opinion.
SOURCE: `REF/annual` §4, `REF/interval-design` §9 — Cusick (C-H9HA4cupIvg-12, -22, C-qnCAlNgoDxM-30/-31/-34).
HOOK: block_compliance (base-phase intensity floor + long-ride floor).
WKO-GATE: none.

**R55 — RULE:** Bridge from base to sweet-spot with a 1–2-session transitional workout, and from SST to FTP with supra-threshold classic intervals.
NUMBERS: bridge = ~6-min tempo / 1-min rest, 1–2 sessions. SST→FTP transition = 4×10 min, or 4×8 min hard-start, supra-threshold. Progressive rides start ~5–10 W easier and finish stronger near LT1. Short-event athletes (<~90–120 min events) can justify pure VO2max work sooner.
CONFIDENCE: expert-opinion / coaching-heuristic.
SOURCE: `REF/interval-design` §9 — Cusick (C-H9HA4cupIvg-33/-41/-32/-42).
HOOK: block_chain (transition workouts between phases) + workout_selector.
WKO-GATE: none.

**R56 — RULE:** Gate any intensive VO2max/FTP block on demonstrated aerobic capacity; if it's missing, reset capacity first.
NUMBERS: qualitative — "the signal falls on deaf ears." Readiness illustration (explicitly not validated): comfortably holding 3.6 W/kg for 2.5 hr against a ~4.0 W/kg threshold ⇒ candidate to pivot to FTP/power work.
CONFIDENCE: expert-opinion.
SOURCE: `REF/fatigue` §5.3, `REF/interval-design` §9 — Cusick (C-M_I3GwOtJKE-21, -40, C-ldRCkYGaSvI-26).
HOOK: physiology gate before Build.
WKO-GATE: none if implemented as a long-sub-threshold-effort ratio from FIT history.

---

# D. Taper / race week

**R57 — RULE:** Structure the taper as rest starting ~10–14 days out, then reload with 2–3 hard efforts before the event.
NUMBERS: rest window ~10–14 days out (TSB rises, "can leave the athlete too flat"); reload = ~2–3 hard efforts.
CONFIDENCE: **anecdote** (pro tapering practice; the weakest tier in the store).
SOURCE: `REF/training-load` §6.3 — Cusick (C-vfC-CRkl5Kk-34).
HOOK: taper/race week (shape + duration).
WKO-GATE: none.
**REINFORCEMENT with a shape addition to the ratified taper rules: the ratified rules cap hard content (no ≥92% rep >120 s; ≤15 min hard work) but don't mandate the *reload* — the store says the reload is what prevents flatness.**

**R58 — RULE:** In peak/race phase, manage ATL as the active lever and treat CTL as a lagging result.
NUMBERS: ATL and TSB are ~inverse, offset ~1 day. Peak-performance TSB clusters near 0 in one worked case (3-yr avg CTL ~110; top-10 performances at CTL ~105). Second case: avg daily CTL 123, peaks at ~80–90(?) — the gap is individual (could be 5, 10, or 20 points), not a fixed offset.
CONFIDENCE: expert-opinion / anecdote for the cases.
SOURCE: `REF/training-load` §2.5, §9.3 — Cusick (C-M_I3GwOtJKE-33/-34, C-ZKcZTYUIFfc-27, C-OEWJxhxM3TY-19).
HOOK: taper/race week (target ATL, not CTL, in the final 2 weeks).
WKO-GATE: none.

**R59 — RULE:** Give no taper to non-A races; race them as hard training days.
NUMBERS: binary; requires explicit athlete buy-in in advance.
CONFIDENCE: expert-opinion.
SOURCE: `REF/annual` §8 — Cusick (C-ldRCkYGaSvI-24).
HOOK: calculate_plan_dates (B/C-race handling — currently often over-tapered by generators).
WKO-GATE: none.

**R60 — RULE:** Keep one long easy "booster" ride weekly (or every other week) through the peak phase, and make it the first thing cut if fatigue shows.
NUMBERS: weekly, min every-other-week.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/annual` §8 — Cusick (C-ldRCkYGaSvI-33).
HOOK: taper/race week + block_compliance (peak-phase aerobic-maintenance floor with an explicit cut-priority).
WKO-GATE: none.

**R61 — RULE:** Set maintenance load below build load and test how low it can go for the specific athlete.
NUMBERS: no number — "what it takes to get there is not what it takes to stay there"; minimum maintenance dose is highly individual.
CONFIDENCE: expert-opinion (attributed to Dean Golich via Cusick).
SOURCE: `REF/annual` §8, `REF/coaching` §6.7 — Golich/Cusick (C-M_I3GwOtJKE-45, C-ldRCkYGaSvI-38).
HOOK: taper/race week + in-season maintenance blocks.
WKO-GATE: none.

---

# E. Testing protocol

**R62 — RULE:** Gate every model-derived number behind a data-volume check before displaying it.
NUMBERS: ≥30 days minimum, 90 days preferred, with a genuine max effort in short, medium, AND long ranges. Post-baseline, the model takes a further 30–90 days to flesh out (slower in early base, faster mid-season). Trust the fit while normalized residuals sit <~5% (author's personal band ±7.5; a third framing says ~5–7, unit ambiguous — the store marks these as **disputed, don't collapse to one number**).
CONFIDENCE: expert-opinion / coaching-heuristic (thresholds disputed).
SOURCE: `REF/testing` §1 — Cusick (C-HF_yh3rcX6Q-09, C-RA52lI2WRrg-03, C-Qr9UlkZKvO4-18, C-RA52lI2WRrg-08).
HOOK: testing protocol + physiology gate (suppress CP/W′-derived prescriptions on thin data; lead with the gap).
WKO-GATE: mFTP/FRC/TTE/iLevels → CP, W′, t=W′/(P−CP), duration-matched %CP zones. The ±5%/±7.5 thresholds are WKO's own calibration and **must not be reused as-is** — Endure needs independently derived bands.

**R63 — RULE:** Run a multi-day baseline battery — one max effort per day, never stacked — at season start, after a layoff, or after any power-meter swap.
NUMBERS: 4–6 days (also cited 7–10). Representative sequence: D1 warm-up + 5-min max; D2 20–30 min max (≤30 cap, phenotype-adjusted); D3 1-min max; D4 recovery; D5 sprints (150 m × 2). Order not mandatory.
CONFIDENCE: expert-opinion.
SOURCE: `REF/testing` §2 — Cusick (C-RA52lI2WRrg-05, C-jsm1bPSakYs-06, C-qnCAlNgoDxM-24).
HOOK: testing protocol (onboarding block); block_chain (baseline week as a first-class block type).
WKO-GATE: none.

**R64 — RULE:** Set the Day-2 long test duration by phenotype.
NUMBERS: ~20 min diesel/TT/flat-curve; ~25 min all-arounder/sprinter; ~30 min pursuit type; hard cap 30 min. Rationale: the test must fully drain anaerobic capacity before the aerobic contribution reads clean. Pacing for tests >8–10 min: first ~3 min ~5% under expected power, then open up.
CONFIDENCE: expert-opinion / coaching-heuristic (pacing).
SOURCE: `REF/pd-model` §10, `REF/testing` §3 — Cusick (C-RA52lI2WRrg-06, C-jsm1bPSakYs-07, -11, C-RA52lI2WRrg-38).
HOOK: testing protocol + athlete classification (phenotype→test duration is a rare, directly implementable phenotype hook).
WKO-GATE: none — protocol, not metric.

**R65 — RULE:** After baseline, stop scheduling discrete test days; blend near-maximal efforts into hard training every 4–6 weeks, steered by the stalest duration.
NUMBERS: default 4–6 wks (outer bound 30–90 d; other framings 30–45 d, 30–60 d weighted toward 30). Early base: relax to every 6–8 weeks. In specificity blocks: ~1 max effort/week, rotating short/medium/long, early in the cycle right after a rest week. 4-week rotation: short = wk 1; wk 2 = long (PD-curve framing) or medium (dFRC framing) — **disputed**; remainder wks 3–4. Long/max tests placed in **week 2** of a cycle (freshest week). Skip formal testing in the very first base cycle of a new block.
CONFIDENCE: expert-opinion / coaching-heuristic.
SOURCE: `REF/testing` §4, `REF/annual` §6, `REF/training-load` §9.5 — Cusick (C-Qr9UlkZKvO4-14/-15, C-RA52lI2WRrg-07/-39, C-jsm1bPSakYs-13/-14, C-HF_yh3rcX6Q-11).
HOOK: testing protocol + block_chain (test placement within the microcycle).
WKO-GATE: none.

**R66 — RULE:** Test after rest, but not cold — insert 1–2 days of moderate work if the athlete has had several days fully off.
NUMBERS: example pattern 3 days off + 2 easy days before test, end of mesocycle.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/testing` §4 — Cusick (C-vfC-CRkl5Kk-45).
HOOK: testing protocol (test-day placement relative to the recovery week).
WKO-GATE: none.

**R67 — RULE:** Prompt runners for a short sprint test every 30–60 days; they are the highest-risk population for a corrupted model.
NUMBERS: ~50 m or a hard 400 m, every 30–60 d, plus a solid 5K+.
CONFIDENCE: expert-opinion / coaching-heuristic (cadence).
SOURCE: `REF/testing` §3 — Cusick (C-HF_yh3rcX6Q-16/-17).
HOOK: testing protocol (sport-conditional).
WKO-GATE: none.

**R68 — RULE:** Backfill a 1-minute max effort for frequent racers — races rarely produce one.
NUMBERS: qualitative; the named hidden gap.
CONFIDENCE: expert-opinion.
SOURCE: `REF/testing` §5 — Cusick (C-jsm1bPSakYs-38).
HOOK: testing protocol (duration-coverage audit).
WKO-GATE: none.

**R69 — RULE:** Match test environment to training environment.
NUMBERS: athletes doing ≥75% of workouts indoors should baseline indoors. Indoor FTP inflation example ~20 W higher indoors (Zwift habituation just under threshold); power-meter calibration drift example ~15 W underread.
CONFIDENCE: expert-opinion / anecdote for the deltas.
SOURCE: `REF/testing` §1, §3 — Cusick (C-jsm1bPSakYs-09, C-H9HA4cupIvg-27, C-4_ixu9OaHGM-05).
HOOK: testing protocol + `ROOT/fit` ingestion (environment-normalized reads).
WKO-GATE: none.

**R70 — RULE:** Re-run the full baseline at the same calendar point every year and again in late foundation, comparing directly to the original numbers.
NUMBERS: season sequence — 4-point baseline → unstructured/residual tests → full re-baseline in late foundation → residual testing resumes. Cap lab/ramp tests at annual/biannual (a few/year even for pros) — retest noise (e.g. VO2max 60→61→59) is too small to change training.
CONFIDENCE: coaching-heuristic / anecdote (lab cap).
SOURCE: `REF/testing` §4, `REF/annual` §9 — Cusick (C-qnCAlNgoDxM-26, C-jsm1bPSakYs-37, C-Qr9UlkZKvO4-10).
HOOK: testing protocol (annual anchor).
WKO-GATE: none.

**R71 — RULE:** Round any displayed threshold up to the nearest 5 W and present it as a range.
NUMBERS: round to nearest 5 (272→275) or to nearest 0/5 (276→280); FTP fuzz band ~5 W; quasi-steady-state band ~±5% (300 W → 293–307 W).
CONFIDENCE: coaching-heuristic / expert-opinion.
SOURCE: `REF/testing` §1, `REF/coaching` §3.2, `REF/zones` M22/M28 — Cusick (C-t9cMtn3pe8A-09, C-ZKcZTYUIFfc-17, -16).
HOOK: zone boundary logic (rendering + rounding).
WKO-GATE: none.

**R72 — RULE:** Frame every test to the athlete as training, not an event.
NUMBERS: qualitative — reduces test anxiety; "testing is training, training is testing" (Coggan).
CONFIDENCE: expert-opinion (attributed) / coaching-heuristic.
SOURCE: `REF/coaching` §10.1, §10.2 — Cusick/Coggan (C-jsm1bPSakYs-27, -31).
HOOK: testing protocol (workout copy/description generation).
WKO-GATE: none.

**R73 — RULE:** Deliberately program work beyond 20 minutes; the "20-minute revolution" has under-developed long-duration capacity.
NUMBERS: metabolic transitions continue to ~40 min, after which mean-max power is more stable/predictive. MLSS is 30–70 min, most 45–60. FTP-alone testing: 45–60 min or a ~40 km TT.
CONFIDENCE: expert-opinion (explicit personal soapbox) / expert-consensus for MLSS duration.
SOURCE: `REF/coaching` §10.5, `REF/zones` M23/M31, `REF/testing` §3 — Cusick (C-jtBW4CIGiEU-11, C-RA52lI2WRrg-13, C-ZKcZTYUIFfc-22).
HOOK: testing protocol + workout_selector.
WKO-GATE: none.

---

# F. Phenotype / athlete classification

**R74 — RULE:** Classify phenotype from the **shape** of the %FTP-normalized power-duration curve, relative to the athlete's own history — never from absolute watts.
NUMBERS: sprinter can be classified off a peak as low as ~600–700 W if that duration is disproportionately elevated; a sprinter's short power can exceed 400% of FTP. Inter-athlete variance is low above ~1000 s and can run 250–600%(?) below ~500 s. Classic %FTP zones fit ~50% of athletes well, with ~25% outliers each side.
CONFIDENCE: expert-opinion (WKO user-base derived); the 250–600% figure flagged (?) as casually cited off a log chart.
SOURCE: `REF/pd-model` §2 — Cusick (C-M_c_e-t9U7o-05, C-0Qm5fXPo09k-01/-02).
HOOK: athlete classification (phenotype from PD curve shape).
WKO-GATE: **Endure has no population dataset** — the store mandates self-relative language only ("more sprinter-shaped than diesel-shaped, relative to your own history"). A population-percentile phenotype is UNUSABLE as specified.

**R75 — RULE:** Use phenotype-point scatter across repeated assessments as a training-consistency diagnostic, not just a type label.
NUMBERS: tight clustering = consistent, well-executed training; wide scatter = inconsistent history and possibly missing base fitness. Variability narrows as the athlete approaches genetic ceiling.
CONFIDENCE: expert-opinion.
SOURCE: `REF/pd-model` §2 — Cusick (C-OEWJxhxM3TY-15).
HOOK: athlete classification (intake diagnostic → base-depth decision).
WKO-GATE: computable from own curve; no proprietary metric.

**R76 — RULE:** Give higher-anaerobic-bias athletes longer, lower-power max-aerobic intervals than flatter-curve athletes; round modeled durations up.
NUMBERS: worked pair — Joe (flatter) 2:44 @ 300–320 W → round to 2:45–3:00; Jane (higher anaerobic bias) 5:02 @ 296–316 W. Rationale: more time needed to burn down the anaerobic reserve and force aerobic dominance.
CONFIDENCE: expert-opinion.
SOURCE: `REF/interval-design` §4 — Cusick (C-M_c_e-t9U7o-24, -26).
HOOK: workout_selector (phenotype-conditional interval duration — **the single most concrete phenotype→workout mapping in the store**).
WKO-GATE: optimized intervals → "duration/power combos from the fitted CP hyperbola at a chosen %W′ depletion." The store notes what's lost: curve-inflection detection. The *direction* (anaerobic bias → longer max-aerobic reps) is portable.

**R77 — RULE:** At peak entry, place the athlete on a capacity-vs-power quadrant and prioritize exactly one.
NUMBERS: no numbers — the short peak window doesn't allow both. Signature of high-capacity/low-power: normal HR, normal breathing, good fueling, "just could not access the power" ⇒ prioritize power work, not more volume. A high-capacity athlete may be muscularly/fast-twitch limited, requiring power/muscular work before VO2max sessions become productive. Anaerobic power is the slowest quality lost in detraining.
CONFIDENCE: expert-opinion.
SOURCE: `REF/pd-model` §14 — Cusick (C-M_I3GwOtJKE-13/-14/-15/-17/-18).
HOOK: athlete classification → workout_selector at peak.
WKO-GATE: **fully portable** — the store explicitly says so: compare recent CP/aerobic-trend movement against actual best-effort output trend.

**R78 — RULE:** Apply the same "athlete has more left" signal in opposite directions depending on phase.
NUMBERS: base/capacity phases — add another interval. Final ~4–5-week peaking phase — go harder on the last interval instead.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/annual` §5 — Cusick (C-my4Y0DulYTY-33).
HOOK: series progression (phase-conditional SDT branch).
WKO-GATE: none.

**R79 — RULE:** Reject age-normed power benchmarks; benchmark against training maturity.
NUMBERS: none — "population variance is dominated by training maturity, not age"; using an age average is called "mathematically inappropriate."
CONFIDENCE: expert-opinion.
SOURCE: `REF/coaching` §2.4 — Cusick (C-Qr9UlkZKvO4-38).
HOOK: athlete classification.
WKO-GATE: none.

**R80 — RULE:** Don't confuse "room to grow" with "potential to grow" when selecting a limiter to train.
NUMBERS: none. Case: a pro whose sprint scored as her largest chart weakness spent ~2 years on aerobic development instead; sprint power stayed flat (slightly declined) and she started winning.
CONFIDENCE: expert-opinion; the case is anecdote (n=1, no comparison group, flagged in Verification notes).
SOURCE: `REF/coaching` §4.2, §4.3 — Cusick (C-RA52lI2WRrg-32, -33).
HOOK: athlete classification (limiter selection must be cross-checked against phenotype + event demand, not "biggest gap wins").
WKO-GATE: strengths/limiters chart is population-normed → self-relative trend only.

---

# G. Zone boundary logic

**R81 — RULE:** Anchor zone boundaries as follows and treat them as bands, not points.
NUMBERS: recovery floor ~55% FTP; endurance 56–75%; sweet spot 88–93% (some widen to 85–90%+); classic VO2max 105–120% (criticized as too generic); anaerobic 121–150%; sprint/max >150%. Threshold caps at 80–85% of VO2max. Three-zone frame: Z1 <LT1, Z2 LT1–LT2, Z3 ≥LT2. LT2/OBLA/MLSS/AT are functionally equivalent labels.
CONFIDENCE: expert-consensus (sweet spot, MLSS, LT framework) / expert-opinion (band values).
SOURCE: `REF/zones` M13–M19, M32 — Cusick, citing Coggan.
HOOK: zone boundary logic.
WKO-GATE: iLevels → "power-duration-curve-based zone estimate," never a 9-zone clone.

**R82 — RULE:** Only individualize zones above threshold; below FTP the curve-based gain is negligible.
NUMBERS: no optimized-interval zone below FTP — variance there is only ~1–3 W. Sweet-spot targets stay close between athletes (worked case: 242–259 W vs. 237–255 W) even when short-duration targets diverge by 105 W (390–465 vs. 419–574 W) for the *same* near-identical-FTP pair whose classic VO2max targets differed by only ~4–6 W.
CONFIDENCE: expert-opinion, case data (one case restated three times with drifting deltas 6 W/5 W/4 W — treat as **one anecdote, not three confirmations**).
SOURCE: `REF/zones` M3, M9, M10; `REF/pd-model` §12 — Cusick (C-0Qm5fXPo09k-07/-09, C-my4Y0DulYTY-07).
HOOK: zone boundary logic (spend individualization budget above threshold only).
WKO-GATE: iLevels analogue.

**R83 — RULE:** Prescribe endurance in the bottom-middle of the zone, never the top edge.
NUMBERS: worked example 165 W vs. 189 W within a 150–190 W range — the top edge gives "very very tiny" extra aerobic effect for much higher fatigue cost.
CONFIDENCE: expert-opinion.
SOURCE: `REF/interval-design` §8, `REF/zones` M52 — Cusick (C-t9cMtn3pe8A-39, C-jtBW4CIGiEU-21).
HOOK: zone boundary logic + workout_selector target rendering.
**STRONG REINFORCEMENT of the ratified endurance IF .60–.70 scaled down with duration, and of the ≤50 TSS/hr endurance cap. The store's mechanism ("more fatigue for near-zero extra aerobic effect") is the exact rationale.**

**R84 — RULE:** Watch for one-notch-hot zone creep and correct toward the true definition.
NUMBERS: named pattern — "most people ride their tempo like SST and their SST like FTP." Correct base progression: mid-Level-2 → true Tempo → true SST. Detection: a "Tempo"/"SST" file whose average power matches the next zone up.
CONFIDENCE: expert-opinion.
SOURCE: `REF/zones` M53 — Cusick (C-jtBW4CIGiEU-25).
HOOK: block_compliance (post-hoc execution audit) + `ROOT/fit` ingestion.
WKO-GATE: none.

**R85 — RULE:** Restrict Zone 1 to early base and true recovery; excess Z1 elsewhere is "too little" stimulus.
NUMBERS: qualitative. Related: zone-2 discipline lapsing into zone 1 mid-base coincides with a performance/form decline (n=1 anecdote).
CONFIDENCE: expert-opinion / anecdote for the case.
SOURCE: `REF/zones` M48, M57 — Cusick (C-qnCAlNgoDxM-16, C-OEWJxhxM3TY-25).
HOOK: block_compliance (weekly zone-2-time floor).
WKO-GATE: none.

**R86 — RULE:** Classify a generated week by its actual TID shape, not by its label.
NUMBERS: polarized = 1–2 hard days/wk, ~20–30% hard / 70–80% easy; pyramidal = 2–3 days/wk, ~40–50% / 50–60%; threshold = 4–5 hard days/wk, ~60–70% / 30–40% (source audio garbled — carries (?)). Named failure: frequent hard group rides silently produce a threshold-modality week. Intensity distribution should shift gradually — a "slow wave" — from Z1 toward Z2/Z3 across mid-to-late base, **without volume reduction**.
CONFIDENCE: expert-opinion (threshold split disputed/garbled).
SOURCE: `REF/zones` M44–M47, M49 — Cusick (C-qnCAlNgoDxM-17/-18/-19/-20, C-H9HA4cupIvg-21).
HOOK: block_compliance (new R-rule: computed TID shape must match the declared phase modality).
WKO-GATE: none.

**R87 — RULE:** Target LT1 rising toward LT2 as the early-phase aerobic goal, and use "aerobic power" (just above LT1) only as a bridge to tempo/SST.
NUMBERS: no LT1 formula is safe — the store lists ~50–55% of power-at-VO2max, ~65–75% FTP, ~65–75% max HR as **disputed and partly garbled**; LT1 repeat testing scatters (≥4 different values in 5 daily tests) vs. LT2/FTP reliability. Pick one formula and track the trend.
CONFIDENCE: expert-opinion (goal) / disputed (formulas).
SOURCE: `REF/zones` M50/M51, `REF/testing` §6 — Cusick (C-M_I3GwOtJKE-41, C-H9HA4cupIvg-20, C-qnCAlNgoDxM-38/-39/-40, C-wlWOb6Nn9Lw-09).
HOOK: zone boundary logic. **Do not hard-code an LT1 formula.**
WKO-GATE: LT1 is not resolved even in WKO ("a roadmap item, not part of the current PD model").

---

# H. Fatigue resistance / durability

**R88 — RULE:** When an athlete completes a validated target once but fails to repeat it 2–3×, treat it as a durability limiter — keep the wattage and build repeatability.
NUMBERS: 2–3× repeat threshold.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/fatigue` §6.1 — Cusick (C-0Qm5fXPo09k-18).
HOOK: series progression (failure-response branch: do NOT down-level) + block_compliance.
WKO-GATE: none.

**R89 — RULE:** Train durability by placing hard intervals late in an already-fatigued workout, and spend that "fatigue budget" in build/peak, not early base.
NUMBERS: qualitative. Early foundation's purpose is resiliency and platform, not watts — deliberately withhold power gains there.
CONFIDENCE: coaching-heuristic / expert-opinion.
SOURCE: `REF/fatigue` §2.1, §2.2 — Cusick (C-H9HA4cupIvg-31, C-my4Y0DulYTY-23, C-qnCAlNgoDxM-28).
HOOK: workout_selector (a "post-fatigue interval" archetype, phase-gated to build/peak) — **directly relevant to gravel durability.**
WKO-GATE: none.

**R90 — RULE:** Build the acute component of fatigue resistance by manipulating hard/easy day sequencing, not workout content.
NUMBERS: chronic = day-after-day capacity; acute = within-workout sustainability, "more impacted by your training rhythm not necessarily training content."
CONFIDENCE: expert-opinion.
SOURCE: `REF/fatigue` §2.3 — Cusick (C-Qr9UlkZKvO4-47).
HOOK: block_chain (microcycle ordering as a durability lever).
WKO-GATE: none.

**R91 — RULE:** Schedule 2–3 dedicated durability probes per year, at the end of a training cycle, separate from FTP retests.
NUMBERS: 2–3×/yr. Descriptive measure: compare the power curve before vs. after a fixed cumulative-work split — ~1000 kJ commonly, sometimes 1500 or 2000 kJ depending on the athlete's race demand.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/fatigue` §2.4, §6.7 — Cusick (C-vfC-CRkl5Kk-46, C-OEWJxhxM3TY-14).
HOOK: testing protocol (a second, separate cadence from R65) + athlete classification.
WKO-GATE: stamina (0–100 score) → **UNUSABLE as a score**; the store mandates "observed power-decay rate over a specific ride/duration." The kJ-split durability chart is fully portable and is the recommended substitute. `ROOT/fit` also names durability (power-duration after N kJ) as an adopt-next method that "discriminates performance better than fresh FTP."

**R92 — RULE:** Expect and plan for a strain inflection at ~90 min–2 hr of constant power; treat later hours as costing more than earlier ones.
NUMBERS: ~90 min–2 hr, cardiac drift as the marker ("hockey stick").
CONFIDENCE: expert-consensus.
SOURCE: `REF/fatigue` §6.3 — Cusick (C-ZKcZTYUIFfc-34).
HOOK: physiology gate (long-ride TSS/IF scaling) — **mechanistic backing for the ratified "endurance IF scaled down with duration."**
WKO-GATE: none.

**R93 — RULE:** Expect W′ recovery within a long set to get both slower and shallower from mid-set onward; don't read incomplete late-set recovery as a model error or a bad target.
NUMBERS: illustrative 10×3min set — degradation visible from ~reps 4–8, worst by reps 8–10. Full anaerobic-battery refill happens only ~1–2× per session, and only when recovery is held **under** FTP (faster the further under).
CONFIDENCE: expert-opinion (illustrative, n=1).
SOURCE: `REF/fatigue` §3.3, §3.4 — Cusick (C-M_c_e-t9U7o-08, C-HF_yh3rcX6Q-07).
HOOK: physiology gate (W′bal nadir interpretation) + workout_selector (recovery-power spec must be sub-FTP, cf. R26).
WKO-GATE: FRC/dFRC → W′ / differential W′bal (Skiba, or Froncioni-Clarke). The store calls dFRC→W′bal "essentially no loss" / "the closest 1:1 open-literature match."
**REINFORCEMENT of the ratified W′bal nadir gate, with a shape expectation: a good progressive set drains a little deeper each rep, tank nearly empty only at the end.**

**R94 — RULE:** Target W′ depletion depth on VO2max-style efforts and flag under-execution.
NUMBERS: intervals <10 min are where W′bal is informative. >50% depletion "pretty deep"; ~2/3 "good"; **under ~50% = under-executed**. Over-hard-start signature: deep drain on rep 2 (to ~−8 kJ) → shallower drains and falling power later (330–340 W → 290–300 W in a 6×3min set).
CONFIDENCE: expert-opinion.
SOURCE: `REF/interval-design` §5 — Cusick (C-HF_yh3rcX6Q-19, -20).
HOOK: physiology gate.
**REINFORCEMENT + EXTENSION of the ratified "over-cooked < −2 kJ nadir": the store adds an under-cooked floor (<50% W′ depletion on a VO2max session) that the current gate lacks.**

**R95 — RULE:** Expect little to no W′ drawdown on a correctly executed sweet-spot interval; sustained drawdown means the athlete rode above prescription.
NUMBERS: qualitative — "the level people most commonly overcook."
CONFIDENCE: expert-opinion.
SOURCE: `REF/zones` M36 — Cusick (C-HF_yh3rcX6Q-32).
HOOK: physiology gate (per-zone W′bal expectation, not a single global gate) + block_compliance.
WKO-GATE: dFRC→W′bal.

**R96 — RULE:** Mix full-rest W′-depleting work with race-specific short-rest "lactate stacking" surges.
NUMBERS: stacking target ~85–90% of the point where the anaerobic-contribution curve flattens. Worked example: at 50 s, anaerobic contributes 323 W on top of a 254 W aerobic curve ≈ 577 W combined; inability to hold reps at ≥85% of that mark flags a detraining gap.
CONFIDENCE: expert-opinion / coaching-heuristic.
SOURCE: `REF/interval-design` §5 — Cusick, crediting Dean Golich (C-jtBW4CIGiEU-42/-43/-46/-39/-41).
HOOK: workout_selector (gravel surge-repeatability archetype).
WKO-GATE: FTP-contribution chart is WKO-proprietary → reconstruct from the CP/W′ fit (P(t) = CP + W′/t decomposition). Usable but the store flags the crossover methodology is undisclosed.

**R97 — RULE:** For stage-race and multi-day athletes, accept 10–20 W below peak threshold in exchange for durability.
NUMBERS: ~10–20 W, explicitly hedged as athlete/event-dependent.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/fatigue` §5.1 — Cusick (C-Qr9UlkZKvO4-46).
HOOK: athlete classification (event-archetype → objective weighting).
WKO-GATE: none.

**R98 — RULE:** For chronic underperformance despite an adequate, well-tested FTP, prescribe durability work before more threshold work.
NUMBERS: framing — "FTP is the single greatest factor in performance *success*; lack of fatigue resistance is the single greatest factor in performance *failure*."
CONFIDENCE: expert-opinion (WKO user-base database-pattern claim).
SOURCE: `REF/fatigue` §5.2 — Cusick (C-jtBW4CIGiEU-12).
HOOK: workout_selector / block_chain (limiter-conditional block ordering).
WKO-GATE: none.

**R99 — RULE:** Use tightness of an athlete's top-performance cluster to size how much racing load they can absorb.
NUMBERS: clustering within ~1–2% (worked example 98–99%) = resilient, repeatable ⇒ can absorb more back-to-back demand; wide scatter = anomalies/inconsistency. Race-readiness cluster analysis compares peak power across three matched 30-day windows: last 30 d, this season −30, same window prior season; tighter cluster = closer to peak **provided hard efforts actually occurred**.
CONFIDENCE: expert-opinion (n=1 illustrative for the 98–99% figure).
SOURCE: `REF/fatigue` §6.2, `REF/testing` §6, `REF/pd-model` §15 — Cusick (C-ZKcZTYUIFfc-30, C-ldRCkYGaSvI-19).
HOOK: athlete classification + taper/race week (peak-readiness signal). Must distinguish "no hard efforts occurred" from "not ready."
WKO-GATE: none — computable from best-effort history.

**R100 — RULE:** For long-duration disciplines, raise threshold as the indirect lever on durability.
NUMBERS: stamina and FTP are "highly correlated" for ultra runners, Ironman, 24-hr riders (stated qualitatively, no r-value — the store flags this as a soft claim worth tightening).
CONFIDENCE: expert-opinion.
SOURCE: `REF/fatigue` §4.2 — Cusick (C-t9cMtn3pe8A-47).
HOOK: block_chain (durability-limited ultra athlete still gets threshold work).
WKO-GATE: stamina → power-decay rate.

---

# I. Recovery-week depth / compliance / execution

**R101 — RULE:** Read a TSB drift to a high positive extreme as detraining risk, not freshness; train back toward the middle band.
NUMBERS: very low/negative TSB = overload risk; very high = detraining/reversibility; middle band = target training zone. Read qualitatively, not as an absolute number.
CONFIDENCE: expert-opinion.
SOURCE: `REF/training-load` §2.8 — Cusick (C-OEWJxhxM3TY-26).
HOOK: block_compliance (upper bound on recovery-week depth — the store's argument that recovery weeks can be **too** deep).
WKO-GATE: none.
**REINFORCEMENT of the ratified recovery-week TSS at 50–65% of the load average, with a named failure mode on the too-light side.**

**R102 — RULE:** Read "completes every session but stops improving" as non-functional overreaching, not appropriate load.
NUMBERS: NFOR signature = "recovered just enough to survive the next workout, too fatigued to adapt." Response: prescribe time off; the athlete gets faster after rest and restart.
CONFIDENCE: expert-opinion.
SOURCE: `REF/training-load` §5.2, §5.3 — Cusick (C-vfC-CRkl5Kk-36, -37).
HOOK: block_compliance / plan-adjustment trigger.
WKO-GATE: none.

**R103 — RULE:** Don't repeat one high-impact session format for more than a few weeks.
NUMBERS: repeating the single highest-impact session ~3–5 weeks straight causes performance decline; repeating one "efficient" format stagnates within ~6–8 weeks.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/training-load` §5.6 — Cusick (C-RjJ7PNu3sNg-24, -35).
HOOK: workout_selector (format-repetition ceiling across a chain).
WKO-GATE: TIS → session time-in-zone dose.

**R104 — RULE:** Require at least one load channel (aerobic or anaerobic) to be trending up at all times outside planned rest.
NUMBERS: when both plateau or decline, subsequent peaks are lost. Companion: an athlete who peaks repeatedly on progressive overload stops peaking the moment progression stalls.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/training-load` §5.11, §3.5 — Cusick (C-OEWJxhxM3TY-24, -20).
HOOK: block_compliance (new R-rule on the chain, not the week).
WKO-GATE: chronic/acute TIS → chronic/acute time-in-zone by band using CTL/ATL-style EW constants (the store cites a community implementation: chronic ~42 d paired with acute 7, 10, or 13 d).

**R105 — RULE:** Design plans expecting 60–70% adherence.
NUMBERS: 60–70% is a "good" plan outcome once illness and life events are accounted for.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/coaching` §6.4 — Cusick (C-H9HA4cupIvg-03).
HOOK: block_compliance (tolerance calibration) + plan-quality expectations.
WKO-GATE: none.

**R106 — RULE:** Give athletes bounded self-determined-training rules, phase-gated — never open discretion.
NUMBERS: early base "feels great" day → extend duration at the same power (3×15 → 3×20; 2×20 → 2×25). Peak-phase "killing it" day → push watts within the planned reps, bounded to "one watt harder," explicitly not 10–20 W more, and **never add reps**. Failed set: resume after 5–10 min rest only if the early reps weren't already a struggle; if struggling from rep one, end the session.
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/coaching` §7.2–7.6 — Cusick (C-H9HA4cupIvg-35, C-qnCAlNgoDxM-27, C-M_I3GwOtJKE-28, C-my4Y0DulYTY-32).
HOOK: workout_selector (structured-workout notes field) + series progression. The store calls this "a concrete, implementable guardrail, not just a coaching philosophy note."
WKO-GATE: none.

**R107 — RULE:** Read "the athlete is tolerating, never wanting more" as starting intensity set too high; default conservative.
NUMBERS: qualitative. Corollary: sweet spot produces "sneaky fatigue" — athletes under-report fatigue in heavy SST blocks, so cross-check subjective reports against objective load trend.
CONFIDENCE: coaching-heuristic / expert-opinion.
SOURCE: `REF/training-load` §7.2, `REF/coaching` §7.7, §8.8 — Cusick (C-M_I3GwOtJKE-32, C-ldRCkYGaSvI-17, C-H9HA4cupIvg-36).
HOOK: series progression (starting-level selection biases low).
WKO-GATE: none.

**R108 — RULE:** Weight yesterday's subjective report above any power-derived metric when writing today's hard session in peak phase.
NUMBERS: qualitative — "the single greatest influence on today's workout is yesterday's workout." Subjective inputs checked daily and **before** power: sleep, stress, motivation, sickness/injury, RPE. Sleep weighted above HRV. HRV smoothed with a 7-day EWMA matched to the ATL constant (8–9 days for aging athletes pre-peak, reverting to 7 near peak). Collect a qualitative post-interval report: empty/exhausted, depleted, or ready for another.
CONFIDENCE: expert-opinion / coaching-heuristic / anecdote for HRV.
SOURCE: `REF/coaching` §8.3–8.7, `REF/interval-design` §10 — Cusick (C-M_I3GwOtJKE-23/-31, C-ldRCkYGaSvI-16, C-vfC-CRkl5Kk-40/-39, C-wlWOb6Nn9Lw-27).
HOOK: physiology gate (readiness input precedence) + workout_selector.
WKO-GATE: none.

**R109 — RULE:** Target outdoor coasting below ~8% and flag above ~10% as wasted training time before blaming terrain.
NUMBERS: <8% target, 5–10% acceptable, >10% wasted. Indoor/outdoor load equivalence depends on it: a rider coasting ~25% gains real time-efficiency indoors; a rider at ~5% coasting sees roughly equivalent load either way.
CONFIDENCE: coaching-heuristic / expert-opinion.
SOURCE: `REF/coaching` §11.7, §11.5 — Cusick (C-qnCAlNgoDxM-37, C-qnCAlNgoDxM-08).
HOOK: block_compliance (post-ride execution metric) + `ROOT/fit` ingestion.
WKO-GATE: none — computable directly from the file.

**R110 — RULE:** Prescribe explicit cadence spread; indoor platforms narrow athletes into "cadence drones."
NUMBERS: gravel example 65 / 85 / 105 rpm. Early-base hard days biased 95–100+ rpm to shift strain cardiovascular-ward and preserve muscular fatigue for later. Review cadence clustering over 28–35-day cycles; a monotone MMP-by-cadence chart signals insufficient cadence work ("rainbow" spread is the goal).
CONFIDENCE: expert-opinion / coaching-heuristic.
SOURCE: `REF/coaching` §11.6, `REF/interval-design` §9, `REF/testing` §6 — Cusick (C-qnCAlNgoDxM-33/-34/-36, C-H9HA4cupIvg-28).
HOOK: workout_selector (cadence field is a cheap, unused specificity lever for gravel).
WKO-GATE: none.

**R111 — RULE:** Restrict two-a-days to Base 1/2, disciplined athletes only, and avoid late-evening second sessions.
NUMBERS: qualitative — evening second session risks sympathetic/parasympathetic disruption and poor sleep.
CONFIDENCE: expert-opinion.
SOURCE: `REF/coaching` §11.8 — Cusick (C-qnCAlNgoDxM-51).
HOOK: calculate_plan_dates (double-day placement rules).
WKO-GATE: none.

**R112 — RULE:** Leave long unstructured pre-season windows unstructured.
NUMBERS: qualitative — structure is itself a stress input ("athlete stress budget"); give broad goals, not detailed prescriptions. Related: don't start a periodized plan before it's needed — "once you light that fuse it's going to burn at its own rate."
CONFIDENCE: coaching-heuristic.
SOURCE: `REF/annual` §10, §1 — Cusick (C-qnCAlNgoDxM-52, C-qnCAlNgoDxM-03).
HOOK: calculate_plan_dates (plan start date is as consequential as the end date — long runways should NOT be filled).
**DIRECT CONTRADICTION of the common generator default (and, per `ROOT/stabilization`, of Endure's own phase-calculator, which "fills all available time with Base → Build → Peak as a continuous ramp — exactly what this principle warns against").**

---

# J. Fueling

**R113 — RULE:** Only prescribe fasted riding as an all-or-nothing 8–10-week protocol; otherwise skip it entirely.
NUMBERS: near-daily for 8–10 straight weeks; must stay in a tight/narrow fat-oxidation intensity band; carb restriction as overall (not acute) nutrition; stop and refuel once depleted. Missing any element more than ~10% of the time yields **zero** benefit and only adds fatigue.
CONFIDENCE: expert-opinion.
SOURCE: `REF/coaching` §11.11 — Cusick (C-OEWJxhxM3TY-04).
HOOK: fueling (this is effectively a "do not offer a watered-down fasted-ride option" guardrail).
WKO-GATE: none.

**R114 — RULE:** Treat glycogen/nutrition status as an unmodeled variable and never attribute a late-set fade to a single cause.
NUMBERS: repeat-effort capacity varies with battery size and glucose/glycogen status — "variables outside what any model measures." Recovery-side modelling is where nearly all W′bal error originates: it can't see nutrition, sleep, or cumulative multi-day fatigue. Prolonged submaximal fatigue is driven mainly by blood-sugar/glycogen depletion + lactate accumulation; short intense efforts by ATP/PCr depletion + lactate/H⁺ + falling neuromuscular drive. (Cusick is personally skeptical of the dehydration/heat contribution — flagged as a tension with the mainstream narrative.)
CONFIDENCE: expert-opinion, with explicit hedge on dehydration/heat.
SOURCE: `REF/fatigue` §1.3, §3.2, `REF/interval-design` §5 — Cusick (C-jtBW4CIGiEU-08/-09, C-HF_yh3rcX6Q-23/-05).
HOOK: fueling + physiology gate (distinguish gradual fade = "soak" from sudden late collapse = check environment/fueling first).
WKO-GATE: dFRC→W′bal; the store says the recovery-side hedge applies **harder** to an open implementation.

**R115 — RULE:** For ultra/long-course athletes, use long zone 1–2 volume explicitly as fueling practice, not just aerobic work.
NUMBERS: qualitative — more Z1/Z2 time "builds muscular endurance, sustainable threshold, **and fueling practice**."
CONFIDENCE: expert-opinion.
SOURCE: `REF/annual` §2 — Cusick (C-M_I3GwOtJKE-38).
HOOK: workout_selector (long-ride description should carry a fueling objective for gravel/ultra athletes).
WKO-GATE: none.

---

# K. Analysis / ingestion guardrails that gate everything above

**R116 — RULE:** Normalize for environment before judging any executed session.
NUMBERS: worked case — same 3×10×40/20 s session, two environments, FTP ~357 W both. Georgia 425 m / 72 °F / 90% RH → decoupling +4.7%. Colorado 1,625 m / 91 °F / 8% RH → decoupling +16%, on-effort power −50 to −66 W per block. Decomposition: altitude model attributes −9.6% (dominant), ~2.5% residual to heat/dehydration/terrain. A naive summary read wrongly called it "lower intensity."
CONFIDENCE: worked case study with a published-model decomposition.
SOURCE: `ROOT/fit` — Endure white paper; altitude/heat decomposition via published population models.
HOOK: block_compliance / series progression (do not down-level an athlete on an environment-suppressed session).
WKO-GATE: none.

**R117 — RULE:** Derive sample rate with the **median** Δt, never the mean, before computing any time-in-zone.
NUMBERS: one pause can drive a 3.8 s mean Δt and inflate time-in-zone to ~10 hours. Also: read first-non-null across `enhanced_*` then legacy; index by seconds-from-t₀ (records aren't contiguous); FTP sanity check = NP ÷ IF; TSS/IF depend on the device FTP at ride time.
CONFIDENCE: engineering-verified parsing rules.
SOURCE: `ROOT/fit` Part A — reference impl `~/.claude/tools/analyze_fit.py`.
HOOK: every TIZ-based rule above (R13–R17, R36–R37) is invalid without this.
WKO-GATE: n/a.

**R118 — RULE:** Compare matched segments and read slopes; never judge from whole-ride aggregates or min/avg/max.
NUMBERS: detect workout structure before interpreting effort; bin environment over 10-min windows; a 30 s @ 500 W spike can lift a whole interval's average to 350 W without achieving the intended stimulus.
CONFIDENCE: expert-opinion (Cusick) + Endure analytical doctrine.
SOURCE: `ROOT/fit` Part B; `REF/interval-design` §3 — Cusick (C-wlWOb6Nn9Lw-31).
HOOK: block_compliance (execution scoring must be TIZ-based, not average-power-based).
WKO-GATE: none.

---

# Reinforcements & contradictions vs. the ratified standards

**Reinforced**
- Endurance IF .60–.70 scaled down with duration → R83 (ride the bottom-middle of the zone; top edge = "very very tiny" gain for much higher fatigue) and R92 (strain inflects at 90 min–2 hr at constant power).
- ≤50 TSS/hr endurance cap → R83; also cross-checks against the store's 25 TSS/30 min (~50/hr) strength proxy (R6).
- 45-min floor → R17 (SST rep floor 15 min, threshold 10 min) and R37 (per-category TIZ minimums) operate at the interval layer beneath it.
- Recovery week 50–65% of load average → R101 adds the missing upper bound (too-fresh TSB = reversibility band).
- W′bal nadir gate → R93/R94/R95 supply per-zone expectations and set shape ("drain a little deeper each rep, empty only at the end").
- T@VO2max gate → R14 supplies the upper bound (15–18 min above 95%) the current gate lacks, plus a prescribed-time→banked-time conversion (12–30 min prescribed ≈ 15 min banked).

**Contradicted / needs a decision**
- "2–3 intensity/load week" → R19 makes this maturity-conditional: **2 for novices**, 3 only at ≥1–2 yrs training age, and **2–2.5 in a VO2max block**. A flat 2–3 over-doses novices.
- "VO2 every 14 days" → R36 puts max-aerobic maintenance at **1 per 7–14 workouts**, which at 5 sessions/wk is roughly every 1.5–3 weeks. The ratified rule sits at the sparse end; the store's base-phase intensity floor is 1 hard day per 8–14 **workouts** (R54), which is denser than 14 days for most athletes.
- 45-min floor vs. R38 (5–6 × ~1 hr beats 2–3 × ~3 hr at equal hours) — the store's frequency argument favors more, shorter sessions where hours are constrained; a hard 45-min floor can force the wrong trade for a 5-hr/week athlete.
- Taper rules cap hard content but don't mandate the **reload** (R57: rest 10–14 d out, then 2–3 hard efforts). The store's stated failure mode is an athlete left "too flat." Note this is the store's weakest tier — **anecdote**.
- Plan-filling behavior: `ROOT/stabilization` names Endure's own phase-calculator as doing exactly the wrong thing (filling all available time with a continuous Base→Build→Peak ramp). R41 (base ≤16 wks), R42 (peak 3–6 wks), R112 (don't light the fuse early), R10 (insert a stabilization phase) all point the same way: **a long runway should produce a later start plus a stabilization block, not longer phases.**

**Marked UNUSABLE**
- Any 0–100 "stamina" score (R91) — no open normalized scale exists; substitute a kJ-split power-decay read.
- Population-percentile phenotype / "World Class %" / strengths-vs-population charts (R74, R80) — Endure has no comparable dataset; self-relative only.
- TIS 1–10 badges and TIS band targets (base anaerobic ~5–6; peak anaerobic 9–10 1–2×/wk with aerobic ~4–7) — no open equivalent to the undisclosed weighted-work algorithm or its adaptive scaling. The *structure* (aerobic axis is time-weighted and can't reach 10 under ~1 hr; anaerobic axis is intensity-weighted and can) is a useful design intuition for a home-grown session-dose metric, but the numbers don't transfer.
- WKO's ±5% / ±7.5 residual thresholds (R62) — explicitly "WKO's own calibration, not transferable."

---

# Shortlist — 10 highest-value rules by expected impact on plan quality

1. **R21 + R22** — "plus-one" TIZ step (+45 s → +1 min) with outcome-gated, one-lever-at-a-time progression and a hard "never repeat unchanged 3×" rule. This is the store's most directly usable series-progression increment and it replaces calendar-driven level ramps with something defensible.
2. **R1 + R3 + R5** — ramp 5–8 CTL/wk for 2–4 wks, halve above CTL 100, with CTL bands set by training age (−10 for >50). Turns ramp-rate from a constant into an athlete-classified function; highest-leverage single change to block_chain.
3. **R43 + R8** — enforce "volume slope ≤0 while intensity slope >0 in Peak" and "no monotonic CTL climb." Two cheap block_compliance rules that catch the two most-named coaching mistakes in the entire store.
4. **R14** — VO2max session ceiling 15–18 min above 95%, with the 12–30 min prescribed → ~15 min banked conversion. Closes the open end of the existing T@VO2max gate and prevents endless VO2max duration inflation.
5. **R45** — gravel/ultra peak stays **pyramidal**, not polarized; volume is the specificity; ~8-week specific-prep window. Directly contradicts the default polarized-peak assumption for Gravel God's core event type.
6. **R47** — residual-effect stacking (aerobic 30±5 d, VO2max/glycolytic 18±4 d, speed 5±3 d) as a spacing constraint between a quality's last block and race day. The only peer-reviewed sequencing anchor in the store, and the store says the phase-calculator doesn't encode it.
7. **R41 + R42 + R112** — base ≤16 wks, peak 3–6 wks front-loaded, and **do not fill a long runway**. Fixes the "perma-fit" failure mode that a time-filling phase calculator produces by construction.
8. **R94 + R95** — per-zone W′bal expectations: VO2max efforts should deplete >50% (target ~2/3) or they're under-executed; sweet spot should show near-zero drawdown or the athlete rode hot. Adds an under-cooked floor and a zone-conditional dimension to the existing single-threshold nadir gate.
9. **R88 + R89 + R91** — durability as a first-class object: 2–3× repeat-failure means keep the wattage and build repeatability; train it with intervals placed late in a fatigued ride, phase-gated to build/peak; probe it 2–3×/yr with a kJ-split power-decay test (1000/1500/2000 kJ). Highest-value new workout archetype for gravel, and it prevents the generator from silently down-leveling durability-limited athletes.
10. **R62 + R65** — gate all model-derived prescriptions behind ≥30 d (90 preferred) with short/medium/long coverage, then blend testing into training every 4–6 weeks (6–8 in early base), steered by the stalest duration and placed in week 2 of the cycle after a rest week. Makes every other rule on this list trustworthy, and converts "test week" from a plan interruption into a normal hard day.

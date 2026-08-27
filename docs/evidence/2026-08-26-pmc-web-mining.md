# PMC Web Mining — CTL/ATL/TSB Planning, Tapering, Race-Day Form

**Date:** 2026-08-26 · **Method:** live web mining (WebSearch/WebFetch/exa), every claim
cited to URL/author. Derived arithmetic computed from the TP recurrence and marked [M].
**Tiers** (per `docs/ALGORITHM_EVIDENCE.md`): `[P]` peer-reviewed · `[E]` expert-opinion
(named coach on record) · `[H]` coaching heuristic · `[A]` anecdote · `[M]` model-derived.
Citation keys here: `PW-#` (PMC Web).

---

## 1. The model itself

**PW-1 [E] Exact form.** CTL = exponentially weighted moving average of daily TSS,
default time constant **42 d**; ATL = same, default **7 d**; **TSB = CTL − ATL**, and
"today's TSB = yesterday's (CTL − ATL)" — TSB is computed from *yesterday's* values.
— Coggan, "The Science of the TrainingPeaks Performance Manager"
(https://www.trainingpeaks.com/learn/articles/the-science-of-the-performance-manager/);
TSB-lag detail: Alex Simmons (http://alex-cycle.blogspot.com/2013/03/a-time-for-bit-of-sensitivity-analysis.html).
Recurrence (TP implementation): `CTL_t = CTL_{t−1} + (TSS_t − CTL_{t−1})/42`;
ATL identical with 7.

**PW-2 [E] Banister lineage.** Coggan's PMC is Banister et al. (1975) impulse-response
with τa = 42 d (fitness), τf = 7 d (fatigue), and the gain factors ka/kf **eliminated**
— which is why PMC output is unitless "form," not a performance prediction. Coggan:
the Performance Manager is "part science, part art." (Science of the Performance
Manager, URL above.)

**PW-3 [E] Coggan's own TSB semantics.** "A TSB of less than −10 would usually not be
accompanied by the feeling of very 'fresh' legs… a TSB of greater than +10 usually
would be. −10 to +10 might be considered 'neutral.'" Explicit caveat: precise values
"should not be applied too literally." (Same article.)

**PW-4 [E] Load ceiling + ramp limit (Coggan).** Optimal chronic load "CTL somewhere
between 100 and 150 TSS/d"; "few, if any, athletes… sustain a long-term average of
>150 TSS/d"; ramping CTL "at a rate of >5–7 TSS/d/wk for four or more weeks is often
a recipe for disaster." (Same article.) Corroborated: "Very fit athletes can increase
their CTL up to five-to-seven points a week" — Andrew Simmons, TrainingPeaks coach blog
(https://www.trainingpeaks.com/coach-blog/a-coachs-guide-to-atl-ctl-tsb/). [E]

**PW-5 [E] Adjusting the constants.** Coggan (WKO+ FAQ, quoted verbatim in search
capture and corroborated on the wattage list, 2008): younger athletes / low training
load / sustained-power events → shorter ATL constant, **4–5 d**; masters / high load /
non-sustainable-power events → longer, **10–12 d**. (Wattage thread quoting "Coggan's
point #2 on the wko website": https://wattage.topica.narkive.com/8xCOt9op/atl-and-ctl-constants-on-wko).
FasCat (Frank Overton) runs ATL constants **3–7** by recovery speed
(https://fascatcoaching.com/blogs/training-tips/performance-manager-chart/). [E]
Alex Simmons: the chart is **insensitive to the CTL constant** ("may as well leave it
at 42"), far more sensitive to the ATL constant; changing ATL shifts absolute TSB and
phase but not the pattern; Skiba's RaceDay Apollo can fit personal constants but with
sizeable error (URL in PW-1). [E]
The current TP help article "Adjusting CTL/ATL Parameters"
(https://help.trainingpeaks.com/hc/en-us/articles/226119807-Adjusting-CTL-ATL-Parameters)
now only covers adjusting **starting values** (ATP config menu / PMC ☰ menu) — TP no
longer exposes time-constant editing guidance there. [E]

**PW-6 [M] Half-life correction.** With τ = 42 in the TP recurrence, CTL half-life is
**28.8 days**, and 42 days of full rest leaves **36.3%** (≈ e⁻¹), not 50%. FasCat's
published claim "42 is the 1/2 life of training… CTL 100 → 50 after 42 days off"
(Overton, URL above) is **arithmetically wrong** [A — do not encode].

**PW-7 [E][P] Known limitations.**
- Coggan lists five: no physiological mechanism; unlimited performance ceiling assumed;
  Banister fitting needs 20–200 performance measurements; parameter instability at low
  loads; high gain-factor variability across studies (Science of the Performance
  Manager, URL above). [E]
- TSS is intensity-distribution-blind: identical TSS from IF 0.5 volume vs IF 1.1
  intervals is treated as identical adaptation stimulus — "not supported by practice or
  scientific literature"; NP/TSS also ignores how long supra-FTP effort is sustained
  (3D impulse-response model paper, arXiv: https://arxiv.org/pdf/2503.14841). [P]
- Short/stochastic racing (crit, track, CX-style sessions): weekly TSS "can look
  surprisingly high despite the actual recovery demand being manageable" — and
  conversely NP-based TSS misprices repeated anaerobic surges (Roadman Cycling,
  https://roadmancycling.com/blog/training-stress-score-tss-cycling-guide). [H]
- 80/20 Endurance ("Your Performance Management Chart Is Lying To You",
  https://www.8020endurance.com/performance-management-chart-is-lying-to-you/):
  CTL-maximizing selects against polarized distribution (worked example: 603 TSS/wk
  moderate rider vs 570 TSS/wk 80/20 rider — lower CTL, better race); infinite workout
  mixes share one TSS; CTL stays flat when FTP rises even though fitness rose. [E]

## 2. Race-day TSB targets

**PW-8 [E] Friel's canonical zones** (Joe Friel, "Managing Training Using TSB",
https://joefrieltraining.com/managing-training-using-tsb/):
- **< −30**: high-risk — "flirting with extreme overreaching"; a few days at most,
  2–4 extended episodes per season.
- **−30 to −10**: optimal training zone ("most effective training occurs").
- **−10 to +5**: grey zone — "not much happening that will improve fitness."
- **+5 to +25**: freshness zone — race day; individual optimum varies (+20…+25 for
  some, +5…+10 for others; "trial and error").
- **> +25**: transition — "very safe, but fitness is also very low."

**PW-9 [E] Friel worked peaks.** Race-day Form actually achieved for A-races: **+20,
+21, +22** (TT and Ironman examples), with CTL loss held to ~10% ("More on Peaking",
http://www.trainingbible.com/joesblog/2009/08/more-on-peaking.html; "Projecting Race
Readiness", http://www.trainingbible.com/joesblog/2009/09/projecting-race-readiness.html).
Friel: the real target is *fitness kept*, not TSB height — "the issue is not how high
form rises but rather how low fitness drops when peaking" ("Strong and Weak Form",
http://www.trainingbible.com/joesblog/2008/07/strong-and-weak-form.html).

**PW-10 [E] Other published bands.**
- Coggan: fresh above +10; −10..+10 neutral (PW-3).
- Andrew Simmons (TrainingPeaks): peak performance "between **+15 and +25**"; train at
  −10..−30; beyond −30 = extreme strain (coach-blog URL in PW-4).
- Matt Fitzgerald (TrainingPeaks, "Managing Your Training Stress Balance",
  https://www.trainingpeaks.com/blog/managing-your-training-stress-balance/): "slightly
  positive (**+5 or so**) on race day"; don't dip below **−20** more than once/10 days.
- Zwift Insider ("Coming into form", https://zwiftinsider.com/coming-into-form/):
  A-race goal TSB **+15..+25**; B/C races **−10..0** (train through); taper starts
  **10–14 d** out; avoid living in −10..+10.
- Roadman Cycling (https://roadmancycling.com/blog/cycling-taper-pmc-performance-management-chart):
  most riders **+5..+15**; TT/climbers +10..+20; sprinters slightly lower.
- Event-duration direction (Overton/FasCat, PMC article URL above): shorter events
  (crit/track) → higher TSB; longer events → lower TSB. No numbers published. [H]
- Consensus overlap of all published bands: **+5..+25**, mode ≈ +15..+20 for A-races.

## 3. Taper science

**PW-11 [P] Bosquet et al. 2007** (Med Sci Sports Exerc 39(8):1358-65; meta-analysis,
27 of 182 studies; https://pubmed.ncbi.nlm.nih.gov/17762369/, effect sizes via
https://www.semanticscholar.org/paper/a41517ab5fa06b92568b861e2b1aa32b3003d214):
- Optimal: **2-week taper, exponential volume reduction 41–60%, intensity and
  frequency maintained**.
- Effect sizes: volume −41–60% → **ES 0.72 ± 0.36**; 2-week duration → **ES 0.59 ± 0.33**;
  intensity maintained → ES 0.33 ± 0.14; frequency maintained → ES 0.35 ± 0.17
  (all P < 0.001). Typical performance gain ≈ **3%** (range 0.5–6%) — Mujika & Padilla
  (Pyne, Mujika, Reilly 2009, https://umh1617.umh.es/files/2016/05/Pyne-et-al.-2009.-Peaking-for-optimal-performance-invited-commentary.pdf).

**PW-12 [P] Mujika & Padilla taxonomy** ("Scientific Bases for Precompetition Tapering
Strategies", MSSE 2003, https://www.researchgate.net/publication/10678071): taper types
= **linear**, **exponential fast-decay**, **exponential slow-decay**, **step**.
Progressive (nonlinear) tapers beat step tapers; exponential fast-decay tends to beat
slow-decay; step = sudden fixed reduction, linear = steady weekly cut.

**PW-13 [P] Wang et al. 2023** (PLOS ONE, 14 studies,
https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0282838):
TT performance SMD −0.45 overall; progressive taper SMD −0.51 vs step −0.38; duration
**8–14 d strongest (SMD −1.47)**; ≤7 d and 15–21 d significant, **≥22 d not
significant**; volume reduction **41–60% the only significant band (SMD −0.77)**;
maintain intensity + frequency; **pre-taper overload beat conventional taper**.

**PW-14 [P] Modeling studies (Busso/Thomas/Mujika line).**
- Thomas, Mujika, Busso 2008 (J Sports Sci): optimal *linear* taper after a 28-d
  overload at 120% of normal training = reduce load **32 ± 6% over 35 ± 6 d**
  (non-athletes) or **49 ± 18% over 33 ± 16 d** (elite swimmers) — overload going in
  demands longer/deeper tapers (https://www.researchgate.net/publication/5508482).
- Thomas, Mujika, Busso 2009 (JSCR 23(6):1729-36): **two-phase taper** — optimal linear
  taper plus a **+20–30% load bump in the final ~3 days** — outperforms pure linear
  taper in simulation (https://www.ovid.com/jnls/nsca-jscr/abstract/10.1519/jsc.0b013e3181b3dfa1~computer-simulations-assessing-the-potential-performance).
- Avalos-line longitudinal swimmers study (J Sports Sci Med 2013,
  https://pmc.ncbi.nlm.nih.gov/articles/PMC3873657/): best 3-wk taper pattern = load
  peak in week 1 then slow decay (**57 → 45 → 38%** of individual max weekly load);
  best overload = 84/81/80%. With training age (season 4+), higher overload + sharper
  taper wins.

## 4. The CTL-retention problem

**PW-15 [E] Friel's ≤10% rule (verified — it exists).** "Keep Chronic Training Load
('Fitness') losses to around 10%" during a peak; worked examples −11% (85.2→76.1) and
−9% (62.8→56.9); "Weak Form" = fitness drops "significantly more than 10 percent"
while TSB balloons (+30 in his example). Taper length scales with event: **12 d**
(20 km TT) to **21 d** (Ironman). ("More on Peaking" + "Strong and Weak Form" +
"Projecting Race Readiness", URLs in PW-9; cumulative −13% by a second peak was
accepted for race two.)

**PW-16 [M] Derived taper table.** From the TP recurrence (PW-1), starting at steady
state CTL = ATL = 100, TSB = 0, constant reduced daily load for the taper:

| Taper | Load kept | CTL end | CTL lost | TSB end |
|-------|-----------|---------|----------|---------|
| 7 d   | 70%       | 95.3    | 4.7%     | +15.1   |
| 7 d   | 50%       | 92.2    | 7.8%     | +25.2   |
| 10 d  | 70%       | 93.6    | 6.4%     | +17.2   |
| 10 d  | 60%       | 91.4    | 8.6%     | +22.9   |
| 14 d  | 70%       | 91.4    | 8.6%     | +17.9   |
| 14 d  | 60%       | 88.5    | 11.5%    | +23.9   |
| 14 d  | 50%       | 85.7    | 14.3%    | +29.9   |
| 21 d  | 70%       | 88.1    | 11.9%    | +16.9   |
| 21 d  | 60%       | 84.1    | 15.9%    | +22.5   |
| 21 d  | 50%       | 80.1    | 19.9%    | +28.2   |

Full rest from CTL 100: 7 d → 84.5, 14 d → 71.4, 21 d → 60.3, 28 d → 50.9.
Everything scales linearly in CTL₀ (percentages hold at any starting CTL).
Key joint reading [M]: **Bosquet's optimal taper (14 d at ~50% load) costs ~14% CTL and
overshoots Friel's +25 ceiling; the intersection of "TSB +15..+25" and "CTL loss ≤10%"
is a 7–10 d taper at 50–60% load, or 14 d at 60–70%.** Friel's own event-scaled
durations (12–21 d) require the milder 60–70% retention to respect his 10% rule —
consistent with his worked examples (~10% loss, TSB ~ +20).

**PW-17 [P][E] Ramp-into-taper (overload week).** Pre-taper overload improves taper
outcome (Wang 2023, PW-13; Thomas 2008 modeled it explicitly, PW-14) but demands a
longer/deeper taper. Practical cost of overreaching first: taper gains roughly double
from ~ +3% only if overload is absorbed; unabsorbed overload with a standard 2-wk taper
underperforms (Thomas 2008 simulation, URL in PW-14).

## 5. TSB manipulation patterns

**PW-18 [H][M] Openers / why TSB dips then rebounds.** Race-week openers (4–6 × 30 s–2 min
at/above race intensity, full recovery) add small TSS → ATL blips up (TSB dips ~1 day)
then falls fast on τ = 7 while CTL barely moves on τ = 42 — "reduce fatigue (ATL)
faster than you lose fitness (CTL)… mathematically guaranteed" (Roadman,
https://roadmancycling.com/blog/cycling-taper-pmc-performance-management-chart;
TrainerRoad, https://www.trainerroad.com/blog/tapering-and-peaking-for-cyclists-be-ready-for-race-day/).
Intensity is what you keep: two short sharp sessions/wk inside the taper (80/20
Endurance, https://www.8020endurance.com/tapering-for-endurance-athletes/). The 2-phase
taper simulation (PW-14) is the peer-reviewed version of the same move.

**PW-19 [E] Multi-peak seasons.** Friel: **~3 A-priorities max per season, spaced
several weeks apart**; consecutive peaking weeks bleed CTL — "by the third or fourth
week of continued Fatigue reduction, Fitness is likely to be so low that performance is
significantly compromised" ("Projecting Race Readiness", URL in PW-9). His accepted
cumulative CTL cost across two close peaks: −13%. TP ATP enforces A-races within 32
weeks of each other and rebuilds base between A-races for "Weak" fitness athletes
(PW-21).

**PW-20 [E][H] Race blocks / racing into form.**
- CX season (Overton, https://fascatcoaching.com/blogs/training-tips/peak-for-cyclocross-nationals):
  hold CTL in a "race 'n recover" plateau (low 60s) through the season, then a
  **17–19 d taper** cutting volume but keeping CX intensity; CTL 66 → 53 (−20%) for a
  **TSB +29** at Nationals — deliberately above Friel's ceiling, Overton calls this
  "super fresh… crucial for cyclocross." Tune-up races: bring TSB "slightly positive."
- Stage races: start TSB moderately positive; Friel on a 4-day stage race at TSB +11:
  "a higher TSB by day 1" is generally preferable ("More on Peaking" comments, PW-9).
  During the block TSB goes deeply negative by design; training camps are the rehearsal
  for deep negative TSB (TrainingPeaks,
  https://www.trainingpeaks.com/blog/using-the-performance-management-chart-to-maximize-your-spring-training-camp/).
- Fitzgerald's frequency cap while racing/training: TSB below −20 no more than once per
  10 days (PW-10).

## 6. TP ATP internals (TSS allocation)

**PW-21 [E] ATP methodologies** (TrainingPeaks Help,
https://help.trainingpeaks.com/hc/en-us/articles/224662768-Annual-Training-Plan-Methodologies):
- Three planning modes: **duration** (hours), **weekly average TSS** (ATP computes
  weekly TSS targets + projects PMC), **Event CTL** (enter race-day CTL; ATP
  **back-calculates required weekly TSS**; manual mode = *linear progression* to the
  Event CTL goal).
- Period lengths (Friel methodology): Transition 1–6 wk, Prep 3–4, **Base 8–12,
  Build 6–8, Peak 1–2, Race 1–3**. Period assignment is a **lookup table** keyed on:
  weeks to A-event, position between A-races, Strong/Weak fitness, 3- vs 4-week
  recovery cycle. "Weak" inserts base periods between races; A-races must be within
  32 wk of each other. 4-wk cycles for experienced/under-40, 3-wk for inexperienced/
  over-40.
- Annual volume table (weekly TSS by longest-race duration, finish vs performance
  goals): up to 3 h → 350–500 / 500–1000 TSS/wk; 3–8 h → 500–640 / 725–1250 TSS/wk;
  >8 h → 640–890 / 1000–1500 TSS/wk.
- TP publishes **no intra-period weekly-TSS distribution math** beyond "linear
  progression to Event CTL" in manual+CTL mode; the automatic mode is Friel's book
  methodology behind a lookup table. (Companion: "Suggested Weekly TSS and Target CTL",
  https://help.trainingpeaks.com/hc/en-us/articles/230904648-Suggested-Weekly-TSS-and-Target-CTL.)

---

## Computable rules candidates

Each stated as a testable inequality; encode against sim output of the PW-1 recurrence.

- **CR-1 (A-race form window).** Race-day TSB ∈ **[+5, +25]**, target sub-band
  [+15, +25] default, AND CTL(race) ≥ **0.90 × CTL(taper start)**. — Friel PW-8/PW-9/PW-15;
  Simmons PW-10. [E]
- **CR-2 (taper prescription).** Taper duration ∈ **[8, 21] d** scaled by event
  duration (≈12 d short events → ≈21 d ultra), daily load = **50–70%** of pre-taper
  average (pick within band to satisfy CR-1's CTL clause), **intensity and session
  frequency unchanged**. — Bosquet PW-11, Wang PW-13, Friel PW-15, derived PW-16. [P][E][M]
- **CR-3 (taper shape).** Progressive/exponential decay ≥ step: weekly load
  monotonically non-increasing within taper, except an allowed opener bump of
  **+20–30% of taper load in the final 3 days** (openers). — Mujika & Padilla PW-12,
  Thomas 2009 PW-14, Wang PW-13. [P]
- **CR-4 (chronic load rails).** ΔCTL ≤ **+5–7 /wk**, never 4+ consecutive weeks at the
  ceiling; long-term CTL target ≤ 100–150 TSS/d (athlete-tier scaled down for
  age-groupers). — Coggan PW-4. [E]
- **CR-5 (training-phase TSB rails).** Productive weeks: TSB ∈ [−30, −10]; TSB < −30
  never > a few consecutive days and ≤ 2–4 episodes/season; TSB < −20 at most once per
  10 days; minimize planned time in [−10, +5] outside taper/race weeks. — Friel PW-8,
  Fitzgerald PW-10. [E]
- **CR-6 (B/C races).** B/C race-day TSB ∈ **[−10, 0]** (train through; no CTL
  sacrifice). — Zwift Insider PW-10, FasCat PW-20. [H]
- **CR-7 (multi-peak spacing).** ≤ 3 A-peaks/season; ≥ several weeks (TP: within a
  32-wk window, rebuild between) apart; cumulative CTL loss across back-to-back peaks
  ≤ ~13%; never > 2 consecutive peaking weeks. — Friel PW-19, TP ATP PW-21. [E]
- **CR-8 (overload-into-taper coupling).** If pre-taper week(s) ≥ 110–120% of normal
  load, extend/deepen taper (modeled optimum after 28 d @120%: ~33 d at −49% for
  elites) — i.e. taper depth/duration must be a function of entry fatigue (TSB at taper
  start), not fixed. — Thomas 2008 PW-14, Wang PW-13, swimmers PW-14. [P]
- **CR-9 (stage race / race block entry).** Multi-day event: day-1 TSB ≥ +10 preferred;
  within-block TSB is unconstrained (goes deeply negative by design). — Friel PW-20. [E]
- **CR-10 (model guardrail).** Do not encode "42 = half-life" (false; half-life = 28.8 d
  [M], PW-6) and never compare CTL across athletes or across FTP changes as "fitness"
  (PW-7). [M][E]

## Open questions

1. **TSB ceiling conflict:** Friel caps race-day freshness at +25 with ≤10% CTL loss;
   Overton peaked CX Nationals at TSB +29 / −20% CTL and calls it crucial for CX. Is the
   ceiling event-type-dependent (short anaerobic events tolerate more CTL sacrifice)?
2. **ATL constant per athlete:** Coggan's 4–5 d (young/sustained-power) vs 10–12 d
   (masters/anaerobic events) changes race-day TSB by ±5–10 points for the same plan.
   Do we individualize τ_ATL in Motoren (age-keyed default?), or keep 7 and widen bands?
3. **Openers bump:** encode the two-phase taper (+20–30% final 3 days) as default or as
   an opt-in? Simulation-only evidence [P/M]; universal coaching practice [H] agrees
   directionally but with much smaller doses.
4. **B/C race band:** −10..0 comes from secondary sources only [H]. Does Matti ratify a
   B-race band (e.g. TSB ∈ [−10, +5]) or leave B/C races unconstrained?

# Loading Benchmarks by Performance Level — volume, TSS, CTL (2026-08-26)

**Status: EVIDENCE + PROPOSED RULE — NOT RATIFIED.** Mined for Matti's
2026-08-26 directive: "demonstrated load is an important consideration, but
so is general loading levels… point out to an athlete a mismatch between
goals and the time they're putting in i.e. being a national level gravel
racer on 5 hours a week."

Evidence tiers per `docs/ALGORITHM_EVIDENCE.md`: `[P]` peer-reviewed ·
`[E]` expert-opinion (named coach on record) · `[H]` coaching heuristic
(unattributed/aggregator) · `[A]` anecdote · `[M]` model-derived
(arithmetic). Every number carries a URL or a repo citation. Cells with no
defensible source say so.

Repo anchors reused (already ratified, cited by rule ID):

- **AE-1.5** — CTL bands by training age; feasibility cap first (6–8 h/wk ⇒
  CTL ~75 ceiling); 800 h/yr ≈ serious age-grouper, 1,000 h/yr ≈ top tier.
  (R5, R6, R79; A1)
- **R5/R6/R7** verbatims: `docs/evidence/2026-08-23-wko-store-mining.md`
  (Cusick, WKO `REF/training-load` §2.2, §3.1–3.3, §8.1; `REF/annual` §3).
- **A1** verbatim: `docs/evidence/2026-08-23-couzens-corpus-mining.md`
  (Couzens classified corpus, `nxrVHH8ZLog.json`, `304OhuvWPEM.json`).
- **AE-2.10** — demonstrated dose beats archetype default.

---

## 1. Benchmark table — gravel / road endurance racing (primary)

Sustained in-season figures, not one-off peak weeks. CTL ≈ (weekly TSS)/7
[M — arithmetic identity of the 42-day PMC model]. Weekly-TSS cells that
carry only [H] are aggregator-published and unattributed — treat as
plausibility checks, not anchors.

| Level | Weekly hours (in-season sustained) | Weekly TSS | CTL | Annual hours |
|---|---|---|---|---|
| **Recreational finisher** (finish the event) | 5–9 h/wk — TP Unbound-200 beginner/finisher plans run 8–12 h/wk [E-plan]¹; TP Gravel-100 plan 9–12 h/wk [E-plan]² | 200–350 [H]³ | 40–60 — CTS: "CTL values around 40–100 for century and non-competitive gran fondo riders" [E]⁴; TP Gravel-100 plan entry bar "CTL over 50", Gravel-200 ultra "over 60" [E-plan]² | ~250–450 h [M — weekly×48; Couzens mid-pack IM path ≈300–520 h/yr [E]⁵] |
| **Competitive age-grouper** (top half, local podiums) | 8–12 h/wk [E]⁴ ⁶ | 400–600 [H]³ | 70–100 — CTS: masters racers / MTB XC / AG fondo "typically fall in the 70–120 range" [E]⁴; Science to Sport: "70 TSS/day for some competitive age group athletes" [E]⁷; Cusick mid band 61–95 (2–5 yr training age) [E, R5] | ~400–600 h [M] |
| **Top age-grouper / regional podium** | 12–16 h/wk — Couzens: 800 h/yr tier ≈ 16 h/wk avg, "10–12 h/wk early season and 20+ h/wk weeks in-season" [E, A1]; TP experienced Unbound plans peak 16–19 h [E-plan]⁸ | 600–800 [H]³ [M — CTL×7] | 85–115 — Cusick high band ≥96 (2–5 yr) / 81–115 (5+ yr) [E, R5]; Couzens: "typical top age group CTL numbers of 150 or so" is TRIATHLON multisport-summed — do not import to cycling-only [E]⁹ | ~600–800 h — Couzens: "It's very rare for an athlete to put in 800 to 1,000+ hours per year and not qualify for Kona" [E, A1]⁵ |
| **National elite (amateur elite / privateer-adjacent)** | 16–22 h/wk [M — interpolation between the 800 h/yr tier and pro anecdotes; no direct named-coach source found for this exact tier in gravel] | 750–1,000 [H]³ [M] | 105–135 — Cusick developing-pro trajectory 115→125→135, ceiling ≈140–155 [E, R7]; aggregator "elite amateur 120–130" [H]¹⁰ | 800–1,000+ h [E, A1] |
| **Pro (gravel privateer / continental)** | 20–28 h/wk — Keegan Swenson: "27, 28 hours?" in-season [A]¹¹ | 900–1,200+ [H]³ | 130–155 — Science to Sport: "as high as 140 CTL for pro tour riders" [E]⁷; Cusick ceiling 140–155, Grand-Tour 180–200 "not convertible to peak form" [E, R3/R7]; Couzens 9-hr Ironman cohort ≈ CTL 150 (multisport) [E]¹² | ~1,000–1,200 h [M — 20–24 h/wk × 48] — but the peer-reviewed systematic-review figure for WorldTour ROAD is lower: ~680–730 h/yr training [P]¹³. Racing days excluded from "training" likely explain the gap — flagged, not resolved. |

**Discipline notes (where sources differentiate):**

- **MTB XC** — sits inside the CTS 70–120 band (named alongside masters
  road) [E]⁴. No XC-specific hours table found beyond that.
- **CX** — low-CTL / high-intensity by design. FasCat (Frank Overton), CX
  Nationals case: race-season "training load (chronic training load/CTL)
  will remain in the low 60's from a race 'n recover style", tapered 66→53
  for race day, peak TSB +29 [E]¹⁴. TrainingPeaks (CIL article): "When
  your goal races are criteriums, cyclocross races, or mountain bike
  races, using CTL may undervalue the short hard interval sessions" [E]¹⁵.
  **Do not apply the road/gravel CTL column to a CX goal**; a national-level
  CX racer at CTL 60–70 is normal, not underloaded.
- **CX/crit corollary**: mismatch detection for these disciplines must key
  on hours + intensity budget, not CTL. (Consistent with the corpus
  critique that CTL/TSS is a load, not stress, measure —
  `2026-08-23-couzens-corpus-mining.md` line 89.)

**TP/Friel official position** — TrainingPeaks' own canonical CTL article
(Friel, "Applying the Numbers Part 1") explicitly REFUSES universal CTL
targets: "I wish I could be more specific about the actual Fitness number,
but as explained I can't. It just depends." Only concrete anchors: 150
TSS/day named as "very high", ramp 5–8 CTL/wk [E]¹⁶. So the table above is
built from coach-published bands (CTS, Cusick, Couzens), not from a TP
official standard — TP support material does not publish one. The
TP-platform numbers that DO exist are plan entry bars (CTL>50 gravel 100,
CTL>60 gravel 200) [E-plan]².

**No source found:** gravel-specific weekly-TSS norms by category (all
weekly-TSS cells are [H] aggregator or [M] arithmetic); women-specific
bands (van Erp reports women lower-volume/higher-intensity than men [P]¹³,
no absolute bands published in the abstract); national-elite gravel hours
as a named-coach number (interpolated [M], flagged in-cell).

---

## 2. Proposed AE-2.11 — Goal-load feasibility (NOT ratified)

**AE-2.11 — Goal-load feasibility.** [E][M] At intake and at every build,
compare the athlete's stated goal level against (a) their hour budget and
(b) their current/recent CTL, using the §1 table (discipline-adjusted; CX
uses hours+intensity, not CTL). Feasibility arithmetic per AE-1.5/R6: the
hour budget caps achievable CTL before any band is assigned. A goal whose
band floor exceeds what the budget can reach is a MISMATCH. A mismatch is
SURFACED, never silently absorbed:

1. **Coaching brief: always.** State goal tier, required band, budgeted
   hours, achievable CTL ceiling, and the gap in one table row.
2. **Athlete-facing: honest, non-crushing, terse (AE-9.10).** Sentence
   pattern:

   > Goal: [national-level gravel]. Riders at that level hold
   > [16–22 h/wk, CTL 105+]. Your budget: [5 h/wk] → ceiling ≈ [CTL 45].
   > That gap is structural — no plan closes it at these hours. Three
   > options: 1) find [X] more h/wk and we re-run this math; 2) keep
   > [5 h/wk] and race to win [your age group / regionals] instead;
   > 3) build toward it over [2–3] seasons. This plan is built for the
   > hours you actually have.

3. **The plan itself is still built to the budget** (AE-2.10 anchor +
   AE-1.5 caps). Mismatch changes the conversation and the stated target,
   never inflates prescribed load.

**Lint shape (proposed):** `--goal-level
<finisher|competitive|top-agegroup|national|pro>` on the compliance/lint
pass. Compares plan average load-week hours AND modeled end-of-plan CTL
path against the §1 band for the tier + discipline. Below band floor ⇒
WARN `GOAL_LOAD_MISMATCH` (message carries the three-option pattern
above). Never FAIL — the coach owns the conversation. No flag ⇒ no check
(tier is not inferable from race registration alone).

**Relation to AE-1.5:** consistent, not superseding. AE-1.5 classifies by
training age and caps by hours; AE-2.11 adds the goal axis: AE-1.5 answers
"what can this athlete safely hold", AE-2.11 answers "what does the goal
require" and surfaces the difference.

---

## 3. Interaction with AE-2.10 (one paragraph)

AE-2.10 makes demonstrated load the FLOOR and anchor — what the athlete
has actually absorbed is what the plan doses from. The §1 table is the
GOAL's requirement — what the stated ambition demands, independent of the
athlete. Neither overrides the other: the plan is always built from the
AE-2.10 anchor upward at AE-1.4 ramp rates, and the table is never used to
inflate prescription. The gap between demonstrated load and the goal band
IS the coaching conversation — its size (in CTL points and hours/wk) and
the ramp math (≤10 CTL/month, AE-1.4) give an honest earliest-date for the
goal to be physiologically on the table, which is exactly the "compressed
uncertainty" the athlete is paying for.

---

## 4. Open questions for Matti (max 3)

1. **Which TSS/hr arithmetic does the feasibility ceiling use?** R6 says
   6–8 h/wk ⇒ CTL ~75 ceiling (≈65 TSS/hr); the ratified Q6 endurance cap
   of 50 TSS/hr gives 7 h/wk ⇒ ~50 ceiling. The lint needs one number —
   propose 50 TSS/hr (conservative, matches Q6) with R6's 75 treated as an
   intensity-heavy upper bound. Ratify?
2. **Do athletes see the tier names?** "Competitive age-grouper" vs
   goal-language ("top-10 at [race]"). The sentence pattern in §2 assumes
   goal-language with numbers behind it.
3. **Hard stop or WARN-only at extreme mismatch** (e.g. pro goal on
   <6 h/wk at intake, before money changes hands)? WARN-only is proposed;
   order-safety suggests surfacing pre-purchase for custom plans.

---

## Sources

1. TP Unbound 200 Finisher/Beginner plan (8–12 h/wk):
   https://www.trainingpeaks.com/training-plans/cycling/gran-fondo-century/tp-599529/5-unbound-200-finisher-beginner-first-timer-plan-12-weeks
2. TP Gravel 100 plan (9–12 h/wk, "CTL over 50") / Gravel 200 Ultra
   (12–14 h/wk, "over 60"):
   https://www.trainingpeaks.com/training-plans/cycling/road-cycling/tp-285956/gravel-100-event-8-weeks-to-peak-classic-training-zones-9-12-hours-per-week ·
   https://www.trainingpeaks.com/training-plans/cycling/road-cycling/tp-281700/gravel-200-ultra-event-8-weeks-to-peak-classic-training-zones-12-14-hours-per-we
3. [H] Aggregator weekly-TSS bands (recreational 200–350, competitive
   amateur 400–600, serious racer 600–900, pro 800–1,200+), uncredited:
   https://roadmancycling.com/blog/training-load-ctl-atl-tsb-explained-cyclists
4. CTS (Carmichael), "What Is Chronic Training Load (CTL)":
   https://trainright.com/what-is-chronic-training-load-ctl-and-how-to-use-it-to-improve-performance/
   (also the road-racer 40–175 CTL across 6–25 h/wk spread)
5. Couzens, "What it Takes (Part II)" — 12,000 h behind a 9:30 IM ≈ 800
   h/yr × 15 yr; mid-pack ≈300–520 h/yr path; elite development 18–24
   h/wk: http://alancouzens.blogspot.com/2009/08/what-it-takes-part-ii.html
6. CTS on time-crunched amateurs "8 to 12 hours a week" summer norm:
   https://trainright.com/top-5-things-cyclocross-will-fitness/
7. Science to Sport, "Monitoring Training Load" — "70 TSS/day, for some
   competitive age group athletes, to as high as 140 CTL for pro tour
   riders": https://www.sciencetosport.com/monitoring-training-load/
8. T2M Unbound 200 16-wk plan (peak 19 h, 11-h long day):
   https://www.trainingpeaks.com/training-plans/cycling/gran-fondo-century/tp-319219/t2m-unbound-gravel-200-16-week-training-plan
9. Couzens, "CTL Ramp Rates" — "typical top age group CTL numbers of 150
   or so" (triathlon, multisport-summed); conservative ramp 3–5/wk:
   https://www.alancouzens.com/blog/CTLramp.html
10. [H] ProCyclingCoaching CTL calculator page (amateur 100–110, elite
    amateur 120–130, pro 140–150, post-Grand-Tour ~170; uncredited):
    https://www.procyclingcoaching.com/resources/fitness-ctl-calculator
11. [A] Keegan Swenson, The Hard Way podcast — "27, 28 hours?" per week:
    https://www.choosethehardway.com/episodes/keegan-swenson
12. Couzens chart via Triathlete — 9-hr IM cohort ≈ CTL 150, 10-hr ≈ 120,
    12-hr mid-pack ≈ 80 (multisport-summed; paywalled, numbers per search
    excerpt — verify before quoting externally):
    https://www.triathlete.com/training/how-many-hours-does-it-really-take-to-conquer-ironman/
13. [P] van Erp et al., IJSPP 2019 (4-yr pro road cohort;
    https://pubmed.ncbi.nlm.nih.gov/31722298/) + systematic review citing
    WorldTour ≈680–730 h/yr, 67–69% low-intensity:
    https://www.academia.edu/109640236/Training_Periodization_Intensity_Distribution_and_Volume_in_Trained_Cyclists_A_Systematic_Review
14. FasCat (Overton), "How to Peak for Cyclocross Nationals" — CX season
    CTL "low 60's", 66→53 taper, TSB +29:
    https://fascatcoaching.com/blogs/training-tips/peak-for-cyclocross-nationals
15. TrainingPeaks, "Chronic Intensity Load v. CTL" — CTL undervalues
    crit/CX/MTB interval load:
    https://www.trainingpeaks.com/blog/chronic-intensity-load-a-new-measure-of-training-load-based-on-intensity-factor/
16. Friel on TrainingPeaks, "Applying the Numbers Part 1: Chronic Training
    Load" (no universal target; 150 TSS/day "very high"; 5–8 CTL/wk):
    https://www.trainingpeaks.com/learn/articles/applying-the-numbers-part-1-chronic-training-load/
    · Friel, "The CTL Ramp Rate":
    https://joefrieltraining.com/the-ctl-ramp-rate/ · Friel, "Part 1:
    Chronic Training Load—So What?":
    https://joefrieltraining.com/part-1-chronic-training-loadso-what/

Repo: R1–R7 `docs/evidence/2026-08-23-wko-store-mining.md` · A1/B1
`docs/evidence/2026-08-23-couzens-corpus-mining.md` · AE-1.4/AE-1.5/
AE-2.10/AE-9.10 `docs/ALGORITHM_EVIDENCE.md`.


## ADDENDUM (2026-08-26, Matti-supplied source — supersedes the "TP refuses to publish" claim above)

**TrainingPeaks Help Center, "Suggested Weekly TSS and Target CTL"** (article
230904648, ATP setup guidance; table shipped as an image, transcribed verbatim
below). [E] — official TP support material. The earlier claim that TP refuses
to publish CTL targets was wrong for the ATP context: this is TP's own
published table, organized by EVENT TYPE with low–high envelopes (low ≈
finisher end, high ≈ elite end), not by performance tier.

| Event type | Weekly hours | Weekly TSS | Target CTL |
|---|---|---|---|
| **Cycling — Road Racing** | 6–25 | 290–1230 | 40–175 |
| Cycling — Century/Metric (≤6h, completion goal) | 6–15 | 290–740 | 40–105 |
| **Cycling — Gravel/Fondo/other (competitive or 6+ hours)** | **10–25** | **490–1230** | **70–175** |
| Cycling — MTB XCO | 6–20 | 290–980 | 40–140 |
| Cycling — MTB Marathon (3–6h) | 8–25 | 390–1230 | 55–175 |
| Cycling — MTB Ultra (6+h) | 8–25 | 390–1230 | 55–175 |
| Other (Nordic ski/rowing/multisport), A-race ≤3h | 6–18 | 290–880 | 40–125 |
| Other, A-race 3–8h | 8–22 | 390–1080 | 55–155 |
| Other, A-race 8+h | 10–25 | 490–1230 | 70–175 |
| Tri Sprint / Standard / Half / Full | 6–15 / 8–18 / 10–20 / 12–30 | 290–740 / 390–880 / 490–980 / 590–1470 | 40–105 / 55–125 / 70–140 / 85–210 |
| Run 5k–10k / Half / Marathon / Ultra (duration) | 4–15 / 6–18 / 8–18 / 10–20 | 220–820 / 330–990 / 440–990 / 550–1100 | 35–135 / 55–160 / 70–160 / 90–180 |

**Two load-bearing consequences:**
1. **Q1 answered by the source itself**: the table's internal arithmetic is
   ~49 TSS/hr at both ends (290/6, 1230/25) — TP's own feasibility constant is
   ~50 TSS/hr, agreeing with ratified Q6 (50), not the Cusick-implied ~65.
   AE-2.11's feasibility math uses 50.
2. **The competitive-gravel floor is now officially citable**: "competitive
   gravel" per TP = 10 h/wk, 490 TSS/wk, CTL 70 minimum. A national-level
   gravel goal on 5 h/wk fails TP's own published entry bar before our tier
   table is even consulted. The athlete-facing mismatch sentence can cite
   this directly.

**Reconciliation with the tier table above**: TP's event-type envelopes are
the outer bounds; the coach-published tier table (§1) tiers WITHIN those
envelopes. Both feed AE-2.11: envelope floor = hard mismatch line, tier band
= the goal conversation.

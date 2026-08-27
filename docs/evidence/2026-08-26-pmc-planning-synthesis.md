# PMC Planning Synthesis — CTL/ATL/TSB, Taper, Race-Day Form

**Date:** 2026-08-26. Synthesizes: `2026-08-26-pmc-web-mining.md` (PW-1..21, CR-1..10),
`2026-08-26-pmc-kb-mining.md` (Matti's positions, corpus R-claims, 4 guide
contradictions), `sources/atp-period-lookup.csv` (TP ATP state machine, 960
rows, analyzed structurally below), `sources/couzens-banister_MAD.ipynb`
(decoded + executed), `sources/cusick-training-load-webinar-notes.md`, and
`docs/ALGORITHM_EVIDENCE.md` AE-1.2/1.4/1.5/1.12/1.14. No code changed. Every
number below traces to a citation. Tiers: `[P]` peer-reviewed · `[E]`
expert-opinion · `[H]` heuristic · `[A]` anecdote · `[M]` model-derived.
Register: AE-9.10.

---

## 1. One-page verdict

**What we now know that we didn't this morning:**

1. Taper dose-response literature is now fully cited (Bosquet 2007 meta-analysis,
   Wang 2023 meta-analysis, Mujika & Padilla taxonomy, Thomas-Busso modeling) —
   this morning it was gap #2 in the kb-mining doc, totally absent from the
   corpus.
2. A derived, arithmetic-checked table connects taper duration + load-kept to
   %CTL-lost and TSB-at-race (PW-16) — closes kb-mining gap #3 (acceptable
   CTL bleed) with real numbers instead of extrapolating from AE-1.14's
   single-athlete heuristic.
3. Friel's ≤10% CTL-loss rule is now source-verified (his own blog, worked
   examples, event-scaled taper durations 12–21d) — not secondhand.
4. TP's ATP state machine is now reverse-engineered structurally: age-bound
   recovery cycle length, a Strong/Weak branch between A-races, a 32-week
   transition-context window, and a Preparation period gated on race history.
   Previously opaque.
5. The Couzens notebook is now decoded and run: it fits a 5-parameter Banister
   model (k1, k2, P0, τ_CTL, τ_ATL) via RMSE (the filename says "MAD"; the
   code is not MAD) against a sparse ~5-point textbook dataset. The optimizer
   converges to **boundary solutions** on 3 of 5 parameters — a live
   demonstration of Coggan's own warning that Banister fitting needs 20–200
   data points and is unstable below that (PW-7).

**What we still don't have:** a numeric race-day TSB target Matti has
personally ratified (his own writing gives shape, not a number — kb-mining
§a.1); a numeric intensity-retention threshold for a taper-shape compliance
check (flagged OPEN below); resolution of a genuine three-way TSB conflict.

**Where sources agree.** The +5..+25 race-day TSB band (Friel, Coggan,
Simmons, Fitzgerald, Zwift Insider, Roadman — PW-8/9/10) intersects Friel's
own ≤10% CTL-loss rule (PW-15) at a narrow, computable taper prescription:
**7–10 d at 50–60% load, or 14 d at 60–70% load** (PW-16, derived and
arithmetic-verified). This is the single most load-bearing number this
synthesis produces — six independent sources and one arithmetic derivation
converge on it.

**Where sources conflict — three sharp disagreements, not citation gaps:**

1. **Bosquet-optimal vs. Friel's 10% rule.** Bosquet's meta-analysis (PW-11,
   27 studies, `[P]`) finds the biggest performance effect size at **14 d,
   ~50% load kept**. Per PW-16's table that taper costs **14.3% CTL** and
   overshoots Friel's +25 TSB ceiling (+29.9). A peer-reviewed statistical
   optimum and a coaching heuristic point in different directions. This is
   the sharpest tension in the whole domain — flagging it, not resolving it,
   because resolving it is a coaching call (performance-optimal vs.
   fitness-conservative), not a research question.
2. **CX +29 counterexample.** Overton's CX Nationals case (loading-benchmarks
   doc, `[E]`) deliberately sits at TSB +29 / −20% CTL — above Friel's
   ceiling AND outside the 10% rule — and he calls it "crucial for
   cyclocross." Confirms AE-1.16 below needs an explicit event-class
   carve-out; +5..+25 and ≤10% are not universal physics, they're
   long-duration-endurance-event heuristics.
3. **Corpus TSB≈0 claim.** The WKO/Couzens corpus's own best empirical
   worked case for peak performance clusters TSB **near 0** (R58,
   kb-mining §b) — not +15..+25. This contradicts both the public guide's
   +15..+25 and Friel's optimum, and lands instead near the top edge of
   Coggan's own "−10..+10 = neutral" band. A real unresolved three-way
   disagreement (guide / corpus / Friel), surfaced as such below rather than
   silently picked.

---

## 2. Proposed rules, ratification-ready

House format matches `docs/ALGORITHM_EVIDENCE.md` §1. Numbered to extend
AE-1.x. None of these are ratified — all require Matti's yes (§6).

**AE-1.16 — Race-day TSB band by event class.** `[E][H][M]` A-race (gravel/
road, ≥3 h): acceptable band TSB ∈ **[+5, +25]**, target sub-band **[+15,
+25]**. Stage-race day 1: TSB ≥ **+10** preferred; within-block TSB
unconstrained by design (deep negative during the block is the point).
CX/short-format (<1 h, high-anaerobic): wider ceiling to ~**+29**, larger
CTL bleed acceptable — documented as a single event-class exception, **not**
folded into the general band (Overton CX Nationals case, verdict §1.2).
Consensus of 6 independent published sources: +5..+25, mode +15..+20
(PW-8/9/10; CR-1). Matti's own "very, very positive TSB" (SBT retro,
kb-mining §a.1) is directionally consistent — under-specifies rather than
contradicts.

**AE-1.17 — Taper prescription.** `[P][E][M]` Duration **8–21 d**, scaled to
event length (~12 d short A-race → ~21 d ultra, Friel PW-15). Daily load
**50–70%** of pre-taper average, exponential/progressive decay (beats
linear/step — PW-12, PW-13). Intensity and session frequency **held**, not
cut (PW-11, PW-13). Optional final-3-day opener bump **+20–30%** of taper-day
load (two-phase taper, Thomas 2009 PW-14) — **opt-in, not default**:
simulation-only evidence, open question in web-mining §PW-Q3. Entry-fatigue
scaling: pre-taper overload (≥110–120% of normal load) requires extending/
deepening the taper (Thomas 2008 modeled ~33 d at −49% after 28 d @ 120% for
elites — PW-14/CR-8). Taper depth and duration are a function of fatigue AT
TAPER START, never a fixed lookup.

**AE-1.18 — CTL-retention gate (reconciles/joins AE-1.14).** `[E][M]` Two
anchors, both checked, the tighter one binds:
(a) **AE-1.14 unchanged** — race-day CTL ≥ 90% of CTL at plan-build time
    (whole-plan gate; catches accidental detraining plans).
(b) **NEW** — race-day CTL ≥ 90% of CTL at taper START (peak CTL), i.e.
    taper-window CTL loss ≤ 10% (Friel PW-15).
(b) binds whenever the plan builds CTL meaningfully above its start point —
the normal case. Per PW-16, hitting CTL-loss ≤10% AND TSB ∈ [+15, +25]
(AE-1.16) simultaneously requires **7–10 d @ 50–70% load, or 14 d @ 60–70%**
— 14 d @ 50% and any 21-d taper hit the TSB target but blow the 10% cap.
Duration and load-retention are coupled, not independently chosen.

**AE-1.19 — TSB phase rails during build.** `[E]` Productive load/build
weeks: TSB ∈ **[−30, −10]** (Friel's "most effective training" zone, PW-8).
TSB < −30: at most a few consecutive days, ≤2–4 episodes/season. TSB < −20:
no more than **1-in-10 days** (Fitzgerald, PW-10). Minimize planned time in
the [−10, +5] grey zone outside taper/race weeks — neither productive nor
fresh (PW-8).

**AE-1.20 — ATL time-constant individualization policy.** `[E][M]` Default
τ_ATL = **7** (Coggan standard, PW-1). Categorical deviation only, **never**
per-athlete curve-fitting on <20–200 performance points (Coggan's own stated
minimum N, PW-7). The Couzens notebook is the cautionary evidence: fitting a
5-parameter Banister model against a sparse ~5-point dataset drives the
optimizer to boundary/degenerate solutions (k1 → 5.0 upper bound, τ_ATL →
10.0 lower bound, k2 → 4.51 near-upper) — a live illustration of exactly this
failure mode (§5 notebook detail). Deviation table: masters / high sustained
load / non-sustainable-power events → lengthen toward **10–12 d**; young /
low training load / sustained-power events (TT, climbing) → shorten toward
**4–5 d** (Coggan wattage-thread PW-5; FasCat's operational range 3–7,
PW-5). Caution: the chart is far more sensitive to τ_ATL than τ_CTL (Alex
Simmons, PW-5) — a deviation shifts absolute TSB and phase timing, not the
pattern. Any deviation from 7 must be logged as a plan-level assumption, not
silently applied.

**AE-1.21 — Age-based recovery cycle length.** `[H][M]` TP's ATP state
machine binds recovery cadence to age: **Over40 → 3-week cycle** (2 load
weeks + 1 recovery), **Under40 → 4-week cycle** (3 load weeks + 1 recovery)
— from the CSV's own header plus structural confirmation across all 8
transition contexts (§5 below). Refines, doesn't replace, AE-1.4's "≤8
CTL/week inside a loading block, 2–4 weeks max before a rest week": default
the block-length ceiling to 3 wk at age ≥40, 4 wk under 40, instead of
leaving it purely load-driven. Directionally consistent with AE-1.5's
existing age-50 CTL-band haircut (older = tighter ceiling) — but TP's
cutoff is 40, not 50. Flagging the mismatch, not silently harmonizing it.

**AE-1.22 — B/C race TSB band.** `[H]` B/C race-day TSB ∈ **[−10, 0]** —
train through, no CTL sacrifice, no taper week/phase (Zwift Insider PW-10,
FasCat PW-20; consistent with AE-1.9's existing "no taper WEEK/PHASE"
ruling). Secondary-source only — weakest citation tier in this rule set.

**AE-1.23 — Multi-peak season limits.** `[E][M]` ≤3 A-priority peaks/season
(Friel PW-19), spaced several weeks apart. AE-1.9's existing "warn at 3+" is
already more conservative and is **unchanged** by this rule — AE-1.23 adds
the spacing and bleed numbers AE-1.9 lacks. Never >2 consecutive peaking
weeks. Cumulative CTL loss across back-to-back peaks ≤ **13%** (Friel's own
accepted worked case, PW-15/19). Cross-ref: TP's own transition-context
window tops out at **32 weeks** between A-races (PW-21, confirmed against
the CSV — PriorA/PriorB1 contexts, which run to 48 wk, only apply beyond
that window). Adopt 32 wk as the outer bound past which "between A-races"
rebuild logic no longer applies and the plan is a fresh prep.

---

## 3. ae-lint gate extension spec (spec only, no code)

Grounded in the live gate at `athletes/scripts/ae_lint.py`: `lint_ctl_trajectory`
(lines 231–264) already walks a 42-day CTL recurrence day-by-day from
`current_ctl` through race day using `_daily_tss`, is silent unless armed via
`--race-date`/`--current-ctl`, and reuses `CTL_TAU_DAYS = 42`. This spec
extends that exact pattern.

1. **New function `lint_race_day_tsb`**, same shape as `lint_ctl_trajectory`.
   Reuses `_daily_tss`. Adds a parallel ATL walk with a new
   `ATL_TAU_DAYS = 7` constant (AE-1.20 default). `TSB(race) = CTL(race) −
   ATL(race)`.
2. **New CLI flag `--current-atl`**, parallel to the existing
   `--current-ctl`. If `--current-ctl` is supplied without `--current-atl`,
   default `current_atl = current_ctl` (TSB = 0 at plan-build time) — an
   explicit, logged ASSUMPTION in the finding output, never a silent
   default.
3. **FAIL condition** (A-race context only — infer from payload race-priority
   metadata if present, else assume A-race when `--race-date` is given
   without a qualifier): TSB(race) outside **[+5, +25]** (AE-1.16). A new
   `--coach-override` flag downgrades FAIL → WARN with the override reason
   logged. New rule tag `"AE-1.16"` in the existing finding schema
   (`{"day", "title", "severity", "rule", "msg"}`).
4. **New function `lint_taper_shape`.** Given `--race-date`, take the taper
   window as 10–21 d before race (default 14 d unless the plan declares
   otherwise). Two checks:
   a. **Volume decay** — via the existing `_weekly_totals` helper: weekly
      TSS inside the window must be monotonically non-increasing, except
      one allowed final-3-day bump ≤30% (AE-1.17 opener).
   b. **Intensity retention** — via the existing `_hard_seconds`/
      `_vo2_seconds` helpers (already present, lines 101/111): hard-seconds
      per week inside the taper window must not drop below X% of the
      pre-taper week. **No source in this evidence base gives a number for
      X.** Proposing X = 70% as a starting point (directionally supported by
      "intensity held" language in PW-11/PW-13, which is qualitative) —
      flag OPEN, Matti to set or reject.
5. Both new checks are opt-in and silent (`return []`) unless their inputs
   are supplied — matches the file's existing silent-unless-armed design
   exactly (`lint_ctl_trajectory`, `lint_demonstrated_dose`).

---

## 4. Guide fix list

All four are PUBLIC-FACING (`gravel-race-automation/guide/gravel-guide-content.json`).
**Matti's yes required before any copy ships** — per standing governance,
never publish public content without it.

1. **Race-day TSB target (L1392: "+15 to +25").** Previously uncited and
   contradicted by the corpus's TSB≈0 case (R58) and unspecified by Matti's
   own writing. Correction: this number turns out to be directionally
   supported (AE-1.16's target sub-band is the same +15..+25) — but ship it
   only once AE-1.16 is ratified with its citation, and only with the CX/
   short-format exception called out separately so the guide doesn't imply
   one band fits all events. The corpus TSB≈0 case is a different context
   (worked individual case, not a general rule) — note it, don't let it
   silently override a properly event-class-scoped number.
2. **10-day taper openers (L2930: 3×5 min AT THRESHOLD)** — violates AE-1.12's
   hard-content cap (no ≥92%-FTP rep >120 s; ≤15 min total ≥92% per session).
   Correction: cut to ≤120 s reps, ≤15 min total ≥92%-FTP work per session —
   align with the pipeline's own generated openers (4×15–30 s), which already
   comply.
3. **"Your CTL is peaked" race-week copy (L2854)** — contradicts AE-1.2 (peak
   CTL lands 8–12 wk before race, then flat-lines). Correction: rewrite to
   the ratified shape — CTL flat-lined weeks ago; today's freshness is TSB
   rising, not CTL rising. Also fix the periodization chapter's week-10–11
   framing, which draws CTL still climbing into the taper.
4. **Base ramp "+3-5 CTL/wk" (L1384)** — equals ~13–21 CTL/month, exceeding
   AE-1.4's ≤10 CTL/month net cap (within-week ≤8 is fine; the monthly net is
   the binding constraint the guide ignores). Correction: rewrite to
   "+2–3/wk sustained, capped at 4 consecutive weeks" — matches the ≤10/month
   net cap.

---

## 5. The ATP-table adoption question

Structural findings from `atp-period-lookup.csv` (960 rows, 8 transition
contexts × {S,W,SW} × {Over40,Under40} × 1–48 weeks-to-race), verified by
direct extraction, not eyeballing:

- **8 contexts**: PriorA, PriorB1, A-A, A-B, A2-A3, A2-B, B-A, B1-B2 — first-
  ever-race-of-type (Prior*) vs. race-to-race transitions.
- **Age binds recovery cycle length directly**, confirmed structurally: Over40
  rows use week-labels {1, 2, 4} (skip 3) = 3 calendar weeks per block;
  Under40 rows use {1, 2, 3, 4} = 4 calendar weeks per block. Matches the
  CSV's own header claim exactly.
- **Peak period never exceeds 2 weeks**, in every one of the 960 rows,
  including 48-week runways.
- **A-B, A2-B, B1-B2 (destination = B-race) never include a Peak period** —
  structurally enforces "no taper phase for B-races" (matches AE-1.9).
- **A-A "Weak" inserts a Base 3 block before Build; "Strong" skips straight
  to Build** — confirmed at identical weeks-to-race (verified at 9–16 wk):
  the S/W branch is a real, gated structural difference, not commentary.
- **A-A/A-B/A2-A3/B-A contexts cap at 32 weeks-to-race**; beyond that the
  lookup falls through to PriorA/PriorB1 (max 48 wk), which alone contain a
  "Preparation" period. Matches PW-21's "A-races must be within 32 wk of
  each other."

**Adopt:**
- Age-based recovery cycle length (3 wk Over40 / 4 wk Under40) — AE-1.4/1.5
  have no equivalent; genuine gap, folded into AE-1.21 above.
- The Strong/Weak branch point between A-races (rebuild-base-first vs.
  straight-to-build) — AE-1.9 currently only *mentions* this qualitatively
  (via PW-21); TP gates it structurally. Recommend making it an explicit,
  gated rule rather than prose.
- The 32-week transition-context window as the outer bound for "between
  A-races" rebuild logic (folded into AE-1.23) — currently AE-1.9 has no
  such bound; annual-macro features are formally PARKED per ruling Q11, so
  this is adopt-when-unparked, not immediate.

**Adapt (not contradiction, terminology mismatch):**
- TP's rigid 1–2-week "Peak" period name vs. AE-1.1's "peak 3–6 weeks,
  front-loaded." These likely describe different spans — TP's named "Peak"
  period is probably the tail of what AE-1.1 calls "peak" (Build 2 + Peak
  together ≈ AE-1.1's 3–6 wk figure). Recommend clarifying the mapping
  rather than treating the week-counts as conflicting evidence.

**Reject:**
- TP's Preparation-period-gated-on-race-history as a hard import. AE-1.2's
  stabilization phase is a *deliberate* divergence (load-based trigger,
  fires for any 12+ week prep regardless of prior-race history) — importing
  TP's history-gated trigger would silently undo that ratified choice. Keep
  AE-1.2 as-is.

**Couzens notebook (`sources/couzens-banister_MAD.ipynb`, decoded from
base64, executed).** Fits `Performance = P0 + k1·CTL − k2·ATL` via
`scipy.optimize.minimize`, loss = RMSE (not MAD, despite the filename) against
a 35-day toy dataset with only ~5 real performance points. Bounds: k1, k2 ∈
(0,5); P0 ∈ (100,300); τ_CTL ∈ (20,60); τ_ATL ∈ (10,20) — notably Couzens'
own floor for τ_ATL (10 d) sits *above* Coggan's stated default (7 d) and
above the low end of Coggan's own individualization range (4–5 d, PW-5). The
optimizer converges to k1 = 5.0 (upper bound), τ_ATL = 10.0 (lower bound),
k2 ≈ 4.51 (near-upper) — three of five parameters pinned to their bound
edges. This is not evidence *for* a specific individualized constant; it's a
worked demonstration of Coggan's own instability warning (PW-7) and directly
supports AE-1.20's "categorical deviation only, never curve-fit on sparse
data" stance.

---

## 6. Questions for Matti (max 5, hardest first)

1. **Ratify AE-1.16** — race-day TSB band [+5,+25], target [+15,+25] for A
   gravel/road, CX/short exception to ~+29 — over the corpus's near-0 worked
   case (R58) and your own unnumbered "very, very positive"? This is the
   single most athlete-visible, most contested number in the whole domain.
2. **CTL-retention reconciliation (AE-1.18)** — adopt the dual-anchor gate
   (current-CTL AE-1.14 stays; add a peak/taper-start ≤10%-loss check)? And:
   does the 10% cap flex by event duration (7–10 d @ 50–60% vs. 14 d @
   60–70%, per PW-16), or is it a flat 10% regardless of taper length?
3. **ATL individualization (AE-1.20)** — keep τ=7 fixed for everyone, or
   adopt the categorical deviation table (age/load/event-type, bounded
   4–12 d)? Given the Couzens notebook's own instability demonstration,
   per-athlete curve-fitting is off the table either way — this is fixed-
   default vs. categorical-table only.
4. **Age-based recovery cycle (AE-1.21)** — adopt TP's 3wk-Over40/4wk-Under40
   split as a refinement of AE-1.4's "2–4 week" range, or keep it purely
   load-driven as now? Also: TP's cutoff is 40, AE-1.5's existing haircut is
   at 50 — harmonize, or keep as two independent age thresholds?
5. **Guide fixes (§4)** — approve rewriting the public gravel guide's PMC
   chapter to the ratified numbers (TSB band, taper openers, "CTL peaked"
   language, ramp rate)? All four corrections are ready to ship pending this
   yes.

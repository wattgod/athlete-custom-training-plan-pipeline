# Pipeline + intake findings from order `cs_live_a12JPpqG…` (Monika Renk, 2026-08-04)

Every item below is a defect observed on a **real paid order**, not a
hypothetical. The delivered package was unusable and had to be rebuilt by hand.
Ordered by what would most reduce babysitting per order.

Source of truth for the raw answers:
`/data/.intake/14478914-e6cd-47d9-85bc-c37c5038fa29.json` on the Railway volume.

---

## P0 — Fabricated data presented as fact

### 1. The pipeline invents an FTP and marks it only with a quiet flag
She submitted `ftp: ""` and `powerOrHr: "hr"`. The profile came out with
`ftp_watts: 127, ftp_estimated: true`, and every one of the 34 ZWO files plus
the staged `tp_manifest.json` was anchored to it. 127 W is 2.15 W/kg for a 45F
who rides 7–10 h/week and wants to compete — implausible on its face.

`ftp_estimated: true` exists but gates nothing. Nothing downstream reads it, the
coaching brief prints "FTP | 127W (2.15 W/kg)" as though it were measured, and
the plan ships.

**Fix:** an estimated threshold must be a *blocking* condition, not a flag. Either
(a) refuse to emit percentage-of-FTP structures and emit RPE/HR-anchored ones
instead, or (b) route the order to BLOCKED_REVIEW. This is exactly what J1's
state machine in `plan-ir-v0` is for — it is written and unmerged.

### 2. Equipment fields are fabricated boilerplate
Profile carried `devices: [power, meter, hr, strap]` — the strings "power meter"
and "hr strap" whitespace-split into four tokens — while simultaneously setting
`power_meter_bike: false` and `hr_monitor: false`. None of it came from her; the
form never asks. Anything not asked should be absent, never defaulted to a
plausible-looking value.

### 3. Race provenance is recorded and then ignored
The profile carried `race_provenance_issue: "Race facts have no recorded source
URL and source type."`, `verified_at: null`, `source_urls: []` — and shipped
anyway. H1 in `plan-ir-v0` makes this BLOCKED_REVIEW. Unmerged.

---

## P0 — Intake form gaps that forced guesses

| Missing question | What went wrong without it |
|---|---|
| **Do you ride with a power meter?** | Never asked. The pipeline inferred power capability and invented an FTP. |
| **Which course/distance are you registered for?** | Free-text miles only. She typed `75`; Mammoth has no 75. The real options are ~41/67/89, and UCI banding puts 19–49 on the 89 and 50+ on the 67 — so her age makes the answer genuinely ambiguous. Should be a **select populated from the race record's course list**. |
| **What elevation do you live/train at?** | Never asked. For an 8,000 ft race this is the single biggest planning input. |
| **What have your last 4 weeks looked like?** | `hours_per_week` is availability. There is no field for *recent completed* load, so ramp rate is unverifiable. |
| **Do your stated hours include strength?** | She does 2×/week and declined programming. The plan peaks at 9h30 riding against a stated 10 h ceiling — if strength is inside that, it is over. |
| **Which platform account should we deliver to?** | Her TP account existed, was dormant since 2019, and carried stale thresholds and a wrong birthday. Nothing checks the destination account's health. |

`longest_ride` **is** captured (`4-5hrs`) and is arguably the most important
number on the form for a long-course race — it is not used anywhere in plan
shaping. The race was at her all-time ceiling and nothing flagged it.

---

## P1 — Plan generation defects

### 4. Stated schedule is inverted
Form: `long_ride_days: [Mon, Tue, Sun]`, `interval_days: [Wed, Thu]`. Generated
plan put intervals on Tue **and** Sun — four interval days a week (Tue/Wed/Thu/Sun).

The root confusion: three "long ride days" inside a 7–10 h week is
arithmetically impossible, so those lists are *availability*, not intent. The
builder treats them as intent. Either rename the fields on the form
(`which days could you ride long?`) or teach the builder to reconcile the lists
against the weekly hour budget and fail loudly when they cannot all be honoured.

### 5. Structural holes in a 6-week plan
- **No race-day workout at all** for 2026-09-19.
- Race week contained only Tue and Thu.
- Two FTP tests in W1 (Thu 08-13 *and* Sun 08-16).
- "Openers" mid-BUILD in W4.
- Two W00 workouts dated 08-04 and 08-05 — **in the past at delivery time**.
- 34 files for six weeks at 7–10 h.

The 11 CRITICAL compliance rules did not catch any of these. Whatever gate ran,
"plan has a race day" and "no session is dated before delivery" are not in it.

### 6. Weeks paid ≠ weeks delivered
`computed_weeks: 7` / `computed_price_cents: 10500`, plan generated as six. No
reconciliation between what pricing sold and what generation produced.

### 7. Goal drift and stale rationale text
`goal: "compete"` became `goal_type: "podium"`, while the same brief said
"Finish goal → favor endurance/durability" and cited **"200mi event favors
Polarized, MAF, HVLI"** for a 75-mile race. Row 3 called a 10+ year rider
"Beginner-friendly methodology". These are template strings not bound to the
athlete's actual values.

### 8. Generic fuelling table pasted into a short plan
Gut-training progression printed "BASE weeks 1-6 / BUILD 7-14 / PEAK 15-18" into
a **6-week** plan, with a race-day row of 70–90 g/hr contradicting the plan's own
prescribed 58 g/hr. Same contradiction class sol caught on Heather v6. G1/G2 in
`plan-truth-fixes` addresses the number; the *table* is separately hardcoded.

---

## P1 — Tooling

### 9. `build_tp_bodies.py` hardcodes `percentOfFtp`
Line 118, with a docstring implying it is TP's only option. **Verified live**:
TP accepts `percentOfThresholdHr`, `percentOfMaxHr`, `rpe` and
`percentOfThresholdPace` equally — all POST 200 and round-trip intact. Only
`heartRate` is rejected. For HR-only athletes this is the difference between a
real prescription and a fabricated one. Parameterise the metric.

### 10. `compute_polyline` overshoots normalised time
Observed x up to **1.004** (and non-monotonic) on four of 46 workouts — enough to
draw a small backward tail in TP's graph. Shared, byte-identical between
`gravel-god-training-plans/tools/tp_polyline.py` and this repo, so the golden
fixture in both is encoding the bug. Clamp to `[0,1]` and force monotonicity.

### 11. Race day should never carry a structure
A structured range block syncs to a head unit as an executable target, and TP
resolves a range to its midpoint on devices that cannot show ranges — turning
race day into a five-hour ERG instruction. Race entries need duration + TSS
estimate + prose only.

### 12. `/api/intel-stats` is hardcoded to 24 hours
`webhook/app.py:3312`. There is no way to ask "what were the last N orders"
without SSHing to the Railway volume and reading `.logs/*.jsonl` by hand. Add a
`?hours=` or `?limit=` parameter — this is the only read path onto the order
ledger and it cannot answer the most common question.

---

## P1 — The altitude section silently did not fire

### 12b. An 8,000 ft race shipped a guide with no altitude section
`_conditional_triggers` fires altitude on `start_elevation_asl_ft > 5000`.
`mammoth-tuff.json` carries `start_elevation_asl_ft: 8100`. Regenerating her
guide locally from the same athlete data produces **section 15, Altitude
Training** (and Heat Training). The guide delivered to her had neither — 15
sections ending at Masters.

So the race data did not resolve at generation time on Railway. `_flatten_race_data`
carries a docstring noting that before it existed "the altitude section silently
never fired for any race, mountain or not" — this looks like the same class of
failure returning by a different route (race JSON not present or not resolvable
in the container). Worth an assertion: if a race record resolves with
`start_elevation_asl_ft > 5000` and the altitude section is absent from the
rendered guide, fail the build rather than ship it.

## P2 — Race data

### 13. `mammoth-tuff.json` is single-course
Carries TUFFEST (89 mi / 7,500 ft) as the race's headline vitals with no
per-course breakdown, so her 75 mi got paired with the 89-mile course's
elevation. Multi-distance events are the norm in gravel; the schema needs a
`courses[]` array with distance, elevation and any category/age banding, and the
intake form should select from it. `validation_status: "pending"` and
`sources: ["cursor_web_search"]` on a race we are actively selling plans for.

---

## What this adds up to

The engine is not the problem — the block-builder produced coherent sessions.
Every failure above is at the **boundaries**: what we ask, what we do when the
answer is missing, and whether anything refuses to ship when a required input
was guessed rather than given.

The single highest-leverage change is J1's fulfilment state machine, already
written on `plan-ir-v0`: an order whose plan rests on a fabricated threshold, an
unverified race, or an unmatched course should reach the coach as
ACTION-REQUIRED and never reach the athlete. That one change would have caught
items 1, 3 and most of 5 on this order.

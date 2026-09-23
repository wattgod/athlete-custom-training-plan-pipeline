# Proposal: the AE-2.1 hard-minutes floor for low-frequency athletes

Status: **PROPOSED, needs a ruling from Matti.** Nothing here is implemented.
Opened 2026-09-23 from the 2026-09-22 custom-plan order. Extends the open
contradiction §12 C2 in `docs/ALGORITHM_EVIDENCE.md`.

## What happened

A paying athlete, time-crunched, riding 2-3 days a week (~75 mi, about
5 h), lifting kettlebells three days a week, back from a crash and
concussion, asked for "a structured plan that will not leave me over trained
and blasted all the time." His 34-week plan came back from the review gate
with 26 `HARD_MINUTES_BELOW_FLOOR` warnings (5-44 hard minutes per load
week against 90) and an `R05` critical on every load week (1 intensity
session, gate wants 2).

The PR that carries this file fixes one place where the gate applied a
rule more broadly than the rule is written: **AE-2.1 is scoped to athletes
training at least 6 h/wk.** The gate applied it to everyone; it now skips
athletes whose stated weekly hours are under 6.

Three decisions are left for Matti:

1. **Decision 1:** the AE-2.1 floor for athletes at 6 h/wk or more who have
   only 2-3 riding days (the main body of this proposal).
2. **Decision 2:** whether R05 allows one quality day on low-availability
   calendars. It is not changed in this PR.
3. **Decision 3:** what "maximal" means in the unresolved-pain gate.

## The rules involved

| Rule | Tier | What it says | Citations |
|---|---|---|---|
| AE-2.1 | Matti-authored | 90-120 min at >=92% FTP per load week for athletes at >=6 h/wk; below ~90, VO2max gains are "small and inconsistent"; day cap novices 2, mature 3 | "The 80/20 Trap"; R19; F3 |
| AE-2.2 | Matti-authored | Intensity share scales inversely with hours, ~70/30 at 7 h/wk, measured by time in zone ("hard" = everything above Z2) | WG "80/20 Trap", "Peter Attia" draft; D4 |
| AE-2.3 | E | Polarized is about 1-2 hard days; pyramidal 2-3 | R86; F4; J1 |
| AE-2.6 | H | VO2 maintenance every 14 days stands, even in base | R36, R54 |
| AE-3.1 | P, M | A VO2 session carries 5-18 min at >=106% FTP | WG FUNDAMENTALS + scorecard; R14, R93-R95 |
| R05 | registry, ACTIVE/CRITICAL | 2-3 intensity sessions per load week; training age <1 or <=3 available cycling days allows 1-3 | `docs/SPEC_EARNED_SELECTION.md` A3.6 |
| R01 | registry, ACTIVE/CRITICAL | No back-to-back intensity days | same |
| Long-ride buffer | house pattern, not an AE rule | Intensity days are never placed next to the long ride unless the athlete asked for that | `CLAUDE.md` ("Intensity days prefer Tue/Thu") |

## Decision 1: why 90 minutes is out of reach for these calendars

The floor counts minutes at or above 92% FTP.

- A VO2 day is capped by AE-3.1 at 18 minutes at or above 106%. Counting
  the sub-106% reps, a VO2 day lands around 15-25 hard minutes.
- A threshold day at 95-100% can carry 40-45 minutes (2x20, 3x15).
- With two quality days the only way to 90 is two long threshold days
  every load week, which leaves no room for the VO2 touch AE-2.6 requires
  every 14 days.
- With one quality day the ceiling is roughly 45-60 minutes unless the long
  ride itself carries threshold blocks.

The generator's output bears this out. A synthetic athlete with three
riding days (Tue/Thu/Sat, so two quality days fit), 34-week plan, hard
minutes per load week as the gate measures them:

| Stated hours | Load weeks under 90 | Hard minutes (min / median / max) | Floor applies? |
|---|---|---|---|
| 5 h/wk | 26 of 26 | 6 / 24 / 77 | No: AE-2.1 starts at 6 h. The gate flagged these before this PR. |
| 7 h/wk | 26 of 26 | 6 / 20 / 54 | Yes, and every load week fails |

The 7 h row is the conflict. It is the same finding §12 C2 records for
Judd, Forest and Steve (10-24 hard minutes per load week): the floor is
not being met anywhere, and on a two- or three-ride week it cannot be met
without every ride being hard.

AE-2.2 does not settle it. Its 30% "hard" at 7 h is 126 minutes, but that
share counts tempo and sweet spot. AE-2.1 counts only work at 92% FTP and
up. The two rules use different rulers.

## Decision 1: options

**A. Scale the floor by how many quality days the calendar can hold.** For
example, 45 minutes per quality day, capped at the current 90-120 band. The
floor bends with the schedule and still bites when the schedule has room.
Cost: 45 is a new number that needs evidence and a ruling. It also lets a
plan with one short quality day pass as compliant.

**B. For athletes with 3 or fewer riding days, replace the weekly warning
with one plan-level coach confirmation.** For example: "Low-frequency
athlete: the AE-2.1 floor is not reachable at N riding days. Confirm the
intensity dose." Measure everyone else over a rolling two-load-week window
(180 minutes) so one light week does not flag. Cost: the per-week signal
goes away for low-frequency athletes, and AE-2.1 would need a
low-availability line. Ideally it is the same line Decision 2 draws for
R05, so the two rules agree on who counts as low-frequency. That is a
ruling, not a code change.

**C. Keep the floor and make the generator reach it.** Put 92%-plus blocks
into the long ride and allow a second quality day next to the long ride.
Cost: it overrides the house long-ride buffer, goes against AE-2.3's 1-2
hard days for polarized weeks, and does the opposite of what this athlete
asked for. For someone coming back from a concussion that is hard to
defend.

**Recommendation: B.** The floor's evidence is about VO2 gains in athletes
who can absorb 90+ hard minutes. For a two- or three-ride week the useful
decision is the coach's, made once per plan, not 26 warnings that get
waived by reflex. The testing-week half of §12 C2 still needs its own
ruling. Option B does not settle it.

## Decision 2: R05 on low-availability calendars

The order's other repeated blocker was `R05` on every load week: "1
intensity (need 2-2)". The generator placed one quality day because, with
three riding days and a Saturday long ride, the only way to a second one
is to put it next to the long ride (the house buffer) or the day after it.
That makes every ride hard, for an athlete who asked not to be blasted.

What the documents say:

- **Ratified:** only AE-2.1's migration note. It calls R05 the active
  registry rule and says changing it needs "an R05 revision (owner review
  + version bump per registry rules)".
- **Draft:** `SPEC_EARNED_SELECTION.md` (DRAFT r6), A3.6, R05 row, target
  column (`algorithm_since: E3`): "training age <1 or <=3 available
  cycling days allows 1-3".
- **Frozen production verdict:** the same spec's A3.0 keeps production
  R05 at `min(2, max_intensity)..max_intensity` until the E3 cutover.
  That is what `block_compliance.r05_intensity_count` does.

The first version of this PR implemented the draft clause. Review caught
that it was a rule change, and it was reverted. The parity tests now assert R05 fires on the
Thu/Sat/Sun fixture, marked as pending this decision.

Options:

- **A. Adopt the registry clause now (<=3 available cycling days allows
  1).** This fixes the order's layout. It does not fix four available
  days with a Saturday long ride (for example Wed/Thu/Fri/Sat): R01 and
  the long-ride buffer still leave one quality slot, so the generator
  schedules one and R05 still wants two.
- **B. Count quality-eligible days instead of available days.** A
  quality-eligible day is an available day that is neither the long ride
  nor next to it. Allow 1 when there is only one such day. This covers
  the 4-day case and says what the 3-day clause is trying to say.
- **C. Keep R05 at 2 and let the generator put a quality day next to the
  long ride** on low-availability calendars. This breaks the house buffer
  and goes against the athlete's request.

**Recommendation: B.** Either A or B needs the R05 revision (owner review
and a version bump) that AE-2.1 names.

## Decision 3: what the pain gate calls "maximal"

`UNRESOLVED_PAIN_MAX_PRESCRIPTION` treats any structured step at or above
105% FTP as "maximal". That covers every VO2 session, the race simulations
and the race-week openers. R02 (VO2 every 14 days, critical) and the
race-week opener and activation checks require exactly those sessions. So
for an athlete with injury text, the gate fires on most of the plan, and
the generator cannot fix that without breaking R02.

Intake also marks any non-"none" current-injury answer `status: active`,
so "broke my wrist in 2023, fully healed and cleared" reads as unresolved
pain.

What this PR does, and does not do:

- It leaves off only the mid- and late-plan FTP retests, and only when the
  injury text says nothing about being healed, cleared or resolved. No
  deliverable surface promises a retest.
- The Week 1 re-anchor, which the profile, canonical model, TP manifest
  and guide all promise, stays scheduled.
- The gate still fires as before, so the coach decides.

Options:

- Ask a clearance question at intake: cleared by a clinician, and when?
- Define "maximal" as RPE 9 or higher, all-out efforts, sprints and tests,
  not 105% FTP.

Recommendation: both.

## Known gap: VOICE_CONTRACT on long plans

The weekly-note phrase pools are sized for plans of roughly 12-16 weeks.
The position lines ("Last load week of this block.", "Back into peak with
fresh legs.") recur every block, and the notice pool wraps. A 34-week plan
repeats about 32 sentences, so `VOICE_CONTRACT` fires on every long plan.

This PR now reports all the repeats in one finding. Before, only the last
one reached the coach. It does not remove the repeats: dropping them left
11 of 36 Monday notes as a bare "Week N of M." The fix is more phrasings,
which is copy work under `docs/AI_WRITING_POLICY.md`. Until then, the
finding keeps firing on long plans.

**Blocked on:** Matti.

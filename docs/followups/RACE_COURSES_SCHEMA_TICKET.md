# Ticket: per-course race records (`courses[]`) and course-level matching

- Status: filed; blocks nothing in SPEC_TRUSTWORTHY_FULFILMENT (the interim
  control there is a **non-waivable** `COURSE_UNRESOLVED` blocker whose only
  remediation is a facts-omitted regeneration — plan/guide rebuilt from
  athlete-supplied facts only), but must land before course-specific facts
  can anchor plans without coach verification.
- Owner: pipeline
- Origin: Monika Renk order — `mammoth-tuff.json` carries TUFFEST
  (89 mi / 7,500 ft) as headline vitals with no per-course breakdown, so her
  stated 75 mi was paired with the 89-mile course's elevation
  (`docs/MONIKA_RENK_PIPELINE_FINDINGS.md` finding 13). The slug matched at
  1.0, suppressing `RACE_UNMATCHED`, and provenance was the only remaining
  guard.

## Problem

Race snapshot records are one-record-per-race. Multi-course events (short/
medium/long) cannot be matched at the course level, so an athlete's stated
distance silently inherits the headline course's distance, elevation, and
demand facts.

## Required work

1. Schema: add `courses[]` to the race record — per course: name, distance
   (km+mi), elevation (m+ft), and optionally surface/timing facts; headline
   vitals become a designated course, not free-floating fields.
2. Matching: intake distance/category resolves to a specific course; no
   match → `COURSE_UNRESOLVED` persists (it is not removed by this ticket —
   it stops firing when resolution succeeds).
3. Enrichment: backfill multi-course events, starting with events appearing
   in paid orders.
4. Regression fixture: a verified-provenance, multi-course event where the
   athlete's distance matches a non-headline course — asserts the plan and
   guide carry that course's facts, independent of `RACE_STALE`.

## Acceptance

- The Monika replay fixture ("athlete-m") resolves its 75 mi intake to the
  correct course once the event is backfilled, and `COURSE_UNRESOLVED` no
  longer fires for it.
- No course-specific fact reaches a plan or guide from an unresolved match.

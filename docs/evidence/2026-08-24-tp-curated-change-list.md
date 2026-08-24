# TP-curated library — ratified-standards change list

**Generated:** 2026-08-24 against `athletes/config/tp_library_index.json.gz`
(1459 selectable items, 24 libraries) via `tp_library_snapshot.load_index()`.

**Status: REPORT ONLY.** Nothing in this document has been applied to the
coach's TrainingPeaks library or to the index. This is the audit deliverable
for workstream 4 of the cadence-emission task (see docs/ALGORITHM_EVIDENCE.md
AE-2.7, AE-2.8, AE-3.11, AE-6.3) — Matti reviews and dispositions each row;
none of these rows were acted on by this pass.

## Method

- **(a) Endurance-class band violations** — items in `library_key` ∈
  {endurance_z2_long, endurance_z2_short, endurance_with_work} (202 of the
  1459 selectable items) with `if_planned` outside the ratified .60–.70
  band, or a computed `tss / (duration_min/60)` over the AE-2.8 50 TSS/hr
  ceiling.
- **(b) Session floor** — any rideable item (excludes `recovery` and
  `testing_openers` library keys, the two structurally exempt classes) with
  `duration_min` under the AE-2.7 45-minute floor.
- **(c) Purge-list names/descriptions** — case-insensitive match for
  `fatmax`, `fartlek`, or `fasted` in the item's raw TP name or description
  (AE-3.11 name purge, AE-6.3 fasted-riding purge).

An item can appear in more than one category (its full violation list is
shown once); **proposed action** takes the highest-severity verdict across
all categories it hit (retire > fix-at-TP-source > exempt-with-reason).

## Summary

| Category | Items flagged |
|---|---|
| (a) endurance IF/TSS-per-hr | 100 |
| (b) under 45-min floor | 90 |
| (c) purge-list name/description | 16 |
| **Total unique items flagged** | **188** |

Proposed-action totals: 15 retire,
173 fix-at-TP-source,
0 exempt-with-reason.

## (a) Endurance-class band violations (100)

| item_id | name | duration | IF | violation | proposed action |
|---|---|---|---|---|---|
| 14355808 | Endurance - Aerobic loaded Sprints - ref - 87min - RPE10 | 87min | 0.70 | IF 0.70 > .70 ceiling | fix-at-TP-source |
| 14355811 | Endurance - Optional - Keep the legs turning - ref - 36min - RPE10 | 36min | 0.84 | IF 0.84 > .70 ceiling; 70.0 TSS/hr (>50 cap, AE-2.8); 36min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355816 | Endurance - Workout - ref - 60min - RPE3-4 | 60min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355821 | Endurance - + - 3 - 180min - RPE5-6 | 180min | 0.74 | IF 0.74 > .70 ceiling; 54.5 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355825 | Endurance - Workout - ref - 150min - RPE3-4 | 150min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355829 | Endurance - Dark is the Night - 1 - 90min - RPE7-8 | 90min | 0.78 | IF 0.78 > .70 ceiling; 60.1 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355830 | Endurance - Dark is the Night - 2 - 112min - RPE7-8 | 112min | 0.80 | IF 0.80 > .70 ceiling; 63.6 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355831 | Endurance - Dark is the Night - 3 - 137min - RPE9-10 | 137min | 0.82 | IF 0.82 > .70 ceiling; 67.4 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355833 | Endurance - Workout - ref - 180min - RPE3-4 | 180min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355834 | Endurance - Workout - ref - 300min - RPE3-4 | 300min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355835 | Endurance - Workout - ref - 360min - RPE3-4 | 360min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355836 | Endurance - Workout - ref - 45min - RPE3-4 | 45min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355837 | Endurance - Workout - ref - 210min - RPE3-4 | 210min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355838 | Endurance - TT Base - - 1 - 65min - RPE3-4 | 65min | 0.60 | IF 0.60 < .60 floor | fix-at-TP-source |
| 14355839 | Endurance - TT Base - - 2 - 90min - RPE3-4 | 90min | 0.72 | IF 0.72 > .70 ceiling; 52.5 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355840 | Endurance - TT Base - - 3 - 120min - RPE3-4 | 120min | 0.72 | IF 0.72 > .70 ceiling; 52.5 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355843 | Endurance - This is Uncomfortable - 1 - 60min - RPE3-4 | 60min | 0.38 | IF 0.38 < .60 floor | fix-at-TP-source |
| 14355844 | Endurance - This is Uncomfortable - 2 - 60min - RPE3-4 | 60min | 0.38 | IF 0.38 < .60 floor | fix-at-TP-source |
| 14355845 | Endurance - Delayed Sorrow - 1 - 240min - RPE8-9 | 240min | 0.72 | IF 0.72 > .70 ceiling; 51.7 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355846 | Endurance - Spin Cycle - 1 - 70min - RPE6-7 | 70min | 0.76 | IF 0.76 > .70 ceiling; 57.8 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355847 | Endurance - Workout - ref - 30min - RPE3-4 | 30min | 0.71 | IF 0.71 > .70 ceiling; 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355858 | Endurance - End - - 1 - 30min - RPE7-8 | 30min | 0.58 | IF 0.58 < .60 floor; 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355867 | Endurance - Workout - ref - 240min - RPE3-4 | 240min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355868 | Endurance - Workout - ref - 120min - RPE3-4 | 120min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355872 | Endurance - Workout - ref - 90min - RPE3-4 | 90min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355876 | Endurance - Workout - ref - 270min - RPE3-4 | 270min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355877 | Endurance - Workout - ref - 330min - RPE3-4 | 330min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355898 | Endurance - Aerobic Economy - ref - 270min - RPE5-6 | 270min | 0.70 | IF 0.70 > .70 ceiling | fix-at-TP-source |
| 14355899 | Endurance - Low Z2 + HC - ref - 90min - RPE3-4 | 90min | 0.32 | IF 0.32 < .60 floor | fix-at-TP-source |
| 14355900 | Endurance - Staying Power - ref - 75min - RPE7-8 | 75min | 0.92 | IF 0.92 > .70 ceiling; 83.8 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355906 | Endurance - XL Endurance / Aerobic Econ. - ref - 330min - RPE5-6 | 330min | 0.53 | IF 0.53 < .60 floor | fix-at-TP-source |
| 14355908 | Endurance + 30/30 | 264min | 0.71 | IF 0.71 > .70 ceiling; 50.4 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355910 | Endurance - Unsteady Eddy - 3 - 315min - RPE10 | 315min | 0.72 | IF 0.72 > .70 ceiling; 51.6 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355927 | Endurance - Aerobic Load Sprints - ref - 90min - RPE6-7 | 90min | 0.72 | IF 0.72 > .70 ceiling; 51.7 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355932 | Endurance - General w/ Surges - ref - 120min - RPE6-7 | 120min | 0.71 | IF 0.71 > .70 ceiling; 50.5 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355933 | Endurance - RLP Compressed Endurance - Prep Session V2 - ref - 60min - RPE8-9 | 60min | 0.71 | IF 0.71 > .70 ceiling; 50.2 TSS/hr (>50 cap, AE-2.8); description prescribes fasted riding (AE-6.3) | fix-at-TP-source |
| 14355935 | Endurance - RLP up 'n down Z2 - ref - 25min - RPE6-7 | 25min | 0.59 | IF 0.59 < .60 floor; 25min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355940 | Endurance - Steady State - ref - 90min - RPE8-9 | 90min | 0.75 | IF 0.75 > .70 ceiling; 56.9 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355941 | Endurance - Mixtape Feat Tempo - 1 - 107min - RPE7-8 | 107min | 0.71 | IF 0.71 > .70 ceiling; 50.4 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355943 | Endurance - Intensive Endurance 3*20 - ref - 105min - RPE5-6 | 105min | 0.72 | IF 0.72 > .70 ceiling; 52.1 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355947 | Endurance - Zone 2 with 10sec Sprints v1.1 - ref - 45min - RPE10 | 45min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355948 | Endurance - Zone 2 with 12sec Sprints v1.1 - ref - 45min - RPE10 | 45min | 0.72 | IF 0.72 > .70 ceiling; 52.3 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355949 | Endurance - Zone 2 with 20sec Sprints v1.1 - ref - 55min - RPE10 | 55min | 0.75 | IF 0.75 > .70 ceiling; 56.0 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355951 | Commute | 30min | 0.38 | IF 0.38 < .60 floor; 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355953 | Endurance - + - 4 - 240min - RPE5-6 | 240min | 0.75 | IF 0.75 > .70 ceiling; 56.1 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355954 | Endurance - + - 5 - 300min - RPE5-6 | 300min | 0.76 | IF 0.76 > .70 ceiling; 57.7 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355955 | Endurance - + - 6 - 360min - RPE5-6 | 360min | 0.75 | IF 0.75 > .70 ceiling; 57.0 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355956 | Endurance - + 2.5 - ref - 150min - RPE5-6 | 150min | 0.74 | IF 0.74 > .70 ceiling; 54.0 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355957 | Endurance - + - 2 - 120min - RPE5-6 | 120min | 0.73 | IF 0.73 > .70 ceiling; 53.5 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355958 | Endurance - + .5 - ref - 30min - RPE5-6 | 30min | 0.75 | IF 0.75 > .70 ceiling; 57.0 TSS/hr (>50 cap, AE-2.8); 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355959 | Endurance - + .75 - ref - 45min - RPE5-6 | 45min | 0.75 | IF 0.75 > .70 ceiling; 56.9 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355960 | Endurance - + - 1 - 60min - RPE5-6 | 60min | 0.75 | IF 0.75 > .70 ceiling; 57.0 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355961 | Endurance - + 1.5 - ref - 90min - RPE5-6 | 90min | 0.75 | IF 0.75 > .70 ceiling; 57.0 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355962 | Endurance - + Vision Quest - ref - 420min - RPE5-6 | 420min | 0.76 | IF 0.76 > .70 ceiling; 58.0 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355971 | Endurance - Blocks - 5 - 225min - RPE3-4 | 225min | 0.73 | IF 0.73 > .70 ceiling; 53.9 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355972 | Endurance - Blocks - 4 - 200min - RPE3-4 | 200min | 0.73 | IF 0.73 > .70 ceiling; 53.6 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355973 | Endurance - Blocks - 6 - 240min - RPE3-4 | 240min | 0.73 | IF 0.73 > .70 ceiling; 53.8 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355974 | Endurance - Blocks - 1 - 120min - RPE3-4 | 120min | 0.73 | IF 0.73 > .70 ceiling; 53.1 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355975 | Endurance - Blocks - 2 - 160min - RPE3-4 | 160min | 0.73 | IF 0.73 > .70 ceiling; 53.4 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355976 | Endurance - Blocks - 3 - 180min - RPE3-4 | 180min | 0.73 | IF 0.73 > .70 ceiling; 53.8 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355977 | Endurance - with Surges - 2 - 280min - RPE9-10 | 280min | 0.70 | IF 0.70 > .70 ceiling | fix-at-TP-source |
| 14355978 | Endurance - with Surges - 6 - 370min - RPE9-10 | 370min | 0.71 | IF 0.71 > .70 ceiling; 50.4 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355979 | Endurance - with Surges - 5 - 370min - RPE9-10 | 370min | 0.71 | IF 0.71 > .70 ceiling; 50.1 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355980 | Endurance - with Surges - 1 - 250min - RPE9-10 | 250min | 0.70 | IF 0.70 > .70 ceiling | fix-at-TP-source |
| 14355981 | Endurance - with Surges - 3 - 310min - RPE9-10 | 310min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355982 | Endurance - with Surges - 4 - 310min - RPE9-10 | 310min | 0.71 | IF 0.71 > .70 ceiling | fix-at-TP-source |
| 14355983 | Endurance - Unsteady Eddy Vision Quest - ref - 430min - RPE10 | 430min | 0.73 | IF 0.73 > .70 ceiling; 53.3 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355985 | Endurance - 05_Almquist_Z2-plus-Sprints - ref - 98min - RPE10 | 98min | 0.72 | IF 0.72 > .70 ceiling; 52.1 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355986 | Endurance - Z2 + Sprints - 4 - 132min - RPE10 | 132min | 0.72 | IF 0.72 > .70 ceiling; 52.5 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355987 | Endurance - Z2 + Sprints - 3 - 108min - RPE10 | 108min | 0.71 | IF 0.71 > .70 ceiling; 50.9 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355988 | Endurance - Z2 + Sprints - 2 - 98min - RPE10 | 98min | 0.72 | IF 0.72 > .70 ceiling; 52.1 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355989 | Endurance - Z2 + Sprints - 1 - 68min - RPE10 | 68min | 0.71 | IF 0.71 > .70 ceiling; 51.1 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355990 | Endurance with Surges - 6 - 80min - RPE9-10 | 80min | 0.76 | IF 0.76 > .70 ceiling; 58.1 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355991 | Endurance with Surges - 5 - 80min - RPE9-10 | 80min | 0.74 | IF 0.74 > .70 ceiling; 55.2 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355992 | Endurance with Surges - 4 - 80min - RPE9-10 | 80min | 0.72 | IF 0.72 > .70 ceiling; 52.1 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14355993 | Endurance with Surges - 3 - 80min - RPE9-10 | 80min | 0.70 | IF 0.70 > .70 ceiling | fix-at-TP-source |
| 14356002 | Endurance - Structured Fartlek - 6 - 60min - RPE6-7 | 60min | 0.75 | IF 0.75 > .70 ceiling; 55.5 TSS/hr (>50 cap, AE-2.8); name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356003 | Endurance - Structured Fartlek - 5 - 60min - RPE6-7 | 60min | 0.73 | IF 0.73 > .70 ceiling; 53.7 TSS/hr (>50 cap, AE-2.8); name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356004 | Endurance - Structured Fartlek - 4 - 60min - RPE6-7 | 60min | 0.72 | IF 0.72 > .70 ceiling; 51.8 TSS/hr (>50 cap, AE-2.8); name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356005 | Endurance - Structured Fartlek - 3 - 60min - RPE6-7 | 60min | 0.71 | IF 0.71 > .70 ceiling; name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356008 | Endurance - FatMax Development - 6 - 200min - RPE2-3 | 200min | 0.60 | IF 0.60 < .60 floor; name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356009 | Endurance - FatMax Development - 5 - 180min - RPE2-3 | 180min | 0.60 | IF 0.60 < .60 floor; name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356010 | Endurance - FatMax Development - 4 - 160min - RPE2-3 | 160min | 0.60 | IF 0.60 < .60 floor; name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356011 | Endurance - FatMax Development - 3 - 140min - RPE2-3 | 140min | 0.60 | IF 0.60 < .60 floor; name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356012 | Endurance - FatMax Development - 2 - 120min - RPE2-3 | 120min | 0.60 | IF 0.60 < .60 floor; name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356013 | Endurance - FatMax Development - 1 - 100min - RPE2-3 | 100min | 0.60 | IF 0.60 < .60 floor; name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356014 | Endurance - 3x15 Tempo - 6 - 110min - RPE3-4 | 110min | 0.75 | IF 0.75 > .70 ceiling; 56.2 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14356015 | Endurance - 3x15 Tempo - 5 - 104min - RPE3-4 | 104min | 0.75 | IF 0.75 > .70 ceiling; 55.6 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14356017 | Endurance - 3x15 Tempo - 4 - 98min - RPE3-4 | 98min | 0.74 | IF 0.74 > .70 ceiling; 54.9 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14356018 | Endurance - 3x15 Tempo - 3 - 92min - RPE3-4 | 92min | 0.74 | IF 0.74 > .70 ceiling; 54.1 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14356019 | Endurance - 3x15 Tempo - 2 - 86min - RPE3-4 | 86min | 0.73 | IF 0.73 > .70 ceiling; 53.2 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14356020 | Endurance - 3x15 Tempo - 1 - 80min - RPE3-4 | 80min | 0.72 | IF 0.72 > .70 ceiling; 52.1 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14356050 | Endurance - Blocks 2h59 - ref - 180min - RPE7-8 | 180min | 0.73 | IF 0.73 > .70 ceiling; 52.9 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14416915 | Endurance - Tempo (Continuous Ladder) - 1 - 40min - RPE5-6 | 40min | 0.73 | IF 0.73 > .70 ceiling; 52.7 TSS/hr (>50 cap, AE-2.8); 40min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14416916 | Endurance - Tempo (Continuous Ladder) - 2 - 61min - RPE5-6 | 61min | 0.74 | IF 0.74 > .70 ceiling; 55.3 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14416917 | Endurance - Tempo (Continuous Ladder) - 3 - 79min - RPE5-6 | 79min | 0.76 | IF 0.76 > .70 ceiling; 57.6 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14416918 | Endurance - Tempo (Continuous Ladder) - 4 - 89min - RPE5-6 | 89min | 0.77 | IF 0.77 > .70 ceiling; 59.2 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14416919 | Endurance - Tempo (Continuous Ladder) - 5 - 94min - RPE5-6 | 94min | 0.77 | IF 0.77 > .70 ceiling; 59.9 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14416920 | Endurance - Tempo (Continuous Ladder) - 6 - 99min - RPE5-6 | 99min | 0.78 | IF 0.78 > .70 ceiling; 60.5 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |
| 14416921 | Endurance - Z2 + Sprints - ref - 98min - RPE10 | 98min | 0.72 | IF 0.72 > .70 ceiling; 52.1 TSS/hr (>50 cap, AE-2.8) | fix-at-TP-source |

## (b) Under the 45-minute session floor (90)

| item_id | name | duration | IF | violation | proposed action |
|---|---|---|---|---|---|
| 4250978 | Cyclocross Run Workout | 21min | 0.46 | 21min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355555 | Anaerobic - Tough as Old Boots - 1 - 44min - RPE9-10 | 44min | 0.72 | 44min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355557 | Anaerobic - Tough as Old Boots - 2 - 43min - RPE9-10 | 43min | 0.70 | 43min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355558 | Sprint - Schneider 1 [retained 14355558] - ref - 41min - RPE10 | 41min | 0.90 | 41min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355578 | Anaerobic - Brøt Ben - 1 - 30min - RPE9-10 | 30min | 0.82 | 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355579 | Anaerobic - Brøt Ben - 2 - 32min - RPE9-10 | 32min | 0.89 | 32min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355811 | Endurance - Optional - Keep the legs turning - ref - 36min - RPE10 | 36min | 0.84 | IF 0.84 > .70 ceiling; 70.0 TSS/hr (>50 cap, AE-2.8); 36min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355847 | Endurance - Workout - ref - 30min - RPE3-4 | 30min | 0.71 | IF 0.71 > .70 ceiling; 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355858 | Endurance - End - - 1 - 30min - RPE7-8 | 30min | 0.58 | IF 0.58 < .60 floor; 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355879 | Endurance - (MxHr) - 1 - 30min - RPE1-2 | 30min | 0.63 | 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355911 | Endurance - End (%FTP) - 1 - 30min - RPE3-4 | 30min | 0.66 | 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355934 | Endurance - RLP Rolling Z2 - ref - 30min - RPE5-6 | 30min | 0.61 | 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355935 | Endurance - RLP up 'n down Z2 - ref - 25min - RPE6-7 | 25min | 0.59 | IF 0.59 < .60 floor; 25min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355951 | Commute | 30min | 0.38 | IF 0.38 < .60 floor; 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14355958 | Endurance - + .5 - ref - 30min - RPE5-6 | 30min | 0.75 | IF 0.75 > .70 ceiling; 57.0 TSS/hr (>50 cap, AE-2.8); 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356242 | Specialty - Activations - 1 - 30min - RPE8-9 | 30min | 0.66 | 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356265 | Specialty - RLP Z2 Cadence Play with Bursts - ref - 30min - RPE7-8 | 30min | 0.66 | 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356290 | Specialty - Better Late Than Cadence -1 - ref - 42min - RPE6-7 | 42min | 0.72 | 42min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356733 | Tempo - End: Tempo Drills - ref - 5min - RPE5-6 | 5min | 4.90 | 5min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356734 |  4hrs accel/tempo bookended | 15min | 2.93 | 15min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356757 | Sweet Spot - Base Booster - 4x6min SS - ref - 43min - RPE7-8 | 43min | 0.76 | 43min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356821 | Sweet Spot - Dark Roast - 1 - 40min - RPE7-8 | 40min | 0.82 | 40min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356894 | Sweet Spot - G-Spot Progression - G-Spot 10min - 1 - 25min - RPE6-7 | 25min | 0.73 | 25min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356908 | Sweet Spot - G-Spot Progression - G-Spot 2x11min (Mixed Cadence) - 7 - 42min - RPE6-7 | 42min | 0.76 | 42min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356909 | Sweet Spot - G-Spot Progression - G-Spot 20min (Mixed Cadence) - 6 - 35min - RPE6-7 | 35min | 0.77 | 35min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356910 | Sweet Spot - G-Spot Progression - G-Spot 18min (Low Cadence) - 5 - 33min - RPE6-7 | 33min | 0.77 | 33min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356911 | Sweet Spot - G-Spot Progression - G-Spot 16min (Low Cadence) - 4 - 31min - RPE6-7 | 31min | 0.76 | 31min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356912 | Sweet Spot - G-Spot Progression - G-Spot 14min (High Cadence) - 3 - 29min - RPE6-7 | 29min | 0.75 | 29min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356913 | Sweet Spot - G-Spot Progression - G-Spot 12min - 2 - 27min - RPE6-7 | 27min | 0.74 | 27min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356919 | Tempo - Workout - 1 - 40min - RPE7-8 | 40min | 0.73 | 40min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356927 | Sweet Spot - Mixed Climbing - 1 - 43min - RPE7-8 | 43min | 0.71 | 43min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14356943 | Sweet Spot - G-Spot / Sweet Spot - 1 - 35min - RPE7-8 | 35min | 0.72 | 35min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357069 | Tempo + PoP | 31min | 0.79 | 31min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357139 | Threshold - Threshold Touch - 2 - 43min - RPE7-8 | 43min | 0.73 | 43min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357140 | Threshold - Threshold Touch - 1 - 30min - RPE7-8 | 30min | 0.75 | 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357193 | Threshold - Single Sustained Threshold - 1 - 42min - RPE6-7 | 42min | 0.82 | 42min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357238 | Torque - Bike - SFR - 3x5min - ref - 35min - RPE5-6 | 35min | 0.69 | 35min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357239 | Torque - Bike - MTI - Tempo and Standing Starts - ref - 35min - RPE9-10 | 35min | 0.65 | 35min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357240 | Torque - Bike - MTI - Tempo + Standing Starts [retained 14357240] - ref - 35min - RPE9-10 | 35min | 0.65 | 35min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357241 | Torque - Hard Workout - ref - 43min - RPE7-8 | 43min | 0.76 | 43min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357242 | Torque - Hard - Pace Changes - ref - 35min - RPE10 | 35min | 0.76 | 35min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357243 | Torque - HC - ref - 40min - RPE5-6 | 40min | 0.65 | 40min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357244 | Torque - Tempo/LT + SIT - ref - 40min - RPE10 | 40min | 0.80 | 40min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357245 | Torque - Time Machine - 1 - 40min - RPE5-6 | 40min | 0.78 | 40min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357347 | Torque - Post Strength Stomps - ref - 38min - RPE10 | 38min | 0.74 | 38min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357387 | Torque - SFR - Sustained Force Repetitions - 1 - 43min - RPE7-8 | 43min | 0.71 | 43min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357391 | Torque - Stomps - 3 - 35min - RPE10 | 35min | 0.69 | 35min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357392 | Torque - Stomps - 6 - 37min - RPE10 | 37min | 0.73 | 37min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357393 | Torque - Stomps - 1 - 34min - RPE10 | 34min | 0.65 | 34min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357394 | Torque - Stomps - 4 - 34min - RPE10 | 34min | 0.70 | 34min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357395 | Torque - Stomps - 2 - 35min - RPE10 | 35min | 0.67 | 35min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357396 | Torque - Stomps - 5 - 34min - RPE10 | 34min | 0.72 | 34min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357446 | Torque - SFR + Cadence Contrast 3x3min/3min + 3x30s/2min (1 of 2) - ref - 43min - RPE8-9 | 43min | 0.70 | 43min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357463 | VO2max - Short Capacity - Brøt Ben - ref - 35min - RPE9-10 | 35min | 0.94 | 35min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357496 | VO2max - The Dæhlie - 1 - 39min - RPE8-9 | 39min | 0.81 | 39min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357573 | VO2max - Rønnestand 0 - ref - 43min - RPE9-10 | 43min | 0.73 | 43min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357583 | VO2max - Buffers - 5 - 42min - RPE8-9 | 42min | 0.84 | 42min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357584 | Buffers - 4 | 42min | 0.83 | 42min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357585 | VO2max - Buffers - 3 - 37min - RPE8-9 | 37min | 0.80 | 37min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357586 | Buffers - 2 | 37min | 0.79 | 37min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357587 | VO2max - Buffers - 1 - 32min - RPE8-9 | 32min | 0.75 | 32min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357593 | VO2max - Broken VO2 40/20 - 1 - 42min - RPE8-9 | 42min | 0.73 | 42min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357599 | VO2max - 30/30 VO2 - 1 [retained 14357599] - ref - 38min - RPE8-9 | 38min | 0.71 | 38min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357607 | VO2max - 40/20 - 5 - 35min - RPE8-9 | 35min | 0.80 | 35min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357608 | VO2max - 40/20 - 6 - 38min - RPE8-9 | 38min | 0.82 | 38min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357609 | VO2max - 40/20 - 3 - 34min - RPE8-9 | 34min | 0.77 | 34min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357610 | VO2max - 40/20 - 4 - 35min - RPE8-9 | 35min | 0.79 | 35min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357611 | VO2max - 40/20 - 1 - 31min - RPE8-9 | 31min | 0.73 | 31min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357612 | VO2max - 40/20 - 2 - 32min - RPE8-9 | 32min | 0.75 | 32min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357613 | VO2max - Microbursts - 5 - 35min - RPE9 | 35min | 0.74 | 35min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357614 | VO2max - Microbursts - 2 - 32min - RPE9 | 32min | 0.71 | 32min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357615 | VO2max - Microbursts - 3 - 33min - RPE9 | 33min | 0.72 | 33min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357616 | VO2max - Microbursts - 4 - 33min - RPE9 | 33min | 0.73 | 33min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357617 | VO2max - Microbursts - 1 - 30min - RPE9 | 30min | 0.69 | 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357618 | VO2max - Microbursts - 6 - 36min - RPE9 | 36min | 0.76 | 36min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357639 | VO2max - Steady Intervals - 1 - 43min - RPE8-9 | 43min | 0.74 | 43min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357643 | VO2max - 30/30 - 2 - 34min - RPE9-10 | 34min | 0.75 | 34min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357644 | VO2max - 30/30 - 1 - 33min - RPE9-10 | 33min | 0.73 | 33min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357645 | VO2max - 30/30 - 4 - 36min - RPE9-10 | 36min | 0.78 | 36min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357646 | VO2max - 30/30 - 3 - 35min - RPE9-10 | 35min | 0.77 | 35min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357647 | VO2max - 30/30 - 6 - 38min - RPE9-10 | 38min | 0.81 | 38min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357648 | VO2max - 30/30 - 5 - 36min - RPE9-10 | 36min | 0.79 | 36min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357699 | VO2max - 6x40s/20s (1 of 2) - ref - 31min - RPE8-9 | 31min | 0.72 | 31min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14357700 | VO2max - 8x40s/15s (2 of 2) - ref - 32min - RPE8-9 | 32min | 0.74 | 32min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14416900 | Endurance - Aerobic Base - 1 - 30min - RPE2-4 | 30min | 0.62 | 30min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14416915 | Endurance - Tempo (Continuous Ladder) - 1 - 40min - RPE5-6 | 40min | 0.73 | IF 0.73 > .70 ceiling; 52.7 TSS/hr (>50 cap, AE-2.8); 40min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14416941 | Sweet Spot - Mixed Climbing - Climbing Simulation - 1 - 43min - RPE7-8 | 43min | 0.71 | 43min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14416959 | Torque - SFR + Cadence Contrast - ref - 43min - RPE5-6 | 43min | 0.70 | 43min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14416963 | VO2max - Buffers - 2 - 37min - RPE8-9 | 37min | 0.79 | 37min (<45min floor, AE-2.7) | fix-at-TP-source |
| 14416964 | VO2max - Buffers - 4 - 42min - RPE8-9 | 42min | 0.83 | 42min (<45min floor, AE-2.7) | fix-at-TP-source |

## (c) Purge-list names/descriptions (16)

| item_id | name | duration | IF | violation | proposed action |
|---|---|---|---|---|---|
| 14355815 | Endurance - Z2 Fasted - ref - 120min - RPE3-4 | 120min | — | name prescribes fasted riding (AE-6.3) | retire |
| 14355822 | Endurance - Fasted Ride - 1 - 60min - RPE3-4 | 60min | 0.66 | name prescribes fasted riding (AE-6.3) | retire |
| 14355826 | Endurance - Fasted Ride - 2 - 80min - RPE3-4 | 80min | 0.66 | name prescribes fasted riding (AE-6.3) | retire |
| 14355933 | Endurance - RLP Compressed Endurance - Prep Session V2 - ref - 60min - RPE8-9 | 60min | 0.71 | IF 0.71 > .70 ceiling; 50.2 TSS/hr (>50 cap, AE-2.8); description prescribes fasted riding (AE-6.3) | fix-at-TP-source |
| 14356002 | Endurance - Structured Fartlek - 6 - 60min - RPE6-7 | 60min | 0.75 | IF 0.75 > .70 ceiling; 55.5 TSS/hr (>50 cap, AE-2.8); name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356003 | Endurance - Structured Fartlek - 5 - 60min - RPE6-7 | 60min | 0.73 | IF 0.73 > .70 ceiling; 53.7 TSS/hr (>50 cap, AE-2.8); name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356004 | Endurance - Structured Fartlek - 4 - 60min - RPE6-7 | 60min | 0.72 | IF 0.72 > .70 ceiling; 51.8 TSS/hr (>50 cap, AE-2.8); name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356005 | Endurance - Structured Fartlek - 3 - 60min - RPE6-7 | 60min | 0.71 | IF 0.71 > .70 ceiling; name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356006 | Endurance - Structured Fartlek - 2 - 60min - RPE6-7 | 60min | 0.69 | name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356007 | Endurance - Structured Fartlek - 1 - 60min - RPE6-7 | 60min | 0.68 | name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356008 | Endurance - FatMax Development - 6 - 200min - RPE2-3 | 200min | 0.60 | IF 0.60 < .60 floor; name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356009 | Endurance - FatMax Development - 5 - 180min - RPE2-3 | 180min | 0.60 | IF 0.60 < .60 floor; name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356010 | Endurance - FatMax Development - 4 - 160min - RPE2-3 | 160min | 0.60 | IF 0.60 < .60 floor; name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356011 | Endurance - FatMax Development - 3 - 140min - RPE2-3 | 140min | 0.60 | IF 0.60 < .60 floor; name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356012 | Endurance - FatMax Development - 2 - 120min - RPE2-3 | 120min | 0.60 | IF 0.60 < .60 floor; name carries a retired archetype (FatMax/Fartlek) | retire |
| 14356013 | Endurance - FatMax Development - 1 - 100min - RPE2-3 | 100min | 0.60 | IF 0.60 < .60 floor; name carries a retired archetype (FatMax/Fartlek) | retire |


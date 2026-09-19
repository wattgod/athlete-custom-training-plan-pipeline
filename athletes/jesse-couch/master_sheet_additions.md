# Master Sheet Additions — Jesse Couch

Prepared 2026-08-29. Target workbook: **Endure Coaching OS — Master 2025–26**, Google Drive file ID `1D2WAo9RzoUMP_u9rhupSILtGe8ckSW-2HoIT6hxUZ1g`. Every tab below was read directly from a freshly downloaded copy of the live workbook (not assumed from the athlete-level context-import schema) -- headers, last-populated-row, and formula/validation cells are all re-verified against that download, not estimated.

**Global check**: searched the whole workbook's shared-strings table (56,156 unique strings across all 42 tabs, including 21 legacy pre-consolidation tabs not touched here) for "Jesse" -- zero matches anywhere, including the roster/Athlete Index tab. No duplicate-row risk.

Row content below reuses, verbatim, the same evidence-sourced data already built and byte-verified into `jesse-couch-2025-26-context-import.xlsx` -- nothing here was re-derived or re-typed from the source files a second time. Where a master-sheet column doesn't exist in the athlete-level file (e.g. `Approval`, `Athlete`, `Service`), it is set to a safe default (`HOLD` for every Approval column, since nothing has been reviewed yet) or left blank with a note, never guessed.

---

## 1. Editor Queue 2025-26

**Header row (A1:N1):**

| Col | Header |
|---|---|
| A | Priority Score |
| B | Priority |
| C | Date |
| D | Athlete |
| E | Service |
| F | Channel |
| G | Status |
| H | Why This Matters |
| I | Evidence |
| J | Suggested Copy |
| K | Source Link |
| L | Source ID |
| M | Confidence |
| N | Your Move |

**First empty row: 45.** Last populated row (44): `Priority Score=900.0 | Priority=01 · ONBOARDING | Date=2026-08-21 | Athlete=Forest Hietpas | Service=Premium | Channel=Email`.

**No formulas or data validation found anywhere in this sheet** -- free text/numbers throughout.

**Flag before pasting:** I could not find the Priority-Score rubric or the controlled vocabulary for the `Priority` column (only one example value seen: `01 · ONBOARDING`) anywhere in the 16 tabs I inspected -- it isn't in Methods & Sources 2025-26 either. I left `Priority Score` blank and used a plain-language `Priority` label rather than guess at a numbering scheme that might already be in use elsewhere in the queue. Assign both per whatever rubric you're actually using.

**Row to paste at A45 (tab-separated):**

```
	OPEN LOOP	2026-08-29	Jesse Couch	Custom	Email	Open	3 athlete emails from the last 48h have no coach reply yet, and the top open item (mid-August FTP retest wattage) blocks correct zone-setting on the live v3 plan.	communications.md threads #44 (sodium screenshot, 08-27), #46 (Weight/Food Update, 08-29), #47 (What Went Well + Race Plan, 08-29 -- athlete explicitly asked 'If the Race Plan does not work for you, please let me know.'). FTP: athlete states 08-17 retest 'was up a fair amount since June' (email 2026-08-21) but no wattage was ever captured in Gmail; last confirmed TP value (270W, 2026-06-23) is known stale.	Pull the actual mid-August FTP wattage from TrainingPeaks directly, then close out the 3 open threads -- the race-plan one has an explicit question waiting.			High — verbatim Gmail archive	APPROVE · EDIT · HOLD
```

---

## 2. Weekly Review Composer — no row prepared

communications.md contains no real sent weekly-review email matching this tab's format (Week Start/Recipient/Subject 'Last Week'/Week Read/Why/Next Move/Good/Better/Goal/Notes/This Week/Self-Review). Only ad hoc 'Check In' correspondence and TrainingPeaks workout-notification emails exist. Master header (A1:Z1) confirmed as: Week Start, Athlete, Recipient, Subject, Week Read, Why, Next Move, Good, Better, YOUR Goal (Reminder), Notes/Big Picture, This Week, Self-Review×3, Self-Review Source, Gmail-ready HTML, Plain Text Body, Email Status, Source IDs, **Approval** (data-validated list `HOLD,APPROVE DRAFT,NEEDS EDIT,DRAFTED`, range U2:U1009), Gmail Draft ID, Draft Created At, Workflow Note, Recovery Signal, Wellness Coverage. First empty row: **1010**. No row to paste — inventing this content is explicitly forbidden by the workbook's own Safety rule ("Never invent... self-review answers").

---

## 3. TP Comment Queue

**Header row (A1:L1):**

| Col | Header |
|---|---|
| A | Date |
| B | Athlete |
| C | Sport |
| D | Workout |
| E | Workout Status |
| F | Athlete Comment |
| G | Suggested Coach Comment |
| H | Draft Status |
| I | TrainingPeaks Link |
| J | Approval |
| K | Posted At |
| L | Workflow Note |

**First empty row: 6096.** Last populated row (6095): `Date=2025-08-21 | Athlete=Tyrel Fuchs | Sport=Other | Workout=Cooldown | Workout Status=Completed unplanned`.

**Validation: J2:J6095 (Approval), list = `HOLD,APPROVE TO POST,NEEDS EDIT,POSTED`.** No formulas.

**5 rows to paste starting at A6096** (Date, Athlete inserted after Date, Sport, Workout, Workout Status, Athlete Comment, Suggested Coach Comment, Draft Status → set to `HOLD` in Approval col J since nothing has been reviewed, TrainingPeaks Link, then blank Approval-adjacent cols, Posted At blank, Workflow Note blank):

```
2026-06-11	Jesse Couch	Bike	Short vo2 90s on/60s off	Completed	I'm a little rusty, but this was a solid effort	Good early-season marker -- rust is expected this early, and the numbers back up 'solid effort.' No change needed, just log it as a baseline.	Needs coach reply	https://app.trainingpeaks.com/#calendar/athletes/1177325	HOLD		
2026-06-15	Jesse Couch	Bike	Easy - 60min	Completed	Errands as well 30 minutes shopping	Noted -- active day outside the ride too. No workout concern here.	Needs coach reply	https://app.trainingpeaks.com/#calendar/athletes/1177325	HOLD		
2026-06-16	Jesse Couch	Bike	Better Late Than Cadence 3	Completed	This was a bit better than last weeks Cadence work. I will switch out my cassette for one with tighter gearing.	Good self-diagnosis on the cadence work. Worth a follow-up once the tighter-ratio cassette is on -- curious whether it changes the cadence numbers on the next Cadence session.	Needs coach reply	https://app.trainingpeaks.com/#calendar/athletes/1177325	HOLD		
2026-06-20	Jesse Couch	Bike	Base - 240min + Time in the drops	Completed	I flatted and then it got hot, then HR spiked	Mechanical + heat spike, not a fitness red flag. Worth a quick ack -- anything needed on the flat-fix side (spares, tools) before the next long ride?	Needs coach reply	https://app.trainingpeaks.com/#calendar/athletes/1177325	HOLD		
2026-06-23	Jesse Couch	Bike	The Assessment - Functional Threshold	Completed	Either Age finally caught me or I have great room for improvement. The good news is my leg power balance finally went 50/50	The 50/50 leg-power-balance shift is worth flagging back to him as a real positive, separate from the wattage number itself -- balance improvements often matter more than the raw FTP delta test-to-test.	Needs coach reply	https://app.trainingpeaks.com/#calendar/athletes/1177325	HOLD		
```

---

## 4. Weekly Brief 2025-26

**Header row (A1:Q1):**

| Col | Header |
|---|---|
| A | Athlete |
| B | Service |
| C | Week Start |
| D | Week End |
| E | Week Type |
| F | CTL |
| G | ATL |
| H | TSB |
| I | Ramp Rate |
| J | Planned Duration |
| K | Completed Duration |
| L | Planned TSS |
| M | Completed TSS |
| N | Adherence % |
| O | Week Read |
| P | TL;DR |
| Q | Email Status |

**First empty row: 1009.** Last populated row (1008): `Athlete=Edward Shapiro | Service=Premium | Week Start=2026-08-17 | Week End=2026-08-23 | Week Type=Recovery Week | CTL=60.0`. No formulas, no data validation.

**Note the column order differs from the athlete-file schema**: master adds `Athlete`/`Service` up front, and splits `Planned/Completed TSS` into their own columns (my per-athlete file's Weekly Brief tab only had Planned/Completed *Duration*, no separate TSS pair) — mapped below: Completed TSS populated from the PMC weekly sum, Planned TSS left blank (same 'no historical planned data' gap as Planned/Completed Duration).

**52 rows to paste starting at A1009** (Monday-anchored weeks 2025-09-01 through 2026-08-24, week-ending CTL/ATL/TSB, all-sport figures, from `pmc-history-20260829.json`; Week Type, Planned Duration/TSS, Completed Duration, Adherence %, Week Read all blank — no coach-authored week labels or historical planned-vs-actual data exist in the available sources; Email Status blank, no review was ever sent):

```
Jesse Couch	Custom	2025-09-01	2025-09-07		93.2	106.5	-12.4					868.5			[Coverage note: Week Type, Planned Duration/TSS, Completed Duration and Adherence % are blank throughout this tab -- no coach-authored week-label or historical planned-vs-actual data exist in the available sources; only completed CTL/ATL/TSB/TSS from the TrainingPeaks PMC history export (pmc-history-20260829.json, all-sport figures, week-ending values). Week Read is a house field requiring coach judgment, left blank.] Week-ending CTL 93.2 / ATL 106.5 / TSB -12.4. Completed TSS 868.5 (7 days).	
Jesse Couch	Custom	2025-09-08	2025-09-14		96.3	113.8	-21.5	3.1				785.5			Week-ending CTL 96.3 / ATL 113.8 / TSB -21.5. Completed TSS 785.5 (7 days).	
Jesse Couch	Custom	2025-09-15	2025-09-21		90.9	75.4	5.1	-5.4				434.5			Week-ending CTL 90.9 / ATL 75.4 / TSB 5.1. Completed TSS 434.5 (7 days).	
Jesse Couch	Custom	2025-09-22	2025-09-28		90.9	81.1	10.4	0.0				651.3			Week-ending CTL 90.9 / ATL 81.1 / TSB 10.4. Completed TSS 651.3 (7 days).	
Jesse Couch	Custom	2025-09-29	2025-10-05		87.6	78.1	11.8	-3.3				473.9			Week-ending CTL 87.6 / ATL 78.1 / TSB 11.8. Completed TSS 473.9 (7 days).	
Jesse Couch	Custom	2025-10-06	2025-10-12		86.3	78.7	9.4	-1.3				557.6			Week-ending CTL 86.3 / ATL 78.7 / TSB 9.4. Completed TSS 557.6 (7 days).	
Jesse Couch	Custom	2025-10-13	2025-10-19		86.8	87.7	4.8	0.5				622.6			Week-ending CTL 86.8 / ATL 87.7 / TSB 4.8. Completed TSS 622.6 (7 days).	
Jesse Couch	Custom	2025-10-20	2025-10-26		74.2	34.1	39.9	-12.6				36.0			Week-ending CTL 74.2 / ATL 34.1 / TSB 39.9. Completed TSS 36.0 (7 days).	
Jesse Couch	Custom	2025-10-27	2025-11-02		71.5	51.1	24.5	-2.7				394.4			Week-ending CTL 71.5 / ATL 51.1 / TSB 24.5. Completed TSS 394.4 (7 days).	
Jesse Couch	Custom	2025-11-03	2025-11-09		71.8	66.1	1.2	0.3				515.2			Week-ending CTL 71.8 / ATL 66.1 / TSB 1.2. Completed TSS 515.2 (7 days).	
Jesse Couch	Custom	2025-11-10	2025-11-16		73.2	79.1	4.4	1.4				558.3			Week-ending CTL 73.2 / ATL 79.1 / TSB 4.4. Completed TSS 558.3 (7 days).	
Jesse Couch	Custom	2025-11-17	2025-11-23		75	85.9	-1.9	1.8				589.1			Week-ending CTL 75 / ATL 85.9 / TSB -1.9. Completed TSS 589.1 (7 days).	
Jesse Couch	Custom	2025-11-24	2025-11-30		63.4	29.2	30.9	-11.6				0			Week-ending CTL 63.4 / ATL 29.2 / TSB 30.9. Completed TSS 0 (7 days).	
Jesse Couch	Custom	2025-12-01	2025-12-07		53.5	9.9	43.3	-9.9				0			Week-ending CTL 53.5 / ATL 9.9 / TSB 43.3. Completed TSS 0 (7 days).	
Jesse Couch	Custom	2025-12-08	2025-12-14		45.2	3.4	42.4	-8.3				0			Week-ending CTL 45.2 / ATL 3.4 / TSB 42.4. Completed TSS 0 (7 days).	
Jesse Couch	Custom	2025-12-15	2025-12-21		38.2	1.1	37.8	-7.0				0			Week-ending CTL 38.2 / ATL 1.1 / TSB 37.8. Completed TSS 0 (7 days).	
Jesse Couch	Custom	2025-12-22	2025-12-28		32.8	2.9	30.1	-5.4				20.8			Week-ending CTL 32.8 / ATL 2.9 / TSB 30.1. Completed TSS 20.8 (7 days).	
Jesse Couch	Custom	2025-12-29	2026-01-04		34.5	35.9	8.7	1.7				296.4			Week-ending CTL 34.5 / ATL 35.9 / TSB 8.7. Completed TSS 296.4 (7 days).	
Jesse Couch	Custom	2026-01-05	2026-01-11		36.9	47.6	-17.7	2.4				343.9			Week-ending CTL 36.9 / ATL 47.6 / TSB -17.7. Completed TSS 343.9 (7 days).	
Jesse Couch	Custom	2026-01-12	2026-01-18		41	57.4	-25	4.1				443.6			Week-ending CTL 41 / ATL 57.4 / TSB -25. Completed TSS 443.6 (7 days).	
Jesse Couch	Custom	2026-01-19	2026-01-25		46.3	68.8	-26.3	5.3				529.3			Week-ending CTL 46.3 / ATL 68.8 / TSB -26.3. Completed TSS 529.3 (7 days).	
Jesse Couch	Custom	2026-01-26	2026-02-01		47.6	54.9	-15.3	1.3				388.5			Week-ending CTL 47.6 / ATL 54.9 / TSB -15.3. Completed TSS 388.5 (7 days).	
Jesse Couch	Custom	2026-02-02	2026-02-08		50.7	59.8	-7.1	3.1				483.1			Week-ending CTL 50.7 / ATL 59.8 / TSB -7.1. Completed TSS 483.1 (7 days).	
Jesse Couch	Custom	2026-02-09	2026-02-15		52.2	59.6	-10.3	1.5				424.4			Week-ending CTL 52.2 / ATL 59.6 / TSB -10.3. Completed TSS 424.4 (7 days).	
Jesse Couch	Custom	2026-02-16	2026-02-22		51.5	51.5	-7.4	-0.7				331.7			Week-ending CTL 51.5 / ATL 51.5 / TSB -7.4. Completed TSS 331.7 (7 days).	
Jesse Couch	Custom	2026-02-23	2026-03-01		50.4	49.1	4.8	-1.1				307.5			Week-ending CTL 50.4 / ATL 49.1 / TSB 4.8. Completed TSS 307.5 (7 days).	
Jesse Couch	Custom	2026-03-02	2026-03-08		51.4	59.7	-1.4	1.0				385.5			Week-ending CTL 51.4 / ATL 59.7 / TSB -1.4. Completed TSS 385.5 (7 days).	
Jesse Couch	Custom	2026-03-09	2026-03-15		53.1	63.6	-19.8	1.7				433.5			Week-ending CTL 53.1 / ATL 63.6 / TSB -19.8. Completed TSS 433.5 (7 days).	
Jesse Couch	Custom	2026-03-16	2026-03-22		55.6	71.3	-26.2	2.5				473.4			Week-ending CTL 55.6 / ATL 71.3 / TSB -26.2. Completed TSS 473.4 (7 days).	
Jesse Couch	Custom	2026-03-23	2026-03-29		57.9	72.6	-25.4	2.3				490.4			Week-ending CTL 57.9 / ATL 72.6 / TSB -25.4. Completed TSS 490.4 (7 days).	
Jesse Couch	Custom	2026-03-30	2026-04-05		58.1	63.9	-15.1	0.2				410.9			Week-ending CTL 58.1 / ATL 63.9 / TSB -15.1. Completed TSS 410.9 (7 days).	
Jesse Couch	Custom	2026-04-06	2026-04-12		55.3	48.2	0.4	-2.8				281.1			Week-ending CTL 55.3 / ATL 48.2 / TSB 0.4. Completed TSS 281.1 (7 days).	
Jesse Couch	Custom	2026-04-13	2026-04-19		55.5	51.7	-3.5	0.2				400.8			Week-ending CTL 55.5 / ATL 51.7 / TSB -3.5. Completed TSS 400.8 (7 days).	
Jesse Couch	Custom	2026-04-20	2026-04-26		51	37.3	8.6	-4.5				178.3			Week-ending CTL 51 / ATL 37.3 / TSB 8.6. Completed TSS 178.3 (7 days).	
Jesse Couch	Custom	2026-04-27	2026-05-03		53.8	57.5	-12	2.8				484.2			Week-ending CTL 53.8 / ATL 57.5 / TSB -12. Completed TSS 484.2 (7 days).	
Jesse Couch	Custom	2026-05-04	2026-05-10		55.8	64.3	-17.9	2.0				465.6			Week-ending CTL 55.8 / ATL 64.3 / TSB -17.9. Completed TSS 465.6 (7 days).	
Jesse Couch	Custom	2026-05-11	2026-05-17		58.4	67.9	-7.2	2.6				513.8			Week-ending CTL 58.4 / ATL 67.9 / TSB -7.2. Completed TSS 513.8 (7 days).	
Jesse Couch	Custom	2026-05-18	2026-05-24		56.7	48.9	1	-1.7				341.3			Week-ending CTL 56.7 / ATL 48.9 / TSB 1. Completed TSS 341.3 (7 days).	
Jesse Couch	Custom	2026-05-25	2026-05-31		62.3	79.6	1.2	5.6				652.1			Week-ending CTL 62.3 / ATL 79.6 / TSB 1.2. Completed TSS 652.1 (7 days).	
Jesse Couch	Custom	2026-06-01	2026-06-07		65.2	81.7	-28.6	2.9				559.4			Week-ending CTL 65.2 / ATL 81.7 / TSB -28.6. Completed TSS 559.4 (7 days).	
Jesse Couch	Custom	2026-06-08	2026-06-14		64.4	67.7	-13.1	-0.8				418.2			Week-ending CTL 64.4 / ATL 67.7 / TSB -13.1. Completed TSS 418.2 (7 days).	
Jesse Couch	Custom	2026-06-15	2026-06-21		64.5	65.6	-10.5	0.1				455.2			Week-ending CTL 64.5 / ATL 65.6 / TSB -10.5. Completed TSS 455.2 (7 days).	
Jesse Couch	Custom	2026-06-22	2026-06-28		64.7	66.8	-11.6	0.2				459.3			Week-ending CTL 64.7 / ATL 66.8 / TSB -11.6. Completed TSS 459.3 (7 days).	
Jesse Couch	Custom	2026-06-29	2026-07-05		65.7	70.7	-15.2	1.0				493.4			Week-ending CTL 65.7 / ATL 70.7 / TSB -15.2. Completed TSS 493.4 (7 days).	
Jesse Couch	Custom	2026-07-06	2026-07-12		66.8	73	-16.7	1.1				508.7			Week-ending CTL 66.8 / ATL 73 / TSB -16.7. Completed TSS 508.7 (7 days).	
Jesse Couch	Custom	2026-07-13	2026-07-19		63.1	53.7	2	-3.7				302.5			Week-ending CTL 63.1 / ATL 53.7 / TSB 2. Completed TSS 302.5 (7 days).	
Jesse Couch	Custom	2026-07-20	2026-07-26		65	69	-13.9	1.9				524.7			Week-ending CTL 65 / ATL 69 / TSB -13.9. Completed TSS 524.7 (7 days).	
Jesse Couch	Custom	2026-07-27	2026-08-02		67.8	78.2	-21.8	2.8				578.6			Week-ending CTL 67.8 / ATL 78.2 / TSB -21.8. Completed TSS 578.6 (7 days).	
Jesse Couch	Custom	2026-08-03	2026-08-09		66.3	65.1	-8.1	-1.5				404.2			Week-ending CTL 66.3 / ATL 65.1 / TSB -8.1. Completed TSS 404.2 (7 days).	
Jesse Couch	Custom	2026-08-10	2026-08-16		69.3	76.7	-18.4	3.0				606.5			Week-ending CTL 69.3 / ATL 76.7 / TSB -18.4. Completed TSS 606.5 (7 days).	
Jesse Couch	Custom	2026-08-17	2026-08-23		69.8	73.5	-14.2	0.5				508.5			Week-ending CTL 69.8 / ATL 73.5 / TSB -14.2. Completed TSS 508.5 (7 days).	
Jesse Couch	Custom	2026-08-24	2026-08-30		73.9	91.8	-0.7	4.1				596.3			Week-ending CTL 73.9 / ATL 91.8 / TSB -0.7. Completed TSS 596.3 (6 days). Partial week -- PMC data available only through 2026-08-29.	
```

---

## 5. Weekly Context 2025-26

**Header row (A1:AY1) — 51 columns, confirmed identical order/text to the athlete-level file:**

| Col | Header | Col | Header |
|---|---|---|---|
| A | Week ID | B | Athlete |
| C | Service | D | Week Start |
| E | Week End | F | Week Type |
| G | Week Type Source | H | Week Type Basis |
| I | CTL | J | ATL |
| K | TSB | L | Ramp Rate |
| M | Ramp Source | N | Metric Source |
| O | Historical Set FTP | P | Set FTP Source |
| Q | Current TP FTP · 2026-08-21 | R | Planned Duration |
| S | Completed Duration | T | Planned TSS |
| U | Completed TSS | V | Planned Workouts |
| W | Completed Planned Workouts | X | Adherence % |
| Y | Athlete Comment Count | Z | Comment Preview Count |
| AA | Email Context Count | AB | Context Flags |
| AC | Data Coverage | AD | Actual Review Count |
| AE | Actual Review Dates | AF | Actual Grade |
| AG | Actual Good | AH | Actual Better |
| AI | Actual Goal | AJ | Actual Big Picture |
| AK | Actual This Week | AL | Actual Sent Review |
| AM | Draft Grade | AN | Draft Good |
| AO | Draft Better | AP | Draft Goal |
| AQ | Draft Big Picture | AR | Draft This Week |
| AS | Draft Email | AT | Effective Grade |
| AU | Effective Review | AV | Email Status |
| AW | TL;DR | AX | Source IDs |
| AY | Source |  |  |

**First empty row: 1009.** Last populated row (1008): `Week ID=tpweek:edward-shapiro:2026-08-17 | Athlete=Edward Shapiro | Service=Premium | Week Start=2026-08-17 | Week End=2026-08-23 | Week Type=Recovery Week`. No formulas, no data validation.

**52 rows to paste starting at A1009** (identical column layout and content to what's already in `Weekly Context 2025-26` inside the athlete-level xlsx — only CTL/ATL/TSB/Completed TSS populated from the PMC history export; everything else, including every Actual/Draft/Effective review field, blank — see the coverage note baked into row 1's TL;DR for the full list of what's intentionally missing and why):

```
tpweek:jesse-couch:2025-09-01	Jesse Couch	Custom	2025-09-01	2025-09-07				93.2	106.5	-12.4			TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							868.5								CTL/ATL/TSB/Completed TSS only (PMC history export)																				[Coverage note: Week Type, Historical/Current per-week FTP, Planned*/Adherence %, and every Actual/Draft/Effective review field are blank throughout this tab -- no coach-authored week labels, no historical planned-vs-actual data, and no real sent weekly review exists in communications.md for this athlete. Only CTL/ATL/TSB/Completed TSS from the TrainingPeaks PMC history export are populated.] Week-ending CTL 93.2 / ATL 106.5 / TSB -12.4. Completed TSS 868.5 (7 days).	athleteId=1177325; weekStart=2025-09-01	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-09-08	Jesse Couch	Custom	2025-09-08	2025-09-14				96.3	113.8	-21.5	3.1	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							785.5								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 96.3 / ATL 113.8 / TSB -21.5. Completed TSS 785.5 (7 days).	athleteId=1177325; weekStart=2025-09-08	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-09-15	Jesse Couch	Custom	2025-09-15	2025-09-21				90.9	75.4	5.1	-5.4	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							434.5								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 90.9 / ATL 75.4 / TSB 5.1. Completed TSS 434.5 (7 days).	athleteId=1177325; weekStart=2025-09-15	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-09-22	Jesse Couch	Custom	2025-09-22	2025-09-28				90.9	81.1	10.4	0.0	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							651.3								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 90.9 / ATL 81.1 / TSB 10.4. Completed TSS 651.3 (7 days).	athleteId=1177325; weekStart=2025-09-22	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-09-29	Jesse Couch	Custom	2025-09-29	2025-10-05				87.6	78.1	11.8	-3.3	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							473.9								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 87.6 / ATL 78.1 / TSB 11.8. Completed TSS 473.9 (7 days).	athleteId=1177325; weekStart=2025-09-29	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-10-06	Jesse Couch	Custom	2025-10-06	2025-10-12				86.3	78.7	9.4	-1.3	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							557.6								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 86.3 / ATL 78.7 / TSB 9.4. Completed TSS 557.6 (7 days).	athleteId=1177325; weekStart=2025-10-06	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-10-13	Jesse Couch	Custom	2025-10-13	2025-10-19				86.8	87.7	4.8	0.5	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							622.6								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 86.8 / ATL 87.7 / TSB 4.8. Completed TSS 622.6 (7 days).	athleteId=1177325; weekStart=2025-10-13	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-10-20	Jesse Couch	Custom	2025-10-20	2025-10-26				74.2	34.1	39.9	-12.6	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							36.0								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 74.2 / ATL 34.1 / TSB 39.9. Completed TSS 36.0 (7 days).	athleteId=1177325; weekStart=2025-10-20	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-10-27	Jesse Couch	Custom	2025-10-27	2025-11-02				71.5	51.1	24.5	-2.7	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							394.4								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 71.5 / ATL 51.1 / TSB 24.5. Completed TSS 394.4 (7 days).	athleteId=1177325; weekStart=2025-10-27	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-11-03	Jesse Couch	Custom	2025-11-03	2025-11-09				71.8	66.1	1.2	0.3	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							515.2								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 71.8 / ATL 66.1 / TSB 1.2. Completed TSS 515.2 (7 days).	athleteId=1177325; weekStart=2025-11-03	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-11-10	Jesse Couch	Custom	2025-11-10	2025-11-16				73.2	79.1	4.4	1.4	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							558.3								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 73.2 / ATL 79.1 / TSB 4.4. Completed TSS 558.3 (7 days).	athleteId=1177325; weekStart=2025-11-10	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-11-17	Jesse Couch	Custom	2025-11-17	2025-11-23				75	85.9	-1.9	1.8	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							589.1								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 75 / ATL 85.9 / TSB -1.9. Completed TSS 589.1 (7 days).	athleteId=1177325; weekStart=2025-11-17	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-11-24	Jesse Couch	Custom	2025-11-24	2025-11-30				63.4	29.2	30.9	-11.6	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							0								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 63.4 / ATL 29.2 / TSB 30.9. Completed TSS 0 (7 days).	athleteId=1177325; weekStart=2025-11-24	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-12-01	Jesse Couch	Custom	2025-12-01	2025-12-07				53.5	9.9	43.3	-9.9	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							0								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 53.5 / ATL 9.9 / TSB 43.3. Completed TSS 0 (7 days).	athleteId=1177325; weekStart=2025-12-01	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-12-08	Jesse Couch	Custom	2025-12-08	2025-12-14				45.2	3.4	42.4	-8.3	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							0								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 45.2 / ATL 3.4 / TSB 42.4. Completed TSS 0 (7 days).	athleteId=1177325; weekStart=2025-12-08	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-12-15	Jesse Couch	Custom	2025-12-15	2025-12-21				38.2	1.1	37.8	-7.0	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							0								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 38.2 / ATL 1.1 / TSB 37.8. Completed TSS 0 (7 days).	athleteId=1177325; weekStart=2025-12-15	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-12-22	Jesse Couch	Custom	2025-12-22	2025-12-28				32.8	2.9	30.1	-5.4	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							20.8								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 32.8 / ATL 2.9 / TSB 30.1. Completed TSS 20.8 (7 days).	athleteId=1177325; weekStart=2025-12-22	TrainingPeaks PMC history export
tpweek:jesse-couch:2025-12-29	Jesse Couch	Custom	2025-12-29	2026-01-04				34.5	35.9	8.7	1.7	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							296.4								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 34.5 / ATL 35.9 / TSB 8.7. Completed TSS 296.4 (7 days).	athleteId=1177325; weekStart=2025-12-29	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-01-05	Jesse Couch	Custom	2026-01-05	2026-01-11				36.9	47.6	-17.7	2.4	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							343.9								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 36.9 / ATL 47.6 / TSB -17.7. Completed TSS 343.9 (7 days).	athleteId=1177325; weekStart=2026-01-05	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-01-12	Jesse Couch	Custom	2026-01-12	2026-01-18				41	57.4	-25	4.1	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							443.6								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 41 / ATL 57.4 / TSB -25. Completed TSS 443.6 (7 days).	athleteId=1177325; weekStart=2026-01-12	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-01-19	Jesse Couch	Custom	2026-01-19	2026-01-25				46.3	68.8	-26.3	5.3	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							529.3								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 46.3 / ATL 68.8 / TSB -26.3. Completed TSS 529.3 (7 days).	athleteId=1177325; weekStart=2026-01-19	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-01-26	Jesse Couch	Custom	2026-01-26	2026-02-01				47.6	54.9	-15.3	1.3	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							388.5								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 47.6 / ATL 54.9 / TSB -15.3. Completed TSS 388.5 (7 days).	athleteId=1177325; weekStart=2026-01-26	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-02-02	Jesse Couch	Custom	2026-02-02	2026-02-08				50.7	59.8	-7.1	3.1	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							483.1								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 50.7 / ATL 59.8 / TSB -7.1. Completed TSS 483.1 (7 days).	athleteId=1177325; weekStart=2026-02-02	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-02-09	Jesse Couch	Custom	2026-02-09	2026-02-15				52.2	59.6	-10.3	1.5	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							424.4								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 52.2 / ATL 59.6 / TSB -10.3. Completed TSS 424.4 (7 days).	athleteId=1177325; weekStart=2026-02-09	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-02-16	Jesse Couch	Custom	2026-02-16	2026-02-22				51.5	51.5	-7.4	-0.7	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							331.7								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 51.5 / ATL 51.5 / TSB -7.4. Completed TSS 331.7 (7 days).	athleteId=1177325; weekStart=2026-02-16	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-02-23	Jesse Couch	Custom	2026-02-23	2026-03-01				50.4	49.1	4.8	-1.1	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							307.5								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 50.4 / ATL 49.1 / TSB 4.8. Completed TSS 307.5 (7 days).	athleteId=1177325; weekStart=2026-02-23	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-03-02	Jesse Couch	Custom	2026-03-02	2026-03-08				51.4	59.7	-1.4	1.0	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							385.5								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 51.4 / ATL 59.7 / TSB -1.4. Completed TSS 385.5 (7 days).	athleteId=1177325; weekStart=2026-03-02	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-03-09	Jesse Couch	Custom	2026-03-09	2026-03-15				53.1	63.6	-19.8	1.7	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							433.5								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 53.1 / ATL 63.6 / TSB -19.8. Completed TSS 433.5 (7 days).	athleteId=1177325; weekStart=2026-03-09	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-03-16	Jesse Couch	Custom	2026-03-16	2026-03-22				55.6	71.3	-26.2	2.5	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							473.4								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 55.6 / ATL 71.3 / TSB -26.2. Completed TSS 473.4 (7 days).	athleteId=1177325; weekStart=2026-03-16	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-03-23	Jesse Couch	Custom	2026-03-23	2026-03-29				57.9	72.6	-25.4	2.3	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							490.4								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 57.9 / ATL 72.6 / TSB -25.4. Completed TSS 490.4 (7 days).	athleteId=1177325; weekStart=2026-03-23	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-03-30	Jesse Couch	Custom	2026-03-30	2026-04-05				58.1	63.9	-15.1	0.2	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							410.9								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 58.1 / ATL 63.9 / TSB -15.1. Completed TSS 410.9 (7 days).	athleteId=1177325; weekStart=2026-03-30	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-04-06	Jesse Couch	Custom	2026-04-06	2026-04-12				55.3	48.2	0.4	-2.8	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							281.1								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 55.3 / ATL 48.2 / TSB 0.4. Completed TSS 281.1 (7 days).	athleteId=1177325; weekStart=2026-04-06	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-04-13	Jesse Couch	Custom	2026-04-13	2026-04-19				55.5	51.7	-3.5	0.2	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							400.8								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 55.5 / ATL 51.7 / TSB -3.5. Completed TSS 400.8 (7 days).	athleteId=1177325; weekStart=2026-04-13	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-04-20	Jesse Couch	Custom	2026-04-20	2026-04-26				51	37.3	8.6	-4.5	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							178.3								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 51 / ATL 37.3 / TSB 8.6. Completed TSS 178.3 (7 days).	athleteId=1177325; weekStart=2026-04-20	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-04-27	Jesse Couch	Custom	2026-04-27	2026-05-03				53.8	57.5	-12	2.8	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							484.2								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 53.8 / ATL 57.5 / TSB -12. Completed TSS 484.2 (7 days).	athleteId=1177325; weekStart=2026-04-27	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-05-04	Jesse Couch	Custom	2026-05-04	2026-05-10				55.8	64.3	-17.9	2.0	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							465.6								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 55.8 / ATL 64.3 / TSB -17.9. Completed TSS 465.6 (7 days).	athleteId=1177325; weekStart=2026-05-04	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-05-11	Jesse Couch	Custom	2026-05-11	2026-05-17				58.4	67.9	-7.2	2.6	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							513.8								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 58.4 / ATL 67.9 / TSB -7.2. Completed TSS 513.8 (7 days).	athleteId=1177325; weekStart=2026-05-11	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-05-18	Jesse Couch	Custom	2026-05-18	2026-05-24				56.7	48.9	1	-1.7	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							341.3								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 56.7 / ATL 48.9 / TSB 1. Completed TSS 341.3 (7 days).	athleteId=1177325; weekStart=2026-05-18	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-05-25	Jesse Couch	Custom	2026-05-25	2026-05-31				62.3	79.6	1.2	5.6	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							652.1								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 62.3 / ATL 79.6 / TSB 1.2. Completed TSS 652.1 (7 days).	athleteId=1177325; weekStart=2026-05-25	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-06-01	Jesse Couch	Custom	2026-06-01	2026-06-07				65.2	81.7	-28.6	2.9	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							559.4								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 65.2 / ATL 81.7 / TSB -28.6. Completed TSS 559.4 (7 days).	athleteId=1177325; weekStart=2026-06-01	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-06-08	Jesse Couch	Custom	2026-06-08	2026-06-14				64.4	67.7	-13.1	-0.8	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							418.2								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 64.4 / ATL 67.7 / TSB -13.1. Completed TSS 418.2 (7 days).	athleteId=1177325; weekStart=2026-06-08	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-06-15	Jesse Couch	Custom	2026-06-15	2026-06-21				64.5	65.6	-10.5	0.1	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							455.2								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 64.5 / ATL 65.6 / TSB -10.5. Completed TSS 455.2 (7 days).	athleteId=1177325; weekStart=2026-06-15	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-06-22	Jesse Couch	Custom	2026-06-22	2026-06-28				64.7	66.8	-11.6	0.2	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							459.3								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 64.7 / ATL 66.8 / TSB -11.6. Completed TSS 459.3 (7 days).	athleteId=1177325; weekStart=2026-06-22	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-06-29	Jesse Couch	Custom	2026-06-29	2026-07-05				65.7	70.7	-15.2	1.0	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							493.4								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 65.7 / ATL 70.7 / TSB -15.2. Completed TSS 493.4 (7 days).	athleteId=1177325; weekStart=2026-06-29	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-07-06	Jesse Couch	Custom	2026-07-06	2026-07-12				66.8	73	-16.7	1.1	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							508.7								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 66.8 / ATL 73 / TSB -16.7. Completed TSS 508.7 (7 days).	athleteId=1177325; weekStart=2026-07-06	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-07-13	Jesse Couch	Custom	2026-07-13	2026-07-19				63.1	53.7	2	-3.7	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							302.5								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 63.1 / ATL 53.7 / TSB 2. Completed TSS 302.5 (7 days).	athleteId=1177325; weekStart=2026-07-13	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-07-20	Jesse Couch	Custom	2026-07-20	2026-07-26				65	69	-13.9	1.9	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							524.7								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 65 / ATL 69 / TSB -13.9. Completed TSS 524.7 (7 days).	athleteId=1177325; weekStart=2026-07-20	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-07-27	Jesse Couch	Custom	2026-07-27	2026-08-02				67.8	78.2	-21.8	2.8	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							578.6								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 67.8 / ATL 78.2 / TSB -21.8. Completed TSS 578.6 (7 days).	athleteId=1177325; weekStart=2026-07-27	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-08-03	Jesse Couch	Custom	2026-08-03	2026-08-09				66.3	65.1	-8.1	-1.5	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							404.2								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 66.3 / ATL 65.1 / TSB -8.1. Completed TSS 404.2 (7 days).	athleteId=1177325; weekStart=2026-08-03	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-08-10	Jesse Couch	Custom	2026-08-10	2026-08-16				69.3	76.7	-18.4	3.0	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							606.5								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 69.3 / ATL 76.7 / TSB -18.4. Completed TSS 606.5 (7 days).	athleteId=1177325; weekStart=2026-08-10	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-08-17	Jesse Couch	Custom	2026-08-17	2026-08-23				69.8	73.5	-14.2	0.5	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							508.5								CTL/ATL/TSB/Completed TSS only (PMC history export)																				Week-ending CTL 69.8 / ATL 73.5 / TSB -14.2. Completed TSS 508.5 (7 days).	athleteId=1177325; weekStart=2026-08-17	TrainingPeaks PMC history export
tpweek:jesse-couch:2026-08-24	Jesse Couch	Custom	2026-08-24	2026-08-30				73.9	91.8	-0.7	4.1	Derived: week-ending CTL minus prior week-ending CTL, from TrainingPeaks PMC history export	TrainingPeaks PMC engine (fitness/v1/athletes/1177325/reporting/performancedata, tau=42/7), pulled 2026-08-29							596.3								CTL/ATL/TSB/Completed TSS only (PMC history export); partial week, data through 2026-08-29																				Week-ending CTL 73.9 / ATL 91.8 / TSB -0.7. Completed TSS 596.3 (6 days). Partial week -- PMC data available only through 2026-08-29.	athleteId=1177325; weekStart=2026-08-24	TrainingPeaks PMC history export
```

---

## 6. Timeline Detail 2025-26

**Header row (A1:AA1):**

| Col | Header |
|---|---|
| A | Row Type |
| B | Athlete |
| C | Service |
| D | Week Start |
| E | Week End |
| F | Date |
| G | Day |
| H | Week Type |
| I | CTL |
| J | ATL |
| K | TSB |
| L | Ramp Rate |
| M | Historical Set FTP |
| N | Current TP FTP |
| O | Status |
| P | Sport |
| Q | Title / Weekly Signal |
| R | TSS |
| S | RPE |
| T | Feeling |
| U | Athlete Comment |
| V | Suggested Coach Comment |
| W | Grade |
| X | Review / Email |
| Y | Email Status |
| Z | Source Link |
| AA | Source ID |

**First empty row: 7000.** Last populated row (6999): `Row Type=WORKOUT | Athlete=Tyrel Fuchs | Service=Lite | Week Start=2026-08-17 | Week End=2026-08-23 | Date=2026-08-21`. No formulas, no data validation. This tab interleaves one `WEEK` summary row per week with that week's `WORKOUT` rows -- both row types share the same 27 columns, with each type using the columns relevant to it and leaving the rest blank.

**73 rows to paste starting at A7000** — 52 `WEEK` rows (same PMC-derived data as Weekly Context, reshaped) each immediately followed by that week's `WORKOUT` rows where any exist (only the 21 workouts already in Workout Detail 2025-26 fall inside the PMC-covered date range, 2025-09-01 through 2026-08-29 — grouped here by the Monday-anchored week each workout's date falls in):

```
WEEK	Jesse Couch	Custom	2025-09-01	2025-09-07				93.2	106.5	-12.4						Completed TSS 868.5 (7 days)										
WEEK	Jesse Couch	Custom	2025-09-08	2025-09-14				96.3	113.8	-21.5	3.1					Completed TSS 785.5 (7 days)										
WEEK	Jesse Couch	Custom	2025-09-15	2025-09-21				90.9	75.4	5.1	-5.4					Completed TSS 434.5 (7 days)										
WEEK	Jesse Couch	Custom	2025-09-22	2025-09-28				90.9	81.1	10.4	0.0					Completed TSS 651.3 (7 days)										
WEEK	Jesse Couch	Custom	2025-09-29	2025-10-05				87.6	78.1	11.8	-3.3					Completed TSS 473.9 (7 days)										
WEEK	Jesse Couch	Custom	2025-10-06	2025-10-12				86.3	78.7	9.4	-1.3					Completed TSS 557.6 (7 days)										
WEEK	Jesse Couch	Custom	2025-10-13	2025-10-19				86.8	87.7	4.8	0.5					Completed TSS 622.6 (7 days)										
WEEK	Jesse Couch	Custom	2025-10-20	2025-10-26				74.2	34.1	39.9	-12.6					Completed TSS 36.0 (7 days)										
WEEK	Jesse Couch	Custom	2025-10-27	2025-11-02				71.5	51.1	24.5	-2.7					Completed TSS 394.4 (7 days)										
WEEK	Jesse Couch	Custom	2025-11-03	2025-11-09				71.8	66.1	1.2	0.3					Completed TSS 515.2 (7 days)										
WEEK	Jesse Couch	Custom	2025-11-10	2025-11-16				73.2	79.1	4.4	1.4					Completed TSS 558.3 (7 days)										
WEEK	Jesse Couch	Custom	2025-11-17	2025-11-23				75	85.9	-1.9	1.8					Completed TSS 589.1 (7 days)										
WEEK	Jesse Couch	Custom	2025-11-24	2025-11-30				63.4	29.2	30.9	-11.6					Completed TSS 0 (7 days)										
WEEK	Jesse Couch	Custom	2025-12-01	2025-12-07				53.5	9.9	43.3	-9.9					Completed TSS 0 (7 days)										
WEEK	Jesse Couch	Custom	2025-12-08	2025-12-14				45.2	3.4	42.4	-8.3					Completed TSS 0 (7 days)										
WEEK	Jesse Couch	Custom	2025-12-15	2025-12-21				38.2	1.1	37.8	-7.0					Completed TSS 0 (7 days)										
WEEK	Jesse Couch	Custom	2025-12-22	2025-12-28				32.8	2.9	30.1	-5.4					Completed TSS 20.8 (7 days)										
WEEK	Jesse Couch	Custom	2025-12-29	2026-01-04				34.5	35.9	8.7	1.7					Completed TSS 296.4 (7 days)										
WEEK	Jesse Couch	Custom	2026-01-05	2026-01-11				36.9	47.6	-17.7	2.4					Completed TSS 343.9 (7 days)										
WEEK	Jesse Couch	Custom	2026-01-12	2026-01-18				41	57.4	-25	4.1					Completed TSS 443.6 (7 days)										
WEEK	Jesse Couch	Custom	2026-01-19	2026-01-25				46.3	68.8	-26.3	5.3					Completed TSS 529.3 (7 days)										
WEEK	Jesse Couch	Custom	2026-01-26	2026-02-01				47.6	54.9	-15.3	1.3					Completed TSS 388.5 (7 days)										
WEEK	Jesse Couch	Custom	2026-02-02	2026-02-08				50.7	59.8	-7.1	3.1					Completed TSS 483.1 (7 days)										
WEEK	Jesse Couch	Custom	2026-02-09	2026-02-15				52.2	59.6	-10.3	1.5					Completed TSS 424.4 (7 days)										
WEEK	Jesse Couch	Custom	2026-02-16	2026-02-22				51.5	51.5	-7.4	-0.7					Completed TSS 331.7 (7 days)										
WEEK	Jesse Couch	Custom	2026-02-23	2026-03-01				50.4	49.1	4.8	-1.1					Completed TSS 307.5 (7 days)										
WEEK	Jesse Couch	Custom	2026-03-02	2026-03-08				51.4	59.7	-1.4	1.0					Completed TSS 385.5 (7 days)										
WEEK	Jesse Couch	Custom	2026-03-09	2026-03-15				53.1	63.6	-19.8	1.7					Completed TSS 433.5 (7 days)										
WEEK	Jesse Couch	Custom	2026-03-16	2026-03-22				55.6	71.3	-26.2	2.5					Completed TSS 473.4 (7 days)										
WEEK	Jesse Couch	Custom	2026-03-23	2026-03-29				57.9	72.6	-25.4	2.3					Completed TSS 490.4 (7 days)										
WEEK	Jesse Couch	Custom	2026-03-30	2026-04-05				58.1	63.9	-15.1	0.2					Completed TSS 410.9 (7 days)										
WEEK	Jesse Couch	Custom	2026-04-06	2026-04-12				55.3	48.2	0.4	-2.8					Completed TSS 281.1 (7 days)										
WEEK	Jesse Couch	Custom	2026-04-13	2026-04-19				55.5	51.7	-3.5	0.2					Completed TSS 400.8 (7 days)										
WEEK	Jesse Couch	Custom	2026-04-20	2026-04-26				51	37.3	8.6	-4.5					Completed TSS 178.3 (7 days)										
WEEK	Jesse Couch	Custom	2026-04-27	2026-05-03				53.8	57.5	-12	2.8					Completed TSS 484.2 (7 days)										
WEEK	Jesse Couch	Custom	2026-05-04	2026-05-10				55.8	64.3	-17.9	2.0					Completed TSS 465.6 (7 days)										
WEEK	Jesse Couch	Custom	2026-05-11	2026-05-17				58.4	67.9	-7.2	2.6					Completed TSS 513.8 (7 days)										
WEEK	Jesse Couch	Custom	2026-05-18	2026-05-24				56.7	48.9	1	-1.7					Completed TSS 341.3 (7 days)										
WEEK	Jesse Couch	Custom	2026-05-25	2026-05-31				62.3	79.6	1.2	5.6					Completed TSS 652.1 (7 days)										
WEEK	Jesse Couch	Custom	2026-06-01	2026-06-07				65.2	81.7	-28.6	2.9					Completed TSS 559.4 (7 days)										
WEEK	Jesse Couch	Custom	2026-06-08	2026-06-14				64.4	67.7	-13.1	-0.8					Completed TSS 418.2 (7 days)										
WORKOUT	Jesse Couch	Custom	2026-06-08	2026-06-14	2026-06-10	Wed								Completed	Bike	Better Late Than Cadence 0	61				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-06-08	2026-06-14	2026-06-11	Thu								Completed	Bike	Short vo2 90s on/60s off	83			I'm a little rusty, but this was a solid effort	Good early-season marker -- rust is expected this early, and the numbers back up 'solid effort.' No change needed, just log it as a baseline.		Draft — not posted		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-06-08	2026-06-14	2026-06-11	Thu								Completed	Bike	Get out of the Center	6				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-06-08	2026-06-14	2026-06-12	Fri								Completed	Strength	Upper	5				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-06-08	2026-06-14	2026-06-13	Sat								Completed	Bike	Base - 210 min + Time in the drops	163				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WEEK	Jesse Couch	Custom	2026-06-15	2026-06-21				64.5	65.6	-10.5	0.1					Completed TSS 455.2 (7 days)										
WORKOUT	Jesse Couch	Custom	2026-06-15	2026-06-21	2026-06-15	Mon								Completed	Strength	LEGS - Heavy	10				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-06-15	2026-06-21	2026-06-15	Mon								Completed	Bike	Easy - 60min	35			Errands as well 30 minutes shopping	Noted -- active day outside the ride too. No workout concern here.		Draft — not posted		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-06-15	2026-06-21	2026-06-16	Tue								Completed	Bike	Better Late Than Cadence 3	113			This was a bit better than last weeks Cadence work. I will switch out my cassette for one with tighter gearing.	Good self-diagnosis on the cadence work. Worth a follow-up once the tighter-ratio cassette is on -- curious whether it changes the cadence numbers on the next Cadence session.		Draft — not posted		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-06-15	2026-06-21	2026-06-17	Wed								Completed	Strength	Upper	5				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-06-15	2026-06-21	2026-06-18	Thu								Completed	Bike	VO2 Max Party v2.1	87				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-06-15	2026-06-21	2026-06-18	Thu								Completed	Strength	LEGS - maintenance	5				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-06-15	2026-06-21	2026-06-20	Sat								Completed	Bike	Base - 240min + Time in the drops	191			I flatted and then it got hot, then HR spiked	Mechanical + heat spike, not a fitness red flag. Worth a quick ack -- anything needed on the flat-fix side (spares, tools) before the next long ride?		Draft — not posted		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WEEK	Jesse Couch	Custom	2026-06-22	2026-06-28				64.7	66.8	-11.6	0.2					Completed TSS 459.3 (7 days)										
WORKOUT	Jesse Couch	Custom	2026-06-22	2026-06-28	2026-06-22	Mon								Completed	Bike	Easy - 60min	36				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-06-22	2026-06-28	2026-06-22	Mon								Completed	Strength	LEGS Maintenance	5				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-06-22	2026-06-28	2026-06-23	Tue								Completed	Bike	The Assessment - Functional Threshold	96			Either Age finally caught me or I have great room for improvement. The good news is my leg power balance finally went 50/50	The 50/50 leg-power-balance shift is worth flagging back to him as a real positive, separate from the wattage number itself -- balance improvements often matter more than the raw FTP delta test-to-test.		Draft — not posted		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WEEK	Jesse Couch	Custom	2026-06-29	2026-07-05				65.7	70.7	-15.2	1.0					Completed TSS 493.4 (7 days)										
WEEK	Jesse Couch	Custom	2026-07-06	2026-07-12				66.8	73	-16.7	1.1					Completed TSS 508.7 (7 days)										
WEEK	Jesse Couch	Custom	2026-07-13	2026-07-19				63.1	53.7	2	-3.7					Completed TSS 302.5 (7 days)										
WEEK	Jesse Couch	Custom	2026-07-20	2026-07-26				65	69	-13.9	1.9					Completed TSS 524.7 (7 days)										
WEEK	Jesse Couch	Custom	2026-07-27	2026-08-02				67.8	78.2	-21.8	2.8					Completed TSS 578.6 (7 days)										
WEEK	Jesse Couch	Custom	2026-08-03	2026-08-09				66.3	65.1	-8.1	-1.5					Completed TSS 404.2 (7 days)										
WEEK	Jesse Couch	Custom	2026-08-10	2026-08-16				69.3	76.7	-18.4	3.0					Completed TSS 606.5 (7 days)										
WEEK	Jesse Couch	Custom	2026-08-17	2026-08-23				69.8	73.5	-14.2	0.5					Completed TSS 508.5 (7 days)										
WORKOUT	Jesse Couch	Custom	2026-08-17	2026-08-23	2026-08-22	Sat								Completed	Bike	The Assessment - Metabolism 3	196				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WEEK	Jesse Couch	Custom	2026-08-24	2026-08-30				73.9	91.8	-0.7	4.1					Completed TSS 596.3 (6 days); partial week, data through 2026-08-29										
WORKOUT	Jesse Couch	Custom	2026-08-24	2026-08-30	2026-08-24	Mon								Completed	Bike	Base - 150 min + Time in the Drops	136				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-08-24	2026-08-30	2026-08-25	Tue								Completed	Bike	30/15 Ronn	98				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-08-24	2026-08-30	2026-08-26	Wed								Completed	Strength	Upper	5				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-08-24	2026-08-30	2026-08-27	Thu								Completed	Bike	Base - 150 min + Time in the Drops	141				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
WORKOUT	Jesse Couch	Custom	2026-08-24	2026-08-30	2026-08-29	Sat								Completed	Bike	Zone 6: FOUR 1 minuters	216				No workout reply needed.		No action		https://app.trainingpeaks.com/#calendar/athletes/1177325	
```

---

## 7. Workout Detail 2025-26

**Header row (A1:AB1) — confirmed identical order/text to the athlete-level file (28 columns):**

| Col | Header | Col | Header |
|---|---|---|---|
| A | Workout ID | B | Athlete |
| C | Service | D | Week Start |
| E | Date | F | Day |
| G | Sport | H | Title |
| I | Status | J | Duration |
| K | Distance | L | TSS |
| M | RPE | N | Feeling |
| O | Readiness | P | Execution |
| Q | Nutrition | R | Misc |
| S | Description | T | Athlete Comment |
| U | Comment Count | V | Comment Truncated |
| W | Review Status | X | Suggested Coach Comment |
| Y | Coach Format | Z | Draft Status |
| AA | Source | AB | Source URL |

**First empty row: 5993.** Last populated row (5992): `Workout ID=3888617466 | Athlete=Edward Shapiro | Service=Premium | Week Start=2026-08-17 | Date=2026-08-21 | Day=Fri`. No formulas, no data validation.

**21 rows to paste starting at A5993** — identical content to `Workout Detail 2025-26` in the athlete-level xlsx (schema matches exactly, no remapping needed). `Workout ID` is blank for all 21 -- these came from Gmail workout-notification emails (June/Aug 2026), not a live TP calendar pull, so no real numeric workout ID exists in the sources; do not invent one.

```
	Jesse Couch	Custom	2026-06-08	2026-06-10	Wed	Bike	Better Late Than Cadence 0	Completed	1:21:00	23.0 mi	61						159W avg / 185W NP	The point of the ending intervals isn't to throw down big power, it's to force your muscles to fire fast.		0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-06-08	2026-06-11	Thu	Bike	Short vo2 90s on/60s off	Completed	1:22:00	24.0 mi	83						174W avg / 214W NP		I'm a little rusty, but this was a solid effort	1	0	Ready for coach edit	Good early-season marker -- rust is expected this early, and the numbers back up 'solid effort.' No change needed, just log it as a baseline.	Acknowledge → Assess → Adjust → Ask	Draft — not posted	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-06-08	2026-06-11	Thu	Bike	Get out of the Center	Completed	0:13:00	3.0 mi	6									0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-06-08	2026-06-12	Fri	Strength	Upper	Completed	0:30:00		5									0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-06-08	2026-06-13	Sat	Bike	Base - 210 min + Time in the drops	Completed	3:51:00	65.0 mi	163							Alternate 1/2 hour in the drops, 1/2 hour out.		0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-06-15	2026-06-15	Mon	Strength	LEGS - Heavy	Completed	0:30:00		10									0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-06-15	2026-06-15	Mon	Bike	Easy - 60min	Completed	1:02:00	16.0 mi	35						137W avg / 151W NP		Errands as well 30 minutes shopping	1	0	Ready for coach edit	Noted -- active day outside the ride too. No workout concern here.	Acknowledge → Assess → Adjust → Ask	Draft — not posted	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-06-15	2026-06-16	Tue	Bike	Better Late Than Cadence 3	Completed	2:11:00	39.0 mi	113						171W avg / 187W NP	The point of the ending intervals isn't to throw down big power, it's to force your muscles to fire fast.	This was a bit better than last weeks Cadence work. I will switch out my cassette for one with tighter gearing.	1	0	Ready for coach edit	Good self-diagnosis on the cadence work. Worth a follow-up once the tighter-ratio cassette is on -- curious whether it changes the cadence numbers on the next Cadence session.	Acknowledge → Assess → Adjust → Ask	Draft — not posted	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-06-15	2026-06-17	Wed	Strength	Upper	Completed	0:30:00		5									0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-06-15	2026-06-18	Thu	Bike	VO2 Max Party v2.1	Completed	1:15:00	23.0 mi	87						184W avg / 217W NP	10x20/40s@130%, 8x30/15s@115%, 3min@110%, 5x40/20s@120%, 5min@110%		0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-06-15	2026-06-18	Thu	Strength	LEGS - maintenance	Completed	0:20:00		5									0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-06-15	2026-06-20	Sat	Bike	Base - 240min + Time in the drops	Completed	4:07:00	71.0 mi	191						170W avg / 177W NP	Alternate 1/2 hour in the drops, 1/2 hour out.	I flatted and then it got hot, then HR spiked	1	0	Ready for coach edit	Mechanical + heat spike, not a fitness red flag. Worth a quick ack -- anything needed on the flat-fix side (spares, tools) before the next long ride?	Acknowledge → Assess → Adjust → Ask	Draft — not posted	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-06-22	2026-06-22	Mon	Bike	Easy - 60min	Completed	1:00:00		36									0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-06-22	2026-06-22	Mon	Strength	LEGS Maintenance	Completed	0:20:00		5									0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-06-22	2026-06-23	Tue	Bike	The Assessment - Functional Threshold	Completed	1:16:00	15.0 mi	96						159W avg / 226W NP	20-minute FTP test protocol (12min progressive warmup, 5m RPE6, 5m RPE2, 5m RPE8-10 all-out, 5m RPE2, then 20m all-out, 10m cooldown).	Either Age finally caught me or I have great room for improvement. The good news is my leg power balance finally went 50/50	1	0	Ready for coach edit	The 50/50 leg-power-balance shift is worth flagging back to him as a real positive, separate from the wattage number itself -- balance improvements often matter more than the raw FTP delta test-to-test.	Acknowledge → Assess → Adjust → Ask	Draft — not posted	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-08-17	2026-08-22	Sat	Bike	The Assessment - Metabolism 3	Completed	4:30:00	80.0 mi	196						166W avg / 178W NP	This ride is about steady on the gas. Looking for where HR decouples so we can see where aerobic fitness is... RPE should be 6/10 to start and grow towards the end... 10min warm up by heart rate and then settle in at the top of your z2/bottom of z3 heart wattage and hold it there for 3 hours to start.		0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-08-24	2026-08-24	Mon	Bike	Base - 150 min + Time in the Drops	Completed	2:58:00	56.0 mi	136						173W avg / 183W NP	Alternate 30 min riding on the hoods, 30 minutes riding in the drops.		0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-08-24	2026-08-25	Tue	Bike	30/15 Ronn	Completed	1:23:00	20.0 mi	98						166W avg / 228W NP			0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-08-24	2026-08-26	Wed	Strength	Upper	Completed	0:30:00		5									0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-08-24	2026-08-27	Thu	Bike	Base - 150 min + Time in the Drops	Completed	3:10:00	60.0 mi	141						170W avg / 180W NP	Alternate 30 min riding on the hoods, 30 minutes riding in the drops.		0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
	Jesse Couch	Custom	2026-08-24	2026-08-29	Sat	Bike	Zone 6: FOUR 1 minuters	Completed	4:00:00	73.0 mi	216						177W avg / 195W NP	4 x 1 min on 1 min off; FuULL GAS - Zone 6 Intervals! As hard as you can.		0	0	No action	No workout reply needed.	Acknowledge → Assess → Adjust → Ask	No action	TrainingPeaks (via Gmail workout-notification email)	https://app.trainingpeaks.com/#calendar/athletes/1177325
```

---

## 8. Engagement 2025-26

**Header row (A1:V1):**

| Col | Header |
|---|---|
| A | Athlete |
| B | Service |
| C | Last Weekly Review |
| D | Days Since Review |
| E | Reviews Sent · 28d |
| F | Last Athlete Contact |
| G | Days Since Athlete Contact |
| H | Athlete Comments · 28d |
| I | Planned Workouts · 28d |
| J | Completed Workouts · 28d |
| K | Workout Adherence |
| L | Comment Completeness |
| M | Goal Clarity |
| N | Open Loops |
| O | Exception Flags |
| P | Data Coverage |
| Q | Engagement Score |
| R | Churn Risk |
| S | Tier |
| T | Why / Evidence |
| U | Recommended Coach Action |
| V | Last Calculated |

**First empty row: 22.** Last populated row (21): `Athlete=Forest Hietpas | Service=Premium | Last Weekly Review=2025-08-18 | Days Since Review=368.0`. No formulas, no data validation (values are static per-athlete snapshots, presumably recalculated by an external process each pull).

**I partially computed this one against the Methods & Sources 2025-26 rubric (Area='Engagement model'), transparently, with the gaps shown**, rather than leaving the whole row blank -- flag everything below before trusting the number:

- Athlete contact recency 30%: last athlete-initiated email 2026-08-29 (same day as this build) → 0 days → weight 1.0.
- Athlete workout comments 20%: **not computed.** The rubric's denominator is "service expectation: Lite 4; Premium 8" -- Jesse's tier is `custom`, which has no defined expectation anywhere I found. 0 comments landed in the last 28 days regardless (all 5 comments in TP Comment Queue are from June).
- Workout adherence 15%: **not computed.** No historical planned-workout count exists for any 28-day window in the available sources (same gap as Weekly Brief/Context Planned TSS).
- Review cadence 15%: 0 reviews sent in 28 days (Weekly Review Composer has none) → weight 0.
- Comment completeness 10%: 0 commented / 6 completed workouts in the last 28 days (2026-08-01 through 2026-08-29, from Workout Detail 2025-26) → weight 0.
- Goal clarity 10%: no sent review exists to carry a goal statement → weight 0 (missing).
- **Confidence gate**: available weight = 30 (recency) + 15 (cadence) + 10 (completeness) + 10 (goal) = 65% ≥ the rubric's 50% gate, so a score is technically calculable: weighted sum (0.30×1.0 + 0.15×0 + 0.10×0 + 0.10×0 = 0.30) ÷ 0.65 available weight ≈ **46**. That would land in the rubric's "Watch" tier (<60) and Churn Risk ≈54 -- **but this number is built on 2 of the 5 signal families being structurally unavailable for a `custom`-tier athlete (workout comments, adherence), not on genuine low engagement.** Jesse is one of the most engaged, detailed correspondents in the archive (47 messages, 22 substantive email threads in under 3 months). Recommend treating this Engagement Score as a data-coverage artifact, not a real signal, until the rubric has a `custom`-tier denominator.

**Row to paste at A22:**

```
Jesse Couch	Custom			0	2026-08-29	0	0		6		0	0	3 open threads (sodium screenshot 08-27, Weight/Food Update 08-29, What Went Well + Race Plan 08-29 with an explicit open question) awaiting coach reply; mid-August FTP retest wattage never captured.	custom-tier denominator undefined for workout-comment and adherence signals (see notes above)	Partial — 4 of 6 weighted signal families available (65% weight); no historical planned-workout data for this athlete in any source	46	54	Watch (data-coverage artifact — see notes, not a real low-engagement signal)	Score is depressed by 2 structurally-missing signal families for `custom` tier, not by actual disengagement — see full breakdown in master_sheet_additions.md before acting on the tier label.	Define a custom-tier denominator for the engagement/adherence signals, or exclude custom-tier athletes from Engagement Score until that exists.	2026-08-29
```

---

## 9. Wellness 2025-26

**Header row (A1:AM1) — 39 columns, adds a Sleep/Body-Battery/Stress block (AC:AM) beyond the athlete-level file's 28 columns:**

| Col | Header | Col | Header |
|---|---|---|---|
| A | Athlete | B | Date |
| C | Source | D | Weight |
| E | Weight Unit | F | Weight · 7d Avg |
| G | Weight · 28d Change % | H | Resting HR |
| I | RHR · 7d Avg | J | RHR · Prior-60d Baseline |
| K | RHR SWC | L | RHR Status |
| M | HRV Metric | N | HRV Raw |
| O | HRV Analysis Value | P | Valid HRV Days · 7d |
| Q | HRV · 7d Avg | R | HRV · 7d CV % |
| S | Valid HRV Days · Prior 60d | T | HRV · Prior-60d Baseline |
| U | HRV · Prior-60d CV % | V | HRV SWC |
| W | Normal Low | X | Normal High |
| Y | HRV Status | Z | Context · Sleep / Stress / Illness / Load |
| AA | Coach Interpretation | AB | Data Quality |
| AC | Sleep Hours | AD | Sleep · 7d Avg |
| AE | Sleep · Prior-28d Baseline | AF | Sleep Δ vs 28d |
| AG | Valid Sleep Days · 7d | AH | Deep Sleep |
| AI | REM Sleep | AJ | Awake |
| AK | Body Battery Low | AL | Body Battery High |
| AM | Stress Avg |  |  |

**First empty row: 3336.** Last populated row (3335): `Athlete=Forest Hietpas | Date=2026-08-21 | Source=TrainingPeaks / Garmin Health`. No formulas, no data validation.

**4 rows to paste starting at A3336** — same weight data as the athlete-level xlsx's Wellness 2025-26 tab; the extra Sleep/Body-Battery/Stress columns (AC:AM) are blank -- no Garmin/wearable source exists anywhere in the available sources, only self-reported bathroom-scale weight in emails:

```
Jesse Couch	2026-06-09	Order intake questionnaire (via 2026-06-09 pipeline-fail email)	69.9	kg																						Intake baseline, pre-plan. Never reconciled against the later self-reported stable weight.	No RHR/HRV data in available sources (profile.yaml: resting_hr/max_hr/lthr all null).											
Jesse Couch	2026-08-26	Athlete self-report, email 2026-08-26 (1a03fa01690b8664)	151.5	lb																						Athlete states this has been stable for 2 months (approx. 2026-06-26 to 2026-08-26).	No RHR/HRV data in available sources (profile.yaml: resting_hr/max_hr/lthr all null).											
Jesse Couch	2026-08-29	Athlete self-report, Weight/Food Update email 2026-08-29 (pre-ride)	153.0	lb																						Pre-ride weight before a 4h endurance ride with 4x1min efforts, ~80F.	No RHR/HRV data in available sources (profile.yaml: resting_hr/max_hr/lthr all null).											
Jesse Couch	2026-08-29	Athlete self-report, Weight/Food Update email 2026-08-29 (post-ride)	152.3	lb																						0.7lb loss across the 4h ride + 4x1min in ~80F heat; consistent with fluid loss on a ride he reports 420g carb / 105g-per-hour fueling for, not an underfueling signal. Athlete reports feeling 'pretty good' afterward.	No RHR/HRV data in available sources (profile.yaml: resting_hr/max_hr/lthr all null).											
```

---

## 10. FTP Audit 2025-26

**Header row (A1:I1) — confirmed identical order/text to the athlete-level file:**

| Col | Header |
|---|---|
| A | Athlete |
| B | Current TrainingPeaks Threshold Power (W) |
| C | Verified Date |
| D | Latest Plausible Legacy sFTP (W) |
| E | Legacy Week |
| F | Difference (TP − Legacy) |
| G | Status |
| H | Legacy Sheet |
| I | Workbook ID |

**First empty row: 22.** Last populated row (21): `Athlete=Forest Hietpas | Current TP Threshold Power=320.0 | Verified Date=2026-08-21 | Latest Plausible Legacy sFTP=300.0 | Legacy Week=2026-08-12 | Difference=20.0`. No formulas, no data validation.

**Row to paste at A22** — identical content to the athlete-level xlsx's FTP Audit tab:

```
Jesse Couch	270	2026-06-23				STALE — athlete reports a materially higher retest ~2026-08-17 ("Functional Threshold Test this past Monday was up a fair amount since June", email 2026-08-21) but no TP threshold-notification email or wattage exists anywhere in the archive for it. Pull the actual value from TrainingPeaks directly before using FTP for zone-setting -- see open_questions.md item 1.	N/A — no legacy workbook for this athlete (new-build, not a migrated legacy athlete)	
```

---

## 11. Context Ledger 2025-26

**Header row (A1:Y1) — confirmed identical order/text to the athlete-level file (25 columns):**

| Col | Header | Col | Header |
|---|---|---|---|
| A | Event ID | B | Athlete |
| C | Athlete Email | D | Week Start |
| E | Week End | F | Event Date |
| G | Source | H | Source Type |
| I | Direction | J | Subject / Workout |
| K | Grade | L | Readiness |
| M | Execution | N | Nutrition |
| O | Misc | P | Good |
| Q | Better | R | Goal Context |
| S | Notes / Big Picture | T | Next Action / This Week |
| U | Raw Text | V | Source Link |
| W | Theme Tags | X | Needs Review |
| Y | Confidence |  |  |

**First empty row: 7243.** Last populated row (7242): `Event ID=decision:forest-hietpas:2026-08-21 | Athlete=Forest Hietpas | Athlete Email=olympicsherpa@gmail.com | Week Start=2026-08-17 | Week End=2026-08-23 | Event Date=2026-08-21`. No formulas, no data validation.

**27 rows to paste starting at A7243** — identical content to `Context Ledger 2025-26` in the athlete-level xlsx (schema matches exactly, no remapping needed). Scope note: these are the 24 correspondence-level events (2 system pipeline-fail emails + 22 direct Jess↔Matti email threads) plus 3 items I'd already flagged `Needs Review=TRUE` for the open loops — the 21 TP workout-notification events are covered separately in Workout Detail 2025-26 / Timeline Detail 2025-26 above, not duplicated here (this mirrors how Edward Shapiro's Context Ledger reads — it carries correspondence, not workout data).

```
gmail-sys:19eae115ee385a1f	Jesse Couch	jesseanthonycouch@gmail.com	2026-06-08	2026-06-14	2026-06-09	Gmail	System	System → Coach	[GG] FAILED: Jesse Couch — Borderlands AZ State Championships									First pipeline attempt failed same day as order.	Manual recovery required.	PIPELINE FAILED: Jesse Couch. Race: Borderlands AZ State Championships (2026-11-14). Tier: custom | FTP: 275W | Weight: 69.9 kg | Hours/week: 12-15. Order: cs_live_a1Rh64ACwrI3DU2RVNiWHav5CAaLl1s3eu7jdTsV5rd2zgNSvjAoilS4Vj. Error: Check Railway logs for details.		pipeline-fail, order, system	FALSE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-06-08	2026-06-14	2026-06-09	Gmail	System	System → Coach	[GG] FAILED: Jesse Couch — Borderlands AZ State Championships (retry)									Second same-day pipeline attempt also failed.	Manual recovery required.	PIPELINE FAILED (retry): Order test_20260609202213. ERROR: Pipeline timed out after 300s.		pipeline-fail, order, system	FALSE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-06-08	2026-06-14	2026-06-11	Gmail	Athlete Email	Athlete → Coach	Re: Payment confirmed — your training plan for Borderlands AZ State Championships									Workouts landed on TP calendar but PDF guide never arrived.	Coach hand-sends PDF guide + gym-day guidance.	Thanks for the training program. I never received the PDF training guide however. Also, if you could give me some information on what is expected on leg day at the gym it would be greatly appreciated... I am thinking I may need to back way off of gym intensity on Mondays in order to be able to properly perform the higher intensity efforts on the bike on Tuesday.		delivery-gap, strength, onboarding	FALSE	High — verbatim Gmail archive
gmail-out:19ebd615b6a00650	Jesse Couch	jesseanthonycouch@gmail.com	2026-06-08	2026-06-14	2026-06-12	Gmail	Coach Email	Coach → Athlete	Fwd: Payment confirmed — your training plan for Borderlands AZ State Championships									Coach hand-attaches Jesse-Couch-Training-Guide.pdf and answers strength-periodization question. States athlete age as 60 (coach-asserted, never athlete-confirmed -- see open_questions.md #7).	None on this thread.	See attached training pdf. As for strength... in general, 20 weeks out from your event, if you don't have big strength deficits, you can emphasize strength work more and lift heavier weights for shorter reps... Since you're 60, it's more important than ever to be consistent in the gym to keep your strength and mobility sharp.		strength, delivery-gap, age-unconfirmed	FALSE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-06-08	2026-06-14	2026-06-13	Gmail	Athlete Email	Athlete → Coach	Re: Payment confirmed — your training plan for Borderlands AZ State Championships											I appreciate this. Thank You		gratitude	FALSE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-06-22	2026-06-28	2026-06-22	Gmail	Coach Email	Coach → Athlete	Check In											Matti here checking in. How is the training plan going so far? All good? Keep me in the loop!		check-in	FALSE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-06-22	2026-06-28	2026-06-23	Gmail	Athlete Email	Athlete → Coach	Re: Check In									First hint of the volume concern that resurfaces 08-26. Heat-driven HR drift flagged this early.		The training is going great. I like the plan, it seems a bit light in total from what I am used to doing. However, the hard days are plenty hard, and clearly my endurance is still lacking... My HR seems to start launching 2 to 2.5 hrs into the ride and coincidentally the same time the heat goes thru the roof. This is my testing week.		volume-concern, heat-hr-drift, testing-week	FALSE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-06-29	2026-07-05	2026-07-04	Gmail	Athlete Email	Athlete → Coach	Re: Check In											Things are going in the right direction with the Bike. I managed to keep my heart rate down for my 5 hour endurance ride today... I had to add some warm up and warm down time to the interval sessions though, as some of them didn't really allow me to get far enough out of town to not get killed.		progress, warmup-adjustment	FALSE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-06-29	2026-07-05	2026-07-04	Gmail	Coach Email	Coach → Athlete	Re: Check In									Coach establishes explicit coaching identity: steady/sane progress, not crash-diet ramps.		Excellent. Glad the plan and workouts are working for you so far. Realize that I'm not a 'crash diet' kind of coach so you can expect steady, sane progress, not a ramp that works/seems magical right up until the moment you explode. Re. Warm up - excellent... Generally as we get older the demand increases.		coaching-identity	FALSE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-07-20	2026-07-26	2026-07-26	Gmail	Athlete Email	Athlete → Coach	Re: Check In									First fueling flag (75g baseline vs. 90g bloating) and first push to de-prioritize Sept Czech races.	Coach closes this loop on 08-20.	All is well with the training... My weight has dropped 2 lbs since we started. I had been consuming 75 grams of carb per hour on all my long Saturday Endurance rides, with Zero problems. Yesterday, I went for 90 grams. 90 grams caused a bit of bloating... Also, I want to emphasize that the races the first weekend in September are purely for fun... I would prefer to focus on my long term goals which are in November.		fueling, sept-races-reframe	FALSE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-17	2026-08-23	2026-08-20	Gmail	Coach Email	Coach → Athlete	Re: Check In									Coach closes the 07-26 loop (carbs, Sept races) and discovers athlete fell off the TP coaching connection at some unknown point.	Awaiting TP reconnection before calendar changes can land.	You were right to flag both of these... On the carbs: 75 grams per hour with zero problems is a strong baseline, so stay there... For the longer November race efforts, we can test 80 and then 85 grams per hour... On September: agreed... I checked TrainingPeaks before replying, and you're no longer showing under my coaching account... Please reconnect your account using this link: https://home.trainingpeaks.com/attachtocoach?sharedKey=2OTEPC6BXNVQU		fueling, sept-races, tp-reconnect	FALSE	High — verbatim Gmail archive
gmail-in:1a022a3f0c129430	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-17	2026-08-23	2026-08-21	Gmail	Athlete Email	Athlete → Coach	Re: Check In									TP reconnected. Athlete discloses self-directed lower-body-to-Z2 swap. Reports a mid-August FTP retest -- no wattage given anywhere in the archive (top open item, open_questions.md #1).	Coach to pull actual mid-August FTP wattage from TrainingPeaks directly.	The account is connected. You will notice I removed all Leg Work at the Gym a few weeks ago and replaced it with Zone 2 riding... My Functional Threshold Test this past Monday was up a fair amount since June, so I adjusted my Training Zones accordingly. It's pretty clear I will struggle to get to my previous FTP marks as that 5 minute "all out" protocol really takes the zing out of your attitude.		tp-reconnect, strength-swap, ftp-retest-unresolved	TRUE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-17	2026-08-23	2026-08-21	Gmail	Athlete Email	Athlete → Coach	Re: Check In									First detailed fueling-product breakdown.		I forgot to address the carb question. I use Hot Sports Drink by Activlab (Polish Company) 32g of carbs per serving x 4 for my rides so 128 ish. Then gels for the remainder NduranZ Nrgy Gel 45 (Slovenia) 45 g of carbs per gel... I am carrying 950 ml bottles with the Hot Sports Drink inside and 2 liters of water in a hydration pak on my back.		fueling-detail	FALSE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-17	2026-08-23	2026-08-22	Gmail	Coach Email	Coach → Athlete	Re: Check In									Coach answers all 4 questions from the 08-21 emails in one structured reply.		Can we treat the September races as training instead of tapering for them? Yes... Should the Zone 2 rides replace lower-body gym work? For now, yes... Should I stay at 75 grams of carbohydrate per hour or keep pushing toward 90? Stay at 75 g/hour as your baseline... How should I interpret the improved FTP test? As a good sign.		sept-races, strength-swap, fueling, ftp	FALSE	High — verbatim Gmail archive
gmail-in:1a027b68b3c03519	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-17	2026-08-23	2026-08-22	Gmail	Athlete Email	Athlete → Coach	Re: Check In									Athlete unprompted offers extra payment.	Coach to decline and offer upsell instead.	Thank You for this valuable information. I would like to send you more funds. Please tell me how you would like it sent.		upsell-signal, gratitude	FALSE	High — verbatim Gmail archive
gmail-out:1a028223a1cdaa8a	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-17	2026-08-23	2026-08-22	Gmail	Coach Email	Coach → Athlete	Re: Check In									Coach declines extra funds, offers structured ongoing-coaching upsell with no pressure.		That's incredibly kind—thank you. You don't owe me anything extra for these recent questions and adjustments... If you'd like more structured ongoing coaching through Borderlands—regular check-ins, plan adjustments, and closer review—I'm happy to send you those options. No pressure whatsoever.		upsell-offered	FALSE	High — verbatim Gmail archive
gmail-in:1a029e644701fbb3	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-17	2026-08-23	2026-08-22	Gmail	Athlete Email	Athlete → Coach	Re: Check In									Detailed fueling self-audit reveals actual intake far above stated 75g/hr baseline.	Coach to correct the math and issue a measurement-before-adjustment ruling (done 08-24).	Okay, so today I did my Metabolism 3 Assesment. 4.5 hours total... So today during a 4.5 hour ride I consumed: 428 grams of carbs/ 107 grams per hour, 5,290 mg of sodium... This is what I have been doing week after week all summer long.		fueling, measurement-reveals-gap	FALSE	High — verbatim Gmail archive
gmail-out:1a034ac481405371	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-24	2026-08-30	2026-08-24	Gmail	Coach Email	Coach → Athlete	Re: Check In									Coach corrects the sodium math and sets the standing rule: measurement before adjustment.	Next controlled ride: weigh before/after, record fluid finished, confirm sodium-per-flask assumption.	This is the useful discovery: you haven't been fueling at 75 g/hour. If you finished everything listed, the math is 428 g carbohydrate over 4.5 hours—about 95 g/hour... Sodium totals closer to 5,740 mg, not 5,290... Don't panic or start cutting things randomly... The measurement comes before the adjustment.		fueling, measurement-before-adjustment	FALSE	High — verbatim Gmail archive
gmail-out:1a03f12b305466a2	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-24	2026-08-30	2026-08-26	Gmail	Coach Email	Coach → Athlete	Re: Re: Check In									v2 rebuild announced -- engine-migration context (repo's June 2026 block-builder overhaul, the 'Jesse Couch incident', see coaching_history.md).	Athlete to review and confirm.	Your fall block got the full rebuild this week... Your old plan was still running on my previous engine; everything from now through Borderlands and El Tour is new, including the two weeks off after El Tour that were missing entirely... Every workout carries an RPE number... Strength is exactly what we agreed... The Czech races stay as agreed... Borderlands Nov 14 is the A-race, El Tour Nov 21 the B-race ridden on residual fitness.		engine-rebuild, v2, race-priorities-confirmed	FALSE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-24	2026-08-30	2026-08-26	Gmail	Athlete Email	Athlete → Coach	Re: Re: Check In									Initial positive reaction to v2; states intent to continue coaching into next season.		Awesome. Thank You. I will check it out now. I will definitely going to continue this relationship. I will need help after the November events, as I intend to do some UCI Gravel events again next year.		upsell-signal, retention	FALSE	High — verbatim Gmail archive
gmail-in:1a03fa01690b8664	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-24	2026-08-30	2026-08-26	Gmail	Athlete Email	Athlete → Coach	Re: Re: Check In									Major volume-pushback email, 3 hours after initial positive reaction to v2. States stable weight (151.5lb/2mo), operating point (700 TSS/12h), CTL trend (100 pre-CX to 72 now, projected low-40s by Nov), diagnoses the Z2-intensity-vs-quantity mechanical error, corrects Sept 7 travel assumption, gives full identity/motivation context. Apologizes for tone at close.	Coach to rebuild again (done same night / next morning as v3).	I have been weighing 151.5 for two months... I have to be honest with you, I like the previous plan much better. There are too many weeks where I am barely riding. When I signed up for your program, I said I ride great when I am doing about 700 TSS a week and 12ish hours. There are too many weeks of 200 TSS... The week of September 7 is not a Travel Week. I have a two hour flight from Czech to Italy, then I am home... I was a World Class Weightlifter in the 1980's... Yes, you are still assigning me a modest amount of Endurance work, but you lowered the quantity substantially and you lowered the Z2 intensity... if Z2 Intensity goes down, my quantity should go up.		volume-pushback, ctl-evidence, z2-mechanical-error, identity, weight-stated	FALSE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-24	2026-08-30	2026-08-26	Gmail	Coach Email	Coach → Athlete	Re: Re: Check In									Same-night acknowledgment of the pushback email.	v3 rebuild to follow by morning.	Love the feedback! I'll change it again with this info in mind and have you go through it		engine-rebuild, responsive	FALSE	High — verbatim Gmail archive
gmail-out:1a0414d61a60c387	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-24	2026-08-30	2026-08-27	Gmail	Coach Email	Coach → Athlete	Re: Check In									v3 rebuild delivered: load weeks matched to athlete's stated 700TSS/12h operating point, CTL re-run (~74 at Borderlands vs. old-plan low-40s), Sept 7 confirmed non-travel, post-El-Tour break added. Coach asks (not assumes) about optional recovery-week strength slot.	Awaiting athlete confirmation + answer to the optional-strength-slot question.	Good feedback. The plan is rebuilt and live on your calendar. What changed: 1. Load weeks are now 620-700 TSS at 11-13 hours. Recovery weeks are ~350-370, not 200. 2. I ran the CTL math on both versions. The old plan had you in the low 40s by November—you were right. The new one has you at ~74 arriving at Borderlands. 3. Sept 7 is a normal training week at home... 5. The two weeks after El Tour: no structure, no targets... One question: I added an optional upper-body/core gym slot in recovery weeks. Keep it, or would you rather have that time on the bike?		engine-rebuild, v3, ctl-corrected, open-question	TRUE	High — verbatim Gmail archive
gmail-in:1a0439687740b5a8	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-24	2026-08-30	2026-08-27	Gmail	Athlete Email	Athlete → Coach	Re: Check In									Athlete confirms v3 fit and gives 2 calendar corrections: Sept 8 flight date (not Monday), Oct 17 US high-school reunion with a ~3h ride planned.	Calendar corrections should be applied if not already reflected in calendar_baseline_v3.json.	I will keep the upper body work that I have been doing for years. I do 3 sets of 12, no assistance needed... Pull ups, Push ups, Bar dips, Sit ups, Bridge, Shrugs, Arm curls. My flight back to Italy is on Tuesday September 8. I was showing it on the 8th but you moved it to Monday. I also showed a ride on October 17th, the day of my reunion. I will definitely ride 3 ish hours that day with some friends from high school... I keep a bike there.		strength-confirmed, calendar-correction, travel	FALSE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-24	2026-08-30	2026-08-27	Gmail	Athlete Email	Athlete → Coach	Re: Check In									Product-label sodium correction, follow-up to the 08-24 'measurement before adjustment' ruling.	No coach reply present in the archive as of 2026-08-29 -- open loop.	I took a screenshot of the ingredients for the sports drink I consume... I use two portions per bottle, so 4 portions total. 197 mg of sodium per portion, so 394 mg of sodium per bottle, plus the sodium I add, plus the sodium from the gels.		fueling, sodium, open-loop	TRUE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-24	2026-08-30	2026-08-29	Gmail	Athlete Email	Athlete → Coach	Weight/Food Update									First live nutrition/weight log under the v3 plan.	No coach reply present in the archive as of 2026-08-29 -- open loop.	So today was 4 hours endurance with 4 one minuters towards the end... I weighed in after all of this at 153 lbs. After the 4 hour ride I weighed 152.3... I ate/drank 420 grams of carbs in total, so 105 grams per hour... 3.7l of liquid.		fueling, weight, open-loop	TRUE	High — verbatim Gmail archive
	Jesse Couch	jesseanthonycouch@gmail.com	2026-08-24	2026-08-30	2026-08-29	Gmail	Athlete Email	Athlete → Coach	What Went Well + Race Plan									Self-review of the Czech doubleheader (raced as training, per standing agreement) plus a race-pacing plan the athlete explicitly asked the coach to review.	No coach reply present in the archive as of 2026-08-29 -- open loop; athlete explicitly asked 'If the Race Plan does not work for you, please let me know.'	All went well. 11.5 hours of pedaling. Pw:Hr is hovering around 5% during the long efforts... Race Plan - It is an enduro format. 75 km of pedaling with 4 timed sections... I plan to Ride Zone 2 during the two races, until the 4 timed sections. Treat each timed sections as a 30 minute time trial.		self-review, race-plan, open-loop, czech-doubleheader	TRUE	High — verbatim Gmail archive
```

---

## 12. Messages Ledger 2025-26 — no row prepared

Header confirmed (A1:L1): Message ID, Athlete, Date, Direction, Sender, Service, Chat, Body, Attachments, Unread, Coaching Signal, Source. First empty row: **2937**. No formulas/validation. This tab holds raw SMS/iMessage text-message content — Jesse has no matched Messages/SMS chat in any available source (same conclusion as Messages Summary below), so there is no real message content to ledger. No placeholder row needed here; the "no match" state is recorded once, in Messages Summary.

---

## 13. Messages Summary

**Header row (A1:N1) — note this has 2 more columns than the athlete-level file (Sent · 28d, Received · 28d inserted at G/H):**

| Col | Header |
|---|---|
| A | Athlete |
| B | Matched Direct Chats |
| C | Messages · 1y |
| D | Sent · 1y |
| E | Received · 1y |
| F | Messages · 28d |
| G | Sent · 28d |
| H | Received · 28d |
| I | Last Text |
| J | Last Inbound |
| K | Last Outbound |
| L | Latest Direction |
| M | Unanswered Latest? |
| N | Coverage Note |

**First empty row: 22.** Last populated row (21): `Athlete=Forest Hietpas | Matched Direct Chats=1.0 | Messages · 1y=769.0 | Sent · 1y=411.0 | Received · 1y=358.0 | Messages · 28d=11.0`. No formulas, no data validation.

**Row to paste at A22:**

```
Jesse Couch	0	0	0	0	0	0	0					FALSE	No confidently matched direct Messages chat; no text history inferred
```

---

## 14. Methods & Sources 2025-26 — no row needed

This tab is athlete-invariant house methodology (16 rows, first empty row **17**, no formulas/validation) — already carries the exact same content I copied verbatim into the athlete-level xlsx's Methods & Sources tab. Nothing athlete-specific to add.

---

## 15. Review Audible Queue — no row prepared

Header confirmed (A1:T1): Schema Version, Review Item ID, Athlete Key, Athlete, Week Start, Theme, Key Workouts, Audible Rules · Email Exact, TP Athlete ID, Target Date, Note Title, Note Body, Review Fingerprint, Source IDs, **Approval** (validated list `HOLD,APPROVE TO POST,NEEDS EDIT,POSTED`, range O2:O100), Posted At, Provider Receipt, Provider Readback, Error, Workflow Note. **This entire tab is empty of data rows workbook-wide** (only the header row is populated for every athlete, not just Jesse) — first empty row **2**. No audible has been evidenced or drafted for Jesse in any available source, so nothing to add.

---

## 16. Connection Cadence

**Header row (A1:S1):**

| Col | Header |
|---|---|
| A | Schema Version |
| B | Athlete Key |
| C | Athlete |
| D | Service Tier |
| E | Coaching Start |
| F | Last Connection |
| G | Connection Channel |
| H | Connection Source ID |
| I | Due On |
| J | Overdue On |
| K | Status |
| L | Last Invited |
| M | Scheduled For |
| N | Prompt |
| O | Athlete Review Line |
| P | Booking URL |
| Q | Review Item ID |
| R | Updated At |
| S | Workflow Note |

**First empty row: 22.** Last populated row (21): `Schema Version=connection-cadence/v1 | Athlete Key=forest-hietpas | Athlete=Forest Hietpas | Service Tier=Premium`.

**Formulas — real gotcha here.** Columns I (Due On), J (Overdue On), K (Status), N (Prompt), O (Athlete Review Line) are formula-driven per row (not ARRAYFORMULA): row 2 carries the literal formula text (e.g. `K2`: `=IF(AND(M2<>"",M2>=TODAY()),"SCHEDULED",IF(I2="","NEEDS LAST CONNECTION",...))`), but rows 3-21 only carry the **cached values** in the xlsx export, not the formula text — the live Google Sheet almost certainly still has the row-relative formula in each row (this is a known Sheets→xlsx export quirk, not evidence the formulas were deleted). **Do not type static values into I, J, K, N, O for row 22** — after pasting the row, select I21:O21 and fill down into I22:O22 (or trigger Sheets' auto-fill-down suggestion) so row 22 gets a real, self-updating formula like every other row.

**Two real taxonomy gaps — flagging rather than forcing a wrong value:**

- **Service Tier (col D) is validated to `Premium,Lite` only.** Jesse's tier is `custom` (profile.yaml `fulfillment.tier: custom`) — neither valid option fits. Left blank below; decide whether custom-tier athletes get a new dropdown option or get mapped to one of the two existing ones for cadence-timing purposes.
- **Connection Channel (col G) is validated to `phone,video,in_person` only.** Every interaction in the archive is async email (47 messages, 0 calls/video/in-person meetings evidenced anywhere) — none of the 3 valid options fit. Left blank below for the same reason.

**Row to paste at A22** (everything the formula columns I/J/K/N/O would need, D and G left blank per the flags above, Last Connection left blank — no live-call event exists in the archive to anchor it to, only ongoing email correspondence):

```
connection-cadence/v1	jesse-couch	Jesse Couch		2026-06-09													2026-08-29	Service Tier and Connection Channel both fall outside their validated dropdown options for this athlete (custom tier, email-only relationship) — see notes above. Formula cols I/J/K/N/O need fill-down from row 21, not typed values.
```

---

## Summary

| # | Tab | Rows prepared | Paste-at row |
|---|---|---|---|
| 1 | Editor Queue 2025-26 | 1 | 45 |
| 2 | Weekly Review Composer | 0 (no real sent review exists) | — |
| 3 | TP Comment Queue | 5 | 6096 |
| 4 | Weekly Brief 2025-26 | 52 | 1009 |
| 5 | Weekly Context 2025-26 | 52 | 1009 |
| 6 | Timeline Detail 2025-26 | 73 (52 WEEK + 21 WORKOUT) | 7000 |
| 7 | Workout Detail 2025-26 | 21 | 5993 |
| 8 | Engagement 2025-26 | 1 (partially computed — see flags) | 22 |
| 9 | Wellness 2025-26 | 4 | 3336 |
| 10 | FTP Audit 2025-26 | 1 | 22 |
| 11 | Context Ledger 2025-26 | 27 | 7243 |
| 12 | Messages Ledger 2025-26 | 0 (no matched chat, nothing to ledger) | — |
| 13 | Messages Summary | 1 | 22 |
| 14 | Methods & Sources 2025-26 | 0 (shared boilerplate, already current) | — |
| 15 | Review Audible Queue | 0 (nothing evidenced/drafted) | — |
| 16 | Connection Cadence | 1 (2 fields flagged — dropdowns don't fit this athlete) | 22 |

**Total new rows across the workbook: 239.**


# Pipeline workout selection vs the curated GG TrainingPeaks libraries

Evaluated 2026-08-17 against a live pull of all 24 "GG |" bike libraries
(1,631 curated workouts; snapshot in
`~/Downloads/guillermo-romero-delivery/gg_tp_library.json`) and the
pipeline's `workout_library.yaml` (36 canonical types, 13 categories),
using the Sonja Field 9-week finisher plan as the usage sample.

## Duration norms (the 30-minute VO2 finding)

The curated library's own numbers back the coach ruling directly:

| GG library | n | median min | share under 45min |
|---|---|---|---|
| VO2 Classic | 98 | 69 | 2% |
| VO2 30-30s & Micro | 96 | 62 | 25% |
| VO2 Blends | 58 | 88 | 13% |
| Threshold (3 libs) | 172 | 73-90 | — |
| Sweet Spot Intervals | 102 | 88 | — |

The pipeline's VO2 ladders encoded 31-38 minutes at EVERY level — the
bare-minimum interval set with no aerobic volume around it. Fixed
2026-08-17: 30/30 and 40/20 ladders now run 45→62 min (Z2 padding around
the same interval sets, honestly reported in the main set), and
`post_render_validator` fails any <45-minute hard session on a day with
>=60 minutes available (`SHORT_QUALITY_SESSION`). Openers/tune-up priming
sessions stay deliberately short by design.

## Selection-breadth map

| GG library (curated n) | Pipeline coverage | Verdict |
|---|---|---|
| VO2 x3 (252) | 5 types | Covered (dose fixed above) |
| Threshold x3 (172) | 5 types | Covered |
| Endurance x3 (237) | 5 types + 6 focus variants | Covered |
| Tempo (66) | 3 types | Covered |
| Race Sim (85) | Act-composed from race facts | Covered, different method (composed > canned) |
| Testing & Openers (53) | FTP + Anaerobic tests, openers/tune-up | Covered |
| Torque x3 (218) | SFR, Stomps, Cadence Work, Mixed Climbing | Partial — thin vs 218 curated |
| Durability Tired Intervals (56, med 147min) | VO2 Bookend + Buffer only | **GAP** — the house's signature end-of-ride intervals pattern barely exists in the generator |
| Sprint & Attacks (65) | Microbursts only | **GAP** — no sprint/attack work at all in emitted plans |
| Anaerobic Capacity (48) | Stars In Your Eyes only | **GAP** — one archetype vs 48 curated |
| Sweet Spot x3 (186) | G-Spot only | Deliberate? — polarized methodology avoids SS; fine if intentional, wrong if an SS-appropriate athlete gets none |
| Skills & Specialty (101) | none | Expected — course/skills work is not generator territory yet |

## The structural finding

The pipeline renders its own 36 synthetic archetypes; it never selects
from the 1,631 curated TP library workouts. Curation work on the TP
library therefore does not flow into custom plans, and vice versa. Two
paths, coach's call:

1. **Grow the generator toward the gaps** — add tired-interval durability,
   sprint/attack, and 2-3 anaerobic-capacity types (cheap, keeps the
   composed-plan architecture).
2. **Teach the pipeline to place curated library items by
   exerciseLibraryItemId** — true convergence; the TP library becomes the
   single source and curation compounds into every custom order (bigger
   lift: needs a selection index over the library with
   category/duration/level metadata).

Filed as T21 (durability tired intervals), T22 (sprint/attacks +
anaerobic variety), T23 (library-convergence decision) pending coach
prioritization.

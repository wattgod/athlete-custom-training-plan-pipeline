# Coverage sweep — 2026-06-22-net2

**60/60 orders DELIVERED a plan (100%)** — the customer-facing number (no refund). Of those, 37 were clean and 23 need a coach pass before sending. **0 produced NO plan** (the only refund bucket).

Breadth complement to the daily depth judge: every cell is a real pipeline build. 'Clean' passes the deterministic send-worthy contract; 'needs review' delivered but tripped a compliance check (coach reviews before sending); 'failed' produced nothing.

## Pass rate by persona
- weekend_warrior: 33%
- masters_returner: 58%
- ambitious_first_timer: 66%
- time_crunched_parent: 75%
- veteran_podium_chaser: 75%

## Pass rate by discipline
- road: 60%
- gravel: 62%

## Failures by type (frequency)
- ×18  preview fail
- ×12  needs review

## Worst-offending races (fix top-down)
### Sparkassen Munsterland Giro — 4 persona(s) failed
- veteran_podium_chaser: preview FAIL: Zone Distribution
- ambitious_first_timer: preview FAIL: Zone Distribution
- weekend_warrior: needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution

### Around the Bay in a Day — 4 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- ambitious_first_timer: preview FAIL: Zone Distribution
- weekend_warrior: preview FAIL: Zone Distribution

### Ötztaler Radmarathon — 4 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- ambitious_first_timer: preview FAIL: Zone Distribution

### GFNY Bremen — 3 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Zone Distribution
- weekend_warrior: needs review: compliance flagged (delivered)

### Granfondo Alpi del Mare — 3 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)

### Eroica Germania — 2 persona(s) failed
- masters_returner: preview FAIL: Zone Distribution
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### TotalEnergies Gran Fondo Alberto Contador — 1 persona(s) failed
- weekend_warrior: preview FAIL: Weekly Volume

### Cyclotour du Léman — 1 persona(s) failed
- veteran_podium_chaser: preview FAIL: Weekly Volume; preview FAIL: Zone Distribution

### Little Sugar MTB — 1 persona(s) failed
- weekend_warrior: needs review: compliance flagged (delivered)

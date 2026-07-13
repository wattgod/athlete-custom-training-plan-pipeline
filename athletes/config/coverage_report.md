# Coverage sweep — 2026-07-13

**195/200 orders DELIVERED a plan (97%)** — the customer-facing number (no refund). Of those, 140 were clean and 55 need a coach pass before sending. **5 produced NO plan** (the only refund bucket).

Breadth complement to the daily depth judge: every cell is a real pipeline build. 'Clean' passes the deterministic send-worthy contract; 'needs review' delivered but tripped a compliance check (coach reviews before sending); 'failed' produced nothing.

## Pass rate by persona
- weekend_warrior: 62%
- time_crunched_parent: 65%
- masters_returner: 70%
- veteran_podium_chaser: 70%
- ambitious_first_timer: 82%

## Pass rate by discipline
- gravel: 69%
- road: 71%

## Failures by type (frequency)
- ×37  preview fail
- ×37  needs review
- ×5  pipeline exited non-zero (gate blocked)

## Worst-offending races (fix top-down)
### Bike MS: New York City — 5 persona(s) failed
- time_crunched_parent: pipeline exited non-zero (gate blocked)
- masters_returner: pipeline exited non-zero (gate blocked)
- ambitious_first_timer: pipeline exited non-zero (gate blocked)
- veteran_podium_chaser: pipeline exited non-zero (gate blocked)
- weekend_warrior: pipeline exited non-zero (gate blocked)

### L'Etape Poland by Tour de France — 4 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Zone Distribution
- veteran_podium_chaser: preview FAIL: Zone Distribution
- weekend_warrior: needs review: compliance flagged (delivered)

### L'Eroica — 4 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### Trough Creek Gravel Grinder — 3 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution
- veteran_podium_chaser: preview FAIL: Zone Distribution
- weekend_warrior: needs review: compliance flagged (delivered)

### GFNY Chile — 3 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### UCI Gravel World Championships — 3 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution

### Gran Fondo Il Lombardia Felice Gimondi — 3 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Heck of the North — 3 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution
- weekend_warrior: preview FAIL: Zone Distribution

### Vapor Trail 125 — 2 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### Dunoon Dirt Dash — 2 persona(s) failed
- weekend_warrior: preview FAIL: Zone Distribution
- veteran_podium_chaser: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### Cycling Shimanami — 2 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)

### Gran Fondo Eilat — 2 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### L'Etape Turkey by Tour de France — 2 persona(s) failed
- masters_returner: needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)

### Walburg Dirty 30 — 2 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Wild Gravel — 2 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution
- weekend_warrior: preview FAIL: Zone Distribution

### Lake Taupo Cycle Challenge — 2 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- ambitious_first_timer: preview FAIL: Zone Distribution

### Gran Fondo Maryland — 2 persona(s) failed
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Iceman Cometh — 1 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution

### Sea Otter Ciclobrava — 1 persona(s) failed
- veteran_podium_chaser: preview FAIL: Zone Distribution

### Chequamegon MTB — 1 persona(s) failed
- weekend_warrior: needs review: compliance flagged (delivered)

### TotalEnergies Gran Fondo Alberto Contador — 1 persona(s) failed
- weekend_warrior: needs review: compliance flagged (delivered)

### Tour de Tucson — 1 persona(s) failed
- weekend_warrior: preview FAIL: Zone Distribution

### Around the Bay in a Day — 1 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### Spotted Horse Ultra — 1 persona(s) failed
- ambitious_first_timer: needs review: compliance flagged (delivered)

### El Tour de Tucson — 1 persona(s) failed
- veteran_podium_chaser: needs review: compliance flagged (delivered)

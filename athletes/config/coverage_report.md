# Coverage sweep — 2026-07-06

**195/200 orders DELIVERED a plan (97%)** — the customer-facing number (no refund). Of those, 135 were clean and 60 need a coach pass before sending. **5 produced NO plan** (the only refund bucket).

Breadth complement to the daily depth judge: every cell is a real pipeline build. 'Clean' passes the deterministic send-worthy contract; 'needs review' delivered but tripped a compliance check (coach reviews before sending); 'failed' produced nothing.

## Pass rate by persona
- weekend_warrior: 62%
- masters_returner: 65%
- time_crunched_parent: 67%
- veteran_podium_chaser: 67%
- ambitious_first_timer: 75%

## Pass rate by discipline
- gravel: 65%
- road: 71%

## Failures by type (frequency)
- ×41  preview fail
- ×36  needs review
- ×5  pipeline exited non-zero (gate blocked)

## Worst-offending races (fix top-down)
### Bike MS: New York City — 5 persona(s) failed
- time_crunched_parent: pipeline exited non-zero (gate blocked)
- masters_returner: pipeline exited non-zero (gate blocked)
- ambitious_first_timer: pipeline exited non-zero (gate blocked)
- veteran_podium_chaser: pipeline exited non-zero (gate blocked)
- weekend_warrior: pipeline exited non-zero (gate blocked)

### Cycling Shimanami — 4 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution
- masters_returner: preview FAIL: Zone Distribution
- veteran_podium_chaser: preview FAIL: Zone Distribution
- weekend_warrior: preview FAIL: Zone Distribution

### Old Fashioned Gravel — 3 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution
- veteran_podium_chaser: preview FAIL: Zone Distribution
- weekend_warrior: needs review: compliance flagged (delivered)

### Granfondo Tre Valli Varesine — 3 persona(s) failed
- ambitious_first_timer: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Zone Distribution
- weekend_warrior: needs review: compliance flagged (delivered)

### Iceman Cometh — 3 persona(s) failed
- masters_returner: preview FAIL: Zone Distribution
- ambitious_first_timer: preview FAIL: Weekly Volume
- weekend_warrior: needs review: compliance flagged (delivered)

### The Mane Event Gravel — 3 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### L'Eroica — 3 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### TotalEnergies Gran Fondo Alberto Contador — 3 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution

### L'Etape Turkey by Tour de France — 3 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Dunoon Dirt Dash — 3 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Weekly Volume

### Pony Express 120 — 3 persona(s) failed
- masters_returner: needs review: compliance flagged (delivered)
- ambitious_first_timer: preview FAIL: Zone Distribution
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Alpenbrevet — 2 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)

### Taiwan KOM Challenge — 2 persona(s) failed
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Zone Distribution

### Chequamegon MTB — 2 persona(s) failed
- weekend_warrior: preview FAIL: Zone Distribution
- veteran_podium_chaser: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### GFNY Maryland Cambridge — 2 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Sparkassen Munsterland Giro — 2 persona(s) failed
- masters_returner: needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)

### Around the Bay in a Day — 2 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Soldier Cutoff Hillduro — 2 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- ambitious_first_timer: preview FAIL: Zone Distribution

### Big Sugar — 2 persona(s) failed
- masters_returner: preview FAIL: Zone Distribution
- veteran_podium_chaser: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)

### RBC GranFondo Whistler — 2 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution

### Sea Otter Ciclobrava — 1 persona(s) failed
- weekend_warrior: preview FAIL: Weekly Volume

### GFNY Cozumel — 1 persona(s) failed
- veteran_podium_chaser: preview FAIL: Weekly Volume

### GFNY Chile — 1 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution

### Tour de Tucson — 1 persona(s) failed
- weekend_warrior: preview FAIL: Zone Distribution

### La Ruta de los Conquistadores — 1 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)

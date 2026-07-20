# Coverage sweep — 2026-07-20

**195/200 orders DELIVERED a plan (97%)** — the customer-facing number (no refund). Of those, 132 were clean and 63 need a coach pass before sending. **5 produced NO plan** (the only refund bucket).

Breadth complement to the daily depth judge: every cell is a real pipeline build. 'Clean' passes the deterministic send-worthy contract; 'needs review' delivered but tripped a compliance check (coach reviews before sending); 'failed' produced nothing.

## Pass rate by persona
- masters_returner: 57%
- time_crunched_parent: 62%
- veteran_podium_chaser: 65%
- weekend_warrior: 65%
- ambitious_first_timer: 80%

## Pass rate by discipline
- gravel: 65%
- road: 67%

## Failures by type (frequency)
- ×45  needs review
- ×40  preview fail
- ×5  pipeline exited non-zero (gate blocked)

## Worst-offending races (fix top-down)
### UCI Gran Fondo Loutraki — 9 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- veteran_podium_chaser: needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Weekly Volume; preview FAIL: Zone Distribution

### Bike MS: New York City — 5 persona(s) failed
- ambitious_first_timer: pipeline exited non-zero (gate blocked)
- masters_returner: pipeline exited non-zero (gate blocked)
- time_crunched_parent: pipeline exited non-zero (gate blocked)
- weekend_warrior: pipeline exited non-zero (gate blocked)
- veteran_podium_chaser: pipeline exited non-zero (gate blocked)

### UCI Gran Fondo Brasil – Pomerode — 4 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution
- weekend_warrior: preview FAIL: Per-Day Duration Caps; needs review: compliance flagged (delivered)
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Gran Fondo Maryland — 4 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- ambitious_first_timer: preview FAIL: Zone Distribution
- veteran_podium_chaser: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Sparkassen Munsterland Giro — 3 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Zone Distribution
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### La Ruta de los Conquistadores — 3 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)

### Hellhole Gravel Grind Stage Race — 3 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- ambitious_first_timer: preview FAIL: Zone Distribution
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### Gran Fondo Eilat — 3 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution
- weekend_warrior: needs review: compliance flagged (delivered)

### L'Étape Ciudad de México by Tour de France — 3 persona(s) failed
- time_crunched_parent: preview FAIL: Per-Day Duration Caps
- masters_returner: needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)

### JUST.GRAVEL — 3 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution
- masters_returner: preview FAIL: Zone Distribution
- weekend_warrior: preview FAIL: Zone Distribution

### Taiwan KOM Challenge — 3 persona(s) failed
- masters_returner: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Per-Day Duration Caps; needs review: compliance flagged (delivered)

### Lake Taupo Cycle Challenge — 2 persona(s) failed
- masters_returner: preview FAIL: Per-Day Duration Caps; needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)

### GFNY Miami — 2 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution
- masters_returner: preview FAIL: Zone Distribution

### Around the Bay in a Day — 2 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)

### Iceman Cometh — 2 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)

### Gravel Revival — 2 persona(s) failed
- weekend_warrior: needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Weekly Volume

### Sea Otter Ciclobrava — 2 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)

### Dunoon Dirt Dash — 2 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Heck of the North — 2 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution

### Spirit World 100 — 1 persona(s) failed
- veteran_podium_chaser: preview FAIL: Zone Distribution

### Little Sugar MTB — 1 persona(s) failed
- weekend_warrior: needs review: compliance flagged (delivered)

### 5 Mila Marche Gran Fondo — 1 persona(s) failed
- weekend_warrior: preview FAIL: Per-Day Duration Caps; needs review: compliance flagged (delivered)

### Chequamegon MTB — 1 persona(s) failed
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Bowral Classic — 1 persona(s) failed
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Red Granite Grinder — 1 persona(s) failed
- masters_returner: needs review: compliance flagged (delivered)

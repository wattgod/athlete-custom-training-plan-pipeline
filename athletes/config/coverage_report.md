# Coverage sweep — 2026-08-10

**190/200 orders DELIVERED a plan (95%)** — the customer-facing number (no refund). Of those, 127 were clean and 63 need a coach pass before sending. **10 produced NO plan** (the only refund bucket).

Breadth complement to the daily depth judge: every cell is a real pipeline build. 'Clean' passes the deterministic send-worthy contract; 'needs review' delivered but tripped a compliance check (coach reviews before sending); 'failed' produced nothing.

## Pass rate by persona
- veteran_podium_chaser: 57%
- weekend_warrior: 57%
- masters_returner: 60%
- time_crunched_parent: 62%
- ambitious_first_timer: 80%

## Pass rate by discipline
- road: 58%
- gravel: 67%

## Failures by type (frequency)
- ×45  preview fail
- ×45  needs review
- ×10  pipeline exited non-zero (gate blocked)

## Worst-offending races (fix top-down)
### Bike MS: New York City — 10 persona(s) failed
- time_crunched_parent: pipeline exited non-zero (gate blocked)
- masters_returner: pipeline exited non-zero (gate blocked)
- ambitious_first_timer: pipeline exited non-zero (gate blocked)
- veteran_podium_chaser: pipeline exited non-zero (gate blocked)
- weekend_warrior: pipeline exited non-zero (gate blocked)

### L'Étape Ciudad de México by Tour de France — 7 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution

### Gran Fondo Hincapie — 6 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution
- veteran_podium_chaser: needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Per-Day Duration Caps; needs review: compliance flagged (delivered)

### Lake Taupo Cycle Challenge — 5 persona(s) failed
- masters_returner: preview FAIL: Per-Day Duration Caps; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Per-Day Duration Caps
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)

### Taiwan KOM Challenge — 5 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution
- weekend_warrior: needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Zone Distribution
- veteran_podium_chaser: preview FAIL: Zone Distribution

### GFNY Miami — 4 persona(s) failed
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Per-Day Duration Caps; needs review: compliance flagged (delivered)

### Gravel Revival — 3 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution
- veteran_podium_chaser: preview FAIL: Zone Distribution
- weekend_warrior: needs review: compliance flagged (delivered)

### Around the Bay in a Day — 3 persona(s) failed
- masters_returner: needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)

### GFNY Cozumel — 3 persona(s) failed
- masters_returner: preview FAIL: Zone Distribution; preview FAIL: Per-Day Duration Caps
- veteran_podium_chaser: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Per-Day Duration Caps; needs review: compliance flagged (delivered)

### Tour de Tucson — 3 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- ambitious_first_timer: preview FAIL: Zone Distribution
- veteran_podium_chaser: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)

### Gran Fondo Guadeloupe — 3 persona(s) failed
- ambitious_first_timer: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### La Ruta de los Conquistadores — 2 persona(s) failed
- veteran_podium_chaser: preview FAIL: Zone Distribution
- time_crunched_parent: needs review: compliance flagged (delivered)

### Spotted Horse Ultra — 2 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### Iceman Cometh — 2 persona(s) failed
- weekend_warrior: preview FAIL: Zone Distribution
- veteran_podium_chaser: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### Grassroots Gravel — 2 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)

### Red Granite Grinder — 2 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)

### Gran Fondo Il Lombardia Felice Gimondi — 2 persona(s) failed
- veteran_podium_chaser: preview FAIL: Zone Distribution
- weekend_warrior: preview FAIL: Zone Distribution

### Spirit World 100 — 2 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution

### UCI Gravel World Championships — 1 persona(s) failed
- veteran_podium_chaser: preview FAIL: Zone Distribution

### Walburg Dirty 30 — 1 persona(s) failed
- weekend_warrior: needs review: compliance flagged (delivered)

### UCI Gran Fondo Brasil – Pomerode — 1 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution

### Alentejo Gravel — 1 persona(s) failed
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### UCI Gran Fondo Loutraki — 1 persona(s) failed
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### Lowell Classic — 1 persona(s) failed
- weekend_warrior: preview FAIL: Zone Distribution

### Marys Mayhem — 1 persona(s) failed
- veteran_podium_chaser: needs review: compliance flagged (delivered)

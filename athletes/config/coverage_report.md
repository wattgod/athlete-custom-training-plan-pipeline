# Coverage sweep — 2026-08-17

**190/200 orders DELIVERED a plan (95%)** — the customer-facing number (no refund). Of those, 55 were clean and 135 need a coach pass before sending. **10 produced NO plan** (the only refund bucket).

Breadth complement to the daily depth judge: every cell is a real pipeline build. 'Clean' passes the deterministic send-worthy contract; 'needs review' delivered but tripped a compliance check (coach reviews before sending); 'failed' produced nothing.

## Pass rate by persona
- time_crunched_parent: 12%
- weekend_warrior: 20%
- veteran_podium_chaser: 30%
- masters_returner: 32%
- ambitious_first_timer: 42%

## Pass rate by discipline
- road: 24%
- gravel: 29%

## Failures by type (frequency)
- ×129  needs review
- ×46  preview fail
- ×10  pipeline exited non-zero (gate blocked)

## Worst-offending races (fix top-down)
### Gran Fondo Hincapie — 10 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)

### Bike MS: New York City — 10 persona(s) failed
- time_crunched_parent: pipeline exited non-zero (gate blocked)
- masters_returner: pipeline exited non-zero (gate blocked)
- ambitious_first_timer: pipeline exited non-zero (gate blocked)
- veteran_podium_chaser: pipeline exited non-zero (gate blocked)
- weekend_warrior: pipeline exited non-zero (gate blocked)

### Gran Fondo Eilat — 10 persona(s) failed
- masters_returner: needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Weekly Volume
- ambitious_first_timer: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)

### UCI Gran Fondo Brasil – Pomerode — 8 persona(s) failed
- ambitious_first_timer: needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### Gran Fondo Guadeloupe — 8 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)

### GFNY Cozumel — 8 persona(s) failed
- masters_returner: needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; preview FAIL: Per-Day Duration Caps

### L'Étape Ciudad de México by Tour de France — 8 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Per-Day Duration Caps; needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)

### El Tour de Tucson — 7 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Per-Day Duration Caps; needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### Around the Bay in a Day — 6 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)

### La Ruta de los Conquistadores — 6 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### Cycling Shimanami — 5 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### UCI Gran Fondo Loutraki — 5 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Iceman Cometh — 4 persona(s) failed
- masters_returner: needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Wild Gravel — 4 persona(s) failed
- masters_returner: needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### Spotted Horse Ultra — 4 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)

### Marys Mayhem — 4 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Alentejo Gravel — 4 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### Bowral Classic — 4 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)

### Lowell Classic — 4 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- veteran_podium_chaser: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)

### Big Sugar — 3 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)

### Walburg Dirty 30 — 3 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution
- masters_returner: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)

### Gravelista — 3 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)

### GFNY Miami — 3 persona(s) failed
- ambitious_first_timer: needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)

### Flanders Legacy Gravel — 3 persona(s) failed
- masters_returner: preview FAIL: Zone Distribution
- ambitious_first_timer: needs review: compliance flagged (delivered)
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### Gravel Revival — 3 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

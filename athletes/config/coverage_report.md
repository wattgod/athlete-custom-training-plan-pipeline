# Coverage sweep — 2026-08-31

**138/140 orders DELIVERED a plan (98%)** — the customer-facing number (no refund). Of those, 83 were clean and 55 need a coach pass before sending. **2 produced NO plan** (the only refund bucket).

Breadth complement to the daily depth judge: every cell is a real pipeline build. 'Clean' passes the deterministic send-worthy contract; 'needs review' delivered but tripped a compliance check (coach reviews before sending); 'failed' produced nothing.

## Pass rate by persona
- time_crunched_parent: 39%
- weekend_warrior: 50%
- veteran_podium_chaser: 64%
- masters_returner: 64%
- ambitious_first_timer: 78%

## Pass rate by discipline
- road: 58%
- gravel: 60%

## Failures by type (frequency)
- ×41  needs review
- ×31  preview fail
- ×2  gate

## Worst-offending races (fix top-down)
### El Tour de Tucson — 6 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume
- weekend_warrior: needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)

### GFNY Cozumel — 5 persona(s) failed
- masters_returner: preview FAIL: Zone Distribution
- ambitious_first_timer: needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Zone Distribution
- masters_returner: preview FAIL: Zone Distribution

### Lake Taupo Cycle Challenge — 5 persona(s) failed
- masters_returner: preview FAIL: Weekly Volume
- veteran_podium_chaser: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- veteran_podium_chaser: gate: CanonicalModelError: athlete-visible description contains compiler-only copy[0m
- masters_returner: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)

### UCI Gran Fondo Loutraki — 5 persona(s) failed
- veteran_podium_chaser: needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)

### La Ruta de los Conquistadores — 4 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution

### Gran Fondo Eilat — 4 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- ambitious_first_timer: needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Zone Distribution
- weekend_warrior: needs review: compliance flagged (delivered)

### Atlas Gran Fondo — 4 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume
- weekend_warrior: needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Weekly Volume; preview FAIL: Zone Distribution

### L'Étape Ciudad de México by Tour de France — 3 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)

### GFNY Miami — 3 persona(s) failed
- veteran_podium_chaser: preview FAIL: Zone Distribution
- time_crunched_parent: preview FAIL: Weekly Volume; preview FAIL: Zone Distribution
- weekend_warrior: needs review: compliance flagged (delivered)

### Walburg Dirty 30 — 3 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume; needs review: compliance flagged (delivered)

### Gran Fondo Guadeloupe — 3 persona(s) failed
- veteran_podium_chaser: preview FAIL: Weekly Volume
- weekend_warrior: needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)

### Tour de Tucson — 3 persona(s) failed
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- ambitious_first_timer: preview FAIL: Zone Distribution
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### Spirit World 100 — 3 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- ambitious_first_timer: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)

### UCI Gran Fondo Brasil – Pomerode — 3 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Zone Distribution
- weekend_warrior: preview FAIL: Zone Distribution; preview FAIL: Per-Day Duration Caps

### UCI Gravel Dustman — 2 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution
- weekend_warrior: needs review: compliance flagged (delivered)

### Iceman Cometh — 1 persona(s) failed
- veteran_podium_chaser: gate: CanonicalModelError: athlete-visible description contains compiler-only copy[0m

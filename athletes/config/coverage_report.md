# Coverage sweep — 2026-09-07

**129/130 orders DELIVERED a plan (99%)** — the customer-facing number (no refund). Of those, 78 were clean and 51 need a coach pass before sending. **1 produced NO plan** (the only refund bucket).

Breadth complement to the daily depth judge: every cell is a real pipeline build. 'Clean' passes the deterministic send-worthy contract; 'needs review' delivered but tripped a compliance check (coach reviews before sending); 'failed' produced nothing.

## Pass rate by persona
- time_crunched_parent: 46%
- weekend_warrior: 46%
- masters_returner: 65%
- ambitious_first_timer: 69%
- veteran_podium_chaser: 73%

## Pass rate by discipline
- gravel: 57%
- road: 63%

## Failures by type (frequency)
- ×32  needs review
- ×29  preview fail
- ×1  gate

## Worst-offending races (fix top-down)
### Atlas Gran Fondo — 7 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution

### Gran Fondo Eilat — 6 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Weekly Volume; preview FAIL: Per-Day Duration Caps
- time_crunched_parent: preview FAIL: Zone Distribution
- masters_returner: preview FAIL: Weekly Volume

### L'Étape Ciudad de México by Tour de France — 5 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)
- time_crunched_parent: preview FAIL: Weekly Volume
- veteran_podium_chaser: needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### El Tour de Tucson — 5 persona(s) failed
- veteran_podium_chaser: preview FAIL: Zone Distribution
- time_crunched_parent: preview FAIL: Weekly Volume
- masters_returner: preview FAIL: Weekly Volume
- veteran_podium_chaser: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution

### GFNY Cozumel — 5 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- ambitious_first_timer: preview FAIL: Zone Distribution
- ambitious_first_timer: preview FAIL: Zone Distribution
- weekend_warrior: preview FAIL: Zone Distribution

### Lake Taupo Cycle Challenge — 5 persona(s) failed
- ambitious_first_timer: gate: CanonicalModelError: athlete-visible description contains compiler-only copy[0m
- time_crunched_parent: needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume
- weekend_warrior: needs review: compliance flagged (delivered)

### GFNY Miami — 4 persona(s) failed
- weekend_warrior: needs review: compliance flagged (delivered)
- ambitious_first_timer: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume
- weekend_warrior: preview FAIL: Zone Distribution

### UCI Gran Fondo Loutraki — 3 persona(s) failed
- weekend_warrior: needs review: compliance flagged (delivered)
- veteran_podium_chaser: preview FAIL: Weekly Volume
- time_crunched_parent: needs review: compliance flagged (delivered)

### Tour de Tucson — 3 persona(s) failed
- masters_returner: preview FAIL: Zone Distribution
- ambitious_first_timer: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)
- weekend_warrior: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

### UCI Gravel Dustman — 3 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)
- ambitious_first_timer: preview FAIL: Zone Distribution
- veteran_podium_chaser: needs review: compliance flagged (delivered)

### UCI Gran Fondo Brasil – Pomerode — 2 persona(s) failed
- masters_returner: needs review: compliance flagged (delivered)
- time_crunched_parent: needs review: compliance flagged (delivered)

### Walburg Dirty 30 — 2 persona(s) failed
- ambitious_first_timer: needs review: compliance flagged (delivered)
- weekend_warrior: needs review: compliance flagged (delivered)

### Gran Fondo Guadeloupe — 1 persona(s) failed
- time_crunched_parent: needs review: compliance flagged (delivered)

### Spirit World 100 — 1 persona(s) failed
- masters_returner: preview FAIL: Zone Distribution; needs review: compliance flagged (delivered)

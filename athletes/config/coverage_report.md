# Coverage sweep — 2026-06-22

**16/30 builds send-worthy (53%)** across the main personas × the race database.

Breadth complement to the daily depth judge: every cell is a real pipeline build checked against the deterministic send-worthy contract (no LLM).

## Pass rate by persona
- veteran_podium_chaser: 33%
- weekend_warrior: 50%
- masters_returner: 50%
- ambitious_first_timer: 50%
- time_crunched_parent: 83%

## Pass rate by discipline
- gravel: 45%
- road: 70%

## Failures by type (frequency)
- ×8  pipeline exited non-zero (gate blocked)
- ×6  preview fail

## Worst-offending races (fix top-down)
### Gran Fondo Başkent — 4 persona(s) failed
- masters_returner: preview FAIL: Zone Distribution
- weekend_warrior: pipeline exited non-zero (gate blocked)
- ambitious_first_timer: preview FAIL: Zone Distribution
- veteran_podium_chaser: preview FAIL: Zone Distribution

### Little Sugar MTB — 3 persona(s) failed
- weekend_warrior: pipeline exited non-zero (gate blocked)
- masters_returner: pipeline exited non-zero (gate blocked)
- time_crunched_parent: preview FAIL: Zone Distribution

### UCI Gravel World Championships — 3 persona(s) failed
- ambitious_first_timer: preview FAIL: Zone Distribution
- weekend_warrior: pipeline exited non-zero (gate blocked)
- veteran_podium_chaser: preview FAIL: Zone Distribution

### Sparkassen Munsterland Giro — 3 persona(s) failed
- masters_returner: pipeline exited non-zero (gate blocked)
- ambitious_first_timer: pipeline exited non-zero (gate blocked)
- veteran_podium_chaser: pipeline exited non-zero (gate blocked)

### Spotted Horse Ultra — 1 persona(s) failed
- veteran_podium_chaser: pipeline exited non-zero (gate blocked)

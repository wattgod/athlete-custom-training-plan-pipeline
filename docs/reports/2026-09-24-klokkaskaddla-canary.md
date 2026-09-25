# Klokkaskaddla DRAFT canary preflight — 2026-09-24

**Outcome: stopped before any new TP write.** This is a negative safety test, not a successful live publisher canary or an athlete-calendar application.

- Identity: Klokka Skaddla is Matti Rowe, TrainingPeaks athlete `480149` (verified in the live TP UI). The existing coach-library DRAFT is plan `672665`, titled `DRAFT — Matti Rowe — Post-Nats Closer + Break 8wk`; its UI folder is `Athlete Dynamic Plans`.
- Source inspected: private `plan-builds/matti-rowe/plan_payload.json` and `proposal.md` from 2026-08-26. It is 61 workouts plus 16 notes, dated 2026-09-14 through 2026-11-08, but is **not** a sealed paid-order revision and therefore cannot enter the new order-bound publisher or review packet.
- Fresh `ae_lint.py` run on that 61-workout source with the proposal's historical CTL 115.8, demonstrated weekly load 909 TSS, and its 2026-10-24 race-date assumption returned **2 FAIL, 16 WARN**. Both FAIL rows are AE-1.14: modeled race-day CTL 101.0, 13% below the supplied 115.8. The historical CTL is not claimed to be current on 2026-09-24.
- The plan's October 24 closer is still `TBD`. Its September 21–27 week assumes no race, while Klokkaskaddla's live TP calendar shows The Rad Dirt Fest on September 26. The proposal itself flags that conflict and says its first two weeks cannot coexist with that race week.
- The new publisher also has no proven live `plans/v1` transport/folder-placement adapter; its injected transport tests do not authorize a TP write. A DRAFT in the coach library is not a delivery or calendar receipt.

The canary can resume only from a fresh, lint-clean, sealed order-scoped plan using current goals and verified load/availability, with the September 26 race respected; then use a reviewed live TP adapter and read back the exact folder, cards, and `isDynamic`. Any athlete-calendar application remains the separate Phase 5 gate.

# Golden refresh

Golden dates move only in a dedicated PR. A freshness failure is not fixed by
weakening the eight-week threshold, using a fake wall clock in the nightly job,
or silently changing a race during unrelated work.

## Refresh checklist

- [ ] Open a dedicated `test: refresh date-pinned goldens` PR and link the
      failing nightly run.
- [ ] Run `python scripts/check_fixture_freshness.py` and record every `FAIL` and
      `WARN` pin before editing.
- [ ] Choose replacement races from the committed race sources used by the
      pipeline. Verify names, dates, distance, elevation, discipline, slug, and
      provenance together; do not copy a live lookup into only one fixture.
- [ ] In `athletes/scripts/test_order_acceptance.py`, update the literal golden
      clock and the affected race objects/orders together.
- [ ] In `tests/fixtures/athlete_m/`, update `clock.json`, `race_snapshot.json`,
      and the intake A-race date as one coherent snapshot.
- [ ] Regenerate athlete-m `expected/plan_dates.yaml` through the production
      generation test with `GG_UPDATE_ATHLETE_M_GOLDEN=1`. Review the diff; the
      flag updates plan dates only and is not approval for other expected files.
- [ ] Re-run the Phase 1, Phase 3, and Phase 4 athlete-m golden cases. Update
      `expected/phase1.json`, `phase3.json`, or `phase4.json` only when a reviewed
      semantic change requires it—never merely to accept a failure.
- [ ] Run the acceptance suite with a writable isolated home: create a temporary
      directory in the operator's approved scratch area, store its path in
      `GG_ACCEPTANCE_HOME`, then run
      `HOME="$GG_ACCEPTANCE_HOME" GG_RUN_ACCEPTANCE=1 python -m pytest athletes/scripts/test_order_acceptance.py -q`.
- [ ] Run `python scripts/check_fixture_freshness.py`; require no `FAIL`.
- [ ] Run the full suite and inspect generated workout/artifact diffs. Explain
      every changed expected value in the PR.
- [ ] Keep the PR limited to fixture clocks, pinned race snapshots, regenerated
      goldens, and their evidence. Do not combine product behavior changes.

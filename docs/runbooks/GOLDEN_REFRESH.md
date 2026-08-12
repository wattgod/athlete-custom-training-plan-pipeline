# Golden refresh

Golden dates move only in a dedicated PR. The freshness gate fails when the
acceptance goldens' pinned generation clock is more than 180 days old (warns
past 120). Pinned fixtures inject their frozen clock into generation, so they
never rot mechanically — the gate bounds drift from reality, not future-dated
races. A freshness failure is not fixed by weakening the age threshold, using
a fake wall clock in the nightly job, or silently changing a race during
unrelated work.

**athlete-m is exempt and out of scope here**: its dates are normative fixture
contract in `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` and move only with a spec
revision, never in a routine refresh.

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
- [ ] Leave `tests/fixtures/athlete_m/` untouched (spec-frozen; see above). If a
      spec revision has moved the athlete-m fixture contract, that change ships
      with the spec PR, regenerating `expected/plan_dates.yaml` via
      `GG_UPDATE_ATHLETE_M_GOLDEN=1` and re-running the Phase 1/3/4 golden cases
      there — not here.
- [ ] Run the acceptance suite with a writable isolated home: create a temporary
      directory in the operator's approved scratch area, store its path in
      `GG_ACCEPTANCE_HOME`, then run
      `HOME="$GG_ACCEPTANCE_HOME" GG_RUN_ACCEPTANCE=1 python -m pytest athletes/scripts/test_order_acceptance.py -q`.
- [ ] Run `python scripts/check_fixture_freshness.py`; require no `FAIL`.
- [ ] Run the full suite and inspect generated workout/artifact diffs. Explain
      every changed expected value in the PR.
- [ ] Keep the PR limited to fixture clocks, pinned race snapshots, regenerated
      goldens, and their evidence. Do not combine product behavior changes.

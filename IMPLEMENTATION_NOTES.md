# Plan-Truth: fueling truth + warm-up slice

## G1

- Added `FuelingPrescription` in `athletes/scripts/fueling_policy.py` with a
  version, race target/range, total grams, training tiers, hydration,
  assumptions, and input provenance.
- `calculate_fueling.py` serializes that object to `fueling.yaml` as
  `prescription`, while retaining the legacy `carbohydrates` fields for existing
  callers.
- The policy uses duration, body mass, FTP × goal-specific intensity factor,
  goal, and tolerance. Missing tolerance is explicitly flagged and caps a
  sub-65 kg athlete at 70 g/hr. Sex only creates an energy-availability warning;
  it is not a carbohydrate discount.
- The profile builder preserves intake-provided `training_fuel` where available.

## G2

- Removed hardcoded personalized ranges from `FUEL_TAGS` and from Nate workout
  nutrition prose. Package tags are now rendered from the serialized
  prescription tiers; the guide card reads the same prescription.
- Existing `carbohydrates` fields remain only as compatibility projections of
  the prescription. Generic education elsewhere in the guide was left alone.

## G6

- Steady endurance/recovery construction now caps warm-up end power at the main
  steady power, normalizes legacy cooldown attribute ordering to monotonic down,
  and provides a validator for warm-up, cooldown, and nonzero-main-set checks.
- Interval warm-ups are not changed.

## Follow-up deliberately left out

Only G1, G2, and G6 were changed. J1, G3–G5, H1, and I1–I2 remain untouched.

## Verification

`pytest athletes/scripts/ -q` passed: **1126 passed, 53 skipped**. One
pre-existing pytest warning remains in `test_custom_guide.py` because that test
returns a boolean instead of asserting; no tests failed before or after this
slice.

## Commit note

The workspace sandbox permits source changes but denies writes to this linked
worktree's external Git metadata (`.../.git/worktrees/wt-plantruth/index.lock`),
so commits could not be created here. No branch was pushed or changed.

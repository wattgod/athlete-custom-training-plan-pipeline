# Ten-order Motoren offline rehearsal

Run from the repository root with a fresh, ignored output directory:

```bash
python3 tools/replay_ten_order_cohort.py --out-root .gg-acctest-delivery/cohort-YYYYMMDD
```

The fixed synthetic intake cases cover a five-week and a nineteen-week runway,
blank FTP, HR/RPE, full gym, no strength, two A races, a repeat buyer with two
order IDs, and a tight weekly schedule. Event names and dates come from the
committed race snapshot, with a fixed 2026-08-06 generation clock. Each case
calls the production webhook runner, persists its own sealed revision, verifies
the seal, and attempts the sealed TP package build. The report records wall time,
peak generator child RSS, order state, blockers, source-to-payload counts, and
guide/TP race agreement. All local inputs are synthetic. No provider writes or
athlete messages occur.

For a quick one-case smoke, add `--limit 1`. To test that a corrupted sealed
guide is rejected and regenerated into a new revision, add
`--seal-edit-case 10`. The deliberately corrupted r1 is rejected and never
reused; regeneration creates a new r2 that still obeys every quality blocker.

This is an offline generator/package rehearsal. PDF rendering is disabled in
this local harness. Its sequential wait time is not the production queue age.
It cannot establish TrainingPeaks folder/readback, coach time per order,
athlete-calendar placement, delivery confirmation, the three-day soak, or the
capacity to fulfill ten paid orders per day. Those remain Card 5 exit checks.

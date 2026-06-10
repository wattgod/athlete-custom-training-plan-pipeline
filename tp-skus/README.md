# TrainingPeaks Static-Plan SKUs — Build Runbook

Northstar Phase 3.1. ~27 SKUs (9 demand families × 8/12/16 weeks) cover all
1,184 races across both brands. TP's plan builder is manual — that's the
bottleneck this system minimizes: build each plan ONCE from its generated
manifest, and every mapped race page sells it forever.

## What's generated (run `python3 tp-skus/generate_skus.py`)

```
tp-skus/output/{family}-{weeks}wk/
  workouts/           ZWO files (dated names = placement guide)
  BUILD_MANIFEST.md   marketplace listing copy + day-by-day table
  training_guide.html reference
```

## The manual loop (per SKU, ~30-45 min each in TP)

1. TrainingPeaks → Coach → **Training Plans → Create Plan**.
2. Title/description: copy from BUILD_MANIFEST.md "Marketplace listing".
3. Upload the ZWOs (workout library), then place per the Day column
   (Day 1 = plan Monday). The `<name>` inside each ZWO is athlete-clean;
   the filename is your placement guide.
4. Price: ladder says $49–99. Suggested: $49 (8wk), $59 (12wk), $69 (16wk).
   Founding discount optional — keep parity with course pricing strategy
   (course-playbook/PRICING.md).
5. Publish → copy the plan's marketplace URL.
6. Paste the URL into **BOTH** brand repos:
   - `gravel-race-automation/data/tp-sku-links.json`
   - `road-race-automation/data/tp-sku-links.json`
   under `"{family}": {"{weeks}": "<url>"}` (gravel families in the gravel
   file, road families in the road file).
7. Regenerate + deploy plan pages in the affected repo:
   `python3 wordpress/generate_training_plan_pages.py --all` then
   `python3 scripts/push_wordpress.py --sync-plan-pages` — the "Ready-Made
   Version" section appears automatically on every mapped race's
   /training-plan/ page.

## Build order (revenue-weighted by mapped-race counts)

| Priority | SKU family | Races covered |
|---|---|---|
| 1 | gravel-allrounder (12wk first) | 316 |
| 2 | gravel-climber | 258 |
| 3 | road-allrounder | 236 |
| 4 | gravel-ultra | 118 |
| 5 | road-distance | 73 |
| 6 | road-alpine-fondo | 67 |
| 7 | road-rolling-fast | 51 |
| 8 | gravel-fast-punchy | 42 |
| 9 | gravel-conditions | 23 |

Start with the 12-week variant of each family (the modal purchase), add
8/16 as demand shows. 9 plans ≈ one focused day in TP; full 27 ≈ three.

## Phase 6 note

When Endure Labs delivery ships, these same SKU ids swap from
`tp-sku-links.json` to Endure URLs — the race→family mapping is the
durable asset, the storefront is interchangeable.

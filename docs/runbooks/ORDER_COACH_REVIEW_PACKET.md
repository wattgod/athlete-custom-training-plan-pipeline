# Offline coach review packet (Card 3)

`tools/build_order_review_packet.py` reads one explicit paid order and prints a
JSON packet. It has no provider transport or fulfillment-state mutation. Run it
with the canonical order state, its current sealed revision, and the matching
Card 1 package:

```bash
python3 tools/build_order_review_packet.py \
  --order-id "$ORDER_ID" \
  --state-path "/data/deliveries/orders/$ORDER_ID/fulfillment_status.json" \
  --revision-dir "/data/deliveries/orders/$ORDER_ID/revisions/r$REVISION" \
  --package-dir "$PACKAGE_DIR" \
  > "$PACKET_PATH"
```

Add `--draft-journal "$JOURNAL_PATH"` only for that same order and revision.
The tool rebuilds Card 1's package in temporary storage and compares the
receipt, lint, exclusions, and payload with the supplied package. The sealed
release verifier checks every source artifact. A mismatch exits 2. A readable
packet with unresolved release blockers exits 1. It exits 0 only when the
existing authenticated approval binds the freshly rebuilt Card 1 receipt and
sealed customer guide, and every packet check has evidence.

The packet includes local paths to the plan preview, PlanIR, payloads, HTML
guide, and PDF; their seal and receipt digests; assumptions and derived-value
provenance; canonical blockers; W00 manual actions; TP library DRAFT readback
status; and week-one, middle, and race-week session samples. Open the exact
artifacts in the packet and review their athlete, events, schedule, strength,
fueling, and workouts. The machine checks named athlete/event strings in the
HTML; it does not certify the prose, the PDF's rendered content, or hosted
guide access. Missing PDF or plan preview is a release blocker.

For a ready canonical TP package, the existing fulfillment approval records
`tp_package_binding.coverage_receipt_sha256` and its sealed `customer_guide`
path and digest. The packet rebuilds the receipt and compares those exact
values. It cannot grant or modify approval. Regeneration changes the release
binding and makes the former approval stale. Older TP releases without Card 1
sources, Endure, and manual approvals retain their previous state behavior,
but cannot pass this Card 3 TP packet without the binding. A library DRAFT,
even with verified folder readback, is not athlete-calendar application or
delivery evidence.
Hosted-guide publication remains a separate coach decision; no URL is inferred.

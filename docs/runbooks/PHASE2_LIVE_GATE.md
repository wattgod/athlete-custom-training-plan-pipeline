# Phase 2 live gate — one page-approved real order

Owner: coach, witnessed by the pipeline operator. Run once on a deployed,
reviewed release. This gate ends at `APPROVED`; it performs no TrainingPeaks or
Endure write.

## Preconditions

- [ ] The reviewed commit is deployed and its automated suite is green.
- [ ] Production review/download key configuration is explicit; no development
      default is in use.
- [ ] Select one newly generated real paid order. Do not choose an order with a
      non-waivable blocker such as `FTP_ESTIMATED`, `COURSE_UNRESOLVED`,
      `STATE_UNAVAILABLE`, validator crash, or `SEAL_MISMATCH`.
- [ ] Record the order only in the authenticated operator record. Do not copy a
      customer name, email, order id, or account id into the repository.

## Coach checklist

- [ ] Open the notification's review link. After fragment exchange, confirm the
      visible URL is `/review/<order_id>` with no bearer in its query string.
- [ ] Match the intended order, platform, generation revision, and status.
- [ ] Read every blocker, required confirmation, soft confirmation, and verified
      fact. Check the typed value, unit, source, basis, sensitivity, and revision.
- [ ] Download the review bundle. Confirm it is the same revision and contains
      review material only—no `.zwo`, TP-native payload, apply payload, or
      customer release bundle.
- [ ] If any value, revision, seal, or artifact is wrong, stop. Regenerate and
      reopen the new revision; do not use the operator transition endpoint.
- [ ] Enter a substantive reason for each waivable blocker. Never attempt to
      waive a non-waivable blocker.
- [ ] Confirm every required item and verified fact; deliberately choose the
      disposition of each soft item.
- [ ] Click **Approve sealed revision** once. This is the human approval action.
- [ ] After redirect, require the Approved banner to name the same revision and
      say the decision is bound to its seal and displayed values.
- [ ] Confirm the page exposes no apply, confirm, guide-release, or Gmail action.

## Required evidence

In the authoritative state at
`$DATA_DIR/deliveries/orders/<order_id>/fulfillment_status.json`, verify:

- [ ] `status == "APPROVED"`.
- [ ] `approval.snapshot_version == "approval_snapshot/v2"`.
- [ ] Approval revision, model seal, release-manifest digest, and review-catalog
      digest exactly equal the current state values.
- [ ] `approval.credential` begins with `review-link:`.
- [ ] Approval confirmations contain exactly one value/type-identical snapshot
      and persisted disposition for every current review item.
- [ ] `approval_matches_release(state)` is true.
- [ ] `application` and `confirmation` are null.
- [ ] No platform write, customer send, public guide, or Gmail draft occurred.

Keep the raw evidence only in authenticated state and deployment logs. Record a
redacted pass/fail checklist in the rollout PR or release record; include commit,
UTC time, revision number, assertion results, and witness, but no customer or
platform identifiers. Stop at `APPROVED`.

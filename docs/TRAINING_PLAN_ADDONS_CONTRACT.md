# Training-plan add-on contract

The add-on boundary is server-owned. Browsers submit only catalog IDs in
`plan_addons`; they never submit an amount, Stripe price, brand, or fulfillment
instruction.

## Current entitlement

`gravel_grit` is included with every Gravel God custom training plan. The
checkout records it in the intake and Stripe metadata, but it never creates a
second line item. Roadie Labs receives no Gravel Grit entitlement.

## Adding an optional module later

1. Add one `PlanAddon` catalog entry with its allowed brand and environment
   variable name for a Stripe Price.
2. Configure that Stripe Price in the service environment. The selection stays
   unavailable if the value is missing or is not a `price_...` ID.
3. Add the catalog ID to the site UI; display copy and price are informational,
   while checkout continues to trust only the server catalog.
4. Read the canonical `plan_addons` list from the stored intake during
   fulfillment and emit an auditable entitlement receipt.
5. Add checkout, fulfillment, and provider-readback tests before enabling it.

Unknown, duplicate, malformed, cross-brand, or unpriced selections fail closed.

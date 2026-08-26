"""Fail-closed catalog boundary for custom-plan add-ons.

The client may select only catalog IDs. Prices and brand eligibility are
server-owned; no client-supplied amount or Stripe price is ever accepted.
Included modules are recorded automatically so fulfillment has one stable
field before the first paid add-on launches.
"""

from dataclasses import dataclass
import os
from typing import Iterable, Mapping, Optional, Sequence


class AddonSelectionError(ValueError):
    """The requested add-on selection is invalid or unavailable."""


@dataclass(frozen=True)
class PlanAddon:
    addon_id: str
    brands: frozenset[str]
    included: bool = False
    stripe_price_env: Optional[str] = None


PLAN_ADDON_CATALOG: Mapping[str, PlanAddon] = {
    # Gravel Grit remains part of every Gravel God custom plan. Recording it
    # here must never be interpreted as an extra Stripe line item.
    "gravel_grit": PlanAddon(
        addon_id="gravel_grit",
        brands=frozenset({"gravelgod"}),
        included=True,
    ),
}


def resolve_plan_addons(
    requested: Optional[Sequence[str]],
    brand: str,
    *,
    catalog: Mapping[str, PlanAddon] = PLAN_ADDON_CATALOG,
) -> dict:
    """Return canonical included/optional IDs for one checkout.

    Unknown, duplicate, non-string, or cross-brand selections fail closed.
    Included modules are added even when the browser sends no selection.
    """
    if requested is None:
        requested = []
    if isinstance(requested, (str, bytes)) or not isinstance(requested, Sequence):
        raise AddonSelectionError("plan_addons must be an array of catalog IDs")

    requested_ids = []
    seen = set()
    for raw in requested:
        if not isinstance(raw, str) or not raw.strip():
            raise AddonSelectionError("plan_addons contains an invalid ID")
        addon_id = raw.strip().lower()
        if addon_id in seen:
            raise AddonSelectionError("plan_addons contains a duplicate ID")
        seen.add(addon_id)
        addon = catalog.get(addon_id)
        if addon is None:
            raise AddonSelectionError(f"unknown plan add-on: {addon_id}")
        if brand not in addon.brands:
            raise AddonSelectionError(
                f"plan add-on {addon_id} is not available for {brand}")
        requested_ids.append(addon_id)

    included = sorted(
        addon.addon_id for addon in catalog.values()
        if addon.included and brand in addon.brands)
    optional = sorted(
        addon_id for addon_id in requested_ids
        if not catalog[addon_id].included)
    return {
        "included": included,
        "optional": optional,
        "all": sorted(set(included) | set(optional)),
    }


def stripe_line_items_for_addons(
    addon_ids: Iterable[str],
    *,
    catalog: Mapping[str, PlanAddon] = PLAN_ADDON_CATALOG,
    environ: Mapping[str, str] = os.environ,
) -> list[dict]:
    """Build server-priced Stripe line items for optional catalog entries."""
    line_items = []
    for addon_id in addon_ids:
        addon = catalog[addon_id]
        if addon.included:
            continue
        if not addon.stripe_price_env:
            raise AddonSelectionError(
                f"plan add-on {addon_id} has no Stripe price configuration")
        price_id = str(environ.get(addon.stripe_price_env) or "").strip()
        if not price_id.startswith("price_"):
            raise AddonSelectionError(
                f"plan add-on {addon_id} is not currently available")
        line_items.append({"price": price_id, "quantity": 1})
    return line_items

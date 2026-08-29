"""Contract tests for the server-owned training-plan add-on catalog."""

import pytest

from webhook.training_plan_addons import (
    AddonSelectionError,
    PlanAddon,
    resolve_plan_addons,
    stripe_line_items_for_addons,
)


def test_gravel_grit_is_automatically_included_for_gravel_god():
    selection = resolve_plan_addons(None, "gravelgod")

    assert selection == {
        "included": ["gravel_grit"],
        "optional": [],
        "all": ["gravel_grit"],
    }
    assert stripe_line_items_for_addons(selection["optional"]) == []


def test_gravel_grit_is_not_silently_added_to_other_brands():
    assert resolve_plan_addons([], "roadielabs")["all"] == []


@pytest.mark.parametrize(
    "requested,error",
    [
        ("gravel_grit", "array"),
        (["missing"], "unknown"),
        (["gravel_grit", "gravel_grit"], "duplicate"),
        ([42], "invalid"),
    ],
)
def test_bad_client_selections_fail_closed(requested, error):
    with pytest.raises(AddonSelectionError, match=error):
        resolve_plan_addons(requested, "gravelgod")


def test_cross_brand_selection_fails_closed():
    with pytest.raises(AddonSelectionError, match="not available"):
        resolve_plan_addons(["gravel_grit"], "roadielabs")


def test_future_paid_addon_uses_only_server_owned_stripe_price():
    catalog = {
        "lab_review": PlanAddon(
            addon_id="lab_review",
            brands=frozenset({"roadielabs"}),
            stripe_price_env="TEST_LAB_REVIEW_PRICE",
        )
    }
    selection = resolve_plan_addons(
        ["lab_review"], "roadielabs", catalog=catalog)

    assert selection["optional"] == ["lab_review"]
    assert stripe_line_items_for_addons(
        selection["optional"],
        catalog=catalog,
        environ={"TEST_LAB_REVIEW_PRICE": "price_server_owned"},
    ) == [{"price": "price_server_owned", "quantity": 1}]


def test_future_paid_addon_without_valid_server_price_fails_closed():
    catalog = {
        "lab_review": PlanAddon(
            addon_id="lab_review",
            brands=frozenset({"roadielabs"}),
            stripe_price_env="TEST_LAB_REVIEW_PRICE",
        )
    }

    with pytest.raises(AddonSelectionError, match="not currently available"):
        stripe_line_items_for_addons(
            ["lab_review"], catalog=catalog, environ={})

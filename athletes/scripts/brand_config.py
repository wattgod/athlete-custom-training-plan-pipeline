#!/usr/bin/env python3
"""Load the shared multi-brand registry copied into the production image."""

from __future__ import annotations

import copy
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


BRANDS_PATH = Path(__file__).resolve().parent.parent / "config" / "brands.yaml"


@lru_cache(maxsize=1)
def _raw_registry() -> Dict[str, Any]:
    with BRANDS_PATH.open(encoding="utf-8") as handle:
        registry = yaml.safe_load(handle) or {}
    brands = registry.get("brands") or {}
    default = registry.get("default_brand")
    if not default or default not in brands:
        raise RuntimeError("brands.yaml must declare a valid default_brand")
    for key, cfg in brands.items():
        allowed = cfg.get("allowed_disciplines") or []
        if cfg.get("discipline") not in allowed:
            raise RuntimeError(
                f"brand {key!r} discipline must be in allowed_disciplines"
            )
    return registry


def default_brand() -> str:
    return str(_raw_registry()["default_brand"])


def normalize_brand(brand: Optional[str]) -> str:
    key = str(brand or "").strip().lower()
    return key if key in _raw_registry()["brands"] else default_brand()


def load_brands(resolve_env: bool = True) -> Dict[str, Dict[str, Any]]:
    """Return a mutable webhook-friendly copy of the brand registry.

    Analytics values remain at the historical top-level keys used by app.py;
    their defaults and environment-variable names live in brands.yaml.
    """
    brands = copy.deepcopy(_raw_registry()["brands"])
    if not resolve_env:
        return brands
    for cfg in brands.values():
        analytics = cfg.get("analytics") or {}
        measurement_env = analytics.get("measurement_id_env", "")
        secret_env = analytics.get("api_secret_env", "")
        cfg["ga4_measurement_id"] = os.environ.get(
            measurement_env, analytics.get("measurement_id", "")
        ) if measurement_env else analytics.get("measurement_id", "")
        cfg["ga4_mp_api_secret"] = os.environ.get(secret_env, "") if secret_env else ""

        email = cfg.get("email") or {}
        sender_env = email.get("resend_from_env", "")
        email["resend_from"] = (
            os.environ.get(sender_env, email.get("resend_from", ""))
            if sender_env else email.get("resend_from", "")
        )
    return brands


def get_brand_config(brand: Optional[str] = None, resolve_env: bool = True) -> Dict[str, Any]:
    return load_brands(resolve_env=resolve_env)[normalize_brand(brand)]


def brand_for_discipline(discipline: Optional[str]) -> str:
    disc = str(discipline or "").strip().lower()
    for key, cfg in _raw_registry()["brands"].items():
        if cfg.get("discipline") == disc:
            return key
    return default_brand()


def brand_from_profile(profile: Optional[dict], discipline: Optional[str] = None) -> str:
    profile = profile or {}
    explicit = str(profile.get("brand") or "").strip().lower()
    if explicit in _raw_registry()["brands"]:
        return explicit
    if discipline:
        return brand_for_discipline(discipline)
    explicit_disc = (
        profile.get("discipline")
        or (profile.get("target_race") or {}).get("discipline")
        or profile.get("discipline_default")
    )
    return brand_for_discipline(explicit_disc)


def workout_author(profile: Optional[dict] = None, discipline: Optional[str] = None) -> str:
    brand = brand_from_profile(profile, discipline)
    return str(get_brand_config(brand).get("workout_author") or "Gravel God Training")


def email_signature(profile: Optional[dict] = None, brand: Optional[str] = None) -> Dict[str, str]:
    key = normalize_brand(brand) if brand else brand_from_profile(profile)
    email = get_brand_config(key).get("email") or {}
    return {
        "name": str(email.get("signature_name") or "Matti"),
        "organization": str(email.get("signature_organization") or ""),
        "site": str(email.get("signature_site") or ""),
    }

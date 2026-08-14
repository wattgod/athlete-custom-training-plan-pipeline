"""Immutable archetype identity and ordered-slot resolution."""

from __future__ import annotations

import copy
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "archetype_ids.json"


class ArchetypeIdentityError(ValueError):
    """The immutable ID/slot registry is missing, malformed, or inconsistent."""


def slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", str(value)).encode(
        "ascii", "ignore"
    ).decode("ascii").casefold()
    return "-".join(re.findall(r"[a-z0-9]+", ascii_value))


def derived_id(category: str, name: str) -> str:
    category_slug, name_slug = slug(category), slug(name)
    if not category_slug or not name_slug:
        raise ArchetypeIdentityError("archetype category/name has an empty slug")
    return f"{category_slug}--{name_slug}"


@lru_cache(maxsize=4)
def load_id_map(path: str | Path = CONFIG_PATH) -> Dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArchetypeIdentityError("archetype ID registry is unavailable") from exc
    if set(payload) != {"schema_version", "categories"}:
        raise ArchetypeIdentityError("archetype ID registry has unknown root fields")
    if payload["schema_version"] != "archetype_ids/v1":
        raise ArchetypeIdentityError("unknown archetype ID registry version")
    categories = payload.get("categories")
    if not isinstance(categories, dict) or not categories:
        raise ArchetypeIdentityError("archetype ID registry has no categories")
    ids: set[str] = set()
    for category, slots in categories.items():
        if not isinstance(slots, list) or not slots:
            raise ArchetypeIdentityError(f"category {category!r} has no ordered slots")
        for slot in slots:
            if set(slot) != {"archetype_id", "name", "status", "replacement_id"}:
                raise ArchetypeIdentityError("archetype slot has unknown fields")
            identifier = slot.get("archetype_id")
            if not isinstance(identifier, str) or not identifier:
                raise ArchetypeIdentityError("archetype slot has no ID")
            if identifier in ids:
                raise ArchetypeIdentityError(f"duplicate archetype ID {identifier}")
            ids.add(identifier)
            if slot.get("status") not in {"active", "retired"}:
                raise ArchetypeIdentityError(f"invalid status for {identifier}")
            if identifier != derived_id(category, slot.get("name", "")):
                raise ArchetypeIdentityError(f"initial ID/name mismatch for {identifier}")
    by_id = {
        slot["archetype_id"]: (category, slot)
        for category, slots in categories.items() for slot in slots
    }
    for identifier, (category, slot) in by_id.items():
        replacement = slot.get("replacement_id")
        if replacement is None:
            continue
        target = by_id.get(replacement)
        if (target is None or target[0] != category
                or target[1].get("status") != "active"):
            raise ArchetypeIdentityError(f"invalid replacement for {identifier}")
        if target[1].get("replacement_id") is not None:
            raise ArchetypeIdentityError("replacement chains are forbidden")
    return payload


def validate_live_registry(live: Dict[str, Iterable[Dict[str, Any]]]) -> None:
    configured = load_id_map()["categories"]
    if list(configured) != list(live):
        raise ArchetypeIdentityError("live category order differs from immutable slots")
    for category, slots in configured.items():
        live_names = [entry.get("name") for entry in live[category]]
        if live_names != [slot["name"] for slot in slots]:
            raise ArchetypeIdentityError(
                f"live archetype order differs from immutable {category} slots")


def resolve_slot(category: str, index: int) -> Dict[str, Any]:
    slots = load_id_map()["categories"].get(category)
    if not slots:
        raise ArchetypeIdentityError(f"unknown archetype category {category!r}")
    chosen_index = int(index) % len(slots)
    chosen = slots[chosen_index]
    if chosen["status"] == "active":
        return copy.deepcopy(chosen)
    replacement = chosen.get("replacement_id")
    if replacement:
        return next(copy.deepcopy(slot) for slot in slots
                    if slot["archetype_id"] == replacement)
    for offset in range(1, len(slots)):
        candidate = slots[(chosen_index + offset) % len(slots)]
        if candidate["status"] == "active":
            return copy.deepcopy(candidate)
    raise ArchetypeIdentityError(f"category {category!r} has no active archetype")


def resolve_live(category: str, index: int,
                 live: Dict[str, list[Dict[str, Any]]]) -> Dict[str, Any]:
    validate_live_registry(live)
    slot = resolve_slot(category, index)
    for archetype in live[category]:
        if archetype.get("name") == slot["name"]:
            result = copy.deepcopy(archetype)
            result["archetype_id"] = slot["archetype_id"]
            return result
    raise ArchetypeIdentityError(f"active ID {slot['archetype_id']} has no live definition")


def get_by_id(identifier: str,
              live: Dict[str, list[Dict[str, Any]]]) -> tuple[str, Dict[str, Any]]:
    validate_live_registry(live)
    for category, slots in load_id_map()["categories"].items():
        for index, slot in enumerate(slots):
            if slot["archetype_id"] == identifier:
                resolved = resolve_slot(category, index)
                for live_entry in live[category]:
                    if live_entry.get("name") == resolved["name"]:
                        value = copy.deepcopy(live_entry)
                        value["archetype_id"] = resolved["archetype_id"]
                        return category, value
    raise ArchetypeIdentityError(f"unknown archetype ID {identifier!r}")

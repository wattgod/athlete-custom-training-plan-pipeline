"""Road-racing format and USA Cycling category helpers.

Explicit intake always wins. Keyword inference is intentionally conservative;
an unknown road event stays generic_road and is reviewable instead of being
silently invented.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


_CONFIG = Path(__file__).parent.parent / "config" / "road_racing.yaml"


@lru_cache(maxsize=1)
def load_road_racing_config() -> Dict[str, Any]:
    with _CONFIG.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _key(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def normalize_event_format(value: Any) -> Optional[str]:
    raw = _key(value)
    if not raw:
        return None
    for key, cfg in load_road_racing_config().get("event_formats", {}).items():
        aliases = {_key(alias) for alias in cfg.get("aliases", [])}
        if raw == key or raw in aliases:
            return key
    return None


def resolve_event_format(profile: Dict[str, Any]) -> Dict[str, Any]:
    race = profile.get("target_race", {}) or {}
    for value in (
        race.get("event_format"), race.get("race_format"),
        profile.get("event_format"), profile.get("race_format"),
    ):
        normalized = normalize_event_format(value)
        if normalized:
            return {"event_format": normalized, "source": "explicit", "needs_review": False}

    name = str(race.get("name") or "").lower()
    matches = []
    for key, cfg in load_road_racing_config().get("event_formats", {}).items():
        if key == "generic_road":
            continue
        if any(str(keyword).lower() in name for keyword in cfg.get("keywords", [])):
            matches.append(key)
    if len(matches) == 1:
        return {"event_format": matches[0], "source": "race_name", "needs_review": False}
    return {"event_format": "generic_road", "source": "default", "needs_review": True}


def normalize_road_category(value: Any) -> Optional[str]:
    raw = str(value or "").strip().lower().replace("category", "cat")
    compact = "".join(ch for ch in raw if ch.isalnum())
    aliases = {
        "novice": "cat_5", "cat5": "cat_5", "5": "cat_5",
        "cat4": "cat_4", "4": "cat_4",
        "cat3": "cat_3", "3": "cat_3",
        "cat2": "cat_2", "2": "cat_2",
        "cat1": "cat_1", "1": "cat_1",
        "unlicensed": "unlicensed", "none": "unlicensed", "na": "unlicensed",
    }
    return aliases.get(compact)


def road_category_profile(value: Any) -> Optional[Dict[str, Any]]:
    category = normalize_road_category(value)
    if not category or category == "unlicensed":
        return None
    data = (load_road_racing_config().get("category_progression", {})
            .get("categories", {}).get(category))
    if not data:
        return None
    return {"category": category, **data}


def event_format_profile(value: Any) -> Dict[str, Any]:
    normalized = normalize_event_format(value) or "generic_road"
    data = load_road_racing_config().get("event_formats", {}).get(normalized, {})
    return {"event_format": normalized, **data}

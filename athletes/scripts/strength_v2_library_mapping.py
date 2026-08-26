"""AE-8.4b (2026-08-24 TP review): strength card -> V2 TP library mapping.

Ruling: "Strength ships structured -- the V2 recipe in TP 3770562 /
strength-program overhaul, never text-only cards."

Repo-side reality (checked before writing this module): `strength_template`
(`generate_athlete_package.py::_strength_template_key`) is a deterministic
KEY only ("foundation_a", "max_strength_b", ...) -- its own docstring says
"rx content/API is out of scope for this workstream". No TP `structure`
(step/targets/exercise) is ever built for a strength session anywhere in
this repo; `delivery_render._strength_template` turns the key into a title
("Foundation A") for a session that ships as a plain text card. The actual
set/rep/exercise V2 recipe lives only in Matti's TP library (org 146d7bb3,
library 3770562) -- per the ruling, this module does NOT fabricate a
structure. It maps every KEY this pipeline actually emits to the phase
context needed to find the matching V2 library item, so the coordinating
session can pull the real structure from TP rather than guess one here.

`athletes/config/strength_periodization.yaml` documents phase-level
sets/reps/exercises but uses a DIFFERENT phase taxonomy than the one
`_strength_template_key` emits (anatomical_adaptation/max_strength/
maintenance/race_prep/racing/deload vs. foundation/max_strength/power/
maintenance) and has no explicit "peak" entry -- flagged per key below
rather than silently reconciled, since guessing the wrong periodization.yaml
row for "power" would misinform the TP pull.
"""
from __future__ import annotations

from typing import Any, Dict, List

# Every KEY _strength_template_key can emit (generate_athlete_package.py),
# with the phase it comes from and the delivered card title
# (delivery_render._strength_template + " - {duration}min").
_TEMPLATE_KEYS: List[Dict[str, Any]] = [
    {
        "template_key": "foundation_a", "phase": "base",
        "delivered_title": "Foundation A",
        "periodization_yaml_row": "anatomical_adaptation",
        "note": None,
    },
    {
        "template_key": "foundation_b", "phase": "base",
        "delivered_title": "Foundation B",
        "periodization_yaml_row": "anatomical_adaptation",
        "note": None,
    },
    {
        "template_key": "max_strength_a", "phase": "build",
        "delivered_title": "Max Strength A",
        "periodization_yaml_row": "max_strength",
        "note": None,
    },
    {
        "template_key": "max_strength_b", "phase": "build",
        "delivered_title": "Max Strength B",
        "periodization_yaml_row": "max_strength",
        "note": None,
    },
    {
        "template_key": "power_a", "phase": "peak",
        "delivered_title": "Power A",
        "periodization_yaml_row": None,
        "note": ("strength_periodization.yaml has no 'peak' cycling_phase row -- "
                 "closest documented rows are race_prep/racing. Confirm the V2 "
                 "library's actual peak-phase strength item before mapping."),
    },
    {
        "template_key": "power_b", "phase": "peak",
        "delivered_title": "Power B",
        "periodization_yaml_row": None,
        "note": ("strength_periodization.yaml has no 'peak' cycling_phase row -- "
                 "closest documented rows are race_prep/racing. Confirm the V2 "
                 "library's actual peak-phase strength item before mapping."),
    },
    {
        # taper/race also resolve to 'maintenance_a' via _strength_template_key
        # (capped at one session/week for those two phases).
        "template_key": "maintenance_a", "phase": "maintenance / taper / race",
        "delivered_title": "Maintenance A",
        "periodization_yaml_row": "maintenance",
        "note": None,
    },
]


def build_mapping() -> List[Dict[str, Any]]:
    """Return the template-key -> V2-library-lookup manifest.

    Every row's ``tp_v2_library_item`` is left unresolved (None) rather than
    guessed -- the coordinating session fills this in from a live read of TP
    library 3770562, then this manifest is the checklist that every KEY the
    pipeline emits got a real structure, not a fabricated one.
    """
    rows = []
    for entry in _TEMPLATE_KEYS:
        rows.append({
            **entry,
            "tp_v2_library_item": None,  # fill from TP 3770562; never fabricate
            "repo_has_structured_emission": False,
        })
    return rows


if __name__ == "__main__":
    import json
    print(json.dumps(build_mapping(), indent=2))

"""Contract tests for the offline RUN-LIB TrainingPeaks folder builder."""

from __future__ import annotations

from copy import deepcopy
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from build_run_tp_library import (  # noqa: E402
    FOLDER_NAME,
    generate_library_payload,
    main,
    reconcile_library_dump,
)
from run_archetypes import RUN_ARCHETYPES, get_run_level  # noqa: E402
from run_structure_export import validate_tp_structure  # noqa: E402


LEVELED_NAME = re.compile(
    r"^Run [A-Z][A-Za-z0-9 ]* - .+ - [1-6] - [1-9][0-9]*min - RPE[1-9]-[1-9]$"
)
BRIEF_NAME = re.compile(r"^Run Race Day - .+ - brief$")


def independent_dump_projection(item):
    """Model a browser-folder export without using the builder's reconciler projection."""
    fields = ("itemName", "workoutTypeValueId", "totalTimePlanned", "tssPlanned", "description", "structure")
    return {field: deepcopy(item[field]) for field in fields if field in item}


def faithful_dump():
    return [independent_dump_projection(item) for item in generate_library_payload()["items"]]


def test_payload_has_all_80_unique_conventionally_named_items():
    payload = generate_library_payload()
    names = [item["itemName"] for item in payload["items"]]

    assert payload["folder_name"] == FOLDER_NAME
    assert len(payload["items"]) == 80
    assert len(names) == len(set(names))
    assert all(LEVELED_NAME.fullmatch(name) or BRIEF_NAME.fullmatch(name) for name in names)


def test_leveled_items_preserve_library_time_tss_and_valid_structure():
    payload = generate_library_payload()
    leveled_items = [item for item in payload["items"] if "structure" in item]

    assert len(leveled_items) == 78
    for item in leveled_items:
        assert item["workoutTypeValueId"] == 3
        assert "BPM" not in item["description"]
        validate_tp_structure(item["structure"])

    expected = [item for item in generate_library_payload()["items"] if "structure" in item]
    assert [item["totalTimePlanned"] for item in expected] == [
        item["totalTimePlanned"] for item in leveled_items
    ]
    assert [item["tssPlanned"] for item in expected] == [
        item["tssPlanned"] for item in leveled_items
    ]


def test_briefs_are_description_only_with_library_tss():
    payload = generate_library_payload()
    briefs = [item for item in payload["items"] if "structure" not in item]

    assert len(briefs) == 2
    for item in briefs:
        assert set(item) == {"itemName", "workoutTypeValueId", "tssPlanned", "description"}
        assert item["tssPlanned"] in {
            workout["tss"] for workout in RUN_ARCHETYPES.values() if workout.get("structure_exempt")
        }


def test_reconciler_accepts_a_faithful_dump():
    report = reconcile_library_dump(faithful_dump())

    assert report == {"missing": [], "extra": [], "mismatched": []}


def test_reconciler_detects_seeded_missing_extra_and_mismatch():
    dump = faithful_dump()
    missing_name = dump.pop()["itemName"]
    mismatch_name = dump[0]["itemName"]
    dump[0] = {**dump[0], "tssPlanned": dump[0]["tssPlanned"] + 1}
    dump.append({
        "itemName": "Run Other - Unexpected - 1 - 30min - RPE2-3",
        "workoutTypeValueId": 3,
        "totalTimePlanned": 0.5,
        "tssPlanned": 18,
        "description": "Unexpected.",
        "structure": generate_library_payload()["items"][0]["structure"],
    })

    report = reconcile_library_dump(dump)

    assert report["missing"] == [missing_name]
    assert report["extra"] == ["Run Other - Unexpected - 1 - 30min - RPE2-3"]
    assert report["mismatched"] == [{
        "itemName": mismatch_name,
        "fields": {"tssPlanned": {"expected": dump[0]["tssPlanned"] - 1, "actual": dump[0]["tssPlanned"]}},
    }]


@pytest.mark.parametrize("corruption", ["type", "description", "target", "structure"])
def test_reconciler_detects_all_faithful_body_corruption(corruption):
    dump = faithful_dump()
    item = next(item for item in dump if "structure" in item)
    item_name = item["itemName"]
    if corruption == "type":
        item["workoutTypeValueId"] = 13
    elif corruption == "description":
        item["description"] += " altered"
    elif corruption == "target":
        item["structure"]["structure"][0]["steps"][0]["targets"][0]["maxValue"] += 1
    else:
        item.pop("structure")

    report = reconcile_library_dump(dump)

    mismatch = next(entry for entry in report["mismatched"] if entry["itemName"] == item_name)
    assert mismatch["fields"]


def test_cli_writes_payload_and_returns_reconciliation_status(tmp_path, capsys):
    output_path = tmp_path / "payload.json"
    assert main(["--out", str(output_path)]) == 0
    assert json.loads(output_path.read_text(encoding="utf-8")) == generate_library_payload()

    dump_path = tmp_path / "faithful-dump.json"
    dump_path.write_text(json.dumps(faithful_dump()), encoding="utf-8")
    assert main(["--reconcile", str(dump_path)]) == 0
    assert "missing:\n  none" in capsys.readouterr().out

    incomplete_dump = faithful_dump()[1:]
    dump_path.write_text(json.dumps(incomplete_dump), encoding="utf-8")
    assert main(["--reconcile", str(dump_path)]) == 1
    assert "missing:\n  Run " in capsys.readouterr().out


def test_every_leveled_payload_item_tracks_its_authored_library_record():
    """Tie the generic item body directly to the R1 library rather than fixtures."""
    payload = generate_library_payload()
    for archetype_id, archetype in RUN_ARCHETYPES.items():
        if archetype.get("structure_exempt"):
            continue
        for level, level_data in archetype["levels"].items():
            matching = [
                item for item in payload["items"]
                if f" - {archetype['display_name']} - {level} - " in item["itemName"]
            ]
            assert len(matching) == 1
            assert matching[0]["totalTimePlanned"] == level_data["duration"] / 3600
            assert matching[0]["tssPlanned"] == level_data["tss"]
            assert level_data == get_run_level(archetype_id, level)


def test_digest_is_browser_serialization_stable():
    """A dump that round-tripped through browser JSON (300.0 -> 300) must digest identically."""
    from build_run_tp_library import _structure_digest

    item = next(i for i in generate_library_payload()["items"] if "structure" in i)

    def browserify(obj):
        if isinstance(obj, bool):
            return obj
        if isinstance(obj, float) and obj.is_integer():
            return int(obj)
        if isinstance(obj, dict):
            return {k: browserify(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [browserify(v) for v in obj]
        return obj

    assert _structure_digest(item["structure"]) == _structure_digest(browserify(item["structure"]))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s["structure"][0].__setitem__("begin", s["structure"][0]["begin"] + 30),
        lambda s: s["structure"][0]["steps"][0]["length"].__setitem__("unit", "minute"),
        lambda s: s["structure"][0]["steps"][0].__setitem__("openDuration", True),
        lambda s: s.__setitem__("primaryIntensityMetric", "percentOfFtp"),
    ],
    ids=["begin", "length-unit", "openDuration", "primaryIntensityMetric"],
)
def test_digest_detects_semantic_structure_mutations(mutate):
    from build_run_tp_library import _structure_digest
    import copy

    item = next(i for i in generate_library_payload()["items"] if "structure" in i)
    baseline = _structure_digest(item["structure"])
    corrupted = copy.deepcopy(item["structure"])
    mutate(corrupted)
    assert _structure_digest(corrupted) != baseline

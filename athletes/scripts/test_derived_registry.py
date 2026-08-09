"""A3 provenance and sensitivity enforcement regressions."""
from __future__ import annotations

import pytest
import os
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from derived_registry import (DerivedRegistryError, assert_registry_covers,
                              entry, materialize,
                              registry_document)


def _record(**overrides):
    values = dict(id="SECRET_TARGET", field="fitness.target", value_class="inferred",
                  basis="seeded sensitive fixture", inputs={"duration": 4},
                  sensitivity="sensitive", at="2026-08-08T12:00:00Z",
                  revision=3)
    values.update(overrides)
    return entry(**values)


def test_versioned_registry_materializes_typed_value():
    document = {"fitness": {"target": 67}}
    registry = registry_document([_record()], revision=3)
    derived = materialize(document, registry["entries"], namespace="fueling")
    assert derived[0]["id"] == "FUELING_SECRET_TARGET"
    assert derived[0]["value"] == 67
    assert derived[0]["sensitivity"] == "sensitive"
    assert derived[0]["revision"] == registry["revision"] == 3


def test_registry_rejects_missing_or_stale_entry_revision():
    values = dict(id="X", field="x", value_class="inferred", basis="b",
                  inputs={}, sensitivity="internal")
    with pytest.raises(TypeError):
        entry(**values)
    with pytest.raises(DerivedRegistryError, match="match registry"):
        registry_document([entry(**values, revision=1)], revision=2)


def test_coverage_gate_fails_when_a_derived_output_lacks_provenance():
    from derive_classifications import derive_all
    document = derive_all({
        "weekly_availability": {"cycling_hours_target": 8},
        "target_race": {"goal_type": "finish"},
        "training_history": {"years_structured": 3},
    })
    records = document.pop("_derived")
    document["new_computed_output"] = 8675309
    with pytest.raises(DerivedRegistryError, match="undeclared computed output"):
        assert_registry_covers(
            document, records, artifact="derived", revision=1,
        )


def test_caller_cannot_supply_a_self_declared_coverage_list():
    with pytest.raises(TypeError):
        assert_registry_covers(
            {"x": 1, "new_computed_output": 2}, [],
            required_fields=["x"], revision=1,
        )


def test_fueling_cli_does_not_print_seeded_sensitive_targets(tmp_path):
    athlete_id = "seeded-cli-sensitive"
    athlete_dir = tmp_path / athlete_id
    athlete_dir.mkdir()
    profile = {
        "fitness_markers": {
            "weight_kg": 73.4, "sex": "female", "power_basis": "none",
            "ftp_watts": None, "reanchor": {"action": "field test"},
        },
        "target_race": {
            "distance_miles": 137, "elevation_ft": 8400,
            "goal_type": "compete",
        },
        "nutrition": {"gut_training_phase": "build"},
        "fulfillment": {
            "generation_revision": 1,
            "generation_at": "2026-08-08T12:00:00Z",
        },
    }
    (athlete_dir / "profile.yaml").write_text(yaml.safe_dump(profile))
    (athlete_dir / "derived.yaml").write_text("plan_weeks: 12\n")
    env = os.environ.copy()
    env["GG_ATHLETES_BASE_DIR"] = str(tmp_path)
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "calculate_fueling.py"), athlete_id],
        check=True, capture_output=True, text=True, env=env,
    )
    fueling = yaml.safe_load((athlete_dir / "fueling.yaml").read_text())
    output = completed.stdout
    secret_values = [
        fueling["carbohydrates"]["hourly_target"],
        *fueling["carbohydrates"]["hourly_range"],
    ]
    assert all(f"{value}g/hr" not in output for value in secret_values)
    assert str(fueling["calories"]["total_calories"]) not in output
    assert "authenticated review" in output


@pytest.mark.parametrize("field,value", [
    ("class", "guessed"), ("sensitivity", "unclassified"),
])
def test_registry_rejects_unknown_policy_labels(field, value):
    kwargs = {"value_class" if field == "class" else field: value}
    with pytest.raises(DerivedRegistryError):
        _record(**kwargs)

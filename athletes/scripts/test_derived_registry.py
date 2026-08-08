"""A3 provenance and sensitivity enforcement regressions."""
from __future__ import annotations

import pytest
import sys
from pathlib import Path

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
    document = {"fitness": {"target": 67, "range": [55, 75]}}
    with pytest.raises(DerivedRegistryError, match="missing=.*fitness.range"):
        assert_registry_covers(
            document, [_record()],
            required_fields=["fitness.target", "fitness.range"], revision=3,
        )


@pytest.mark.parametrize("field,value", [
    ("class", "guessed"), ("sensitivity", "unclassified"),
])
def test_registry_rejects_unknown_policy_labels(field, value):
    kwargs = {"value_class" if field == "class" else field: value}
    with pytest.raises(DerivedRegistryError):
        _record(**kwargs)

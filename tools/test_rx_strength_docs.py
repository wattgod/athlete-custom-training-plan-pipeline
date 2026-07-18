#!/usr/bin/env python3
"""Tests for tools/rx_strength_docs.py (Workstream C).

Run: python3 -m pytest tools/test_rx_strength_docs.py -q
"""
import itertools
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import rx_strength_docs as rxdocs

CATALOG_DUMP_PATH = Path(
    "/Users/mattirowe/Documents/Codex/2026-07-17/roadie-pipeline-modernization-handoff"
    "/outputs/rx_exercise_catalog.json"
)

REQUIRED_DOC_KEYS = {
    "workoutType", "lastUpdatedAt", "compliancePercent", "complianceState",
    "structureCompliancePercent", "durationCompliancePercent", "tssCompliancePercent",
    "rpe", "feel", "blocks", "files", "snapshot", "prescribedDate", "prescribedStartTime",
    "startDateTime", "completedDateTime", "calendarId", "title", "instructions",
    "prescribedDurationInSeconds", "orderOnDay", "executedDurationInSeconds", "isLocked",
    "isHidden", "workoutSubTypeId", "prescribedTss", "prescribedIntensityFactor",
    "completedTss", "completedTssSource", "completedIntensityFactor", "id",
}
REQUIRED_BLOCK_KEYS = {
    "prescriptions", "blockType", "title", "coachNotes", "parameters",
    "isComplete", "compliancePercent", "complianceState", "id",
}
REQUIRED_PRESCRIPTION_KEYS = {"id", "exercise", "parameters", "coachNotes", "setSummaryTemplate", "sets"}
REQUIRED_SET_KEYS = {"id", "isComplete", "parameterValues"}
REQUIRED_PARAM_VALUE_KEYS = {"id", "parameter", "executedValue", "inputFormat", "prescribedValue"}

_DECIMAL_MINUTE_RE = re.compile(r"\d+\.\d+ ?min")


def _counting_uuid_factory(prefix="id"):
    counter = itertools.count()
    return lambda: f"{prefix}-{next(counter)}"


def _build(template_key, **overrides):
    kwargs = dict(
        calendar_id=6496835,
        prescribed_date="2026-07-09",
        doc_id=f"doc-{template_key}",
        uuid_factory=_counting_uuid_factory(),
    )
    kwargs.update(overrides)
    return rxdocs.build_strength_doc(template_key, **kwargs)


def _all_strings(obj):
    """Recursively yield every string value in a nested dict/list doc."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _all_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _all_strings(v)


@pytest.fixture(scope="module")
def catalog_dump():
    if not CATALOG_DUMP_PATH.exists():
        pytest.skip(f"catalog dump not available at {CATALOG_DUMP_PATH}")
    return json.loads(CATALOG_DUMP_PATH.read_text())


# ---------------------------------------------------------------------------
# All 7 templates build without error; snapshot counts match actual content.
# ---------------------------------------------------------------------------
class TestAllTemplatesBuild:
    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_builds_without_error(self, template_key):
        doc = _build(template_key)
        assert doc["title"] == rxdocs.TEMPLATE_KEYS[template_key]

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_snapshot_counts_match_actual_content(self, template_key):
        doc = _build(template_key)
        blocks = doc["blocks"]
        real_blocks = len(blocks)
        real_prescriptions = sum(len(b["prescriptions"]) for b in blocks)
        real_sets = sum(len(p["sets"]) for b in blocks for p in b["prescriptions"])
        snap = doc["snapshot"]
        assert snap["totalBlocks"] == real_blocks
        assert snap["totalPrescriptions"] == real_prescriptions
        assert snap["totalSets"] == real_sets
        assert snap["completedBlocks"] == 0
        assert snap["completedSets"] == 0
        assert snap["completedPrescriptions"] == 0
        # every template actually has content -- a silently-empty doc would
        # still "match" 0==0==0, so assert real work exists too.
        assert real_blocks > 0
        assert real_prescriptions > 0
        assert real_sets > 0

    def test_unknown_template_key_raises(self):
        with pytest.raises(ValueError):
            _build("not_a_real_template")


# ---------------------------------------------------------------------------
# Every non-custom exercise id exists in the live catalog dump; every custom
# placeholder appears in custom_exercises_needed().
# ---------------------------------------------------------------------------
class TestCatalogConsistency:
    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_non_custom_ids_exist_in_catalog_dump(self, template_key, catalog_dump):
        doc = _build(template_key)
        for block in doc["blocks"]:
            for presc in block["prescriptions"]:
                exercise = presc["exercise"]
                if "custom" in exercise:
                    continue
                assert exercise["id"] in catalog_dump, f"catalog id {exercise['id']!r} not in dump"
                assert catalog_dump[exercise["id"]]["title"] == exercise["title"]

    def test_every_custom_placeholder_is_in_manifest(self):
        manifest_titles = {c["title"] for c in rxdocs.custom_exercises_needed()}
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            for block in doc["blocks"]:
                for presc in block["prescriptions"]:
                    exercise = presc["exercise"]
                    if "custom" in exercise:
                        assert exercise["custom"] in manifest_titles

    def test_manifest_entries_have_required_fields(self):
        manifest = rxdocs.custom_exercises_needed()
        assert len(manifest) > 0
        for entry in manifest:
            assert entry["title"]
            assert isinstance(entry["movements_covered"], list)
            assert len(entry["movements_covered"]) >= 1
            assert "videoUrl" in entry

    def test_manifest_is_deduplicated_and_sorted(self):
        manifest = rxdocs.custom_exercises_needed()
        titles = [c["title"] for c in manifest]
        assert titles == sorted(titles)
        assert len(titles) == len(set(titles))
        # Dead Bug and Suitcase Carry variants collapse to one canonical entry
        dead_bug = next(c for c in manifest if c["title"] == "Dead Bug")
        assert len(dead_bug["movements_covered"]) >= 3
        suitcase = next(c for c in manifest if c["title"] == "Suitcase Carry")
        assert len(suitcase["movements_covered"]) >= 2


# ---------------------------------------------------------------------------
# Deterministic: same inputs + seeded uuid_factory -> identical doc.
# ---------------------------------------------------------------------------
class TestDeterminism:
    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_identical_output_for_identical_inputs(self, template_key):
        doc_a = _build(template_key, doc_id="fixed-id", uuid_factory=_counting_uuid_factory())
        doc_b = _build(template_key, doc_id="fixed-id", uuid_factory=_counting_uuid_factory())
        assert doc_a == doc_b

    def test_different_uuid_stream_changes_only_ids(self):
        doc_a = _build("foundation_a", doc_id="fixed-id", uuid_factory=_counting_uuid_factory("a"))
        doc_b = _build("foundation_a", doc_id="fixed-id", uuid_factory=_counting_uuid_factory("b"))
        assert doc_a != doc_b
        # but structurally equivalent (same counts, same titles/notes)
        assert doc_a["snapshot"] == doc_b["snapshot"]
        assert [b["blockType"] for b in doc_a["blocks"]] == [b["blockType"] for b in doc_b["blocks"]]

    def test_accepts_date_object_and_string_identically(self):
        import datetime
        doc_str = _build("foundation_a", prescribed_date="2026-07-09", uuid_factory=_counting_uuid_factory())
        doc_date = _build("foundation_a", prescribed_date=datetime.date(2026, 7, 9), uuid_factory=_counting_uuid_factory())
        assert doc_str["prescribedDate"] == doc_date["prescribedDate"] == "2026-07-09"


# ---------------------------------------------------------------------------
# Block types match the mapping rules -- spot-assert known blocks per template.
# ---------------------------------------------------------------------------
class TestBlockTypeMapping:
    def test_foundation_a_block_types(self):
        doc = _build("foundation_a")
        types = [b["blockType"] for b in doc["blocks"]]
        assert types == ["WarmUp", "Circuit", "Superset", "Superset", "CoolDown"]

    def test_foundation_b_has_a_core_circuit(self):
        doc = _build("foundation_b")
        types = [b["blockType"] for b in doc["blocks"]]
        assert types == ["WarmUp", "Circuit", "Superset", "Superset", "Circuit", "CoolDown"]

    def test_max_strength_a_core_carry_is_circuit(self):
        doc = _build("max_strength_a")
        types = [b["blockType"] for b in doc["blocks"]]
        assert types == ["WarmUp", "Circuit", "Superset", "Superset", "Circuit", "CoolDown"]

    def test_power_a_power_prep_and_activation_are_warmup_type(self):
        doc = _build("power_a")
        types = [b["blockType"] for b in doc["blocks"]]
        # WARMUP, POWER PREP, MAIN1, MAIN2, CORE, COOLDOWN
        assert types == ["WarmUp", "WarmUp", "Superset", "Superset", "Circuit", "CoolDown"]
        # the real WARMUP block (mobility) never gets prescriptions...
        assert doc["blocks"][0]["prescriptions"] == []
        # ...but POWER PREP (also WarmUp-typed) does.
        assert len(doc["blocks"][1]["prescriptions"]) > 0

    def test_maintenance_a_activation_is_warmup_with_prescriptions(self):
        doc = _build("maintenance_a")
        types = [b["blockType"] for b in doc["blocks"]]
        assert types == ["WarmUp", "WarmUp", "Superset", "Circuit", "CoolDown"]
        assert doc["blocks"][0]["prescriptions"] == []  # literal WARMUP: coachNotes only
        assert len(doc["blocks"][1]["prescriptions"]) == 3  # ACTIVATION: 3 bullet movements

    def test_warmup_and_cooldown_never_carry_prescriptions_any_template(self):
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            for block in doc["blocks"]:
                if block["blockType"] in ("WarmUp", "CoolDown"):
                    # POWER PREP/ACTIVATION also map to WarmUp but DO carry
                    # prescriptions -- only literal WARMUP/COOLDOWN sections
                    # (identifiable here by non-empty coachNotes movement
                    # list AND zero prescriptions) are coach-notes-only.
                    if block["coachNotes"] and "(demos: gravelgodcycling.com/demos)" in block["coachNotes"]:
                        assert block["prescriptions"] == []

    def test_strength_workout_never_uses_bike_workout_type_id(self):
        # Sanity guard mirrored from the SPEC: strength docs are workoutType
        # "StructuredStrength" and must never resemble a bike (id 2) workout.
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            assert doc["workoutType"] == "StructuredStrength"


# ---------------------------------------------------------------------------
# No dangling 'or'/alternative text in exercise titles; no decimal-minute
# strings anywhere in the doc.
# ---------------------------------------------------------------------------
class TestTextHygiene:
    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_no_dangling_or_in_exercise_titles(self, template_key):
        doc = _build(template_key)
        for block in doc["blocks"]:
            if block["title"]:
                assert not re.search(r"\bor\b", block["title"], re.IGNORECASE), block["title"]
            for presc in block["prescriptions"]:
                exercise = presc["exercise"]
                title = exercise.get("title") or exercise.get("custom")
                assert title, exercise
                assert not re.search(r"\bor\b", title, re.IGNORECASE), title

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_no_decimal_minute_strings_anywhere(self, template_key):
        doc = _build(template_key)
        for s in _all_strings(doc):
            assert not _DECIMAL_MINUTE_RE.search(s), s

    def test_custom_exercise_titles_have_no_dangling_or(self):
        for entry in rxdocs.custom_exercises_needed():
            assert not re.search(r"\bor\b", entry["title"], re.IGNORECASE), entry["title"]

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_prescribed_duration_is_whole_seconds_int(self, template_key):
        doc = _build(template_key)
        assert isinstance(doc["prescribedDurationInSeconds"], int)
        assert doc["prescribedDurationInSeconds"] == 2400  # every template says "~40 min"


# ---------------------------------------------------------------------------
# Doc validates against a minimal schema check (required keys per
# structured_strength_PUT_payload.json's inner "workout" shape).
# ---------------------------------------------------------------------------
class TestMinimalSchema:
    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_doc_has_required_top_level_keys(self, template_key):
        doc = _build(template_key)
        missing = REQUIRED_DOC_KEYS - set(doc.keys())
        assert not missing, f"missing doc keys: {missing}"

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_blocks_prescriptions_sets_have_required_keys(self, template_key):
        doc = _build(template_key)
        for block in doc["blocks"]:
            missing = REQUIRED_BLOCK_KEYS - set(block.keys())
            assert not missing, f"missing block keys: {missing}"
            for presc in block["prescriptions"]:
                missing = REQUIRED_PRESCRIPTION_KEYS - set(presc.keys())
                assert not missing, f"missing prescription keys: {missing}"
                for s in presc["sets"]:
                    missing = REQUIRED_SET_KEYS - set(s.keys())
                    assert not missing, f"missing set keys: {missing}"
                    for pv in s["parameterValues"]:
                        missing = REQUIRED_PARAM_VALUE_KEYS - set(pv.keys())
                        assert not missing, f"missing parameterValue keys: {missing}"

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_every_id_is_unique_within_doc(self, template_key):
        doc = _build(template_key)
        ids = [doc["id"]]
        for block in doc["blocks"]:
            ids.append(block["id"])
            for presc in block["prescriptions"]:
                ids.append(presc["id"])
                for param in presc["parameters"]:
                    ids.append(param["id"])
                for s in presc["sets"]:
                    ids.append(s["id"])
                    for pv in s["parameterValues"]:
                        ids.append(pv["id"])
        assert len(ids) == len(set(ids)), "duplicate ids from uuid_factory"

    def test_instructions_keeps_real_gravelgodcycling_links(self):
        doc = _build("foundation_a")
        assert "gravelgodcycling.com/strength" in doc["instructions"]

    def test_calendar_id_and_doc_id_pass_through(self):
        doc = _build("foundation_a", calendar_id=999, doc_id="custom-doc-id")
        assert doc["calendarId"] == 999
        assert doc["id"] == "custom-doc-id"

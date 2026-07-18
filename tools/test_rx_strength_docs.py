#!/usr/bin/env python3
"""Tests for tools/rx_strength_docs.py (Workstream C).

Run: python3 -m pytest tools/test_rx_strength_docs.py -q
"""
import itertools
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import rx_strength_docs as rxdocs

# Findings doc top-level shape (outputs/rx_strength_capture_findings.md,
# 2026-07-17 live probes): the minimal set of keys a real captured PUT body
# carries. This module's return value is a superset (it also carries the
# fuller structured_strength_PUT_payload.json fields) -- both are checked.
FINDINGS_DOC_TOP_LEVEL_KEYS = {
    "id", "workoutType", "calendarId", "prescribedDate", "title", "instructions",
    "prescribedDurationInSeconds", "orderOnDay", "blocks", "files", "snapshot",
}
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
REQUIRED_PRESCRIPTION_KEYS = {
    "id", "exercise", "parameters", "coachNotes", "setSummaryTemplate", "sets",
    "compliancePercent", "complianceState",
}
REQUIRED_SET_KEYS = {"id", "isComplete", "setOrigin", "parameterValues"}
# NOTE: the SAVE endpoint (stricter than the standalone PUT) rejects a
# `category` key on per-set parameterValues -- it must NOT be present here,
# even though the exercise-level/prescription-level Reps parameter DEFS keep
# `category`. See TestSaveEndpointShape.test_parameter_values_have_no_category_key.
REQUIRED_PARAM_VALUE_KEYS = {"id", "parameter", "executedValue", "inputFormat", "prescribedValue"}
REQUIRED_CUSTOM_EXERCISE_KEYS = {
    "id", "ownerId", "title", "videoUrl", "instructions", "primaryMuscleGroups",
    "secondaryMuscleGroups", "canEdit", "parameters",
}
REQUIRED_CATALOG_EXERCISE_KEYS = {"id", "title", "ownerId", "videoUrl", "instructions", "parameters"}

_DECIMAL_MINUTE_RE = re.compile(r"\d+\.\d+ ?min")


def _is_custom_exercise(exercise: dict) -> bool:
    """Custom exercises carry a client uuid id (not a bare digit string);
    catalog exercises carry the real numeric catalog id as a string."""
    return not str(exercise["id"]).isdigit()


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
# Inline exercise model (2026-07-17 findings doc): catalog movements embed
# the real string catalog id + fields sourced from tools/rx_exercise_catalog
# .json (checked into this repo -- no external-path dependency); custom
# movements embed a FULL inline exercise object (client uuid id, ownerId
# 2000301, canEdit: true) -- never a `{custom: title}` placeholder.
# custom_exercises_needed() is informational only; it no longer gates
# anything the driver does.
# ---------------------------------------------------------------------------
class TestCatalogConsistency:
    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_catalog_movements_embed_real_string_id_from_the_dump(self, template_key):
        doc = _build(template_key)
        for block in doc["blocks"]:
            for presc in block["prescriptions"]:
                exercise = presc["exercise"]
                if _is_custom_exercise(exercise):
                    continue
                assert exercise["id"] in rxdocs.CATALOG_DUMP, f"catalog id {exercise['id']!r} not in dump"
                dump_entry = rxdocs.CATALOG_DUMP[exercise["id"]]
                assert exercise["title"] == dump_entry["title"]
                assert exercise["videoUrl"] == dump_entry.get("video", "")
                assert exercise["ownerId"] == dump_entry.get("owner")
                assert set(exercise.keys()) == REQUIRED_CATALOG_EXERCISE_KEYS

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_custom_movements_embed_full_inline_exercise_object(self, template_key):
        doc = _build(template_key)
        found_custom = False
        for block in doc["blocks"]:
            for presc in block["prescriptions"]:
                exercise = presc["exercise"]
                if not _is_custom_exercise(exercise):
                    continue
                found_custom = True
                assert "custom" not in exercise, "no more {custom: title} placeholders"
                assert set(exercise.keys()) == REQUIRED_CUSTOM_EXERCISE_KEYS
                assert exercise["ownerId"] == 2000301
                assert exercise["canEdit"] is True
                assert exercise["primaryMuscleGroups"] is None
                assert exercise["secondaryMuscleGroups"] is None
                assert exercise["title"]
                assert isinstance(exercise["videoUrl"], str)
                assert isinstance(exercise["instructions"], str)
                # id is a client-generated uuid-ish token, not a bare digit
                # string (which would collide with a catalog id).
                assert not str(exercise["id"]).isdigit()
                assert len(exercise["parameters"]) == 1
                assert exercise["parameters"][0]["parameter"] == "Reps"
        # every template has at least one custom-mapped movement
        assert found_custom

    def test_all_exercises_carry_a_reps_parameter_definition(self):
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            for block in doc["blocks"]:
                for presc in block["prescriptions"]:
                    params = presc["exercise"]["parameters"]
                    assert len(params) == 1
                    assert params[0]["parameter"] == "Reps"
                    assert params[0]["category"] == "Reps"

    def test_custom_exercises_needed_is_informational_and_matches_inline_titles(self):
        """The manifest still lists which canonical movements are inlined as
        custom exercises, but nothing in build_strength_doc()'s output
        depends on it -- every custom exercise is already fully resolved
        inline."""
        manifest_titles = {c["title"] for c in rxdocs.custom_exercises_needed()}
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            for block in doc["blocks"]:
                for presc in block["prescriptions"]:
                    exercise = presc["exercise"]
                    if _is_custom_exercise(exercise):
                        assert exercise["title"] in manifest_titles

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
                title = exercise["title"]
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
                exercise = presc["exercise"]
                # custom exercises carry a uuid_factory-generated id too;
                # catalog exercises carry a fixed real string id (not from
                # uuid_factory) so it's excluded from the uniqueness check.
                if _is_custom_exercise(exercise):
                    ids.append(exercise["id"])
                for param in exercise["parameters"]:
                    ids.append(param["id"])
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

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_matches_findings_doc_top_level_shape(self, template_key):
        """JSON-shape assertion against outputs/rx_strength_capture_
        findings.md's verified top-level doc shape (id, workoutType,
        calendarId, prescribedDate, title, instructions,
        prescribedDurationInSeconds, orderOnDay, blocks, files, snapshot)."""
        doc = _build(template_key, calendar_id=6496835)
        missing = FINDINGS_DOC_TOP_LEVEL_KEYS - set(doc.keys())
        assert not missing, f"missing findings-doc top-level keys: {missing}"
        assert doc["workoutType"] == "StructuredStrength"
        assert doc["calendarId"] == 6496835
        assert isinstance(doc["blocks"], list)
        assert isinstance(doc["files"], list) and doc["files"] == []
        assert isinstance(doc["snapshot"], dict)
        for block in doc["blocks"]:
            assert block["blockType"] in (
                "WarmUp", "Superset", "Circuit", "SingleExercise", "CoolDown",
            )


# ---------------------------------------------------------------------------
# Reps values kept verbatim (ranges NOT truncated to the low end). EVERY
# prescription carries exactly 1 Reps parameter -- a second live probe
# (2026-07-17) found that param-less prescriptions (`parameters: []`) return
# HTTP 200 but 3 field errors ("A Prescription must include at least 1
# Parameter"); the findings doc's earlier "param-less is valid" claim was
# based on a probe that never actually persisted. Per-side ("10/side") and
# timed ("60 sec") movements now get a Reps SURROGATE value (the leading
# number, or "1" for a pure duration/no-count text) plus the full raw text
# unconditionally echoed into coachNotes as "Rx: <text>".
# ---------------------------------------------------------------------------
class TestRepsAndParamless:
    def test_rep_ranges_preserved_verbatim_not_truncated(self):
        # Max Strength (A) MAIN 1: "Goblet Squat ─ 6-8 reps" -- old behavior
        # truncated this to "6"; the live-verified behavior keeps "6-8".
        doc = _build("max_strength_a")
        found = False
        for block in doc["blocks"]:
            for presc in block["prescriptions"]:
                if presc["exercise"]["title"] != "Goblet Squat":
                    continue
                for s in presc["sets"]:
                    for pv in s["parameterValues"]:
                        if pv["parameter"] == "Reps":
                            assert pv["prescribedValue"] == "6-8"
                            found = True
        assert found, "expected a Goblet Squat Reps prescription in max_strength_a"

    def test_reps_parameter_value_never_truncated_to_low_end_anywhere(self):
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            for block in doc["blocks"]:
                for presc in block["prescriptions"]:
                    for s in presc["sets"]:
                        for pv in s["parameterValues"]:
                            assert pv["parameter"] == "Reps"
                            # a bare int or a "low-high" range, never mangled
                            assert re.fullmatch(r"\d+(-\d+)?", pv["prescribedValue"]), pv["prescribedValue"]

    def test_every_prescription_carries_at_least_one_parameter(self):
        # The core regression this class guards: "A Prescription must
        # include at least 1 Parameter" (live field error on parameters:[]).
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            for block in doc["blocks"]:
                for presc in block["prescriptions"]:
                    assert len(presc["parameters"]) >= 1, presc
                    for s in presc["sets"]:
                        assert len(s["parameterValues"]) >= 1, s

    def test_per_side_reps_get_a_reps_surrogate_with_rx_in_coach_notes(self):
        # Foundation (A) PREP: "Hip Rails ─ 10/side"
        doc = _build("foundation_a")
        presc = next(
            p
            for b in doc["blocks"]
            for p in b["prescriptions"]
            if p["exercise"]["title"] == "Hip Rails"
        )
        assert presc["parameters"][0]["parameter"] == "Reps"
        assert presc["setSummaryTemplate"] == "{Reps}"
        assert "Rx: 10/side" in presc["coachNotes"]
        for s in presc["sets"]:
            assert s["parameterValues"][0]["parameter"] == "Reps"
            # "10/side" -> the leading number "10", NOT the per-side detail
            assert s["parameterValues"][0]["prescribedValue"] == "10"
            assert s["setOrigin"] == "Prescribed"
            assert s["isComplete"] is False

    def test_timed_movements_get_reps_one_with_rx_in_coach_notes(self):
        # Max Strength (A) CORE/CARRY: "Hollow Body Hold ─ 20 sec"
        doc = _build("max_strength_a")
        presc = next(
            p
            for b in doc["blocks"]
            for p in b["prescriptions"]
            if p["exercise"]["title"] == "Hollow Body Hold"
        )
        assert presc["parameters"][0]["parameter"] == "Reps"
        assert presc["setSummaryTemplate"] == "{Reps}"
        assert "Rx: 20 sec" in presc["coachNotes"]
        for s in presc["sets"]:
            # NEVER "20" -- that would misread as 20 reps of a hold.
            assert s["parameterValues"][0]["prescribedValue"] == "1"

    def test_all_prescriptions_have_reps_summary_template(self):
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            for block in doc["blocks"]:
                for presc in block["prescriptions"]:
                    assert presc["setSummaryTemplate"] == "{Reps}"

    def test_forced_note_surrogate_and_plain_reps_prescriptions_both_present(self):
        # "1" only ever comes from the reps_forced_note timed/no-count path
        # (never a real Reps prescription -- nobody prescribes literally 1
        # rep); a multi-digit value with no "Rx:" note is a plain Reps
        # prescription whose raw text didn't need echoing.
        saw_forced_note_surrogate = False
        saw_plain_reps_no_note = False
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            for block in doc["blocks"]:
                for presc in block["prescriptions"]:
                    value = presc["sets"][0]["parameterValues"][0]["prescribedValue"]
                    if value == "1":
                        saw_forced_note_surrogate = True
                    elif "Rx:" not in (presc["coachNotes"] or ""):
                        saw_plain_reps_no_note = True
        assert saw_forced_note_surrogate and saw_plain_reps_no_note


# ---------------------------------------------------------------------------
# rx SAVE-endpoint shape (findings doc, "SOLVED -- rx plan-attach save call",
# 2026-07-17): stricter than the standalone PUT. parameterValues drop
# `category` and use `inputFormat:"Integer"` (not null); every block AND
# every prescription carries `compliancePercent:0`/`complianceState:
# "NoCompletion"`; SingleExercise blocks take the exercise's own title.
# ---------------------------------------------------------------------------
class TestSaveEndpointShape:
    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_parameter_values_have_no_category_key(self, template_key):
        doc = _build(template_key)
        for block in doc["blocks"]:
            for presc in block["prescriptions"]:
                for s in presc["sets"]:
                    for pv in s["parameterValues"]:
                        assert "category" not in pv, pv

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_parameter_values_input_format_is_integer(self, template_key):
        doc = _build(template_key)
        for block in doc["blocks"]:
            for presc in block["prescriptions"]:
                for s in presc["sets"]:
                    for pv in s["parameterValues"]:
                        assert pv["inputFormat"] == "Integer", pv

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_parameter_values_still_match_required_shape_exactly(self, template_key):
        doc = _build(template_key)
        for block in doc["blocks"]:
            for presc in block["prescriptions"]:
                for s in presc["sets"]:
                    for pv in s["parameterValues"]:
                        assert set(pv.keys()) == {
                            "id", "parameter", "inputFormat", "prescribedValue", "executedValue",
                        }
                        assert pv["parameter"] == "Reps"
                        assert pv["executedValue"] is None

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_prescription_level_and_exercise_level_params_keep_category(self, template_key):
        # Only the per-set parameterValues drop category -- the prescription's
        # own parameters[] param DEF and the exercise object's parameters[]
        # still carry it.
        doc = _build(template_key)
        for block in doc["blocks"]:
            for presc in block["prescriptions"]:
                for pdef in presc["parameters"]:
                    assert pdef["category"] == "Reps"
                for pdef in presc["exercise"]["parameters"]:
                    assert pdef["category"] == "Reps"

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_every_prescription_has_compliance_fields(self, template_key):
        doc = _build(template_key)
        for block in doc["blocks"]:
            for presc in block["prescriptions"]:
                assert presc["compliancePercent"] == 0
                assert presc["complianceState"] == "NoCompletion"

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_every_block_has_compliance_fields(self, template_key):
        doc = _build(template_key)
        for block in doc["blocks"]:
            assert block["compliancePercent"] == 0
            assert block["complianceState"] == "NoCompletion"

    def test_single_exercise_block_title_is_the_exercise_title(self):
        # None of the 7 real templates happen to produce a SingleExercise
        # block (every MAIN section has >=2 movements) -- exercise the
        # mapping rule directly against a synthetic single-movement MAIN
        # block, same as _build_block sees from the real parser.
        block = rxdocs._RawBlock(
            name="MAIN", num=1, subtitle=None, duration=None, meta=["3 sets", "90s rest"],
            movements=[rxdocs._RawMovement(slot="A1", raw_name="Goblet Squat", presc_text="8 reps")],
        )
        block_dict, n_presc, n_sets = rxdocs._build_block(block, _counting_uuid_factory())
        assert block_dict["blockType"] == "SingleExercise"
        assert block_dict["title"] == "Goblet Squat"
        assert block_dict["title"] == block_dict["prescriptions"][0]["exercise"]["title"]
        assert n_presc == 1 and n_sets == 3

    def test_multi_exercise_blocks_keep_block_type_title_not_exercise_title(self):
        # Superset/Circuit/WarmUp/CoolDown block titles stay the generic
        # block-type title (or coachNotes-only), never an exercise title.
        doc = _build("foundation_a")
        for block in doc["blocks"]:
            if block["blockType"] in ("Superset", "Circuit"):
                assert block["title"] == block["blockType"]

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
# even though the exercise-level/prescription-level parameter DEFS keep
# `category`. See TestSaveEndpointShape.test_parameter_values_have_no_category_key.
REQUIRED_PARAM_VALUE_KEYS = {"id", "parameter", "executedValue", "inputFormat", "prescribedValue"}
# Matti's FINAL ALL-CATALOG decision (2026-07-17): every embedded exercise is
# the FULL live object from rx_exercise_catalog_full.json -- no more trimmed
# stubs and no more inline custom-exercise objects. This is the one shape
# every exercise object now has, regardless of match_kind (exact/fuzzy/mapped).
REQUIRED_EXERCISE_KEYS = {
    "id", "ownerId", "title", "videoUrl", "instructions", "primaryMuscleGroups",
    "secondaryMuscleGroups", "canEdit", "parameters",
}
# The "count" parameter a prescription may end up using -- whichever the
# target exercise itself declares (see _choose_count_param).
VALID_COUNT_PARAMS = {"Reps", "RepsPerSide", "DistanceFt"}

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
# ALL-CATALOG model (Matti's final decision, 2026-07-17, supersedes the
# inline-custom-exercise model): every movement -- exact, fuzzy, or one of
# the former 17 "custom" movements -- resolves to a real catalog id and
# embeds the FULL live exercise object from rx_exercise_catalog_full.json.
# There are no more inline custom-exercise objects; custom_exercises_needed()
# is a no-op stub.
# ---------------------------------------------------------------------------
class TestAllCatalogModel:
    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_every_exercise_id_is_numeric_never_a_uuid(self, template_key):
        doc = _build(template_key)
        for block in doc["blocks"]:
            for presc in block["prescriptions"]:
                exercise = presc["exercise"]
                assert str(exercise["id"]).isdigit(), f"non-catalog exercise id {exercise['id']!r}"

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_embedded_exercise_matches_full_catalog_dump_entry_exactly(self, template_key):
        doc = _build(template_key)
        for block in doc["blocks"]:
            for presc in block["prescriptions"]:
                exercise = presc["exercise"]
                dump_entry = rxdocs.CATALOG_DUMP[str(exercise["id"])]
                assert exercise == dump_entry, f"exercise {exercise['id']!r} was mutated from the dump"
                assert set(exercise.keys()) == REQUIRED_EXERCISE_KEYS

    @pytest.mark.parametrize("canonical,mapping", sorted(rxdocs.CUSTOM_MOVEMENT_CATALOG_MAP.items()))
    def test_all_17_former_custom_movements_resolve_via_the_map(self, canonical, mapping):
        # Every CUSTOM_CANONICAL value must have an entry in the map, and the
        # map's catalog_id must actually be a real, resolvable catalog id.
        expected_cid = int(mapping["catalog_id"])
        assert str(expected_cid) in rxdocs.CATALOG_DUMP
        assert rxdocs.CATALOG_DUMP[str(expected_cid)]["title"] == mapping["catalog_title"]

    def test_custom_canonical_values_are_a_subset_of_the_map_keys(self):
        assert set(rxdocs.CUSTOM_CANONICAL.values()) <= set(rxdocs.CUSTOM_MOVEMENT_CATALOG_MAP.keys())

    def test_mapped_movement_resolves_to_its_map_catalog_id_with_original_name_in_notes(self):
        # Foundation (A) MAIN 2: "Dead Bug (add light weight)" -> canonical
        # "Dead Bug" -> mapped to catalog id 528 "DeadBug".
        doc = _build("foundation_a")
        mapping = rxdocs.CUSTOM_MOVEMENT_CATALOG_MAP["Dead Bug"]
        presc = next(
            p for b in doc["blocks"] for p in b["prescriptions"]
            if p["exercise"]["id"] == mapping["catalog_id"]
        )
        assert presc["exercise"]["title"] == mapping["catalog_title"] == "DeadBug"
        assert "Orig: Dead Bug (add light weight)" in presc["coachNotes"]

    def test_suitcase_carry_resolves_to_waiters_carry(self):
        # Foundation (A) MAIN 2: "Suitcase Carry (single side)" -> canonical
        # "Suitcase Carry" -> mapped to catalog id 921 "Waiter's Carry".
        doc = _build("foundation_a")
        presc = next(
            p for b in doc["blocks"] for p in b["prescriptions"]
            if p["exercise"]["id"] == "921"
        )
        assert presc["exercise"]["title"] == "Waiter's Carry"
        assert "Orig: Suitcase Carry (single side)" in presc["coachNotes"]

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_exact_and_fuzzy_matches_still_carry_original_cue_notes(self, template_key):
        # Spot check that fuzzy/exact behavior is unaffected by the
        # ALL-CATALOG change -- only 'mapped' (former custom) is new.
        doc = _build(template_key)
        for block in doc["blocks"]:
            for presc in block["prescriptions"]:
                assert isinstance(presc["coachNotes"], (str, type(None)))

    def test_custom_exercises_needed_is_a_noop_stub(self):
        assert rxdocs.custom_exercises_needed() == []


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
# Block types match the mapping rules -- spot-assert known blocks per
# template. NOTE (2026-07-17 change): literal WARMUP/COOLDOWN sections (kind
# "coach_only", always zero prescriptions) are no longer emitted as blocks at
# all -- they're dropped and folded into doc-level `instructions` instead
# (see TestBlockFolding). POWER PREP/ACTIVATION still map to blockType
# "WarmUp" but DO carry prescriptions, so they stay as real blocks.
# ---------------------------------------------------------------------------
class TestBlockTypeMapping:
    def test_foundation_a_block_types(self):
        doc = _build("foundation_a")
        types = [b["blockType"] for b in doc["blocks"]]
        assert types == ["Circuit", "Superset", "Superset"]

    def test_foundation_b_has_a_core_circuit(self):
        doc = _build("foundation_b")
        types = [b["blockType"] for b in doc["blocks"]]
        assert types == ["Circuit", "Superset", "Superset", "Circuit"]

    def test_max_strength_a_core_carry_is_circuit(self):
        doc = _build("max_strength_a")
        types = [b["blockType"] for b in doc["blocks"]]
        assert types == ["Circuit", "Superset", "Superset", "Circuit"]

    def test_power_a_power_prep_and_activation_are_warmup_type(self):
        doc = _build("power_a")
        types = [b["blockType"] for b in doc["blocks"]]
        # literal WARMUP dropped/folded; POWER PREP, MAIN1, MAIN2, CORE remain.
        assert types == ["WarmUp", "Superset", "Superset", "Circuit"]
        # POWER PREP (WarmUp-typed) DOES carry prescriptions.
        assert len(doc["blocks"][0]["prescriptions"]) > 0

    def test_maintenance_a_activation_is_warmup_with_prescriptions(self):
        doc = _build("maintenance_a")
        types = [b["blockType"] for b in doc["blocks"]]
        # literal WARMUP dropped/folded; ACTIVATION, MAIN, CORE remain.
        assert types == ["WarmUp", "Superset", "Circuit"]
        assert len(doc["blocks"][0]["prescriptions"]) == 3  # ACTIVATION: 3 bullet movements

    def test_no_block_ever_has_empty_prescriptions(self):
        # The plan save endpoint's behavior on an empty `prescriptions` array
        # is unverified -- every emitted block must carry at least one.
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            for block in doc["blocks"]:
                assert block["prescriptions"], f"{template_key}: empty-prescriptions block {block['blockType']}"

    def test_cooldown_block_type_never_appears(self):
        # COOLDOWN only ever maps to kind "coach_only" (no other template
        # section produces a CoolDown-typed block with prescriptions), so
        # after the empty-block-drop rule it can never survive into `blocks`.
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            assert "CoolDown" not in [b["blockType"] for b in doc["blocks"]]

    def test_strength_workout_never_uses_bike_workout_type_id(self):
        # Sanity guard mirrored from the SPEC: strength docs are workoutType
        # "StructuredStrength" and must never resemble a bike (id 2) workout.
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            assert doc["workoutType"] == "StructuredStrength"


# ---------------------------------------------------------------------------
# Empty-prescription blocks (literal WARMUP/COOLDOWN) are folded into
# doc-level `instructions` as "WARMUP:"/"COOLDOWN:" sections instead of being
# emitted as blocks.
# ---------------------------------------------------------------------------
class TestBlockFolding:
    def test_foundation_a_instructions_contain_folded_warmup_and_cooldown(self):
        doc = _build("foundation_a")
        assert "WARMUP:" in doc["instructions"]
        assert "COOLDOWN:" in doc["instructions"]
        assert "Downward Dog Lunge + Rotation" in doc["instructions"]
        assert "Deep Squat Sit" in doc["instructions"]
        assert "(demos: gravelgodcycling.com/demos)" in doc["instructions"]

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_every_template_folds_warmup_and_cooldown(self, template_key):
        doc = _build(template_key)
        assert "WARMUP:" in doc["instructions"]
        assert "COOLDOWN:" in doc["instructions"]

    def test_folded_sections_precede_zero_equipment_and_notes(self):
        doc = _build("foundation_a")
        text = doc["instructions"]
        assert text.index("WARMUP:") < text.index("COOLDOWN:") < text.index("ZERO EQUIPMENT") < text.index("NOTES")


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
                missing = REQUIRED_EXERCISE_KEYS - set(presc["exercise"].keys())
                assert not missing, f"missing exercise keys: {missing}"
                for s in presc["sets"]:
                    missing = REQUIRED_SET_KEYS - set(s.keys())
                    assert not missing, f"missing set keys: {missing}"
                    for pv in s["parameterValues"]:
                        missing = REQUIRED_PARAM_VALUE_KEYS - set(pv.keys())
                        assert not missing, f"missing parameterValue keys: {missing}"

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_every_uuid_factory_id_is_unique_within_doc(self, template_key):
        # Exercise ids (and their OWN nested parameters[].id) are real,
        # stable catalog ids -- the same exercise legitimately appears more
        # than once in a doc (e.g. Med Ball Slam covers two movements in
        # Power (A)), so they're excluded here. Only ids actually minted by
        # uuid_factory (block/prescription/prescription-param-def/set/
        # parameterValue) are checked for uniqueness.
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

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_same_catalog_exercise_can_repeat_within_a_doc(self, template_key):
        # Documents the inverse of the above: catalog exercise ids are NOT
        # required to be unique within a doc (a movement mapped to the same
        # catalog exercise as another movement is expected, e.g. Power (A)'s
        # "Med Ball Slam" and "Med Ball Chest Pass" both map to catalog id 64).
        doc = _build(template_key)
        for block in doc["blocks"]:
            for presc in block["prescriptions"]:
                assert str(presc["exercise"]["id"]).isdigit()

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
# Count-parameter values kept verbatim (ranges NOT truncated to the low
# end). EVERY prescription carries exactly 1 parameter -- a second live
# probe (2026-07-17) found that param-less prescriptions (`parameters: []`)
# return HTTP 200 but 3 field errors ("A Prescription must include at least
# 1 Parameter"); the findings doc's earlier "param-less is valid" claim was
# based on a probe that never actually persisted. Per-side ("10/side") and
# timed ("60 sec") movements now get a surrogate value (the leading number,
# or "1" for a pure duration/no-count text) plus the full raw text
# unconditionally echoed into coachNotes as "Rx: <text>". WHICH parameter is
# used (Reps / RepsPerSide / DistanceFt) is derived from the target
# exercise's own declaration -- not hardcoded to "Reps" (see module
# docstring's flagged inference).
# ---------------------------------------------------------------------------
class TestRepsAndParamless:
    def test_rep_ranges_preserved_verbatim_not_truncated(self):
        # Max Strength (A) MAIN 1: "Goblet Squat ─ 6-8 reps" -- old behavior
        # truncated this to "6"; the live-verified behavior keeps "6-8".
        # Goblet Squat (catalog id 144) declares "Reps".
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

    def test_count_parameter_value_never_truncated_to_low_end_anywhere(self):
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            for block in doc["blocks"]:
                for presc in block["prescriptions"]:
                    for s in presc["sets"]:
                        for pv in s["parameterValues"]:
                            assert pv["parameter"] in VALID_COUNT_PARAMS, pv["parameter"]
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

    def test_prescription_parameter_never_fabricated_off_the_exercise(self):
        # The prescription's chosen parameter must be one the target
        # exercise itself actually declares -- never a hardcoded "Reps" for
        # an exercise that doesn't declare it (that repeats the proven
        # structural-400 mistake in the opposite direction).
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            for block in doc["blocks"]:
                for presc in block["prescriptions"]:
                    param_name = presc["parameters"][0]["parameter"]
                    exercise_param_names = {p["parameter"] for p in presc["exercise"]["parameters"]}
                    assert param_name in exercise_param_names, (
                        f"{presc['exercise']['title']!r} doesn't declare {param_name!r}"
                    )

    def test_per_side_reps_get_a_repsperside_surrogate_with_rx_in_coach_notes(self):
        # Foundation (A) PREP: "MiniBand Marches ─ 10/side" -> catalog id 942
        # "X Band Walk", which declares ONLY RepsPerSide -- semantically the
        # right fit for a per-side movement.
        doc = _build("foundation_a")
        presc = next(
            p
            for b in doc["blocks"]
            for p in b["prescriptions"]
            if p["exercise"]["title"] == "X Band Walk"
        )
        assert presc["parameters"][0]["parameter"] == "RepsPerSide"
        assert presc["setSummaryTemplate"] == "{RepsPerSide}"
        assert "Rx: 10/side" in presc["coachNotes"]
        for s in presc["sets"]:
            assert s["parameterValues"][0]["parameter"] == "RepsPerSide"
            # "10/side" -> the leading number "10", NOT the per-side detail
            assert s["parameterValues"][0]["prescribedValue"] == "10"
            assert s["setOrigin"] == "Prescribed"
            assert s["isComplete"] is False

    def test_per_side_reps_on_a_reps_declaring_exercise_uses_reps(self):
        # Foundation (A) PREP: "Hip Rails ─ 10/side" -> catalog id 884
        # "Straight Legged Hip Raise", which DOES declare plain "Reps".
        doc = _build("foundation_a")
        presc = next(
            p
            for b in doc["blocks"]
            for p in b["prescriptions"]
            if p["exercise"]["title"] == "Straight Legged Hip Raise"
        )
        assert presc["parameters"][0]["parameter"] == "Reps"
        assert presc["setSummaryTemplate"] == "{Reps}"
        assert "Rx: 10/side" in presc["coachNotes"]
        assert presc["sets"][0]["parameterValues"][0]["prescribedValue"] == "10"

    def test_timed_movements_get_count_one_with_rx_in_coach_notes(self):
        # Max Strength (A) CORE/CARRY: "Hollow Body Hold ─ 20 sec" -> catalog
        # id 892 "Superman Hold", which declares "Reps".
        doc = _build("max_strength_a")
        presc = next(
            p
            for b in doc["blocks"]
            for p in b["prescriptions"]
            if p["exercise"]["title"] == "Superman Hold"
        )
        assert presc["setSummaryTemplate"] == "{" + presc["parameters"][0]["parameter"] + "}"
        assert "Rx: 20 sec" in presc["coachNotes"]
        for s in presc["sets"]:
            # NEVER "20" -- that would misread as 20 reps/side of a hold.
            assert s["parameterValues"][0]["prescribedValue"] == "1"

    def test_all_prescriptions_summary_template_matches_their_own_parameter(self):
        for template_key in rxdocs.TEMPLATE_KEYS:
            doc = _build(template_key)
            for block in doc["blocks"]:
                for presc in block["prescriptions"]:
                    param_name = presc["parameters"][0]["parameter"]
                    assert presc["setSummaryTemplate"] == "{" + param_name + "}"

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
# Later probe (same day): plan save also 500s on inline custom exercises and
# requires the FULL catalog object -- covered by TestAllCatalogModel.
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
                        assert pv["parameter"] in VALID_COUNT_PARAMS
                        assert pv["executedValue"] is None

    @pytest.mark.parametrize("template_key", sorted(rxdocs.TEMPLATE_KEYS))
    def test_prescription_level_and_exercise_level_params_keep_category(self, template_key):
        # Only the per-set parameterValues drop category -- the prescription's
        # own parameters[] param DEF and the exercise object's parameters[]
        # still carry it (whatever category the exercise itself declares --
        # "Reps", "Reps/side", or "Distance").
        doc = _build(template_key)
        for block in doc["blocks"]:
            for presc in block["prescriptions"]:
                for pdef in presc["parameters"]:
                    assert pdef["category"]
                for pdef in presc["exercise"]["parameters"]:
                    assert pdef["category"]

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
        # Superset/Circuit block titles stay the generic block-type title,
        # never an exercise title.
        doc = _build("foundation_a")
        for block in doc["blocks"]:
            if block["blockType"] in ("Superset", "Circuit"):
                assert block["title"] == block["blockType"]

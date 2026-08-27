"""Tests for tools/publish_athlete.py, the generalized kernel publisher
extracted from the three proven one-off scripts (cheesehead-publish,
sonja-publish, steve-publish -- all under the coach's private, non-git
TrainingPeaksPublisher directory).

No live TP transport runs here -- only --stage offline (bootstrap, adoption
contract build, wave filter, normalize, seal, APPROVE) is exercised
end-to-end, plus the pure normalization/filter/schema helpers in isolation.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "webhook"))
sys.path.insert(0, str(ROOT / "athletes" / "scripts"))

import publish_athlete as P  # noqa: E402
from fulfillment_state import write_generation, load as load_state  # noqa: E402
from d2_identity import record_identity_result  # noqa: E402


# --------------------------------------------------------------- collapse
def test_collapse_spaces_collapses_internal_runs_not_at_line_start():
    assert P.collapse_spaces("5 minutes.  Note here.") == "5 minutes. Note here."


def test_collapse_spaces_preserves_line_start_indentation():
    assert P.collapse_spaces("  indented\nrun:  two  spaces") == "  indented\nrun: two spaces"


def test_collapse_spaces_only_touches_description_and_title_keys():
    payload = {"description": "a  b", "title": "c  d", "body": "e  f", "date": "2026-08-16"}
    out = P.collapse_spaces(payload)
    assert out["description"] == "a b" and out["title"] == "c d"
    assert out["body"] == "e  f", "non description/title keys must not be touched"


def test_collapse_spaces_is_shallow_only_description_and_title_keys_recurse():
    # Matches the proven scripts exactly: collapse_spaces is applied
    # directly to a flat create payload (date/title/description at the
    # top level), never to an arbitrarily nested structure -- a dict
    # value under any OTHER key is passed through untouched, even if it
    # itself contains a "description" key.
    out = P.collapse_spaces({"title": "a  b", "payload": {"description": "x  y"}})
    assert out["title"] == "a b"
    assert out["payload"]["description"] == "x  y"


def test_stable_normalizes_integral_floats_recursively():
    assert P.stable({"tss_planned": 71.0, "nested": [36.0, 1.5]}) == {
        "tss_planned": 71, "nested": [36, 1.5]}


# --------------------------------------------------- athlete-layer normalize
def test_normalize_athlete_description_collapses_internal_spaces():
    assert P.normalize_athlete_description("5 minutes.  Note here.") == "5 minutes. Note here."


def test_normalize_athlete_description_strips_continuation_line_leading_whitespace():
    # Juan Echeverri (TP 1683197), 2026-08-25: TP strips leading whitespace
    # on continuation lines on top of the internal-space collapse.
    desired = "Warmup 10min.\n  changes to Zone 2 after.\n    Cool down easy."
    assert P.normalize_athlete_description(desired) == (
        "Warmup 10min.\nchanges to Zone 2 after.\nCool down easy.")


def test_normalize_athlete_description_strips_trailing_whitespace():
    assert P.normalize_athlete_description("Body text.  \n") == "Body text."


def test_normalize_athlete_description_handles_none():
    assert P.normalize_athlete_description(None) == ""


# ------------------------------------------------------------ wave filter
def _op(date, title, disposition="create", kind="workout_upsert"):
    return {
        "kind": kind, "disposition": disposition,
        "payload": {"date": date, "title": title, "description": "d  d"} if disposition == "create" else None,
    }


def test_filter_drops_creates_already_on_the_baseline_calendar():
    baseline = {"workouts": [{"date": "2026-08-16", "title": "Endurance"}], "notes": []}
    ops = [_op("2026-08-16", "Endurance"), _op("2026-08-17", "Intervals")]
    kept, dropped, deferred = P.filter_and_normalize_operations(
        ops, baseline=baseline, wave_cutoff=None, expected_creates=1)
    assert dropped == 1 and deferred == 0
    assert [o["payload"]["title"] for o in kept] == ["Intervals"]


def test_filter_defers_creates_beyond_wave_cutoff():
    baseline = {"workouts": [], "notes": []}
    ops = [_op("2026-08-16", "In wave"), _op("2026-09-30", "Next wave")]
    kept, dropped, deferred = P.filter_and_normalize_operations(
        ops, baseline=baseline, wave_cutoff="2026-08-31", expected_creates=1)
    assert deferred == 1 and dropped == 0
    assert [o["payload"]["title"] for o in kept] == ["In wave"]


def test_filter_normalizes_surviving_create_payloads_before_digest():
    baseline = {"workouts": [], "notes": []}
    ops = [_op("2026-08-16", "Assessment")]
    ops[0]["payload"]["tss_planned"] = 71.0
    kept, _, _ = P.filter_and_normalize_operations(
        ops, baseline=baseline, wave_cutoff=None, expected_creates=1)
    assert kept[0]["payload"]["description"] == "d d"
    assert kept[0]["payload"]["tss_planned"] == 71
    assert kept[0]["expected_digest"] == P.digest(kept[0]["payload"])


def test_filter_keeps_and_notes_pass_through_unfiltered():
    baseline = {"workouts": [], "notes": []}
    ops = [_op(None, None, disposition="keep")]
    kept, dropped, deferred = P.filter_and_normalize_operations(
        ops, baseline=baseline, wave_cutoff=None, expected_creates=0)
    assert kept == ops and dropped == 0 and deferred == 0


def test_expected_creates_assertion_refuses_to_seal_on_mismatch():
    baseline = {"workouts": [], "notes": []}
    ops = [_op("2026-08-16", "Only one")]
    with pytest.raises(P.PublishAthleteError, match=r"expected exactly 2 missing creates, got 1"):
        P.filter_and_normalize_operations(ops, baseline=baseline, wave_cutoff=None, expected_creates=2)


def test_expected_creates_assertion_passes_on_exact_match():
    baseline = {"workouts": [], "notes": []}
    ops = [_op("2026-08-16", "One"), _op("2026-08-17", "Two")]
    kept, _, _ = P.filter_and_normalize_operations(
        ops, baseline=baseline, wave_cutoff=None, expected_creates=2)
    assert len(kept) == 2


# ------------------------------------------------- content conflict (dedup)
def test_content_mismatch_on_matching_tuple_is_a_conflict_not_a_silent_drop():
    # Baseline carries an existing BLANK-body card at the same (kind, date,
    # title); the desired create carries a full body ("d  d"). The tuple
    # matches but content does not -- must refuse, never silently drop the
    # full-body create in favor of the blank baseline row.
    baseline = {"workouts": [{"date": "2026-08-16", "title": "Endurance", "description": ""}],
                "notes": []}
    ops = [_op("2026-08-16", "Endurance")]
    with pytest.raises(P.PublishAthleteError, match="CONFLICT"):
        P.filter_and_normalize_operations(ops, baseline=baseline, wave_cutoff=None, expected_creates=0)


def test_content_mismatch_waived_via_waiver_reason():
    baseline = {"workouts": [{"date": "2026-08-16", "title": "Endurance", "description": ""}],
                "notes": []}
    ops = [_op("2026-08-16", "Endurance")]
    kept, dropped, deferred = P.filter_and_normalize_operations(
        ops, baseline=baseline, wave_cutoff=None, expected_creates=0,
        waiver_reason="confirmed blank placeholder, coach reviewed 2026-08-26")
    assert kept == [] and dropped == 1 and deferred == 0


def test_content_match_on_matching_tuple_is_dropped_normally_no_conflict():
    # Baseline description (post athlete-layer normalization) DOES match
    # the desired create's -- genuinely already landed, drop silently.
    baseline = {"workouts": [{"date": "2026-08-16", "title": "Endurance", "description": "d d"}],
                "notes": []}
    ops = [_op("2026-08-16", "Endurance")]  # payload description == "d  d"
    kept, dropped, deferred = P.filter_and_normalize_operations(
        ops, baseline=baseline, wave_cutoff=None, expected_creates=0)
    assert kept == [] and dropped == 1 and deferred == 0


def test_baseline_row_missing_description_field_is_not_a_conflict():
    # Existing dedup tests (test_filter_drops_creates_already_on_the_
    # baseline_calendar) rely on this: a baseline row that doesn't carry a
    # "description" key at all (summary-only inventory read) can't be
    # compared, so it must not be treated as a conflict.
    baseline = {"workouts": [{"date": "2026-08-16", "title": "Endurance"}], "notes": []}
    ops = [_op("2026-08-16", "Endurance")]
    kept, dropped, deferred = P.filter_and_normalize_operations(
        ops, baseline=baseline, wave_cutoff=None, expected_creates=0)
    assert kept == [] and dropped == 1


def test_workout_structure_presence_mismatch_is_a_conflict():
    baseline = {"workouts": [{"date": "2026-08-16", "title": "Endurance",
                               "description": "d d", "structure": None}], "notes": []}
    ops = [_op("2026-08-16", "Endurance")]
    ops[0]["payload"]["structure"] = {"structure": [{"steps": [{"targets": [{"minValue": 65}]}]}]}
    with pytest.raises(P.PublishAthleteError, match="CONFLICT"):
        P.filter_and_normalize_operations(ops, baseline=baseline, wave_cutoff=None, expected_creates=0)


def test_note_content_conflict_ignores_structure_presence():
    # calendar_note_upsert has no "structure" field -- structure-presence
    # comparison must not apply to notes.
    baseline = {"workouts": [], "notes": [
        {"date": "2026-08-16", "title": "Weekly Briefing", "description": "d d"}]}
    ops = [_op("2026-08-16", "Weekly Briefing", kind="calendar_note_upsert")]
    kept, dropped, deferred = P.filter_and_normalize_operations(
        ops, baseline=baseline, wave_cutoff=None, expected_creates=0)
    assert kept == [] and dropped == 1


# ---------------------------------------------------------- executor pinning
def _ctx(tmp_path, **overrides):
    work_dir = tmp_path / "work"
    work_dir.mkdir(exist_ok=True)
    argv = [
        "--athlete-dir", str(tmp_path / "source"), "--tp-athlete-id", "1",
        "--order-id", "order-1", "--work-dir", str(work_dir),
        "--stage", "all", "--revision", "1",
    ]
    args = P._parse_args(argv)
    for k, v in overrides.items():
        setattr(args, k, v)
    return P.Ctx(args)


def test_canonical_executor_sha256_matches_committed_hash_file():
    committed = (ROOT / "tools" / "tp_phase5_executor.sha256").read_text().strip()
    assert P.canonical_executor_sha256() == committed
    assert len(committed) == 64  # sha256 hex digest


def test_resolve_executor_sha_refuses_on_mismatch(tmp_path):
    executor = tmp_path / "tp_phase5_execute_verbose.py"
    executor.write_text("# not the proven executor\n")
    with pytest.raises(P.PublishAthleteError, match="does not match the canonical"):
        P.resolve_executor_sha(executor)


def test_resolve_executor_sha_accepts_explicit_override(tmp_path):
    executor = tmp_path / "tp_phase5_execute_verbose.py"
    executor.write_text("# a deliberately updated fork\n")
    actual_sha = P.file_sha(executor)
    assert P.resolve_executor_sha(executor, allow_executor_hash=actual_sha) == actual_sha


def test_resolve_executor_sha_override_does_not_accept_arbitrary_other_hash(tmp_path):
    executor = tmp_path / "tp_phase5_execute_verbose.py"
    executor.write_text("# not the proven executor\n")
    with pytest.raises(P.PublishAthleteError, match="does not match the canonical"):
        P.resolve_executor_sha(executor, allow_executor_hash="0" * 64)


def test_stage_execute_missing_executor_still_raises_before_hash_check(tmp_path):
    ctx = _ctx(tmp_path)
    with pytest.raises(P.PublishAthleteError, match="missing"):
        P.stage_execute(ctx, {}, {})


# ------------------------------------------------------------- execute status
def test_main_treats_non_applied_execute_status_as_hard_failure(tmp_path, monkeypatch):
    order_id = "test_publish_athlete_execstatus_v1"
    tp_athlete_id = "9999996"
    source = _make_source_athlete_dir(tmp_path, order_id=order_id, tp_athlete_id=tp_athlete_id)
    work_dir = tmp_path / "work"
    baseline = _empty_baseline(tmp_path, tp_athlete_id=tp_athlete_id)

    offline_args = [
        "--athlete-dir", str(source), "--tp-athlete-id", tp_athlete_id,
        "--order-id", order_id, "--work-dir", str(work_dir),
        "--stage", "offline", "--revision", "1", "--baseline", str(baseline),
    ]
    with pytest.raises(P.PublishAthleteError) as excinfo:
        P.main(offline_args + ["--expected-creates", "999999"])
    actual_creates = int(re.search(r"got (\d+)", str(excinfo.value)).group(1))
    assert P.main(offline_args + ["--expected-creates", str(actual_creates)]) == 0

    # Stub out live transport entirely -- only the post-execute status gate
    # in main() is under test here. counts/missing would all look "fine"
    # (empty before/after, no creates asserted here) if this gate didn't
    # exist, which is exactly the silent-success failure mode being closed.
    monkeypatch.setattr(P, "stage_transport", lambda ctx: {})
    monkeypatch.setattr(P, "inventory", lambda ctx, binding, name: {"workouts": [], "notes": []})
    monkeypatch.setattr(P, "rows_digest", lambda inv: "same")
    monkeypatch.setattr(P, "stage_execute", lambda ctx, binding, state: {
        "status": "running", "operation_count": 3})

    all_args = [
        "--athlete-dir", str(source), "--tp-athlete-id", tp_athlete_id,
        "--order-id", order_id, "--work-dir", str(work_dir),
        "--stage", "all", "--revision", "1", "--baseline", str(baseline),
        "--expected-creates", str(actual_creates),
    ]
    with pytest.raises(P.PublishAthleteError, match="did not report a success status"):
        P.main(all_args)


def test_main_accepts_applied_execute_status(tmp_path, monkeypatch):
    order_id = "test_publish_athlete_execstatus_v2"
    tp_athlete_id = "9999995"
    source = _make_source_athlete_dir(tmp_path, order_id=order_id, tp_athlete_id=tp_athlete_id)
    work_dir = tmp_path / "work"
    baseline = _empty_baseline(tmp_path, tp_athlete_id=tp_athlete_id)

    offline_args = [
        "--athlete-dir", str(source), "--tp-athlete-id", tp_athlete_id,
        "--order-id", order_id, "--work-dir", str(work_dir),
        "--stage", "offline", "--revision", "1", "--baseline", str(baseline),
    ]
    with pytest.raises(P.PublishAthleteError) as excinfo:
        P.main(offline_args + ["--expected-creates", "999999"])
    actual_creates = int(re.search(r"got (\d+)", str(excinfo.value)).group(1))
    assert P.main(offline_args + ["--expected-creates", str(actual_creates)]) == 0

    # Build a fake "after" inventory that matches exactly what the sealed
    # release's own creates need, so the readback gate itself passes and
    # the execute-status gate is the only thing under test.
    contract = json.loads(
        (work_dir / "release-r1" / "artifacts" / "apply_contract.json").read_text())
    creates = [o for o in contract["operations"] if o["disposition"] == "create"]
    after_workouts = [
        {"id": f"w{i}", "date": o["payload"]["date"], "title": o["payload"]["title"],
         "description": o["payload"].get("description", "")}
        for i, o in enumerate(creates) if o["kind"] == "workout_upsert"
    ]
    after_notes = [
        {"id": f"n{i}", "date": o["payload"]["date"], "title": o["payload"]["title"],
         "description": o["payload"].get("description", "")}
        for i, o in enumerate(creates) if o["kind"] == "calendar_note_upsert"
    ]

    def _fake_inventory(ctx, binding, name):
        if name == "after":
            return {"workouts": after_workouts, "notes": after_notes}
        return {"workouts": [], "notes": []}

    monkeypatch.setattr(P, "stage_transport", lambda ctx: {})
    monkeypatch.setattr(P, "inventory", _fake_inventory)
    monkeypatch.setattr(P, "rows_digest", lambda inv: "same")
    monkeypatch.setattr(P, "stage_execute", lambda ctx, binding, state: {
        "status": "applied", "operation_count": len(creates)})

    all_args = [
        "--athlete-dir", str(source), "--tp-athlete-id", tp_athlete_id,
        "--order-id", order_id, "--work-dir", str(work_dir),
        "--stage", "all", "--revision", "1", "--baseline", str(baseline),
        "--expected-creates", str(actual_creates),
    ]
    assert P.main(all_args) == 0


# --------------------------------------------------------- readback summary
def _inventory(workouts=(), notes=()):
    return {"workouts": list(workouts), "notes": list(notes)}


def _contract(operations):
    return {"operations": operations}


def test_publication_summary_ok_when_everything_landed_and_unchanged():
    before = _inventory(
        workouts=[{"id": "w1", "date": "2026-08-16", "title": "Kept", "description": "x"}],
        notes=[{"id": "n1", "date": "2026-08-16", "title": "Kept Note", "description": "y"}],
    )
    after = _inventory(
        workouts=[
            {"id": "w1", "date": "2026-08-16", "title": "Kept", "description": "x"},
            {"id": "w2", "date": "2026-08-17", "title": "New Ride", "description": "d d"},
        ],
        notes=[{"id": "n1", "date": "2026-08-16", "title": "Kept Note", "description": "y"}],
    )
    contract = _contract([
        {"kind": "workout_upsert", "disposition": "create",
         "payload": {"date": "2026-08-17", "title": "New Ride", "description": "d  d"}},
    ])
    summary = P.compute_publication_summary(before, after, contract, execute_status="applied")
    assert summary["ok"] is True
    assert summary["created_missing"] == []
    assert summary["protected_workouts_changed"] == []
    assert summary["protected_notes_changed"] == []
    assert summary["content_mismatches"] == []


def test_publication_summary_flags_protected_note_changed():
    before = _inventory(notes=[{"id": "n1", "date": "2026-08-16", "title": "Weekly", "description": "original"}])
    after = _inventory(notes=[{"id": "n1", "date": "2026-08-16", "title": "Weekly", "description": "MUTATED"}])
    summary = P.compute_publication_summary(before, after, _contract([]), execute_status="applied")
    assert summary["ok"] is False
    assert summary["protected_notes_changed"] == ["n1"]


def test_publication_summary_flags_content_mismatch_on_landed_create():
    before = _inventory()
    after = _inventory(workouts=[
        {"id": "w1", "date": "2026-08-17", "title": "New Ride", "description": "WRONG BODY"}])
    contract = _contract([
        {"kind": "workout_upsert", "disposition": "create",
         "payload": {"date": "2026-08-17", "title": "New Ride", "description": "desired body"}},
    ])
    summary = P.compute_publication_summary(before, after, contract, execute_status="applied")
    assert summary["ok"] is False
    assert summary["content_mismatches"] == [
        {"kind": "workout_upsert", "date": "2026-08-17", "title": "New Ride"}]


def test_publication_summary_content_check_ignores_athlete_layer_normalization_diffs():
    # A description that differs only by internal-space collapse and
    # continuation-line indentation (TP's athlete-layer normalization)
    # must NOT be flagged as a content mismatch.
    before = _inventory()
    after = _inventory(workouts=[{
        "id": "w1", "date": "2026-08-17", "title": "New Ride",
        "description": "Warmup 10min.\nchanges to Zone 2 after.",
    }])
    contract = _contract([{
        "kind": "workout_upsert", "disposition": "create",
        "payload": {"date": "2026-08-17", "title": "New Ride",
                    "description": "Warmup 10min.\n  changes  to Zone 2 after.  "},
    }])
    summary = P.compute_publication_summary(before, after, contract, execute_status="applied")
    assert summary["content_mismatches"] == []
    assert summary["ok"] is True


def test_publication_summary_asserts_cadence_equality_not_just_a_count():
    before = _inventory()
    cadence_structure = {"structure": [{"steps": [
        {"targets": [{"roundOrStridePerMinute": {"minValue": 90}}]}]}]}
    after = _inventory(workouts=[
        {"id": "w1", "date": "2026-08-17", "title": "Cadence Ride", "description": "d d",
         "structure": cadence_structure},
    ])
    contract = _contract([{
        "kind": "workout_upsert", "disposition": "create",
        "payload": {"date": "2026-08-17", "title": "Cadence Ride", "description": "d  d",
                    "structure": cadence_structure},
    }])
    ok_summary = P.compute_publication_summary(
        before, after, contract, execute_status="applied", expected_cadence_count=1)
    assert ok_summary["ok"] is True
    assert ok_summary["release_cadence_landed"] == 1

    mismatch_summary = P.compute_publication_summary(
        before, after, contract, execute_status="applied", expected_cadence_count=2)
    assert mismatch_summary["ok"] is False
    assert mismatch_summary["release_cadence_expected"] == 2


def test_publication_summary_missing_create_flagged():
    before = _inventory()
    after = _inventory()  # nothing landed
    contract = _contract([{
        "kind": "workout_upsert", "disposition": "create",
        "payload": {"date": "2026-08-17", "title": "New Ride", "description": "d  d"},
    }])
    summary = P.compute_publication_summary(before, after, contract, execute_status="applied")
    assert summary["ok"] is False
    assert summary["created_missing"] == [("workout_upsert", "2026-08-17", "New Ride")]


# --------------------------------------------------------- baseline schema
def test_validate_baseline_schema_accepts_well_formed_inventory():
    P.validate_baseline_schema({
        "contract_version": "trainingpeaks_provider_inventory/v1",
        "athlete_id": "12345", "workouts": [], "notes": [], "events": [],
    })


@pytest.mark.parametrize("mutation", [
    lambda b: b.pop("contract_version"),
    lambda b: b.update(contract_version="wrong/v1"),
    lambda b: b.update(athlete_id=""),
    lambda b: b.update(workouts="not-a-list"),
    lambda b: b.update(notes={}),
    lambda b: b.update(events="not-a-list"),
])
def test_validate_baseline_schema_rejects_malformed_inventory(mutation):
    baseline = {
        "contract_version": "trainingpeaks_provider_inventory/v1",
        "athlete_id": "12345", "workouts": [], "notes": [], "events": [],
    }
    mutation(baseline)
    with pytest.raises(P.PublishAthleteError):
        P.validate_baseline_schema(baseline)


def test_validate_baseline_schema_rejects_non_dict():
    with pytest.raises(P.PublishAthleteError):
        P.validate_baseline_schema(["not", "a", "dict"])


# --------------------------------------------------------- fixture athlete
def _write_yaml_placeholders(directory: Path) -> None:
    for name in ("profile.yaml", "methodology.yaml", "fueling.yaml", "plan_dates.yaml"):
        (directory / name).write_text(f"# fixture {name}\n")


def _plan_ir_fixture() -> dict:
    """Mirrors athletes/scripts/test_apply_contract.py::_ir() -- the
    proven minimal plan_ir shape build_contract() accepts directly."""
    return {
        "athlete": {"id": "fixture-athlete"},
        "race_snapshot": {"name": None, "date": None},
        "weeks": [{"number": 1, "sessions": [{
            "date": "2026-08-16", "title": "Endurance Ride",
            "description": "Ride  easy.  Hold Zone 2.",
            "workout_type_value_id": 2, "duration_s": 3600,
            "tss_planned": 40.0, "structure": None,
            "type": "workout", "sport": "cycling", "segments": [],
        }]}],
        "notes": [], "attachments": [], "entitlements": [],
    }


def _make_source_athlete_dir(tmp_path: Path, *, order_id: str, tp_athlete_id: str) -> Path:
    source = tmp_path / "source-athlete"
    source.mkdir()
    (source / "plan_ir.json").write_text(json.dumps(_plan_ir_fixture()))
    (source / "canonical_training_model.json").write_text(json.dumps({
        "model_version": "canonical_training_model/v1",
        "calendar_protection": {"requested": False},
    }))
    _write_yaml_placeholders(source)
    state_path = source / "fulfillment_status.json"
    write_generation(
        state_path, "fixture-athlete", [],
        order_id=order_id, delivery_platform="trainingpeaks",
        required_confirmations=[], soft_confirmations=[], derived_values=[],
    )
    record_identity_result(
        state_path, 1,
        {"outcome": "bound", "tp_athlete_id": tp_athlete_id, "candidates": []},
        capability_jti="fixture-identity-r1",
    )
    return source


def _empty_baseline(tmp_path: Path, *, tp_athlete_id: str) -> Path:
    baseline = tmp_path / "baseline-r1.json"
    baseline.write_text(json.dumps({
        "contract_version": "trainingpeaks_provider_inventory/v1",
        "athlete_id": tp_athlete_id, "workouts": [], "notes": [], "events": [],
        "period": {"start": "2026-08-01", "end": "2026-10-01"},
        "retrieved_at": "2026-08-25T00:00:00Z",
    }))
    return baseline


def test_offline_stage_bootstraps_flips_calendar_protection_and_approves(tmp_path):
    order_id = "test_publish_athlete_dryrun_v1"
    tp_athlete_id = "9999999"
    source = _make_source_athlete_dir(tmp_path, order_id=order_id, tp_athlete_id=tp_athlete_id)
    work_dir = tmp_path / "work"
    baseline = _empty_baseline(tmp_path, tp_athlete_id=tp_athlete_id)

    def _run(expected_creates):
        return P.main([
            "--athlete-dir", str(source), "--tp-athlete-id", tp_athlete_id,
            "--order-id", order_id, "--work-dir", str(work_dir),
            "--stage", "offline", "--revision", "1",
            "--expected-creates", str(expected_creates), "--baseline", str(baseline),
        ])

    # First pass: deliberately wrong count proves the EXPECTED_CREATES
    # assertion fires end-to-end (mirrors the real trial-run workflow the
    # proven scripts were run with by hand).
    with pytest.raises(P.PublishAthleteError) as excinfo:
        _run(999999)
    match = re.search(r"got (\d+)", str(excinfo.value))
    assert match, f"assertion message did not carry the actual count: {excinfo.value}"
    actual_creates = int(match.group(1))
    assert actual_creates >= 1

    # Second pass: correct count seals + approves.
    assert _run(actual_creates) == 0

    state = load_state(work_dir / "athlete" / "fulfillment_status.json")
    assert state["status"] == "APPROVED"
    assert state["order_id"] == order_id
    assert state["model_seal"]

    work_canonical = json.loads((work_dir / "athlete" / "canonical_training_model.json").read_text())
    assert work_canonical["calendar_protection"]["requested"] is True

    source_canonical = json.loads((source / "canonical_training_model.json").read_text())
    assert source_canonical["calendar_protection"]["requested"] is False, (
        "the flip must land on the work-dir copy only, never --athlete-dir's own file")


def test_offline_stage_is_idempotent_on_rerun_after_seal(tmp_path):
    order_id = "test_publish_athlete_dryrun_v2"
    tp_athlete_id = "9999998"
    source = _make_source_athlete_dir(tmp_path, order_id=order_id, tp_athlete_id=tp_athlete_id)
    work_dir = tmp_path / "work"
    baseline = _empty_baseline(tmp_path, tp_athlete_id=tp_athlete_id)

    args = [
        "--athlete-dir", str(source), "--tp-athlete-id", tp_athlete_id,
        "--order-id", order_id, "--work-dir", str(work_dir),
        "--stage", "offline", "--revision", "1", "--baseline", str(baseline),
    ]
    with pytest.raises(P.PublishAthleteError) as excinfo:
        P.main(args + ["--expected-creates", "999999"])
    actual_creates = int(re.search(r"got (\d+)", str(excinfo.value)).group(1))
    assert P.main(args + ["--expected-creates", str(actual_creates)]) == 0
    sealed_state = load_state(work_dir / "athlete" / "fulfillment_status.json")
    # Rerunning offline after a seal reuses it rather than re-sealing.
    assert P.main(args + ["--expected-creates", str(actual_creates)]) == 0
    reloaded = load_state(work_dir / "athlete" / "fulfillment_status.json")
    assert reloaded["model_seal"] == sealed_state["model_seal"]


def test_offline_stage_requires_expected_creates_to_seal(tmp_path):
    order_id = "test_publish_athlete_dryrun_v3"
    tp_athlete_id = "9999997"
    source = _make_source_athlete_dir(tmp_path, order_id=order_id, tp_athlete_id=tp_athlete_id)
    work_dir = tmp_path / "work"
    baseline = _empty_baseline(tmp_path, tp_athlete_id=tp_athlete_id)
    with pytest.raises(P.PublishAthleteError, match="--expected-creates is required"):
        P.main([
            "--athlete-dir", str(source), "--tp-athlete-id", tp_athlete_id,
            "--order-id", order_id, "--work-dir", str(work_dir),
            "--stage", "offline", "--revision", "1", "--baseline", str(baseline),
        ])


def test_offline_stage_requires_source_athlete_dir_artifacts(tmp_path):
    source = tmp_path / "incomplete-athlete"
    source.mkdir()
    state_path = source / "fulfillment_status.json"
    write_generation(state_path, "fixture-athlete", [],
                      order_id="test_publish_athlete_incomplete", delivery_platform="trainingpeaks",
                      required_confirmations=[], soft_confirmations=[], derived_values=[])
    record_identity_result(state_path, 1, {"outcome": "bound", "tp_athlete_id": "1", "candidates": []},
                            capability_jti="fixture-identity-r1")
    work_dir = tmp_path / "work"
    with pytest.raises(P.PublishAthleteError, match="missing required artifact"):
        P.main([
            "--athlete-dir", str(source), "--tp-athlete-id", "1",
            "--order-id", "test_publish_athlete_incomplete", "--work-dir", str(work_dir),
            "--stage", "offline", "--revision", "1", "--expected-creates", "0",
        ])

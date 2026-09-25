"""Crash/retry and readback tests for sealed TP plan-library DRAFTs."""
import copy
import json

import pytest

from tools import build_sealed_tp_plan_package as sealed
from tools import publish_tp_draft as draft
from tools.test_build_sealed_tp_plan_package import _build
from webhook.fulfillment_state import transition


class FakePlans:
    def __init__(self):
        self.plans = {}
        self.workouts = []
        self.notes = []
        self.next_id = 100
        self.calls = []
        self.fail_after = None
        self.crash_after = None
        self.corrupt = None
        self.missing_readback = None
        self.on_write = None

    def _write(self, name):
        self.calls.append(name)
        if self.on_write:
            self.on_write(name)
        if self.crash_after == name:
            self.crash_after = None
            raise KeyboardInterrupt(name)
        if self.fail_after == name:
            self.fail_after = None
            raise TimeoutError(name)

    def list_plans(self):
        return [copy.deepcopy(x) for x in self.plans.values()]

    def create_plan(self, body):
        self.next_id += 1
        plan = {**body, "planId": self.next_id, "planPersonId": 777,
                "isDynamic": False}
        self.plans[self.next_id] = plan
        self._write("create_plan")
        return copy.deepcopy(plan)

    def get_plan(self, plan_id):
        return copy.deepcopy(self.plans[plan_id])

    def update_plan(self, plan_id, body):
        self.plans[plan_id] = copy.deepcopy(body)
        self._write("update_plan")

    def list_workouts(self, plan_id, start, end):
        if self.missing_readback == "workout":
            return None
        rows = copy.deepcopy(self.workouts)
        if self.corrupt == "workout" and rows:
            rows[0]["description"] = "dropped"
        return rows

    def list_notes(self, plan_id, start, end):
        if self.missing_readback == "note":
            return None
        rows = copy.deepcopy(self.notes)
        if self.corrupt == "note" and rows:
            rows[0]["description"] = "dropped"
        return rows

    def create_workout(self, plan_id, body):
        self.next_id += 1
        self.workouts.append({**copy.deepcopy(body), "workoutId": self.next_id})
        self._write("create_workout")

    def create_note(self, plan_id, body):
        self.next_id += 1
        self.notes.append({**copy.deepcopy(body), "id": self.next_id})
        self._write("create_note")

    def delete_workout(self, plan_id, remote_id):
        self.workouts = [row for row in self.workouts if row["workoutId"] != remote_id]
        self._write("delete_workout")

    def delete_note(self, plan_id, remote_id):
        self.notes = [row for row in self.notes if row["id"] != remote_id]
        self._write("delete_note")


def _setup(tmp_path):
    state, revision, artifacts, package = _build(tmp_path, clean=True)
    sealed.build("paid-order-1", state, revision, package)
    journal = tmp_path / "journal" / "draft.json"
    tp = FakePlans()
    args = ("paid-order-1", state, revision, package, journal, tp)
    return args, tp


def _publish(args, **kwargs):
    return draft.publish(*args, expected_folder="Athlete Dynamic Plans", **kwargs)


def _proof(plan_id, folder):
    return {"verified": True, "plan_id": plan_id, "folder": folder,
            "evidence": "injected readback fixture"}


def test_generated_ready_package_publishes_once_and_needs_folder_proof(tmp_path):
    args, tp = _setup(tmp_path)
    result = _publish(args)
    assert result["status"] == "folder_pending"
    assert len(tp.plans) == 1
    assert next(iter(tp.plans.values()))["title"].startswith(
        "DRAFT — Fixture Athlete — Fixture Race 6wk")
    assert len(tp.workouts) == 5
    assert len(tp.notes) == 2
    assert tp.get_plan(result["plan_id"])["isDynamic"] is True
    before = list(tp.calls)
    assert _publish(args, folder_verifier=_proof)["status"] == "verified"
    assert tp.calls == before
    assert json.loads(args[4].read_text())["binding"]["order_id"] == "paid-order-1"


def test_ambiguous_create_reconciles_without_second_container(tmp_path):
    args, tp = _setup(tmp_path)
    tp.fail_after = "create_plan"
    assert _publish(args, folder_verifier=_proof)["status"] == "verified"
    assert tp.calls.count("create_plan") == 1
    assert len(tp.plans) == 1


def test_partial_workout_timeout_resumes_without_duplicate(tmp_path):
    args, tp = _setup(tmp_path)
    tp.crash_after = "create_workout"
    with pytest.raises(KeyboardInterrupt):
        _publish(args)
    assert len(tp.workouts) == 1
    assert _publish(args, folder_verifier=_proof)["status"] == "verified"
    assert len(tp.workouts) == 5


def test_partial_note_timeout_resumes_without_duplicate(tmp_path):
    args, tp = _setup(tmp_path)
    tp.crash_after = "create_note"
    with pytest.raises(KeyboardInterrupt):
        _publish(args)
    assert len(tp.notes) == 1
    assert _publish(args, folder_verifier=_proof)["status"] == "verified"
    assert len(tp.notes) == 2


def test_in_place_rewrite_removes_old_cards_and_reuses_plan(tmp_path):
    args, tp = _setup(tmp_path)
    first = _publish(args)
    tp.workouts[0]["description"] = "stale"
    tp.notes[0]["description"] = "stale"
    assert _publish(args, folder_verifier=_proof)["status"] == "verified"
    assert len(tp.plans) == 1
    assert first["plan_id"] in tp.plans
    assert len(tp.workouts) == 5 and len(tp.notes) == 2
    assert "delete_workout" in tp.calls and "delete_note" in tp.calls


@pytest.mark.parametrize("target", ["workout", "note"])
def test_content_readback_mismatch_fails_closed(tmp_path, target):
    args, tp = _setup(tmp_path)
    _publish(args)
    tp.corrupt = target
    with pytest.raises(draft.DraftPublishError, match="readback mismatch"):
        _publish(args, folder_verifier=_proof)
    assert json.loads(args[4].read_text())["status"] != "verified"


def test_folder_capability_mismatch_never_marks_verified(tmp_path):
    args, tp = _setup(tmp_path)
    with pytest.raises(draft.DraftPublishError, match="target folder"):
        _publish(args, folder_verifier=lambda plan_id, folder: {
            "verified": True, "plan_id": plan_id, "folder": "Custom training plan"})
    assert json.loads(args[4].read_text())["status"] == "folder_pending"


def test_stale_revision_and_edited_package_stop_before_remote_write(tmp_path):
    args, tp = _setup(tmp_path)
    payload = args[3] / "notes_payload.json"
    changed = json.loads(payload.read_text())
    changed[0]["description"] = "tampered"
    payload.write_text(json.dumps(changed))
    with pytest.raises(draft.DraftPublishError, match="differs from current sealed source"):
        _publish(args)
    assert not tp.calls
    sealed.build("paid-order-1", args[1], args[2], args[3])
    transition(args[1], "CANCELLED", "Coach", metadata={"reason": "refunded"})
    with pytest.raises(draft.DraftPublishError, match="ready for draft review"):
        _publish(args)
    assert not tp.calls


def test_duplicate_plan_title_fails_before_entry_writes(tmp_path):
    args, tp = _setup(tmp_path)
    state = json.loads(args[1].read_text())
    manifest = json.loads((args[2] / "artifacts" / "tp_manifest.json").read_text())
    title = draft._plan_title("paid-order-1", state["generation_revision"],
                              state["model_seal"], manifest)
    tp.plans[1] = {"planId": 1, "planPersonId": 777, "title": title}
    tp.plans[2] = {"planId": 2, "planPersonId": 777, "title": title}
    with pytest.raises(draft.DraftPublishError, match="duplicate draft containers"):
        _publish(args)
    assert not tp.calls


def test_plan_title_requires_coherent_sealed_athlete_race_and_week_count():
    source = {"athlete": "Fixture Athlete", "race": {"name": "Fixture Race"},
              "plan_title": "Fixture Athlete · Fixture Race · 6wk [CUSTOM]"}
    title = draft._plan_title("paid-order-1", 1, "a" * 64, source)
    assert title.startswith("DRAFT — Fixture Athlete — Fixture Race 6wk")
    assert "paid-order-1" not in title
    source["plan_title"] = "Another Athlete · Fixture Race · 6wk [CUSTOM]"
    with pytest.raises(draft.DraftPublishError, match="coherent"):
        draft._plan_title("paid-order-1", 1, "a" * 64, source)


@pytest.mark.parametrize("target", ["workout", "note"])
def test_missing_readback_stops_before_card_mutations(tmp_path, target):
    args, tp = _setup(tmp_path)
    tp.missing_readback = target
    with pytest.raises(draft.DraftPublishError, match="readback"):
        _publish(args)
    assert not tp.notes
    if target == "workout":
        assert not tp.workouts


def test_plan_person_identity_mismatch_stops_before_cards(tmp_path):
    args, tp = _setup(tmp_path)
    first = _publish(args)
    tp.plans[first["plan_id"]]["planPersonId"] = None
    with pytest.raises(draft.DraftPublishError, match="planPersonId"):
        _publish(args)


def test_same_journal_cannot_be_rebound_to_another_folder(tmp_path):
    args, tp = _setup(tmp_path)
    _publish(args)
    with pytest.raises(draft.DraftPublishError, match="journal is bound"):
        draft.publish(*args, expected_folder="Custom training plan")


def test_dynamic_timeout_reconciles_by_plan_readback(tmp_path):
    args, tp = _setup(tmp_path)
    tp.fail_after = "update_plan"
    assert _publish(args, folder_verifier=_proof)["status"] == "verified"
    assert tp.calls.count("update_plan") == 1


def test_state_changes_after_plan_create_stop_before_cards(tmp_path):
    args, tp = _setup(tmp_path)

    def cancel_after_create(name):
        if name == "create_plan":
            transition(args[1], "CANCELLED", "Coach", metadata={"reason": "refunded"})

    tp.on_write = cancel_after_create
    with pytest.raises(draft.DraftPublishError, match="ceased to be ready"):
        _publish(args)
    assert len(tp.plans) == 1  # recoverable DRAFT, never an athlete delivery
    assert not tp.workouts and not tp.notes

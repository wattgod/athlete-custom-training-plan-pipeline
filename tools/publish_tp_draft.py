"""Resumable, order-bound TP *plan-library* DRAFT publisher.

The caller supplies a plans/v1 transport. This module contains no browser
credentials, athlete-calendar operation, or live transport. An operator must
inject a separately proven folder verifier before claiming verified success.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from tools import build_sealed_tp_plan_package as sealed
from webhook.fulfillment_state import load, verify_release_manifest


class DraftPublishError(RuntimeError):
    """A draft cannot safely advance; the journal remains available to resume."""


WINDOW_START = "2020-01-01"
WINDOW_END = "2035-12-31"
FILES = ("coverage_receipt.json", "plan_payload.json", "notes_payload.json")
WORKOUT_FIELDS = ("title", "workoutTypeValueId", "workoutDay", "description",
                  "totalTimePlanned", "tssPlanned", "structure", "coachComments")
NOTE_FIELDS = ("title", "noteDate", "description")


def _digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=path.name + ".", delete=False) as handle:
        tmp = Path(handle.name)
        json.dump(data, handle, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


@contextmanager
def _locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _rows(value, label):
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise DraftPublishError(f"missing or malformed {label} readback")
    return value


def _key(row, fields):
    if any(field not in row for field in fields if field != "coachComments"):
        raise DraftPublishError("readback lacks required content fields")
    content = {field: row.get(field, "" if field == "coachComments" else None)
               for field in fields}
    return _digest(content)


def _check_window(workouts, notes):
    days = [row.get("workoutDay", "")[:10] for row in workouts]
    days += [row.get("noteDate", "")[:10] for row in notes]
    if not days or any(day < WINDOW_START or day > WINDOW_END for day in days):
        raise DraftPublishError("payload dates exceed proven plan-library readback window")


def _package(order_id, state_path, revision_dir, package_dir):
    state_path, revision_dir, package_dir = map(Path, (state_path, revision_dir, package_dir))
    state = load(state_path)
    if (state_path.name != "fulfillment_status.json" or state_path.parent.name != order_id
            or state.get("order_id") != order_id
            or revision_dir.resolve() != (state_path.parent / "revisions" /
                                           f"r{state['generation_revision']}").resolve()):
        raise DraftPublishError("order or revision identity mismatch")
    if state.get("status") not in {"GENERATED", "APPROVED"}:
        raise DraftPublishError("order is not ready for draft review")
    verify_release_manifest(state, revision_dir)
    values = {name: _read(package_dir / name) for name in FILES}
    receipt = values["coverage_receipt.json"]
    if not receipt.get("ready_for_review") or state.get("blocking_issues"):
        raise DraftPublishError("package is not ready for review")
    for field in ("order_id", "generation_revision", "athlete_id", "model_seal",
                  "release_manifest_digest"):
        if receipt.get(field) != state.get(field):
            raise DraftPublishError(f"package {field} does not match current order")
    with tempfile.TemporaryDirectory(prefix="tp-draft-rebuild-") as temp:
        rebuilt = sealed.build(order_id, state_path, revision_dir, Path(temp))
        if not rebuilt["ready_for_review"] or any(
            values[name] != _read(Path(temp) / name) for name in FILES
        ):
            raise DraftPublishError("package differs from current sealed source")
    workouts, notes = values["plan_payload.json"], values["notes_payload.json"]
    if not isinstance(workouts, list) or not workouts or not isinstance(notes, list):
        raise DraftPublishError("malformed review payload")
    _check_window(workouts, notes)
    return state, values, _read(revision_dir / "artifacts" / "tp_manifest.json")


def _plan_title(order_id, revision, seal, tp_manifest):
    """Human-readable coach title with a stable order-specific lookup suffix."""
    athlete = tp_manifest.get("athlete")
    race = (tp_manifest.get("race") or {}).get("name") or "Coached Block"
    source = tp_manifest.get("plan_title")
    match = re.search(r" · (\d+)wk \[CUSTOM\]$", source or "")
    if (not isinstance(athlete, str) or not athlete.strip()
            or not isinstance(race, str) or not race.strip()
            or not match or source != f"{athlete} · {race} · {match.group(1)}wk [CUSTOM]"):
        raise DraftPublishError("sealed manifest lacks a coherent athlete/race/week plan title")
    marker = hashlib.sha256(order_id.encode()).hexdigest()[:20]
    return f"DRAFT — {athlete} — {race} {match.group(1)}wk · {marker} r{revision} {seal[:12]}"


def _plan_id(plan):
    if not isinstance(plan, dict):
        raise DraftPublishError("missing plan readback")
    return plan.get("planId") or plan.get("id")


def _journal_action(path, journal, kind, key, state="intent", remote_id=None):
    journal["action"] = {"kind": kind, "key": key, "state": state,
                         "remote_id": remote_id}
    _atomic(path, journal)


def _prewrite(state_path, revision_dir, package_dir, binding):
    state = load(state_path)
    if state.get("status") not in {"GENERATED", "APPROVED"} or state.get("blocking_issues"):
        raise DraftPublishError("order ceased to be ready for draft review")
    verify_release_manifest(state, revision_dir)
    if {name: _digest(_read(package_dir / name)) for name in FILES} != binding["package_digests"]:
        raise DraftPublishError("package changed after journal intent")
    if (state["model_seal"] != binding["model_seal"] or
            state["release_manifest_digest"] != binding["release_manifest_digest"] or
            state["generation_revision"] != binding["generation_revision"]):
        raise DraftPublishError("sealed revision drifted")


def _reconcile(kind, desired, existing, fields, id_fields, delete, create,
               read, journal_path, journal, prewrite):
    desired_counts = Counter(_key(row, fields) for row in desired)
    existing_counts = Counter()
    for row in existing:
        key = _key(row, fields)
        existing_counts[key] += 1
        if existing_counts[key] <= desired_counts[key]:
            continue
        remote_id = next((row.get(field) for field in id_fields if row.get(field) is not None), None)
        if remote_id is None:
            raise DraftPublishError(f"{kind} readback lacks remote ID")
        _journal_action(journal_path, journal, f"delete_{kind}", key, remote_id=remote_id)
        prewrite()
        try:
            delete(remote_id)
        except Exception as exc:
            if any((r.get(field) == remote_id for r in read() for field in id_fields)):
                raise DraftPublishError(f"ambiguous {kind} delete") from exc
        _journal_action(journal_path, journal, f"delete_{kind}", key, "reconciled", remote_id)
    existing = read()
    counts = Counter(_key(row, fields) for row in existing)
    for row in desired:
        key = _key(row, fields)
        if counts[key] > 0:
            counts[key] -= 1
            continue
        _journal_action(journal_path, journal, f"create_{kind}", key)
        prewrite()
        try:
            create(row)
        except Exception as exc:
            # A timeout or expired browser session may have landed the POST.
            observed = Counter(_key(item, fields) for item in read())
            if observed[key] != desired_counts[key]:
                raise DraftPublishError(f"ambiguous {kind} create") from exc
        observed = Counter(_key(item, fields) for item in read())
        if observed[key] > desired_counts[key]:
            raise DraftPublishError(f"duplicate {kind} after create")
        if observed[key] < 1:
            raise DraftPublishError(f"missing {kind} after create")
        _journal_action(journal_path, journal, f"create_{kind}", key, "reconciled")
    final = read()
    if Counter(_key(row, fields) for row in final) != desired_counts:
        raise DraftPublishError(f"{kind} full readback mismatch")
    return final


def publish(order_id, state_path, revision_dir, package_dir, journal_path,
            transport, *, expected_folder, folder_verifier=None):
    """Stage a DRAFT and return verified only after exact folder proof.

    Transport methods map to the proven plans/v1 create/get/list/DELETE/POST/PUT
    calls. ``folder_verifier(plan_id, expected_folder)`` is an independently
    injected capability and must return a matching readback receipt.
    """
    state_path, revision_dir, package_dir, journal_path = map(
        Path, (state_path, revision_dir, package_dir, journal_path))
    if not expected_folder:
        raise DraftPublishError("exact target folder is required")
    with _locked(journal_path.with_suffix(journal_path.suffix + ".lock")):
        state, values, tp_manifest = _package(order_id, state_path, revision_dir, package_dir)
        binding = {field: state[field] for field in
                   ("order_id", "generation_revision", "athlete_id", "model_seal",
                    "release_manifest_digest")}
        binding["package_digests"] = {name: _digest(values[name]) for name in FILES}
        binding["expected_folder"] = expected_folder
        title = _plan_title(order_id, state["generation_revision"],
                            state["model_seal"], tp_manifest)
        binding["title"] = title
        if journal_path.exists():
            journal = _read(journal_path)
            if journal.get("binding") != binding:
                raise DraftPublishError("journal is bound to a different order, seal, package, or folder")
        else:
            journal = {"binding": binding, "plan_id": None, "status": "intent"}
            _atomic(journal_path, journal)

        def prewrite():
            _prewrite(state_path, revision_dir, package_dir, binding)

        plan_id = journal["plan_id"]
        if plan_id is None:
            matches = [row for row in _rows(transport.list_plans(), "plan list")
                       if row.get("title") == title]
            if len(matches) > 1:
                raise DraftPublishError("duplicate draft containers match order title")
            if not matches:
                _journal_action(journal_path, journal, "create_plan", title)
                prewrite()
                try:
                    transport.create_plan({"title": title, "planType": 0})
                except Exception:
                    # Always reconcile by listing, including session expiry and timeouts.
                    pass
                matches = [row for row in _rows(transport.list_plans(), "plan list")
                           if row.get("title") == title]
                if len(matches) != 1:
                    raise DraftPublishError("plan create unresolved or duplicated; no blind retry")
            plan_id = _plan_id(matches[0])
            if not plan_id:
                raise DraftPublishError("plan list lacks plan ID")
            journal["plan_id"] = plan_id
            _atomic(journal_path, journal)
        plan = transport.get_plan(plan_id)
        if (_plan_id(plan) != plan_id or plan.get("title") != title
                or not plan.get("planPersonId")):
            raise DraftPublishError("plan identity or planPersonId readback mismatch")
        person = plan["planPersonId"]
        workouts = values["plan_payload.json"]
        notes = values["notes_payload.json"]

        def read_workouts():
            return _rows(transport.list_workouts(plan_id, WINDOW_START, WINDOW_END), "workouts")

        def read_notes():
            return _rows(transport.list_notes(plan_id, WINDOW_START, WINDOW_END), "notes")

        _reconcile("workout", workouts, read_workouts(), WORKOUT_FIELDS,
                   ("workoutId", "id"), lambda item: transport.delete_workout(plan_id, item),
                   lambda row: transport.create_workout(plan_id, {**row, "planId": plan_id,
                                                                 "athleteId": person}),
                   read_workouts, journal_path, journal, prewrite)
        _reconcile("note", notes, read_notes(), NOTE_FIELDS,
                   ("id", "calendarNoteId", "noteId"),
                   lambda item: transport.delete_note(plan_id, item),
                   lambda row: transport.create_note(plan_id, {**row, "planId": plan_id,
                        "attachments": [], "standardFormatDate":
                        date.fromisoformat(row["noteDate"]).strftime("%A")}),
                   read_notes, journal_path, journal, prewrite)
        if not plan.get("isDynamic"):
            _journal_action(journal_path, journal, "make_dynamic", str(plan_id))
            prewrite()
            try:
                transport.update_plan(plan_id, {**plan, "isDynamic": True})
            except Exception:
                pass
        plan = transport.get_plan(plan_id)
        if (_plan_id(plan) != plan_id or plan.get("title") != title
                or plan.get("planPersonId") != person or plan.get("isDynamic") is not True):
            raise DraftPublishError("plan dynamic or identity readback mismatch")
        if (Counter(_key(row, WORKOUT_FIELDS) for row in read_workouts()) !=
                Counter(_key(row, WORKOUT_FIELDS) for row in workouts)
                or Counter(_key(row, NOTE_FIELDS) for row in read_notes()) !=
                Counter(_key(row, NOTE_FIELDS) for row in notes)):
            raise DraftPublishError("final card-set readback mismatch")
        journal["status"] = "folder_pending"
        _atomic(journal_path, journal)
        if folder_verifier is None:
            return {"status": "folder_pending", "plan_id": plan_id,
                    "workouts": len(workouts), "notes": len(notes)}
        proof = folder_verifier(plan_id, expected_folder)
        if (not isinstance(proof, dict) or proof.get("verified") is not True
                or proof.get("plan_id") != plan_id
                or proof.get("folder") != expected_folder
                or not proof.get("evidence")):
            raise DraftPublishError("exact target folder readback is missing or mismatched")
        journal["folder_proof"] = proof
        journal["status"] = "verified"
        _atomic(journal_path, journal)
        return {"status": "verified", "plan_id": plan_id,
                "workouts": len(workouts), "notes": len(notes), "folder_proof": proof}

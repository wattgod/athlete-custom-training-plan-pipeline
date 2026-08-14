"""Appendix 3 registry execution for the frozen E1 candidate."""

from __future__ import annotations

import copy
import datetime as dt
import math
import re
import unicodedata
from collections import defaultdict
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

import yaml

from block_compliance import INTENSITY_TYPES, VO2MAX_TYPES
from earned_selection import CONFIG_DIR, VERSION_VECTOR, canonical_digest


PRE_EXISTING = {"R01", "R02", "R03", "R04", "R05", "R06", "R14", "R19", "R20"}
HARD_INTENSITIES = {"hard", "threshold", "vo2", "anaerobic", "race"}


class RuleExecutionError(ValueError):
    pass


@lru_cache(maxsize=1)
def rule_registry() -> Dict[str, Any]:
    try:
        value = yaml.safe_load((CONFIG_DIR / "rule_registry.yaml").read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise RuleExecutionError("rule registry unavailable") from exc
    rows = value.get("rules") if isinstance(value, dict) else None
    if value.get("schema_version") != "rule_registry/v1" or not isinstance(rows, list):
        raise RuleExecutionError("invalid rule registry")
    if [row.get("rule_id") for row in rows] != [f"R{i:02d}" for i in range(1, 27)]:
        raise RuleExecutionError("rule registry must contain R01-R26 exactly once")
    return value


def build_legacy_projection(plan: Mapping[str, Any], *, target_hours: float,
                            off_days: Iterable[str], max_intensity: int) -> Dict[str, Any]:
    weeks = []
    for source_week in plan.get("weeks", []):
        days = []
        for source_day in source_week.get("days", []):
            workout = source_day.get("workout")
            days.append({
                "day": source_day.get("day"), "name": source_day.get("name"),
                "role": source_day.get("role"), "duration": source_day.get("duration"),
                "workout": ({"duration": workout.get("duration")} if isinstance(workout, dict)
                            else None),
                "sessions": [
                    {"intensity": session.get("intensity")}
                    for session in (source_day.get("sessions") or [])
                    if isinstance(session, dict)
                ],
            })
        weeks.append({
            "plan_week": source_week.get("plan_week"),
            "phase": source_week.get("phase"),
            "week_type": source_week.get("week_type"),
            "total_tss": source_week.get("total_tss"),
            "total_duration": source_week.get("total_duration"),
            "days": days,
        })
    present = "all_violations" in plan
    projection = {
        "schema_version": "legacy_compliance_projection/v1",
        "target_hours": target_hours, "off_days": list(off_days),
        "max_intensity": max_intensity, "weeks": weeks,
        "all_violations_present": present,
        "all_violations": copy.deepcopy(plan.get("all_violations")) if present else None,
    }
    projection["projection_sha256"] = canonical_digest(projection)
    return projection


def validate_projection(projection: Mapping[str, Any]) -> None:
    digest = projection.get("projection_sha256")
    unhashed = {key: copy.deepcopy(value) for key, value in projection.items()
                if key != "projection_sha256"}
    if projection.get("schema_version") != "legacy_compliance_projection/v1":
        raise RuleExecutionError("unknown legacy projection version")
    if digest != canonical_digest(unhashed):
        raise RuleExecutionError("legacy projection digest mismatch")


def _day_is_intensity(day: Mapping[str, Any]) -> bool:
    if any(str(session.get("intensity") or "").lower() in HARD_INTENSITIES
           for session in (day.get("sessions") or [])):
        return True
    if day.get("role") is not None:
        return day.get("role") == "intensity"
    return day.get("name") in INTENSITY_TYPES


def _race_overlay(week: Mapping[str, Any]) -> bool:
    return any(day.get("role") == "race" for day in week.get("days", []))


def legacy_verdicts(projection: Mapping[str, Any]) -> Dict[str, bool]:
    """The nine A3.0 production-equivalent boolean verdict functions."""
    validate_projection(projection)
    weeks = projection["weeks"]
    result: Dict[str, bool] = {}
    result["R01"] = not any(
        previous and _day_is_intensity(day)
        for week in weeks
        for previous, day in zip(
            [False] + [_day_is_intensity(item) for item in week.get("days", [])[:-1]],
            week.get("days", []),
        )
    )
    applicable = [week for week in weeks
                  if week.get("phase") not in {"racing", "taper"}
                  and week.get("week_type") not in {"race", "recovery"}
                  and not _race_overlay(week)]
    vo2_weeks = []
    for week in weeks:
        if (week.get("week_type") == "recovery"
                or week.get("phase") in {"racing", "taper"}
                or _race_overlay(week)):
            continue
        if any(day.get("name") in VO2MAX_TYPES for day in week.get("days", [])):
            vo2_weeks.append(week.get("plan_week", 0))
    result["R02"] = (not applicable or
                     (not vo2_weeks and len(applicable) <= 3) or
                     (bool(vo2_weeks) and all(
                         later - prior <= 3 for prior, later in zip(vo2_weeks, vo2_weeks[1:]))))
    load = [week.get("total_tss", 0) for week in weeks
            if week.get("week_type") == "load"
            and week.get("phase") not in {"racing", "taper"}
            and not _race_overlay(week)]
    recovery = [week.get("total_tss", 0) for week in weeks
                 if week.get("week_type") == "recovery"
                 and week.get("phase") not in {"racing", "taper"}
                 and not _race_overlay(week)]
    if not load or not recovery or sum(load) / len(load) == 0:
        result["R03"] = True
    else:
        mean = sum(load) / len(load)
        ceiling = .85 if mean < 300 else .75 if mean < 400 else .70 if mean < 500 else .65
        result["R03"] = all(.30 <= value / mean <= ceiling for value in recovery)
    result["R04"] = not any(
        _day_is_intensity(day) and day.get("name") != "Openers"
        for week in weeks if week.get("week_type") == "recovery"
        for day in week.get("days", []))
    max_intensity = projection["max_intensity"]
    result["R05"] = all(
        min(2, max_intensity) <= sum(_day_is_intensity(day)
                                    for day in week.get("days", [])) <= max_intensity
        for week in weeks if week.get("week_type") == "load"
        and week.get("phase") not in {"racing", "taper"}
        and not _race_overlay(week))
    min_long = 60 if projection["target_hours"] and projection["target_hours"] < 7 else 90
    def long_ok(week: Mapping[str, Any]) -> bool:
        long_days = [day for day in week.get("days", []) if day.get("role") == "long_ride"]
        return bool(long_days) and all(not (0 < ((day.get("workout") or {}).get(
            "duration", day.get("duration", 0)) or 0) < min_long) for day in long_days)
    result["R06"] = all(long_ok(week) for week in weeks
                        if week.get("week_type") == "load" and not _race_overlay(week))
    result["R14"] = not bool(projection.get("all_violations"))
    target_hours = projection["target_hours"]
    tolerance = .15 if target_hours < 6 else .10
    maximum, floor = target_hours * (1 + tolerance) * 60, target_hours * .65 * 60
    result["R19"] = all(
        (week.get("total_duration", 0) or 0) <= maximum
        and not (week.get("week_type") == "load"
                 and (week.get("total_duration", 0) or 0) < floor
                 and not (week.get("phase") == "base"
                          and (week.get("plan_week") or 1) <= 4))
        for week in weeks if week.get("week_type") != "recovery"
        and not _race_overlay(week))
    result["R20"] = not any(
        day.get("day") in projection["off_days"] and day.get("role") not in {"off", "race"}
        for week in weeks for day in week.get("days", []))
    return result


class _MondayNoteParser(HTMLParser):
    """Extract the closed per-week Monday note envelope."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.notes: list[dict[str, Any]] = []
        self._active: Optional[dict[str, Any]] = None
        self._depth = 0

    def handle_starttag(self, _tag: str,
                        attrs: list[tuple[str, Optional[str]]]) -> None:
        values = dict(attrs)
        if self._active is not None:
            self._depth += 1
            return
        if (values.get("data-plan-week") is None
                or values.get("data-weekday", "").casefold() != "monday"
                or values.get("data-block-note-template") is None):
            return
        try:
            week = int(values["data-plan-week"] or "")
        except ValueError:
            return
        self._active = {"week": week,
                        "template_id": values["data-block-note-template"],
                        "text_parts": []}
        self._depth = 1

    def handle_endtag(self, _tag: str) -> None:
        if self._active is None:
            return
        self._depth -= 1
        if self._depth == 0:
            active = self._active
            active["text"] = "".join(active.pop("text_parts"))
            self.notes.append(active)
            self._active = None

    def handle_data(self, data: str) -> None:
        if self._active is not None:
            self._active["text_parts"].append(data)


def _normalized_note(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _paid_monday_notes(guide_html: str) -> Optional[dict[int, list[dict[str, Any]]]]:
    try:
        parser = _MondayNoteParser()
        parser.feed(guide_html)
        parser.close()
    except Exception:
        return None
    by_week: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for note in parser.notes:
        by_week[note["week"]].append(note)
    return by_week


def _new_rule_result(rule_id: str, candidate: Mapping[str, Any],
                     guide_html: Optional[str],
                     manifest: Optional[Mapping[str, Any]] = None
                     ) -> tuple[str, list[str], Dict[str, Any], str]:
    sessions, weeks = candidate.get("sessions", []), candidate.get("weeks", [])
    cycling = [session for session in sessions if session.get("sport") == "cycling"]
    week_by_number = {week.get("week"): week for week in weeks}
    cycling_by_week = defaultdict(list)
    for session in cycling:
        cycling_by_week[session.get("week")].append(session)
    if rule_id in {"R18", "R22"}:
        return "NOT_APPLICABLE", [], {}, "Deferred input is not available in E1."
    if rule_id == "R07":
        if guide_html is None:
            return "UNAVAILABLE", [], {}, "Guide evidence unavailable."
        notes = _paid_monday_notes(guide_html)
        if notes is None:
            return "UNAVAILABLE", [], {}, "Guide block-note markup is malformed."
        bad = []
        for week in weeks:
            if not week.get("is_paid"):
                continue
            emitted = notes.get(int(week["week"]), [])
            if (week.get("block_note_template_id") is None or len(emitted) != 1
                    or emitted[0]["template_id"] != week["block_note_template_id"]):
                bad.append(str(week["week"]))
        return ("FAIL" if bad else "PASS", bad,
                {"invalid_week_count": len(bad),
                 "observed_monday_note_count": sum(len(value) for value in notes.values())},
                "Per-paid-week Monday block-note structure audit.")
    if rule_id == "R08":
        if not cycling:
            return "NOT_APPLICABLE", [], {}, "No cycling sessions."
        bad = []
        for session in cycling:
            fuel_class = session.get("fueling_class")
            if fuel_class not in {"HIGH", "LONG_RIDE", "RACE", "NONE"}:
                bad.append(session["id"])
                continue
            purpose_class = (session.get("purpose") or {}).get("class")
            legal_none = (session.get("origin") in {
                "REST_SENTINEL_ZWO", "TRAVEL_SHAKEOUT", "ATHLETE_FIXED"}
                or (session.get("origin") == "PRE_PLAN_GENERATOR"
                    and session["provenance"]["template_id"] in {
                        "pre_plan_rest", "pre_plan_strength_prep"})
                or session.get("session_type") in {
                    "recovery", "easy", "shakeout", "rest", "off", "openers"}
                or purpose_class in {"recovery", "openers"}
                or (purpose_class == "endurance" and
                    (session.get("duration_s") or 0) < 5400))
            if fuel_class == "NONE" and not legal_none:
                bad.append(session["id"])
        return ("FAIL" if bad else "PASS", bad, {"invalid_count": len(bad)}, "Fueling class audit.")
    if rule_id == "R09":
        mapping = {"quality": "HIGH", "long_ride": "LONG_RIDE", "race_sim": "RACE", "empty": "NONE"}
        bad = [s["id"] for s in cycling if mapping.get(s.get("fueling_source_tier")) != s.get("fueling_class")]
        return ("FAIL" if bad else "PASS", bad, {"mismatch_count": len(bad)}, "Fuel tier projection audit.")
    if rule_id == "R10":
        scoped = [s for s in cycling if s.get("fueling_class") in {"RACE", "LONG_RIDE"}]
        if not scoped:
            return "NOT_APPLICABLE", [], {}, "No scoped fuel classes."
        bad = []
        for session in scoped:
            purpose_class = (session.get("purpose") or {}).get("class")
            valid = (session["fueling_class"] == "RACE" and
                     (purpose_class == "race_sim" or session.get("role") == "race")) or (
                     session["fueling_class"] == "LONG_RIDE" and
                     (session.get("role") == "long_ride" or
                      (purpose_class == "endurance" and (session.get("duration_s") or 0) >= 5400)))
            if not valid:
                bad.append(session["id"])
        return ("FAIL" if bad else "PASS", bad, {"invalid_count": len(bad)}, "Fuel scope audit.")
    if rule_id == "R11":
        malformed = [str(w.get("week")) for w in weeks if w.get("is_paid") and
                     (w.get("weekly_structure_state") in {"MISSING", "MALFORMED"}
                      or w.get("strength_artifact_state") in {"MALFORMED", "CONTRADICTORY"})]
        if malformed:
            return "UNAVAILABLE", malformed, {}, "Strength state unavailable."
        scoped = [w for w in weeks if w.get("is_paid") and
                  w.get("weekly_structure_state") == "PRESCRIBES_STRENGTH"]
        if not scoped:
            return "NOT_APPLICABLE", [], {}, "Strength is not prescribed."
        bad = [str(w.get("week")) for w in weeks if w.get("is_paid") and
               w.get("weekly_structure_state") == "PRESCRIBES_STRENGTH" and
               w.get("strength_artifact_state") != "VALID"]
        return ("FAIL" if bad else "PASS", bad, {"invalid_week_count": len(bad)}, "Strength artifact audit.")
    if rule_id == "R12":
        scoped = [w for w in weeks if w.get("is_paid") and w.get("strength_prescribed")]
        if not scoped:
            return "NOT_APPLICABLE", [], {}, "Strength is declined or not prescribed."
        expected = {"transition": "deload", "build": "maintenance",
                    "maintenance": "maintenance", "race_prep": "maintenance_reduced",
                    "racing": "key_lifts"}
        bad, unavailable = [], []
        for week in scoped:
            required = ("deload" if week.get("week_type") == "recovery" else
                        "AA" if week.get("cycling_phase") == "base" and
                        week.get("meso_block_index") == 0 else
                        "max_strength" if week.get("cycling_phase") == "base" else
                        expected.get(week.get("cycling_phase")))
            if required is None or week.get("strength_phase") is None:
                unavailable.append(str(week.get("week")))
            elif week.get("strength_phase") != required:
                bad.append(str(week.get("week")))
        if unavailable:
            return "UNAVAILABLE", unavailable, {}, "Strength phase unavailable."
        return ("FAIL" if bad else "PASS", bad, {"mismatch_count": len(bad)}, "Strength phase audit.")
    if rule_id == "R13":
        heavy = [s for s in sessions if s.get("sport") == "strength" and
                 (s.get("strength") or {}).get("intensity") in {"max", "heavy"}]
        if not heavy:
            return "NOT_APPLICABLE", [], {}, "No max/heavy strength session."
        bad = []
        for strength in heavy:
            bad.extend(ride["id"] for ride in cycling
                       if ride.get("date") == strength.get("date")
                       and ride.get("role") == "intensity"
                       and (ride.get("purpose") or {}).get("class") in {
                           "threshold", "vo2max", "race_sim"})
        return ("FAIL" if bad else "PASS", sorted(set(bad)),
                {"conflict_count": len(set(bad))}, "Strength/key-session conflict audit.")
    if rule_id == "R15":
        grouped = defaultdict(list)
        for session in sessions:
            series = session.get("series") or {}
            if (series and session.get("archetype") is not None and
                    week_by_number.get(session.get("week"), {}).get("week_type") == "load"):
                grouped[series.get("series_id")].append(session)
        bad, unavailable, pairs = [], [], 0
        for values in grouped.values():
            values.sort(key=lambda s: (s["week"], s["date"], s["daily_ordinal"]))
            pairs += max(0, len(values) - 1)
            if any(value.get("progression_level") is None for value in values):
                unavailable.extend(value["id"] for value in values)
                continue
            if any(not 0 <= later["progression_level"] - prior["progression_level"] <= 2
                   for prior, later in zip(values, values[1:])):
                bad.extend(s["id"] for s in values)
        if unavailable:
            return "UNAVAILABLE", sorted(set(unavailable)), {"pairs": pairs}, "Series level unavailable."
        if not pairs:
            return "NOT_APPLICABLE", [], {"pairs": 0}, "No native load-week series pair."
        return ("FAIL" if bad else "PASS", sorted(set(bad)), {"pairs": pairs}, "Level progression audit.")
    if rule_id == "R16":
        scoped, bad = 0, []
        for week in weeks:
            target = week.get("target_cycling_tss")
            if week.get("week_type") == "race" or target is None:
                continue
            if not isinstance(target, (int, float)) or not math.isfinite(target):
                return "UNAVAILABLE", [str(week.get("week"))], {}, "Target TSS unavailable."
            scoped += 1
            total = sum((s.get("tss") or 0) for s in cycling_by_week[week["week"]])
            if not target * .85 <= total <= target * 1.15:
                bad.append(str(week["week"]))
        if not scoped:
            return "NOT_APPLICABLE", [], {}, "No target TSS week."
        return ("FAIL" if bad else "PASS", bad, {"mismatch_count": len(bad)}, "Target TSS audit.")
    if rule_id == "R17":
        try:
            registry = yaml.safe_load((CONFIG_DIR / "phase_purpose_registry.yaml").read_text())
        except (OSError, yaml.YAMLError):
            return "UNAVAILABLE", [], {}, "Phase-purpose registry unavailable."
        bad, scoped = [], 0
        for week in weeks:
            if not week.get("is_paid"):
                continue
            generated = [s for s in cycling_by_week[week["week"]]
                         if s.get("origin") != "ATHLETE_FIXED"]
            if not generated and week.get("week_type") not in {"race", "testing"}:
                continue
            phase_row = (registry.get("phases") or {}).get(week.get("cycling_phase"))
            override = (registry.get("week_type_overrides") or {}).get(week.get("week_type"))
            if not isinstance(phase_row, dict):
                return "UNAVAILABLE", [str(week.get("week"))], {}, "Phase-purpose input unavailable."
            row = override if isinstance(override, dict) and override.get("allowed") else phase_row
            allowed = set(row.get("allowed") or phase_row.get("allowed") or [])
            classes = [(s.get("purpose") or {}).get("class") for s in generated]
            if any(value is None for value in classes):
                return "UNAVAILABLE", [s["id"] for s in generated], {}, "Purpose unavailable."
            scoped += 1
            invalid = any(value not in allowed for value in classes)
            required_any = row.get("require_any") or []
            groups = row.get("require_all_groups") or []
            inclusion_bad = ((bool(required_any) and not set(classes) & set(required_any))
                             or any(not set(classes) & set(group) for group in groups))
            if row.get("require_exactly_one_race_event"):
                inclusion_bad = sum(s.get("fueling_class") == "RACE" for s in generated) != 1
            excluded = set(phase_row.get("excluded_subtypes") or [])
            invalid = invalid or any((s.get("purpose") or {}).get("subtype") in excluded
                                     for s in generated)
            if invalid or inclusion_bad:
                bad.extend(s["id"] for s in generated)
        if not scoped:
            return "NOT_APPLICABLE", [], {}, "No applicable generated cycling week."
        return ("FAIL" if bad else "PASS", sorted(set(bad)),
                {"invalid_session_count": len(set(bad))}, "Phase-purpose audit.")
    if rule_id == "R21":
        if manifest is None:
            return "UNAVAILABLE", [], {}, "Revision-local certification manifest unavailable."
        try:
            from earned_selection import validate_manifest_pin
            validate_manifest_pin(candidate.get("manifest_pin") or {}, manifest)
        except Exception:
            return "UNAVAILABLE", [], {}, "Candidate manifest pin mismatch."
        try:
            producers = (yaml.safe_load(
                (CONFIG_DIR / "non_native_producers.yaml").read_text()) or {}).get("producers") or {}
        except (OSError, yaml.YAMLError):
            return "UNAVAILABLE", [], {}, "Producer registry unavailable."
        manifest_rows = {row.get("row_id"): row for row in manifest.get("rows", [])}
        bad = []
        for session in sessions:
            provenance = session.get("provenance")
            if (not isinstance(provenance, dict) or not provenance.get("source_digests")
                    or any(not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256") or ""))
                           for item in provenance.get("source_digests", []))):
                bad.append(session.get("id")); continue
            if session.get("origin") in {"NATIVE_ARCHETYPE", "LEGACY_NATE_ARCHETYPE"}:
                if (provenance.get("producer_id"), provenance.get("producer_version"),
                    provenance.get("template_id"), provenance.get("template_version")) != (
                        "nate_workout_generator.native_archetype", "v1", "native_archetype", "v1"):
                    bad.append(session.get("id"))
                if (session.get("archetype") or {}).get("manifest_row_id") not in manifest_rows:
                    bad.append(session.get("id"))
                continue
            producer = producers.get(session.get("origin"))
            templates = producer.get("templates") if isinstance(producer, dict) else None
            known = provenance.get("template_id") in templates if isinstance(templates, (dict, list)) else False
            template_version = (producer.get("template_version") if isinstance(producer, dict) else None) or "v1"
            if (not known or provenance.get("producer_id") != producer.get("producer_id")
                    or provenance.get("producer_version") != producer.get("producer_version")
                    or provenance.get("template_version") != template_version):
                bad.append(session.get("id"))
        return ("FAIL" if bad else "PASS", bad, {"unresolved": len(bad)}, "Producer registry resolution audit.")
    if rule_id == "R23":
        grouped = defaultdict(lambda: defaultdict(list))
        for session in cycling:
            identity = (session.get("series") or {}).get("series_id")
            if identity and week_by_number.get(session["week"], {}).get("week_type") == "load":
                grouped[identity][session["week"]].append(session)
        bad, pairs = [], 0
        for values in grouped.values():
            totals = [(number, sum((s.get("tss") or 0) for s in values[number]))
                      for number in sorted(values)]
            pairs += max(0, len(totals) - 1)
            if any(later[1] < prior[1] for prior, later in zip(totals, totals[1:])):
                bad.extend(s["id"] for number, _ in totals for s in values[number])
        if not pairs:
            return "NOT_APPLICABLE", [], {"pairs": 0}, "No load-week series pair."
        return ("FAIL" if bad else "PASS", sorted(set(bad)), {"pairs": pairs}, "Progressive overload audit.")
    if rule_id == "R24":
        age = (candidate.get("athlete") or {}).get("training_age_years")
        if age is None:
            return "UNAVAILABLE", [], {}, "Training age unavailable."
        bad = [s["id"] for s in sessions if age < 1 and s.get("archetype") is not None
               and (s.get("progression_level") or 0) >= 5]
        if age < 2:
            bad.extend(str(w["week"]) for w in weeks if w.get("week_type") == "uber_load")
        return ("FAIL" if bad else "PASS", bad, {"training_age_years": age}, "Training-age audit.")
    if rule_id == "R25":
        if guide_html is None:
            return "UNAVAILABLE", [], {}, "Guide evidence unavailable."
        try:
            block_notes = yaml.safe_load(
                (CONFIG_DIR / "block_notes.yaml").read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            return "UNAVAILABLE", [], {}, "Block-note registry unavailable."
        if not isinstance(block_notes, dict):
            return "UNAVAILABLE", [], {}, "Block-note registry malformed."
        notes = _paid_monday_notes(guide_html)
        if notes is None:
            return "UNAVAILABLE", [], {}, "Guide block-note markup is malformed."
        markers = [_normalized_note("don't be afraid to shorten workouts"),
                   _normalized_note("if anything feels wrong (sharp pain, illness), stop immediately")]
        bad = []
        for week in weeks:
            if not week.get("is_paid"):
                continue
            template_id = week.get("block_note_template_id")
            if template_id not in block_notes:
                return "UNAVAILABLE", [str(week["week"])], {}, "Block-note template unavailable."
            emitted = notes.get(int(week["week"]), [])
            if len(emitted) != 1:
                return "UNAVAILABLE", [str(week["week"])], {}, "Monday note evidence unavailable."
            if not any(marker in _normalized_note(emitted[0]["text"]) for marker in markers):
                bad.append(str(week["week"]))
        return ("FAIL" if bad else "PASS", bad,
                {"weeks_without_marker": len(bad)},
                "Per-paid-week readiness marker audit.")
    if rule_id == "R26":
        bad = []
        by_week = defaultdict(list)
        for session in cycling:
            by_week[session["week"]].append(session)
        for week in weeks:
            if not week.get("is_paid"):
                continue
            reported = week.get("reported_cycling_tss")
            if not isinstance(reported, (int, float)) or not math.isfinite(reported):
                return "UNAVAILABLE", [], {"week": week.get("week")}, "Reported TSS unavailable."
            values = by_week[week["week"]]
            total = sum((s.get("tss") or 0) for s in values)
            without_race = sum((s.get("tss") or 0) for s in values if not s.get("race"))
            delta = min(abs(reported - total), abs(reported - without_race)) if week.get("is_race_week") else abs(reported - total)
            if delta > 15:
                bad.extend(s["id"] for s in values)
        return ("FAIL" if bad else "PASS", sorted(set(bad)), {"invalid_sessions": len(bad)}, "Weekly TSS integrity audit.")
    return "PASS", [], {"observed": True}, "Rule observed in E1."


def execute_rules(candidate: Mapping[str, Any], *, guide_html: Optional[str] = None,
                  stage: Optional[str] = None,
                  manifest: Optional[Mapping[str, Any]] = None) -> list[Dict[str, Any]]:
    legacy = legacy_verdicts(candidate["legacy_compliance_projection"])
    projection_digest = candidate["legacy_compliance_projection"]["projection_sha256"]
    rows = []
    for registry_row in rule_registry()["rules"]:
        if stage and registry_row["stage"] != stage:
            continue
        rule_id = registry_row["rule_id"]
        if rule_id in PRE_EXISTING:
            result = "PASS" if legacy[rule_id] else "FAIL"
            subject_ids, metric = [], {"legacy_compliance_projection_sha256": projection_digest}
            message = "A3.0 production-equivalent verdict."
        else:
            result, subject_ids, metric, message = _new_rule_result(
                rule_id, candidate, guide_html, manifest)
        routed = (registry_row["severity"] == "CRITICAL" and result == "FAIL"
                  and (registry_row["blocking_since"] == "pre-existing"
                       or candidate.get("rollout_phase") == "E3"))
        finding_id = None
        if not routed and result in {"FAIL", "WARNING", "UNAVAILABLE"}:
            finding_id = f"QUALITY_{rule_id}"
        rows.append({
            "rule_id": rule_id, "registry_status": registry_row["status"],
            "stage": registry_row["stage"],
            "blocking_since": registry_row["blocking_since"],
            "severity": registry_row["severity"], "result": result,
            "output_code": registry_row["output_code"],
            "subject_ids": sorted(set(subject_ids)), "metric": metric,
            "message": message, "finding_id": finding_id,
            "routed_to_blocking_issues": routed,
        })
    return rows

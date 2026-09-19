"""Tests for tools/athlete_layer.py.

Two layers:

- Golden tests replay the three real `plan_payload.json` / `notes_payload.json`
  pairs from the private build dir through `apply()` and diff against the
  shipped `*_final.json` files those athletes actually got. Skipped when the
  private dir is absent (any machine other than Matti's).
- Unit tests exercise each rules.yaml key in isolation on small synthetic
  payloads, independent of the private dir.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from tools import athlete_layer as al

PRIVATE_ROOT = Path(os.path.expanduser(
    "~/Library/Application Support/GravelGod/TrainingPeaksPublisher/plan-builds"
))

GOLDEN_CASES = [
    # (rules_dir, build_dir, has_race_card)
    ("forest-hietpas", "forest-hietpas/block2-20260928", False),
    ("edward-shapiro", "edward-shapiro/shawangunk-20260921", True),
    ("ari-shapiro", "ari-shapiro/shawangunk-20260921", True),
]

requires_private_dir = pytest.mark.skipif(
    not PRIVATE_ROOT.exists(),
    reason=f"private build dir not present at {PRIVATE_ROOT}",
)


def _opaque_race_day(plan: list[dict]) -> list[dict]:
    """Blank the 2026-11-07 Race Day description -- race_card.py's output,
    which this layer does not reproduce (rules.yaml: race_card: false)."""
    out = []
    for w in plan:
        w = dict(w)
        if w["workoutDay"].startswith("2026-11-07") and "Race Day" in w["title"]:
            w["description"] = "<opaque: race_card.py>"
        out.append(w)
    return out


@requires_private_dir
class TestGolden:
    @pytest.mark.parametrize("rules_dir,build_dir,has_race_card", GOLDEN_CASES)
    def test_reproduces_shipped_build(self, rules_dir, build_dir, has_race_card):
        rules = yaml.safe_load((PRIVATE_ROOT / rules_dir / "rules.yaml").read_text())
        build = PRIVATE_ROOT / build_dir
        plan = json.loads((build / "plan_payload.json").read_text())
        notes = json.loads((build / "notes_payload.json").read_text())
        expected_plan = json.loads((build / "plan_payload_final.json").read_text())
        expected_notes = json.loads((build / "notes_payload_final.json").read_text())

        got_plan, got_notes, changed = al.apply(plan, notes, rules)

        cmp_got, cmp_expected = got_plan, expected_plan
        if has_race_card:
            cmp_got = _opaque_race_day(got_plan)
            cmp_expected = _opaque_race_day(expected_plan)

        assert cmp_got == cmp_expected
        assert got_notes == expected_notes
        assert changed  # every one of these athletes has at least one real transform


# --------------------------------------------------------------- fixtures

def workout(day, title, kind=2, mins=60, description="", structure=None):
    return {
        "title": title,
        "workoutTypeValueId": kind,
        "workoutDay": f"{day}T00:00:00",
        "description": description,
        "totalTimePlanned": mins / 60,
        "tssPlanned": 0.0,
        "structure": structure,
    }


def note(day, title, description=""):
    return {"title": title, "noteDate": day, "description": description}


def target_structure(value, unit="percentOfFtp"):
    return {
        "structure": [
            {"steps": [{"targets": [{"unit": unit, "maxValue": value}]}]},
        ]
    }


# --------------------------------------------------------------- unit tests

class TestTitleFormat:
    def test_plain_leaves_titles_alone(self):
        plan = [workout("2026-09-21", "Endurance Ride")]
        got, _, changed = al.apply(plan, [], {"title_format": "plain"})
        assert got[0]["title"] == "Endurance Ride"
        assert changed == []

    def test_absent_leaves_titles_alone(self):
        plan = [workout("2026-09-21", "Endurance Ride")]
        got, _, changed = al.apply(plan, [], {})
        assert got[0]["title"] == "Endurance Ride"
        assert changed == []

    def test_duration_lead_prefixes_minutes(self):
        plan = [workout("2026-09-21", "Endurance Ride", mins=90)]
        got, _, changed = al.apply(plan, [], {"title_format": "duration_lead"})
        assert got[0]["title"] == "90 min — Endurance Ride"
        assert len(changed) == 1

    def test_duration_lead_skips_rest_days(self):
        plan = [workout("2026-09-21", "Rest Day", kind=7)]
        got, _, changed = al.apply(plan, [], {"title_format": "duration_lead"})
        assert got[0]["title"] == "Rest Day"
        assert changed == []

    def test_duration_lead_skips_rest_day_by_title_even_if_kind_differs(self):
        plan = [workout("2026-09-21", "Rest Day - active recovery", kind=2, mins=30)]
        got, _, changed = al.apply(plan, [], {"title_format": "duration_lead"})
        assert got[0]["title"] == "Rest Day - active recovery"

    def test_colon_optional_prefix_stripped_and_state_preserved(self):
        # An "OPTIONAL:" (colon) title -- the state a rerun would find --
        # loses the colon-form prefix but stays OPTIONAL in the rebuilt title.
        # The description dedupe check is literal ("does it already start
        # with OPTIONAL"), so optional_intensity.text is written to start
        # with "OPTIONAL" (as Forest's real zero-penalty line does).
        rules = {
            "title_format": "duration_lead",
            "optional_intensity": {
                "enabled": True,
                "text": "OPTIONAL — ZERO PENALTY",
                "intensity_detector": {"type_ids": [2]},
            },
        }
        plan = [workout("2026-09-21", "OPTIONAL: VO2 Intervals", mins=45,
                         description="OPTIONAL — ZERO PENALTY\n\nold body")]
        got, _, _ = al.apply(plan, [], rules)
        assert got[0]["title"] == "OPTIONAL 45 min — VO2 Intervals"
        # description already carries the zero-penalty text; not doubled.
        assert got[0]["description"].count("ZERO PENALTY") == 1


class TestTitleAllowlistPrefixes:
    def test_allowlisted_prefix_bypasses_optional_even_if_hard(self):
        rules = {
            "title_format": "duration_lead",
            "title_allowlist_prefixes": ["4am trainer ride"],
            "optional_intensity": {
                "enabled": True,
                "text": "ZERO",
                "intensity_detector": {"type_ids": [2], "title_regex": "interval"},
            },
        }
        plan = [workout("2026-09-21", "4am trainer ride intervals", mins=30)]
        got, _, _ = al.apply(plan, [], rules)
        assert got[0]["title"] == "30 min — 4am trainer ride intervals"
        assert "ZERO" not in (got[0]["description"] or "")

    def test_allowlisted_prefix_already_duration_led_is_untouched(self):
        rules = {"title_format": "duration_lead", "title_allowlist_prefixes": ["30 min — 4am trainer ride"]}
        plan = [workout("2026-09-21", "30 min — 4am trainer ride — zone 2", mins=30)]
        got, _, changed = al.apply(plan, [], rules)
        assert got[0]["title"] == "30 min — 4am trainer ride — zone 2"
        assert changed == []


class TestOptionalIntensity:
    def _rules(self, **overrides):
        base = {
            "title_format": "duration_lead",
            "optional_intensity": {
                "enabled": True,
                "text": "ZERO PENALTY LINE",
                "intensity_detector": {
                    "power_pct_gte": 90,
                    "exclude_units": ["roundOrStridePerMinute"],
                    "type_ids": [2],
                    "title_regex": "interval|threshold",
                },
            },
        }
        base.update(overrides)
        return base

    def test_high_power_target_marks_optional(self):
        plan = [workout("2026-09-21", "Sweet Spot Push", mins=60,
                         structure=target_structure(92), description="body")]
        got, _, _ = al.apply(plan, [], self._rules())
        assert got[0]["title"] == "OPTIONAL 60 min — Sweet Spot Push"
        assert got[0]["description"].startswith("ZERO PENALTY LINE")

    def test_excluded_unit_does_not_trigger(self):
        plan = [workout("2026-09-21", "Cadence Drill", mins=60,
                         structure=target_structure(110, unit="roundOrStridePerMinute"))]
        got, _, _ = al.apply(plan, [], self._rules())
        assert got[0]["title"] == "60 min — Cadence Drill"

    def test_title_regex_triggers_without_structure(self):
        plan = [workout("2026-09-21", "Threshold Steady", mins=45)]
        got, _, _ = al.apply(plan, [], self._rules())
        assert got[0]["title"].startswith("OPTIONAL")

    def test_type_id_not_in_list_never_flagged(self):
        plan = [workout("2026-09-21", "Threshold Run", kind=3, mins=45)]
        got, _, _ = al.apply(plan, [], self._rules())
        assert got[0]["title"] == "45 min — Threshold Run"

    def test_enabled_false_still_marks_title_but_not_description(self):
        rules = self._rules()
        rules["optional_intensity"]["enabled"] = False
        plan = [workout("2026-09-21", "Threshold Steady", mins=45, description="body")]
        got, _, _ = al.apply(plan, [], rules)
        assert got[0]["title"].startswith("OPTIONAL")
        assert got[0]["description"] == "body"


class TestForceOptionalDates:
    def test_forces_optional_on_matching_date_and_type(self):
        rules = {
            "title_format": "duration_lead",
            "force_optional_dates": ["2026-10-09"],
            "optional_intensity": {"text": "ZERO", "intensity_detector": {"type_ids": [2]}},
        }
        plan = [workout("2026-10-09", "Endurance Ride", mins=90, description="body")]
        got, _, changed = al.apply(plan, [], rules)
        assert got[0]["title"].startswith("OPTIONAL")
        assert got[0]["description"].startswith("ZERO")
        assert len(changed) >= 1

    def test_wrong_date_untouched(self):
        rules = {
            "title_format": "duration_lead",
            "force_optional_dates": ["2026-10-09"],
            "optional_intensity": {"text": "ZERO", "intensity_detector": {"type_ids": [2]}},
        }
        plan = [workout("2026-10-10", "Endurance Ride", mins=90)]
        got, _, _ = al.apply(plan, [], rules)
        assert not got[0]["title"].startswith("OPTIONAL")

    def test_already_optional_not_double_prefixed(self):
        rules = {
            "force_optional_dates": ["2026-10-09"],
            "optional_intensity": {"text": "ZERO", "intensity_detector": {"type_ids": [2]}},
        }
        plan = [workout("2026-10-09", "OPTIONAL Endurance Ride", mins=90)]
        got, _, changed = al.apply(plan, [], rules)
        assert got[0]["title"] == "OPTIONAL Endurance Ride"
        assert changed == []


class TestStripSentences:
    def test_strips_matching_sentence(self):
        rules = {"strip_sentences": [r"[^.\n]*\bcalorie\b[^.\n]*\."]}
        plan = [workout("2026-09-21", "Rest Day", kind=7,
                         description="Sleep well. Watch your calorie deficit today. Mobility work too.")]
        got, _, changed = al.apply(plan, [], rules)
        assert "calorie" not in got[0]["description"]
        assert "Sleep well." in got[0]["description"]
        assert "Mobility work too." in got[0]["description"]
        assert len(changed) == 1

    def test_no_match_no_change(self):
        rules = {"strip_sentences": [r"[^.\n]*\bcalorie\b[^.\n]*\."]}
        plan = [workout("2026-09-21", "Rest Day", kind=7, description="Sleep well.")]
        got, _, changed = al.apply(plan, [], rules)
        assert got[0]["description"] == "Sleep well."
        assert changed == []


class TestReplaceText:
    def test_descriptions_scope(self):
        rules = {"replace_text": [{"scope": "descriptions", "from": "G SPOT", "to": "sweet spot"}]}
        plan = [workout("2026-09-21", "Steady", description="Target G SPOT zone")]
        got, _, _ = al.apply(plan, [], rules)
        assert got[0]["description"] == "Target sweet spot zone"

    def test_titles_scope(self):
        rules = {"replace_text": [{"scope": "titles", "from": "G SPOT", "to": "Sweet Spot"}]}
        plan = [workout("2026-09-21", "G SPOT Intervals")]
        got, _, _ = al.apply(plan, [], rules)
        assert got[0]["title"] == "Sweet Spot Intervals"

    def test_notes_scope(self):
        rules = {"replace_text": [{"scope": "notes", "from": "seven hours", "to": "nine hours"}]}
        notes = [note("2026-09-21", "Week 1", "I want seven hours of sleep.")]
        _, got_notes, _ = al.apply([], notes, rules)
        assert got_notes[0]["description"] == "I want nine hours of sleep."

    def test_applies_in_list_order(self):
        rules = {"replace_text": [
            {"scope": "descriptions", "from": "Target G SPOT zone", "to": "Target sweet spot"},
            {"scope": "descriptions", "from": "G SPOT", "to": "sweet spot"},
        ]}
        plan = [workout("2026-09-21", "Steady", description="Target G SPOT zone and G SPOT again")]
        got, _, _ = al.apply(plan, [], rules)
        assert got[0]["description"] == "Target sweet spot and sweet spot again"

    def test_unknown_scope_raises(self):
        rules = {"replace_text": [{"scope": "bogus", "from": "a", "to": "b"}]}
        with pytest.raises(ValueError):
            al.apply([workout("2026-09-21", "a")], [], rules)


class TestTitleStripRegex:
    def test_strips_week_prefix(self):
        rules = {"title_strip_regex": [r"^Week \d+\s*[-–—:]\s*"]}
        plan = [workout("2026-09-21", "Week 4 - Threshold Steady")]
        got, _, changed = al.apply(plan, [], rules)
        assert got[0]["title"] == "Threshold Steady"
        assert len(changed) == 1

    def test_no_match_untouched(self):
        rules = {"title_strip_regex": [r"^Week \d+\s*[-–—:]\s*"]}
        plan = [workout("2026-09-21", "Threshold Steady")]
        got, _, changed = al.apply(plan, [], rules)
        assert got[0]["title"] == "Threshold Steady"
        assert changed == []


class TestGuardrails:
    def test_appends_guardrail_once(self):
        rules = {"guardrails": [{"title_match_regex": "Ladder", "text": "\n\nGUARDRAIL: watch the knees."}]}
        plan = [workout("2026-09-21", "Descending-Cadence Ladder", description="Main set here.")]
        got, _, changed = al.apply(plan, [], rules)
        assert got[0]["description"] == "Main set here.\n\nGUARDRAIL: watch the knees."
        assert len(changed) == 1

    def test_idempotent_second_pass_does_not_double(self):
        rules = {"guardrails": [{"title_match_regex": "Ladder", "text": "\n\nGUARDRAIL: watch the knees."}]}
        plan = [workout("2026-09-21", "Descending-Cadence Ladder", description="Main set here.")]
        once, _, _ = al.apply(plan, [], rules)
        twice, _, changed = al.apply(once, [], rules)
        assert twice[0]["description"].count("GUARDRAIL") == 1
        assert changed == []

    def test_non_matching_title_untouched(self):
        rules = {"guardrails": [{"title_match_regex": "Ladder", "text": "\n\nGUARDRAIL"}]}
        plan = [workout("2026-09-21", "Endurance Ride", description="body")]
        got, _, changed = al.apply(plan, [], rules)
        assert got[0]["description"] == "body"
        assert changed == []


class TestRaceCard:
    def test_false_leaves_description_untouched(self):
        plan = [workout("2026-11-07", "Race Day — Shawangunk Grit", description="engine-authored")]
        got, _, _ = al.apply(plan, [], {"race_card": False})
        assert got[0]["description"] == "engine-authored"

    def test_absent_key_same_as_false(self):
        plan = [workout("2026-11-07", "Race Day — Shawangunk Grit", description="engine-authored")]
        got, _, _ = al.apply(plan, [], {})
        assert got[0]["description"] == "engine-authored"

    def test_true_raises_not_implemented(self):
        plan = [workout("2026-11-07", "Race Day — Shawangunk Grit")]
        with pytest.raises(NotImplementedError):
            al.apply(plan, [], {"race_card": True})


class TestDropRestOnMultiSessionDays:
    def test_drops_rest_day_sharing_a_day_with_another_session(self):
        plan = [
            workout("2026-09-21", "Rest Day", kind=7),
            workout("2026-09-21", "Strength", kind=3),
        ]
        got, _, changed = al.apply(plan, [], {"drop_rest_on_multi_session_days": True})
        assert len(got) == 1
        assert got[0]["title"] == "Strength"
        assert len(changed) == 1

    def test_solo_rest_day_kept(self):
        plan = [workout("2026-09-21", "Rest Day", kind=7)]
        got, _, changed = al.apply(plan, [], {"drop_rest_on_multi_session_days": True})
        assert len(got) == 1
        assert changed == []

    def test_disabled_by_default(self):
        plan = [
            workout("2026-09-21", "Rest Day", kind=7),
            workout("2026-09-21", "Strength", kind=3),
        ]
        got, _, _ = al.apply(plan, [], {})
        assert len(got) == 2


class TestDropNotes:
    def test_drops_matching_note(self):
        rules = {"drop_notes": [{"date": "2026-10-24", "title_contains": "Long Ride"}]}
        notes = [note("2026-10-24", "Week 4 Long Ride Fuel"), note("2026-10-24", "Week 4")]
        _, got_notes, changed = al.apply([], notes, rules)
        assert [n["title"] for n in got_notes] == ["Week 4"]
        assert len(changed) == 1

    def test_wrong_date_kept(self):
        rules = {"drop_notes": [{"date": "2026-10-24", "title_contains": "Long Ride"}]}
        notes = [note("2026-10-25", "Week 4 Long Ride Fuel")]
        _, got_notes, _ = al.apply([], notes, rules)
        assert len(got_notes) == 1


class TestNotePrefix:
    def test_prepends_to_matching_notes(self):
        rules = {"note_prefix": {"title_regex": "^Week ", "exclude_title_contains": ["Midweek", "Fuel"],
                                  "text": "PREFIX\n\n"}}
        notes = [note("2026-09-21", "Week 1: Base", "Body text.")]
        _, got_notes, changed = al.apply([], notes, rules)
        assert got_notes[0]["description"] == "PREFIX\n\nBody text."
        assert len(changed) == 1

    def test_excluded_title_untouched(self):
        rules = {"note_prefix": {"title_regex": "^Week ", "exclude_title_contains": ["Midweek"],
                                  "text": "PREFIX\n\n"}}
        notes = [note("2026-09-21", "Week 1 Midweek Check-in", "Body text.")]
        _, got_notes, changed = al.apply([], notes, rules)
        assert got_notes[0]["description"] == "Body text."
        assert changed == []

    def test_idempotent(self):
        rules = {"note_prefix": {"title_regex": "^Week ", "exclude_title_contains": [], "text": "PREFIX\n\n"}}
        notes = [note("2026-09-21", "Week 1: Base", "Body text.")]
        _, once, _ = al.apply([], notes, rules)
        _, twice, changed = al.apply([], once, rules)
        assert twice[0]["description"].count("PREFIX") == 1
        assert changed == []


class TestCommitmentNotes:
    def test_appended_after_engine_notes(self):
        rules = {"commitment_notes": [{"date": "2026-10-02", "title": "Matti call",
                                        "description": "11:30 Mountain."}]}
        notes = [note("2026-09-21", "How To Comment On Workouts", "protocol text")]
        _, got_notes, changed = al.apply([], notes, rules)
        assert len(got_notes) == 2
        assert got_notes[-1] == {"title": "Matti call", "noteDate": "2026-10-02", "description": "11:30 Mountain."}
        assert changed == []  # appending is not a "change" to an existing note

    def test_no_commitment_notes_key_is_noop(self):
        notes = [note("2026-09-21", "existing")]
        _, got_notes, _ = al.apply([], notes, {})
        assert got_notes == notes


class TestNoteDateRemap:
    def test_remaps_commitment_note_date(self):
        rules = {
            "commitment_notes": [{"date": "2026-10-09", "title": "Roslyn weekend — protected",
                                   "description": "away"}],
            "note_date_remap": [{"title_prefix": "Roslyn weekend", "to_date": "2026-10-08"}],
        }
        _, got_notes, changed = al.apply([], [], rules)
        assert got_notes[0]["noteDate"] == "2026-10-08"
        assert len(changed) == 1

    def test_remaps_engine_note_too(self):
        rules = {"note_date_remap": [{"title_prefix": "Roslyn", "to_date": "2026-10-08"}]}
        notes = [note("2026-10-09", "Roslyn note")]
        _, got_notes, _ = al.apply([], notes, rules)
        assert got_notes[0]["noteDate"] == "2026-10-08"

    def test_non_matching_prefix_untouched(self):
        rules = {"note_date_remap": [{"title_prefix": "Roslyn", "to_date": "2026-10-08"}]}
        notes = [note("2026-10-09", "Other note")]
        _, got_notes, changed = al.apply([], notes, rules)
        assert got_notes[0]["noteDate"] == "2026-10-09"
        assert changed == []


class TestCLI:
    def test_round_trips_through_files(self, tmp_path):
        in_dir = tmp_path / "in"
        in_dir.mkdir()
        (in_dir / "plan_payload.json").write_text(json.dumps([workout("2026-09-21", "Endurance", mins=60)]))
        (in_dir / "notes_payload.json").write_text(json.dumps([note("2026-09-21", "Week 1", "body")]))
        rules_path = tmp_path / "rules.yaml"
        rules_path.write_text("title_format: duration_lead\n")

        rc = al.main(["--rules", str(rules_path), "--in-dir", str(in_dir), "--out-dir", str(in_dir)])
        assert rc == 0

        plan_final = json.loads((in_dir / "plan_payload_final.json").read_text())
        notes_final = json.loads((in_dir / "notes_payload_final.json").read_text())
        assert plan_final[0]["title"] == "60 min — Endurance"
        assert notes_final[0]["title"] == "Week 1"

    def test_race_card_true_exits_nonzero(self, tmp_path, capsys):
        in_dir = tmp_path / "in"
        in_dir.mkdir()
        (in_dir / "plan_payload.json").write_text(json.dumps([workout("2026-11-07", "Race Day")]))
        (in_dir / "notes_payload.json").write_text("[]")
        rules_path = tmp_path / "rules.yaml"
        rules_path.write_text("race_card: true\n")

        rc = al.main(["--rules", str(rules_path), "--in-dir", str(in_dir), "--out-dir", str(in_dir)])
        assert rc == 2
        assert "race_card" in capsys.readouterr().err

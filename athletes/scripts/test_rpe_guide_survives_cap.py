"""2026-09-18: a compiler-appended RPE guide / heat protocol block must
survive the 180-word athlete-copy cap, and the appended result must be a
fixed point of sanitize_athlete_description (validate_canonical_model
re-sanitizes every athlete-visible description)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import delivery_render as dr  # noqa: E402


def _long_body(words=175):
    return " ".join(f"word{i}" for i in range(words)) + "."


def _segments():
    return [{"kind": "intervals", "repeat": 4, "on_seconds": 300, "on_power": 0.95},
            {"kind": "steady_state", "seconds": 600, "power_target": 0.66}]


def test_rpe_guide_survives_the_word_cap_and_is_a_sanitize_fixed_point():
    out = dr.append_rpe_guide_if_missing(_long_body(), library_item_id=1, segments=_segments())
    assert out.splitlines()[-1].startswith("RPE guide: 95% FTP")
    assert len(dr._ATHLETE_WORD.findall(out)) <= dr._ATHLETE_COPY_MAX_WORDS
    assert dr.sanitize_athlete_description(out) == out


def test_heat_protocol_explainer_survives_the_word_cap():
    out = dr.append_heat_protocol_explainer_if_missing(_long_body(), "Heat Acclimation Protocol")
    assert "HEAT PROTOCOL:" in out and out.rstrip().endswith("push through.")
    assert dr.sanitize_athlete_description(out) == out


def test_short_copy_is_untouched():
    body = "Warm up.\n\nMAIN SET: 3x10 min."
    out = dr.append_rpe_guide_if_missing(body, library_item_id=1, segments=_segments())
    assert out.startswith(body)


def test_overflowing_main_set_line_is_word_cut_not_dropped():
    body = "WARM-UP:\n-15min building.\n\nMAIN SET:\n" + "Ride smoothly and stay seated. " * 60
    out = dr.append_rpe_guide_if_missing(body, library_item_id=1, segments=_segments())
    lines = out.splitlines()
    main_idx = lines.index("MAIN SET:")
    assert lines[main_idx + 1].startswith("Ride smoothly")  # the set survives, cut to budget
    assert len(dr._ATHLETE_WORD.findall(out)) <= dr._ATHLETE_COPY_MAX_WORDS
    assert out.splitlines()[-1].startswith("RPE guide:")
    assert dr.sanitize_athlete_description(out) == out


def test_every_fuel_tier_tag_is_rewritten_by_the_sanitizer():
    for label in ("FUEL", "HIGH FUEL", "MODERATE FUEL", "LONG-RIDE FUEL", "RACE FUEL"):
        out = dr.sanitize_athlete_description(f"[{label}: Target 45g carbs/hr.]\n\nMAIN SET: 3x10.")
        assert out.startswith("FUEL:\nTarget 45g carbs/hr."), (label, out)
        assert "[" not in out

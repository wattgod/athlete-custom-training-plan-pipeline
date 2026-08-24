"""Regression tests for the AE-1.12 taper/race hard-work ceiling on NATIVE
archetype selection (docs/ALGORITHM_EVIDENCE.md).

library_selector._passes_role_ceiling already enforces AE-1.12 (no
>=92%-FTP rep >120s, <=900s total >=92% work per session) for CURATED TP
library selections during taper/race weeks. select_archetype_for_workout
(the native Nate-archetype path, reached from workout_mapper.render_workout
via generate_nate_zwo) has no week_type parameter at all and had no
equivalent gate -- a taper/race slot that fell through to a generic
archetype pick, instead of one of the four hand-calibrated dedicated
renderers (Stars In Your Eyes / Openers / Taper Burst Endurance /
Endurance), could ship uncapped build-phase intensity into race week.

These tests cover the fix in workout_mapper._violates_taper_race_hard_work_
ceiling + render_workout's new `week_type` parameter.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from workout_mapper import render_workout, _violates_taper_race_hard_work_ceiling


class TestTaperRaceHardWorkCeilingHelper:
    def test_hard_threshold_workout_violates_ceiling(self):
        """Threshold Steady's real archetype content is a single sustained
        >=92%-FTP block far over both AE-1.12 caps at every level -- a
        genuine build-phase workout, never coach-appropriate for taper or
        race week."""
        zwo = render_workout('Threshold Steady', level=3, workout_name='test')
        assert zwo is not None
        assert _violates_taper_race_hard_work_ceiling(zwo)

    def test_easy_workout_passes_ceiling(self):
        zwo = render_workout('Cadence Work', level=1, workout_name='test')
        assert zwo is not None
        assert not _violates_taper_race_hard_work_ceiling(zwo)


class TestNativeSelectionRefusesUnsafeTaperRaceContent:
    def test_hard_type_refused_for_race_week(self):
        assert render_workout(
            'Threshold Steady', level=3, workout_name='test', week_type='race'
        ) is None

    def test_hard_type_refused_for_taper_week(self):
        assert render_workout(
            'Threshold Steady', level=3, workout_name='test', week_type='taper'
        ) is None

    def test_hard_type_unaffected_outside_taper_and_race_weeks(self):
        # No week_type / non-gated week_type -- behavior must be unchanged.
        assert render_workout(
            'Threshold Steady', level=3, workout_name='test', week_type=None
        ) is not None
        assert render_workout(
            'Threshold Steady', level=3, workout_name='test', week_type='build'
        ) is not None

    def test_dedicated_taper_slot_archetypes_still_render_in_taper_and_race_weeks(self):
        """The real slots _select_taper_week/_select_race_week place --
        Thirty-Fifteens and Cadence Work -- must not regress: they already
        pass AE-1.12 comfortably and the new gate must not false-positive
        on them."""
        for week_type in ('taper', 'race'):
            for name, level in (('Thirty-Fifteens', 4), ('Cadence Work', 1)):
                zwo = render_workout(
                    name, level=level, workout_name='test', week_type=week_type)
                assert zwo is not None, (
                    f'{name} L{level} unexpectedly refused in a {week_type} week'
                )

    def test_stars_in_your_eyes_dedicated_renderer_unaffected_by_gate(self):
        # Stars In Your Eyes always renders through the hand-calibrated
        # _render_race_week_sharpener, never the generic archetype path --
        # the new gate must not interfere with it in a race week.
        zwo = render_workout(
            'Stars In Your Eyes', level=2, workout_name='test', week_type='race')
        assert zwo is not None

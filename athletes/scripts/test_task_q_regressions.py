"""Regression coverage for Task Q (round-6 grader findings, fresh-eyes pass).

1. Fuel tags missing on taper/race-week archetypes (Ronnestad 30/15, Stars In
   Your Eyes, Pre-Race Openers) + R08 compliance gate was a stub that always
   passed.
2. "Endurance with Surges" (rendered via Taper Burst Endurance) purpose text
   was phase-blind -- always claimed "during the taper" outside taper.
4. Focus-variant endurance rides (Position/Cadence/Burst/Spin-Up Focus) lost
   their Position/Cadence instructions when the description was rewritten
   from executable segments; Burst Focus promised a periodic burst its ZWO
   structure never delivered.
5. Midweek "Race Simulation" cards (role != long_ride) rendered a flat
   over-under set with none of the race-shaped Act logic.
6. "Pre-Race Openers" title rendered unconditionally, even with no race
   within reach.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from act_race_sim import RaceFacts, compose_midweek_sim, render_midweek_sim_zwo
from block_compliance import r08_fuel_tags
from generate_athlete_package import classify_fuel_tier, _get_fuel_tag_for_type
from workout_mapper import render_workout, resolve_display_name
from workout_spec import rewrite_zwo_description


def _fueling():
    return {'prescription': {
        'training_tiers': {
            'quality': {'target_g_per_hour': 55},
            'long_ride': {'target_g_per_hour': 62},
            'race_sim': {'target_g_per_hour': 70},
        },
        'race_target_g_per_hour': 70,
    }}


# ============================================================
# Item 1: fuel tags on taper/race-week archetypes + R08 gate
# ============================================================

class TestFuelTagRoutingGaps:
    @pytest.mark.parametrize('name', ['Thirty-Fifteens', 'Stars In Your Eyes', 'Openers'])
    def test_short_race_week_archetypes_classify_as_quality(self, name):
        """These used to fall through to the duration-gated catch-all and
        render no tag at all -- they must always classify as a taggable
        tier, matching High Cadence Intervals' existing policy."""
        assert classify_fuel_tier(name) in ('quality', 'race_sim')

    @pytest.mark.parametrize('name,duration', [
        ('Thirty-Fifteens', 30), ('Stars In Your Eyes', 58), ('Openers', 15),
    ])
    def test_short_race_week_archetypes_get_a_tag_regardless_of_duration(self, name, duration):
        tag = _get_fuel_tag_for_type(name, _fueling(), duration)
        # Superseded policy (v13 regrade): short quality sessions still carry
        # a tag (R08), but a SOFT one — the rigid ladder target contradicted
        # the ladder's own under-90-minute scope.
        assert 'FUEL' in tag
        assert 'Under 90 minutes' in tag
        assert 'Target' not in tag

    def test_rest_day_and_true_recovery_stay_untagged(self):
        assert _get_fuel_tag_for_type('Rest Day', _fueling(), 0) == ''
        assert _get_fuel_tag_for_type('Recovery', _fueling(), 20) == ''

    def test_short_endurance_ride_still_exempt_by_duration(self):
        """The <90min 'water is fine' policy for genuine easy rides is
        unaffected by moving 'openers' out of the exempt bucket."""
        assert _get_fuel_tag_for_type('Endurance', _fueling(), 45) == ''


def _day(day, name, role, duration, tss, **extra):
    return {'day': day, 'name': name, 'role': role,
            'duration': duration, 'tss': tss, **extra}


class TestR08FuelTagGate:
    def test_r08_was_a_stub_now_actually_checks(self):
        """Regression: a plan with an untagged intensity workout must fail
        R08. Before this fix, r08_fuel_tags() always returned True regardless
        of input -- this constructs a day whose name won't classify as
        taggable to prove the gate can actually fire."""
        weeks = [{'plan_week': 1, 'days': [
            _day('Tue', 'Rest', 'intensity', 60, 60),  # pathological: role says
                                                        # intensity, name classifies exempt
        ]}]
        passed, message = r08_fuel_tags(weeks)
        assert not passed
        assert 'Rest' in message

    def test_r08_passes_a_correctly_tagged_plan(self):
        weeks = [{'plan_week': 1, 'days': [
            _day('Tue', 'Thirty-Fifteens', 'intensity', 30, 60),
            _day('Thu', 'Stars In Your Eyes', 'intensity', 58, 65),
            _day('Sat', 'Openers', 'intensity', 15, 20),
            _day('Sun', 'Endurance', 'long_ride', 200, 150),
            _day('Wed', 'Endurance', 'filler', 45, 30),
        ]}]
        passed, message = r08_fuel_tags(weeks)
        assert passed, message

    def test_r08_ignores_non_intensity_non_long_ride_roles(self):
        """Fillers/easy days are not required to carry a banner -- only
        intensity and long_ride roles are checked (role-based, matching
        R01's classify-by-role pattern)."""
        weeks = [{'plan_week': 1, 'days': [
            _day('Wed', 'Recovery', 'filler', 30, 15),
        ]}]
        passed, _ = r08_fuel_tags(weeks)
        assert passed


# ============================================================
# Item 2: phase-aware Taper Burst Endurance purpose text
# ============================================================

class TestTaperBurstPhaseAwarePurpose:
    def test_taper_phase_keeps_taper_language(self):
        zwo = render_workout('Taper Burst Endurance', level=3, phase='taper')
        assert 'during the taper' in zwo

    @pytest.mark.parametrize('phase,expected_fragment', [
        ('base', 'aerobic base builds'),
        ('build', 'the volume builds'),
        ('peak', 'peak load'),
    ])
    def test_non_taper_phases_get_phase_appropriate_copy(self, phase, expected_fragment):
        zwo = render_workout('Taper Burst Endurance', level=3, phase=phase)
        assert expected_fragment in zwo
        assert 'during the taper' not in zwo

    def test_missing_phase_falls_back_without_a_hardcoded_taper_claim(self):
        zwo = render_workout('Taper Burst Endurance', level=3)
        assert 'during the taper' not in zwo


# ============================================================
# Item 4: focus-variant endurance content must reach the description
# ============================================================

class TestEnduranceFocusVariantContent:
    @pytest.mark.parametrize('variant,label', [
        (0, 'Position'), (1, 'Cadence'), (2, 'Position'), (3, 'Position'), (5, 'Cadence'),
    ])
    def test_dimension_lines_survive_the_description_rewrite(self, variant, label):
        """rewrite_zwo_description regenerates MAIN SET from the executable
        ZWO segments -- it used to silently drop Position/Cadence lines
        (Position was never preserved at all; Cadence's carve-out only
        matched a no-space '-Cadence:' format the endurance renderer never
        produces)."""
        zwo = render_workout('Endurance', level=1, endurance_variant=variant)
        rewritten = rewrite_zwo_description(zwo)
        assert f'{label}:' in rewritten

    def test_burst_focus_structure_matches_its_promise(self):
        """Burst Focus's description explicitly promises a periodic 6sec
        burst -- the ZWO structure must actually contain one, not just a
        flat steady block."""
        zwo = render_workout('Endurance', level=1, endurance_variant=4)
        bursts = re.findall(r'Duration="6" Power="1\.20"', zwo)
        assert len(bursts) >= 2

    def test_flat_no_variant_endurance_unaffected(self):
        zwo = render_workout('Endurance', level=3)
        rewritten = rewrite_zwo_description(zwo)
        assert 'Duration="6" Power="1.20"' not in zwo
        assert rewritten  # still renders

    @pytest.mark.parametrize('variant', range(6))
    def test_focus_variant_description_names_its_warmup(self, variant):
        """Real graded defect: "Endurance — Position Focus" (and every
        sibling focus variant, since they share one description builder)
        opened straight into MAIN SET despite the ZWO structure always
        opening with a <Warmup> ramp -- the description never told the
        athlete a warm-up existed."""
        zwo = render_workout('Endurance', level=1, endurance_variant=variant)
        description = re.search(r'<description>(.*?)</description>', zwo, re.S).group(1)
        assert 'WARM-UP:' in description
        assert description.index('WARM-UP:') < description.index('MAIN SET:')


# ============================================================
# Item 5: midweek race-simulation gets a compressed race shape
# ============================================================

class TestMidweekRaceSimulation:
    def test_exact_duration_budget(self):
        facts = RaceFacts(distance_miles=100, elevation_ft=6200)
        segments = compose_midweek_sim(61, facts)
        total = sum(
            s['seconds'] if s['kind'] == 'steady'
            else s['repeat'] * (s['on_seconds'] + s['off_seconds'])
            for s in segments)
        assert total == 61 * 60

    def test_has_warmup_unit_cooldown_and_no_negative_durations(self):
        facts = RaceFacts(distance_miles=100, elevation_ft=6200)
        for duration in (45, 61, 75, 90):
            segments = compose_midweek_sim(duration, facts)
            assert all(
                (s.get('seconds', 0) if s['kind'] == 'steady'
                 else s['repeat'] * (s['on_seconds'] + s['off_seconds'])) >= 0
                for s in segments)
            labels = ' '.join(s['label'] for s in segments)
            assert 'Warm-up' in labels
            assert 'Unit 1' in labels
            assert 'Cooldown' in labels

    def test_zwo_is_race_shaped_not_a_flat_over_under(self):
        facts = RaceFacts(distance_miles=100, elevation_ft=6200)
        zwo = render_midweek_sim_zwo(
            workout_name='test', display_name='Race Simulation',
            duration_min=61, facts=facts, author='Coach')
        assert 'RACE SIMULATION' in zwo
        # A flat over/under set is two alternating powers; the race-shaped
        # composer has a distinct high-cadence Z3 open, attacks, and a
        # seated low-cadence climb -- more than two distinct power levels.
        powers = set(re.findall(r'Power="([\d.]+)"', zwo))
        assert len(powers) > 3

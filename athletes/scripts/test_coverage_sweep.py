"""Tests for the coverage sweep's pure helpers + the synthesize overrides it
relies on. The build loop itself runs the real pipeline (exercised in CI /
ad-hoc), but the sampling, clustering, and forced-persona/race plumbing must
be deterministic and correct."""

from synthesize_athlete import synthesize, PERSONAS
import coverage_sweep as cs


class TestForcedPersonaAndRace:
    def test_forced_persona_is_used(self):
        a = synthesize("t", 0, today="2026-06-22",
                       persona_key="masters_returner")
        assert a["_meta"]["persona"] == "masters_returner"
        # masters age band is 50-63
        assert 50 <= a["age"] <= 63

    def test_forced_race_overrides_pick(self):
        race = {"name": "Coverage Test Gravel", "date": "2026-12-01",
                "distance_mi": 70, "elevation_ft": 4000, "discipline": "gravel"}
        a = synthesize("t", 0, today="2026-06-22",
                       persona_key="weekend_warrior", race=race)
        assert a["races"][0]["name"] == "Coverage Test Gravel"
        assert a["races"][0]["distance"] == "70 miles"

    def test_forced_race_drives_discipline(self):
        race = {"name": "Some Road Fondo", "date": "2026-12-01",
                "distance_mi": 80, "elevation_ft": 3000, "discipline": "road"}
        a = synthesize("t", 0, today="2026-06-22",
                       persona_key="weekend_warrior", race=race)
        assert a["_meta"]["discipline"] == "road"

    def test_random_persona_still_works_without_key(self):
        a = synthesize("t", 3, today="2026-06-22")
        assert a["_meta"]["persona"] in {p["key"] for p in PERSONAS}


class TestStratifiedSample:
    def _races(self):
        out = []
        for disc in ("gravel", "road"):
            for mi in (40, 60, 100, 140):
                for j in range(5):
                    out.append({"name": f"{disc}-{mi}-{j}",
                                "discipline": disc, "distance_mi": mi})
        return out

    def test_sample_is_deterministic(self):
        races = self._races()
        a = cs._stratified_sample(races, 10, "seed1")
        b = cs._stratified_sample(races, 10, "seed1")
        assert [r["name"] for r in a] == [r["name"] for r in b]

    def test_sample_spans_strata(self):
        races = self._races()
        sample = cs._stratified_sample(races, 8, "seed1")
        # an 8-pick round-robin over 8 strata (2 disc × 4 bands) hits each once
        strata = {(r["discipline"], cs._band(r["distance_mi"])) for r in sample}
        assert len(strata) >= 6

    def test_sample_respects_size(self):
        races = self._races()
        assert len(cs._stratified_sample(races, 5, "s")) == 5
        # asking for more than exist returns all, not a crash
        assert len(cs._stratified_sample(races, 9999, "s")) == len(races)


class TestGateReason:
    class _Proc:
        def __init__(self, out="", err=""):
            self.stdout, self.stderr = out, err

    def test_extracts_failing_critical_rule(self):
        proc = self._Proc(out="[FAIL] R19 [CRITICAL]: Hours out of range: "
                              "W5: 546min < 585min floor")
        r = cs._gate_reason(proc)
        assert "R19" in r and "Hours out of range" in r

    def test_extracts_exception(self):
        proc = self._Proc(err="Traceback...\nValueError: bad distance value")
        assert "ValueError" in cs._gate_reason(proc)

    def test_falls_back_when_opaque(self):
        assert cs._gate_reason(self._Proc(out="nothing useful")) \
            == "pipeline exited non-zero (gate blocked)"


class TestNormalizeFailure:
    def test_buckets_drop_race_specific_detail(self):
        a = cs._normalize_failure("preview FAIL: Zone Distribution")
        b = cs._normalize_failure("preview FAIL: Off Days")
        assert a == b  # both bucket to "preview fail"

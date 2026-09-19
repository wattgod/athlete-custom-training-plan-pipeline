"""Matti ruling 2026-09-17: every Motoren cycling athlete trains on %FTP.

An FTP anchor always wins over the metric the intake requested. RPE is legal
only on field-test cards and as the last-resort fallback for an athlete with
no power AND no HR anchor. Regression for Edward Shapiro's September block,
which shipped 100% RPE because his profile carried ftp_watts 270 alongside
requested_metric "rpe".
"""
import canonical_training_model as ctm


def _profile(**fitness):
    return {"fitness_markers": fitness}


def test_measured_ftp_wins_over_requested_rpe():
    control = ctm.determine_control(_profile(
        ftp_watts=270, power_basis="measured", training_metric="rpe",
        requested_metric="rpe"))
    assert control["control_metric"] == "power"
    assert control["control_basis"] == "ftp"
    assert control["ftp_watts"] == 270
    assert control["requested_metric"] == "rpe"  # recorded, not obeyed


def test_ftp_wins_over_requested_hr_even_with_lthr():
    control = ctm.determine_control(_profile(
        ftp_watts=250, power_basis="measured", training_metric="hr",
        requested_metric="hr", lthr=165))
    assert control["control_metric"] == "power"


def test_no_ftp_with_hr_anchor_never_falls_to_rpe():
    control = ctm.determine_control(_profile(
        ftp_watts=None, power_basis="none", training_metric="rpe",
        requested_metric="rpe", lthr=165))
    assert control["control_metric"] == "hr"
    assert control["control_basis"] == "lthr"


def test_no_anchor_at_all_is_the_only_rpe_path():
    control = ctm.determine_control(_profile(
        ftp_watts=None, power_basis="none", training_metric="rpe",
        requested_metric="rpe"))
    assert control["control_metric"] == "rpe"
    assert control["power_basis"] == "none"

from daily_avatar_run import _contract


def test_contract_fails_closed_on_needs_review_marker(tmp_path, monkeypatch):
    athlete_dir = tmp_path / "avatar"
    delivery_dir = tmp_path / "delivery"
    athlete_dir.mkdir()
    delivery_dir.mkdir()
    (athlete_dir / "NEEDS_REVIEW.txt").write_text("R19 weekly volume")

    # Keep the test focused on the durable compliance signal. The remaining
    # artifact gates may also fail in this intentionally minimal fixture.
    ok, failures = _contract(athlete_dir, delivery_dir)

    assert not ok
    assert "needs review: compliance gate flagged generated plan" in failures

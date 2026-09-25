"""The production image must contain the offline approval-preflight tools."""

from pathlib import Path


def test_dockerfile_ships_canonical_tp_package_dependencies():
    root = Path(__file__).resolve().parents[2]
    dockerfile = (root / "webhook" / "Dockerfile").read_text()
    for name in ("build_sealed_tp_plan_package.py", "build_tp_plan_payload.py",
                 "tp_polyline.py"):
        assert (root / "tools" / name).is_file()
        assert name in dockerfile

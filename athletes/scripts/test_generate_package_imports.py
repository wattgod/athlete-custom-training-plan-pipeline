"""Regression coverage for standalone replacement-plan generation imports."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_standalone_generator_exposes_repo_delivery_package(tmp_path):
    script = Path(__file__).with_name("generate_athlete_package.py").resolve()
    code = (
        "import importlib.util; "
        f"p={str(script)!r}; "
        "s=importlib.util.spec_from_file_location('gap_standalone', p); "
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        "import delivery.trainingpeaks.worker_service; print('ok')"
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"

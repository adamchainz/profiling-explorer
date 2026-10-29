from __future__ import annotations

import cProfile
import functools
import io
import json
import os
import pstats
import subprocess
import sys
import tempfile
from pathlib import Path

from profiling_explorer.views import Profile, build_profile


@functools.cache
def make_test_profile(profiler: str) -> Profile:
    if profiler == "cProfile":
        return _make_cprofile_profile()
    else:
        return _make_sampling_profile()


def _make_cprofile_profile() -> Profile:
    profiler = cProfile.Profile()
    profiler.enable()
    _workload()
    profiler.disable()
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    return build_profile(stats, "test.pstats")


def _make_sampling_profile() -> Profile:
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as tmp_dir:
        script = Path(tmp_dir) / "workload.py"
        script.write_text("from tests.utils import _workload\n_workload()\n")
        output = Path(tmp_dir) / "test.pstats"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "profiling.sampling",
                "run",
                "--pstats",
                "-o",
                str(output),
                str(script),
            ],
            check=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
        )
        stats = pstats.Stats(str(output))
    return build_profile(stats, "test.pstats")


def _workload() -> None:
    data = [{"id": i, "value": i * i} for i in range(100_000)]
    _roundtrip(data)
    _roundtrip(data)


def _roundtrip(data: object) -> None:
    serialized = json.dumps(data)
    json.loads(serialized)

from __future__ import annotations

import cProfile
import functools
import io
import json
import pstats

from profiling_explorer.views import Profile, build_profile


@functools.cache
def make_test_profile() -> Profile:
    profiler = cProfile.Profile()
    profiler.enable()
    _workload()
    profiler.disable()
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    return build_profile(stats, "test.pstats")


def _workload() -> None:
    data = [{"id": i, "value": i * i} for i in range(100_000)]
    serialized = json.dumps(data)
    json.loads(serialized)

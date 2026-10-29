from __future__ import annotations

import pytest

from profiling_explorer import views
from tests.utils import make_test_profile


def pytest_addoption(parser):
    parser.addoption(
        "--profiler",
        choices=["cProfile", "profiling.sampling"],
        default="cProfile",
        help="Profiler used to generate the test profile.",
    )


@pytest.fixture(scope="module", autouse=True)
def profile(request):
    views.profile = make_test_profile(request.config.getoption("profiler"))
    yield views.profile
    views.profile = None  # type: ignore[assignment]

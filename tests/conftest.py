from __future__ import annotations

import pytest

from profiling_explorer import views
from tests.utils import make_test_profile


@pytest.fixture(scope="module", autouse=True)
def profile(db=None):
    views.profile = make_test_profile()
    yield views.profile
    views.profile = None  # type: ignore[assignment]

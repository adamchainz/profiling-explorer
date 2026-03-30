from __future__ import annotations

import subprocess
import sys

from profiling_explorer import __main__  # noqa: F401


def test_main_help_subprocess():
    proc = subprocess.run(
        [sys.executable, "-m", "profiling_explorer", "--help"],
        check=True,
        capture_output=True,
    )

    assert proc.stdout.startswith(b"usage: profiling-explorer ")

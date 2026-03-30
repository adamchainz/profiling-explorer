from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog="profiling-explorer", allow_abbrev=False)
    parser.suggest_on_error = True  # type: ignore[attr-defined]
    parser.add_argument("filename", help="The pstats data file to explore.")
    args = parser.parse_args(argv)

    return 0

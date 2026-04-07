from __future__ import annotations

import argparse
import os
import pstats
import sys
from collections.abc import Sequence

import django
from django.core.management import call_command

from profiling_explorer import settings, views


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog="profiling-explorer", allow_abbrev=False)
    parser.suggest_on_error = True
    parser.add_argument(
        "filename",
        metavar="FILE",
        help="The pstats data file to explore.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8099,
        metavar="PORT",
        help="Port for the local web server (default: 8099).",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        default=False,
        help="Run in development mode (enables server reload and debug mode).",
    )
    args = parser.parse_args(argv)

    settings.DEBUG = args.dev  # type: ignore[attr-defined]

    views.profile = views.build_profile(pstats.Stats(args.filename), args.filename)

    os.environ["DJANGO_SETTINGS_MODULE"] = "profiling_explorer.settings"

    django.setup()

    call_command(
        "runserver",
        f"127.0.0.1:{args.port}",
        "--nothreading",
        *(() if args.dev else ("--noreload",)),
    )

    return 0

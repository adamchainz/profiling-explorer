from __future__ import annotations

import argparse
import os
import pstats
import shlex
import sys
from collections.abc import Sequence

import django
from django.core.management import call_command

from profiling_explorer import settings, views
from profiling_explorer.config import ConfigError, config_path, load_config


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
        "--editor",
        metavar="COMMAND",
        help=(
            "Command to open source files in your editor, such as 'code' or "
            + "'pycharm'. Overrides the 'editor' setting in "
            + "~/.config/profiling-explorer/config.toml. By default, "
            + "profiling-explorer detects a running editor, or uses $VISUAL "
            + "or $EDITOR."
        ),
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        default=False,
        help="Run in development mode (enables server reload and debug mode).",
    )
    args = parser.parse_args(argv)

    try:
        views.editor = _get_editor(args.editor)
    except ConfigError as exc:
        parser.error(str(exc))

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


def _get_editor(cli_editor: str | None) -> str | None:
    editor: object
    if cli_editor is not None:
        editor = cli_editor
    else:
        path = config_path()
        editor = load_config(path).get("editor")
        if editor is None:
            return None
        if not isinstance(editor, str):
            raise ConfigError(f"'editor' in {path} must be a string.")

    try:
        shlex.split(editor)
    except ValueError as exc:
        raise ConfigError(f"Invalid editor command {editor!r}: {exc}") from exc
    return editor

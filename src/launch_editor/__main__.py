from __future__ import annotations

import argparse
import re
import shlex
import sys
from collections.abc import Sequence

from launch_editor import LaunchEditorError, guess_editor, launch_editor

_POSITION_RE = re.compile(r":(\d+)(?::(\d+))?$")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m launch_editor",
        description="Open a file in your editor.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "file",
        metavar="FILE",
        nargs="?",
        help=(
            "The file to open, optionally followed by :LINE or :LINE:COLUMN, "
            + "like example.py:12:4."
        ),
    )
    parser.add_argument(
        "--editor",
        help="The editor command to use, instead of guessing.",
    )
    parser.add_argument(
        "--guess",
        action="store_true",
        help="Print the editor command that would be used, and exit.",
    )
    args = parser.parse_args(argv)

    if args.guess:
        command = guess_editor(args.editor)
        if not command:
            print("No editor found.", file=sys.stderr)
            return 1
        print(shlex.join(command))
        return 0

    if args.file is None:
        parser.error("FILE is required.")

    filename = args.file
    line = column = None
    match = _POSITION_RE.search(filename)
    if match:
        filename = filename[: match.start()]
        line = int(match[1])
        if match[2] is not None:
            column = int(match[2])

    try:
        process = launch_editor(filename, line, column, editor=args.editor)
    except LaunchEditorError as exc:
        print(exc, file=sys.stderr)
        return 1

    # Wait, so terminal editors keep the terminal, and to report failures.
    return process.wait()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

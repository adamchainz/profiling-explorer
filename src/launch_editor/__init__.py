"""
Open files in the user’s editor, at a given line and column.

A Python port of the launch-editor npm package:
https://github.com/vitejs/launch-editor

Copyright (c) 2026 Adam Johnson
Copyright (c) 2017-present, Yuxi (Evan) You
Copyright (c) 2015-present, Facebook, Inc.

Released under the MIT License, see the LICENSE file.
"""

from __future__ import annotations

import logging
import ntpath
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import threading
from collections.abc import Sequence
from pathlib import Path, PureWindowsPath

__all__ = [
    "LaunchEditorError",
    "guess_editor",
    "launch_editor",
    "position_args",
]

logger = logging.getLogger(__name__)


class LaunchEditorError(Exception):
    """
    Raised when the editor cannot be launched.
    """


# Process names, as listed by `ps` on macOS, mapped to the command that opens
# files in that editor. Where there’s no command-line launcher, the process
# path maps to itself.
MACOS_EDITORS = {
    "/Applications/Atom.app/Contents/MacOS/Atom": "atom",
    "/Applications/Atom Beta.app/Contents/MacOS/Atom Beta": (
        "/Applications/Atom Beta.app/Contents/MacOS/Atom Beta"
    ),
    "/Applications/Brackets.app/Contents/MacOS/Brackets": "brackets",
    "/Applications/Sublime Text.app/Contents/MacOS/Sublime Text": (
        "/Applications/Sublime Text.app/Contents/SharedSupport/bin/subl"
    ),
    "/Applications/Sublime Text.app/Contents/MacOS/sublime_text": (
        "/Applications/Sublime Text.app/Contents/SharedSupport/bin/subl"
    ),
    "/Applications/Sublime Text 2.app/Contents/MacOS/Sublime Text 2": (
        "/Applications/Sublime Text 2.app/Contents/SharedSupport/bin/subl"
    ),
    "/Applications/Sublime Text Dev.app/Contents/MacOS/Sublime Text": (
        "/Applications/Sublime Text Dev.app/Contents/SharedSupport/bin/subl"
    ),
    "/Applications/Visual Studio Code.app/Contents/MacOS/Code": "code",
    "/Applications/Visual Studio Code.app/Contents/MacOS/Electron": "code",
    "/Applications/Visual Studio Code - Insiders.app/Contents/MacOS/Code - Insiders": (
        "code-insiders"
    ),
    "/Applications/Visual Studio Code - Insiders.app/Contents/MacOS/Electron": (
        "code-insiders"
    ),
    "/Applications/VSCodium.app/Contents/MacOS/Electron": "codium",
    "/Applications/Cursor.app/Contents/MacOS/Cursor": "cursor",
    "/Applications/Trae.app/Contents/MacOS/Electron": "trae",
    "/Applications/Antigravity.app/Contents/MacOS/Electron": "antigravity",
    "/Applications/AppCode.app/Contents/MacOS/appcode": (
        "/Applications/AppCode.app/Contents/MacOS/appcode"
    ),
    "/Applications/CLion.app/Contents/MacOS/clion": (
        "/Applications/CLion.app/Contents/MacOS/clion"
    ),
    "/Applications/IntelliJ IDEA.app/Contents/MacOS/idea": (
        "/Applications/IntelliJ IDEA.app/Contents/MacOS/idea"
    ),
    "/Applications/IntelliJ IDEA Ultimate.app/Contents/MacOS/idea": (
        "/Applications/IntelliJ IDEA Ultimate.app/Contents/MacOS/idea"
    ),
    "/Applications/IntelliJ IDEA Community Edition.app/Contents/MacOS/idea": (
        "/Applications/IntelliJ IDEA Community Edition.app/Contents/MacOS/idea"
    ),
    "/Applications/PhpStorm.app/Contents/MacOS/phpstorm": (
        "/Applications/PhpStorm.app/Contents/MacOS/phpstorm"
    ),
    "/Applications/PyCharm.app/Contents/MacOS/pycharm": (
        "/Applications/PyCharm.app/Contents/MacOS/pycharm"
    ),
    "/Applications/PyCharm CE.app/Contents/MacOS/pycharm": (
        "/Applications/PyCharm CE.app/Contents/MacOS/pycharm"
    ),
    "/Applications/RubyMine.app/Contents/MacOS/rubymine": (
        "/Applications/RubyMine.app/Contents/MacOS/rubymine"
    ),
    "/Applications/WebStorm.app/Contents/MacOS/webstorm": (
        "/Applications/WebStorm.app/Contents/MacOS/webstorm"
    ),
    "/Applications/MacVim.app/Contents/MacOS/MacVim": "mvim",
    "/Applications/GoLand.app/Contents/MacOS/goland": (
        "/Applications/GoLand.app/Contents/MacOS/goland"
    ),
    "/Applications/Rider.app/Contents/MacOS/rider": (
        "/Applications/Rider.app/Contents/MacOS/rider"
    ),
    "/Applications/Zed.app/Contents/MacOS/zed": "zed",
}

# Process names, as listed by `ps` on Linux, mapped to the command that opens
# files in that editor. Order matters: earlier entries take precedence.
LINUX_EDITORS = {
    "atom": "atom",
    "Brackets": "brackets",
    "code-insiders": "code-insiders",
    "code": "code",
    "vscodium": "vscodium",
    "codium": "codium",
    "cursor": "cursor",
    "trae": "trae",
    "antigravity": "antigravity",
    "emacs": "emacs",
    "gvim": "gvim",
    "idea": "idea",
    "idea.sh": "idea",
    "phpstorm": "phpstorm",
    "phpstorm.sh": "phpstorm",
    "pycharm": "pycharm",
    "pycharm.sh": "pycharm",
    "rubymine": "rubymine",
    "rubymine.sh": "rubymine",
    "sublime_text": "subl",
    "vim": "vim",
    "webstorm": "webstorm",
    "webstorm.sh": "webstorm",
    "goland": "goland",
    "goland.sh": "goland",
    "rider": "rider",
    "rider.sh": "rider",
    "zed": "zed",
}

# Executable names of editors on Windows. A running one is launched by its
# full path.
WINDOWS_EDITORS = [
    "Brackets.exe",
    "Code.exe",
    "Code - Insiders.exe",
    "VSCodium.exe",
    "Cursor.exe",
    "atom.exe",
    "sublime_text.exe",
    "notepad++.exe",
    "clion.exe",
    "clion64.exe",
    "idea.exe",
    "idea64.exe",
    "phpstorm.exe",
    "phpstorm64.exe",
    "pycharm.exe",
    "pycharm64.exe",
    "rubymine.exe",
    "rubymine64.exe",
    "webstorm.exe",
    "webstorm64.exe",
    "goland.exe",
    "goland64.exe",
    "rider.exe",
    "rider64.exe",
    "Trae.exe",
    "zed.exe",
    "Antigravity.exe",
]

# Editors that run in the terminal, taking it over until they exit.
TERMINAL_EDITORS = {"emacs", "hx", "micro", "nano", "nvim", "vi", "vim"}


def guess_editor(editor: str | Sequence[str] | None = None) -> list[str]:
    """
    Return the command for the user’s editor, or an empty list if none is
    found.

    The editor is chosen from, in order:

    1. The ``editor`` argument.
    2. The ``LAUNCH_EDITOR`` environment variable.
    3. A supported editor that is currently running.
    4. The ``VISUAL`` environment variable.
    5. The ``EDITOR`` environment variable.
    """
    if editor:
        if isinstance(editor, str):
            return _split_command(editor)
        return list(editor)

    launch_editor_env = os.environ.get("LAUNCH_EDITOR")
    if launch_editor_env:
        # Like the npm package, treat this as a single command, which is often
        # a script that receives the file, line, and column.
        return [launch_editor_env]

    running = _guess_running_editor()
    if running is not None:
        return [running]

    for var in ("VISUAL", "EDITOR"):
        value = os.environ.get(var)
        if value:
            return _split_command(value)

    return []


def _split_command(command: str) -> list[str]:
    return shlex.split(command, posix=(sys.platform != "win32"))


def _guess_running_editor() -> str | None:
    if sys.platform == "darwin":
        args = ["ps", "x", "-o", "comm="]
    elif sys.platform == "win32":
        args = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
                + "Get-CimInstance -Query "
                + '"select executablepath from win32_process '
                + 'where executablepath is not null" '
                + "| % { $_.ExecutablePath }"
            ),
        ]
    elif sys.platform == "linux":
        args = ["ps", "x", "--no-heading", "-o", "comm", "--sort=comm"]
    else:
        return None

    try:
        output = subprocess.run(
            args,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None

    if sys.platform == "darwin":
        return _editor_from_macos_processes(output)
    elif sys.platform == "win32":
        return _editor_from_windows_processes(output)
    return _editor_from_linux_processes(output)


def _editor_from_macos_processes(output: str) -> str | None:
    processes = output.splitlines()
    for process_name, command in MACOS_EDITORS.items():
        if process_name in processes:
            return command
        # Find editors installed outside /Applications.
        suffix = process_name.removeprefix("/Applications")
        if suffix in output:
            # Use the command-line launcher, if there is one.
            if command != process_name:
                return command
            # Otherwise, use the running process’ path.
            for process in processes:
                if process.endswith(suffix):
                    return process
    return None


def _editor_from_windows_processes(output: str) -> str | None:
    for line in output.splitlines():
        path = line.strip()
        if PureWindowsPath(path).name in WINDOWS_EDITORS:
            return path
    return None


def _editor_from_linux_processes(output: str) -> str | None:
    processes = set(output.split())
    for process_name, command in LINUX_EDITORS.items():
        if process_name in processes:
            return command
    return None


# Editor names, grouped by how they take a position.
_COLON_POSITION_EDITORS = {
    "Atom",
    "Atom Beta",
    "atom",
    "charm",
    "hx",
    "subl",
    "sublime",
    "sublime_text",
    "wstorm",
    "zed",
}
_VSCODE_LIKE_EDITORS = {
    "Code",
    "Code - Insiders",
    "VSCodium",
    "antigravity",
    "code",
    "code-insiders",
    "codium",
    "cursor",
    "trae",
    "vscodium",
}
_JETBRAINS_EDITORS = {
    "appcode",
    "clion",
    "clion64",
    "goland",
    "goland64",
    "idea",
    "idea64",
    "phpstorm",
    "phpstorm64",
    "pycharm",
    "pycharm64",
    "rider",
    "rider64",
    "rubymine",
    "rubymine64",
    "webstorm",
    "webstorm64",
}


def position_args(
    editor: str, filename: str, line: int, column: int | None = None
) -> list[str]:
    """
    Return the arguments to open ``filename`` at ``line`` and ``column`` in
    the given editor command.
    """
    if column is None:
        column = 1
    name = PureWindowsPath(editor).name if "\\" in editor else Path(editor).name
    name = re.sub(r"\.(exe|cmd|bat)$", "", name, flags=re.IGNORECASE)

    if name in _COLON_POSITION_EDITORS:
        return [f"{filename}:{line}:{column}"]
    if name == "notepad++":
        return [f"-n{line}", f"-c{column}", filename]
    if name in {"vim", "mvim", "nvim"}:
        return [f"+call cursor({line}, {column})", filename]
    if name in {"joe", "gvim", "vi"}:
        return [f"+{line}", filename]
    if name in {"emacs", "emacsclient", "micro"}:
        return [f"+{line}:{column}", filename]
    if name == "nano":
        return [f"+{line},{column}", filename]
    if name in {"rmate", "mate", "mine"}:
        return ["--line", str(line), filename]
    if name in _VSCODE_LIKE_EDITORS:
        return ["-r", "-g", f"{filename}:{line}:{column}"]
    if name in _JETBRAINS_EDITORS:
        return ["--line", str(line), "--column", str(column), filename]

    if os.environ.get("LAUNCH_EDITOR"):
        return [filename, str(line), str(column)]

    # For other editors, drop the position, since passing it incorrectly can
    # result in errors or confusing behaviour.
    return [filename]


_terminal_editor: subprocess.Popen[bytes] | None = None
_terminal_editor_lock = threading.Lock()


def launch_editor(
    filename: str | os.PathLike[str],
    line: int | None = None,
    column: int | None = None,
    *,
    editor: str | Sequence[str] | None = None,
) -> subprocess.Popen[bytes]:
    """
    Open ``filename`` in the user’s editor, at ``line`` and ``column`` if
    given.

    The editor is picked by :func:`guess_editor`, using ``editor`` if given.
    GUI editors are started in the background and this function returns
    immediately. Terminal editors, like Vim, take over the current terminal;
    while one is open, further calls to open a terminal editor fail.

    Returns the editor process. Raises :class:`LaunchEditorError` if the
    editor cannot be launched.
    """
    global _terminal_editor

    filename = os.fspath(filename)

    if sys.platform == "win32" and ntpath.abspath(filename).startswith("\\\\"):
        raise LaunchEditorError(
            "UNC paths are not supported on Windows to avoid security issues."
        )

    if not os.path.exists(filename):
        raise LaunchEditorError(f"File does not exist: {filename}")

    command = guess_editor(editor)
    if not command:
        raise LaunchEditorError(
            "Could not find an editor. Set the LAUNCH_EDITOR, VISUAL, or EDITOR "
            + "environment variable."
        )
    editor_command, *args = command

    if (
        sys.platform == "linux"
        and filename.startswith("/mnt/")
        and "microsoft" in platform.release().lower()
    ):
        # Assume WSL is being used, and that the file is on the Windows file
        # system. Windows editors can translate the path, but only if it is
        # relative.
        filename = os.path.relpath(filename)

    if line is not None:
        args += position_args(editor_command, filename, line, column)
    else:
        args.append(filename)

    with _terminal_editor_lock:
        is_terminal = Path(editor_command).name in TERMINAL_EDITORS
        if is_terminal and _terminal_editor is not None:
            if _terminal_editor.poll() is None:
                raise LaunchEditorError(
                    f"{Path(editor_command).name} is already open in the "
                    + "terminal. Close it first."
                )
            _terminal_editor = None

        process = _run(editor_command, args)

        if is_terminal:
            _terminal_editor = process

    threading.Thread(
        name=f"launch_editor-wait-{process.pid}",
        target=_report_failure,
        args=(process, editor_command, filename),
        daemon=True,
    ).start()
    return process


def _run(editor: str, args: list[str]) -> subprocess.Popen[bytes]:
    executable = shutil.which(editor) or editor
    try:
        if sys.platform == "win32" and executable.lower().endswith((".cmd", ".bat")):
            # Windows runs batch files, such as VS Code’s code.cmd, with
            # cmd.exe, which applies its own parsing to the command line. Quote
            # every argument, and reject characters that cmd.exe would still
            # interpret inside quotes, to prevent command injection.
            return subprocess.Popen(_cmd_command_line([executable, *args]))
        return subprocess.Popen([executable, *args])
    except OSError as exc:
        raise LaunchEditorError(f"Could not run {editor!r}: {exc}") from exc


def _cmd_command_line(args: list[str]) -> str:
    for arg in args:
        if any(char in arg for char in '"%!\r\n'):
            raise LaunchEditorError(
                f"Cannot safely pass {arg!r} to a batch file editor command."
            )
    return " ".join(f'"{arg}"' for arg in args)


def _report_failure(
    process: subprocess.Popen[bytes], editor: str, filename: str
) -> None:
    returncode = process.wait()
    if returncode:
        logger.warning(
            "Could not open %s in the editor: %r exited with code %d.",
            os.path.basename(filename),
            editor,
            returncode,
        )

"""
Open files in the user's editor, at a given line.

Ported from launch-editor, as used by Vite:
https://github.com/vitejs/launch-editor
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import threading
from pathlib import Path

# Process names, as listed by `ps`, mapped to the command that opens a file
# in that editor.
LINUX_EDITORS = {
    "antigravity": "antigravity",
    "code": "code",
    "code-insiders": "code-insiders",
    "codium": "codium",
    "cursor": "cursor",
    "emacs": "emacs",
    "goland": "goland",
    "goland.sh": "goland",
    "gvim": "gvim",
    "idea": "idea",
    "idea.sh": "idea",
    "pycharm": "pycharm",
    "pycharm.sh": "pycharm",
    "rider": "rider",
    "rider.sh": "rider",
    "sublime_text": "subl",
    "vim": "vim",
    "vscodium": "vscodium",
    "webstorm": "webstorm",
    "webstorm.sh": "webstorm",
    "zed": "zed",
}

MACOS_EDITORS = {
    "/Applications/Antigravity.app/Contents/MacOS/Electron": "antigravity",
    "/Applications/Cursor.app/Contents/MacOS/Cursor": "cursor",
    "/Applications/GoLand.app/Contents/MacOS/goland": (
        "/Applications/GoLand.app/Contents/MacOS/goland"
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
    "/Applications/MacVim.app/Contents/MacOS/MacVim": "mvim",
    "/Applications/PyCharm.app/Contents/MacOS/pycharm": (
        "/Applications/PyCharm.app/Contents/MacOS/pycharm"
    ),
    "/Applications/PyCharm CE.app/Contents/MacOS/pycharm": (
        "/Applications/PyCharm CE.app/Contents/MacOS/pycharm"
    ),
    "/Applications/Rider.app/Contents/MacOS/rider": (
        "/Applications/Rider.app/Contents/MacOS/rider"
    ),
    "/Applications/Sublime Text.app/Contents/MacOS/Sublime Text": (
        "/Applications/Sublime Text.app/Contents/SharedSupport/bin/subl"
    ),
    "/Applications/Sublime Text.app/Contents/MacOS/sublime_text": (
        "/Applications/Sublime Text.app/Contents/SharedSupport/bin/subl"
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
    "/Applications/WebStorm.app/Contents/MacOS/webstorm": (
        "/Applications/WebStorm.app/Contents/MacOS/webstorm"
    ),
    "/Applications/Zed.app/Contents/MacOS/zed": "zed",
}

# Editors that run in the terminal, and so take over the server's terminal
# until they exit.
TERMINAL_EDITORS = {"emacs", "hx", "micro", "nano", "nvim", "vi", "vim"}


class EditorError(Exception):
    pass


def guess_editor(specified: str | None) -> list[str]:
    """
    Return the command to run the user's editor, or [] if none is found.
    """
    if specified:
        return shlex.split(specified)

    running = _guess_running_editor()
    if running is not None:
        return [running]

    for var in ("VISUAL", "EDITOR"):
        value = os.environ.get(var)
        if value:
            return shlex.split(value)

    return []


def _guess_running_editor() -> str | None:
    if sys.platform == "darwin":
        ps_args = ["ps", "x", "-o", "comm="]
    elif sys.platform == "linux":
        ps_args = ["ps", "x", "--no-heading", "-o", "comm", "--sort=comm"]
    else:
        return None

    try:
        output = subprocess.run(
            ps_args,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None

    if sys.platform == "darwin":
        return editor_from_macos_processes(output)
    return editor_from_linux_processes(output)


def editor_from_macos_processes(output: str) -> str | None:
    processes = output.splitlines()
    for process_name, command in MACOS_EDITORS.items():
        if process_name in processes:
            return command
        # Also find apps installed outside /Applications
        suffix = process_name.removeprefix("/Applications")
        for process in processes:
            if process.endswith(suffix):
                return command if command != process_name else process
    return None


def editor_from_linux_processes(output: str) -> str | None:
    processes = set(output.split())
    for process_name, command in LINUX_EDITORS.items():
        if process_name in processes:
            return command
    return None


# Editor command names, grouped by how they take a line number.
_COLON_LINE_EDITORS = {"charm", "subl", "sublime", "sublime_text", "zed"}
_VSCODE_LIKE_EDITORS = {
    "Code",
    "Code - Insiders",
    "VSCodium",
    "antigravity",
    "code",
    "code-insiders",
    "codium",
    "cursor",
    "vscodium",
}
_LINE_OPTION_EDITORS = {
    "clion",
    "goland",
    "idea",
    "mate",
    "mine",
    "phpstorm",
    "pycharm",
    "rider",
    "rmate",
    "rubymine",
    "webstorm",
}
_PLUS_LINE_EDITORS = {
    "emacs",
    "emacsclient",
    "gvim",
    "hx",
    "joe",
    "micro",
    "mvim",
    "nano",
    "nvim",
    "vi",
    "vim",
}


def position_args(editor: str, filename: str, line: int) -> list[str]:
    """
    Return the arguments to open filename at line in the given editor.
    """
    name = Path(editor).name
    if name.lower().endswith((".exe", ".cmd", ".bat")):
        name = name[:-4]

    if name in _COLON_LINE_EDITORS:
        return [f"{filename}:{line}"]
    if name in _VSCODE_LIKE_EDITORS:
        return ["--reuse-window", "--goto", f"{filename}:{line}"]
    # JetBrains IDEs have '64' suffixed variants on Windows
    if name.removesuffix("64") in _LINE_OPTION_EDITORS:
        return ["--line", str(line), filename]
    if name in _PLUS_LINE_EDITORS:
        return [f"+{line}", filename]
    if name == "notepad++":
        return [f"-n{line}", filename]

    # Unknown editor: open the file without a line number, since passing it
    # in the wrong form can cause errors or confusing behaviour.
    return [filename]


_terminal_editor: subprocess.Popen[bytes] | None = None


def launch_editor(filename: str, line: int, specified: str | None) -> None:
    """
    Open filename at line in the user's editor, raising EditorError on
    failure.
    """
    global _terminal_editor

    command = guess_editor(specified)
    if not command:
        raise EditorError(
            "Could not find your editor. Set $VISUAL or $EDITOR, or pass --editor."
        )

    editor, *args = command
    args += position_args(editor, filename, line)
    is_terminal = Path(editor).name in TERMINAL_EDITORS

    if is_terminal and _terminal_editor is not None:
        if _terminal_editor.poll() is None:
            raise EditorError(
                f"{Path(editor).name} is already open in the profiling-explorer "
                + "terminal. Close it first."
            )
        _terminal_editor = None

    # Resolve e.g. 'code' to 'code.cmd' on Windows.
    executable = shutil.which(editor) or editor
    try:
        process = subprocess.Popen([executable, *args])
    except OSError as exc:
        raise EditorError(f"Could not run {editor!r}: {exc}") from exc

    if is_terminal:
        _terminal_editor = process
    else:
        threading.Thread(
            target=_report_failure,
            args=(process, editor),
            daemon=True,
        ).start()


def _report_failure(process: subprocess.Popen[bytes], editor: str) -> None:
    returncode = process.wait()
    if returncode:
        print(
            f"Editor command {editor!r} exited with code {returncode}.",
            file=sys.stderr,
        )

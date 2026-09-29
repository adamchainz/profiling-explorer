from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

import launch_editor as le
from launch_editor import (
    LaunchEditorError,
    guess_editor,
    launch_editor,
    position_args,
)


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    for var in ("LAUNCH_EDITOR", "VISUAL", "EDITOR"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(le, "_terminal_editor", None)


@pytest.fixture
def no_running_editor(monkeypatch):
    monkeypatch.setattr(le, "_guess_running_editor", lambda: None)


@pytest.fixture
def popen():
    with mock.patch.object(subprocess, "Popen") as popen:
        popen.return_value.wait.return_value = 0
        popen.return_value.poll.return_value = None
        yield popen


@pytest.fixture
def example_file(tmp_path):
    path = tmp_path / "example.py"
    path.write_text("")
    return path


class TestGuessEditor:
    def test_editor_string(self):
        assert guess_editor("code --new-window") == ["code", "--new-window"]

    def test_editor_sequence(self):
        assert guess_editor(("my editor", "-x")) == ["my editor", "-x"]

    def test_editor_string_windows(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        assert guess_editor(r"C:\Tools\ed.exe -x") == [r"C:\Tools\ed.exe", "-x"]

    def test_editor_beats_everything(self, monkeypatch):
        monkeypatch.setenv("LAUNCH_EDITOR", "zed")
        monkeypatch.setattr(le, "_guess_running_editor", lambda: "subl")
        assert guess_editor("code") == ["code"]

    def test_launch_editor_env(self, monkeypatch):
        monkeypatch.setenv("LAUNCH_EDITOR", "/path/to/my script.sh")
        monkeypatch.setattr(le, "_guess_running_editor", lambda: "subl")
        assert guess_editor() == ["/path/to/my script.sh"]

    def test_running(self, monkeypatch):
        monkeypatch.setattr(le, "_guess_running_editor", lambda: "zed")
        monkeypatch.setenv("VISUAL", "vim")
        assert guess_editor() == ["zed"]

    def test_visual(self, monkeypatch, no_running_editor):
        monkeypatch.setenv("VISUAL", "code --wait")
        monkeypatch.setenv("EDITOR", "vim")
        assert guess_editor() == ["code", "--wait"]

    def test_editor_env(self, monkeypatch, no_running_editor):
        monkeypatch.setenv("EDITOR", "vim")
        assert guess_editor() == ["vim"]

    def test_none(self, no_running_editor):
        assert guess_editor() == []


class TestGuessRunningEditor:
    def run_result(self, stdout: str) -> Any:
        return mock.patch.object(
            subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, stdout=stdout),
        )

    def test_macos(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        with self.run_result("/Applications/Zed.app/Contents/MacOS/zed\n") as run:
            assert le._guess_running_editor() == "zed"
        assert run.call_args.args[0] == ["ps", "x", "-o", "comm="]

    def test_linux(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        with self.run_result("bash\ncode\n") as run:
            assert le._guess_running_editor() == "code"
        assert run.call_args.args[0][:2] == ["ps", "x"]

    def test_windows(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        path = r"C:\Program Files\Microsoft VS Code\Code.exe"
        with self.run_result(f"C:\\Windows\\explorer.exe\r\n{path}\r\n") as run:
            assert le._guess_running_editor() == path
        assert run.call_args.args[0][0] == "powershell"

    def test_other_platform(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "freebsd14")
        with mock.patch.object(subprocess, "run") as run:
            assert le._guess_running_editor() is None
        run.assert_not_called()

    def test_command_missing(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        with mock.patch.object(subprocess, "run", side_effect=FileNotFoundError):
            assert le._guess_running_editor() is None

    def test_command_fails(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        error = subprocess.CalledProcessError(1, ["ps"])
        with mock.patch.object(subprocess, "run", side_effect=error):
            assert le._guess_running_editor() is None


class TestEditorFromMacosProcesses:
    def test_exact_path(self):
        output = "\n".join(
            [
                "/sbin/launchd",
                "/Applications/Visual Studio Code.app/Contents/MacOS/Code",
                "/usr/sbin/cfprefsd",
            ]
        )
        assert le._editor_from_macos_processes(output) == "code"

    def test_outside_applications_uses_command(self):
        output = "/sbin/launchd\n/Users/me/dev/Atom.app/Contents/MacOS/Atom\n"
        assert le._editor_from_macos_processes(output) == "atom"

    def test_outside_applications_uses_running_path(self):
        running = "/Users/me/dev/CLion.app/Contents/MacOS/clion"
        output = f"/sbin/launchd\n{running}\n"
        assert le._editor_from_macos_processes(output) == running

    def test_outside_applications_path_not_at_end(self):
        output = "/Users/me/dev/CLion.app/Contents/MacOS/clion-helper\n"
        assert le._editor_from_macos_processes(output) is None

    def test_none(self):
        output = "/sbin/launchd\n/usr/sbin/cfprefsd\n"
        assert le._editor_from_macos_processes(output) is None


class TestEditorFromWindowsProcesses:
    def test_found(self):
        path = r"C:\Program Files\Microsoft VS Code\Code.exe"
        output = f"C:\\Windows\\System32\\svchost.exe\r\n{path}"
        assert le._editor_from_windows_processes(output) == path

    def test_none(self):
        output = "C:\\Windows\\System32\\svchost.exe\r\nC:\\Windows\\explorer.exe"
        assert le._editor_from_windows_processes(output) is None


class TestEditorFromLinuxProcesses:
    def test_found(self):
        assert le._editor_from_linux_processes("systemd\ncode\nbash\n") == "code"

    def test_sublime_text(self):
        assert le._editor_from_linux_processes("systemd\nsublime_text\n") == "subl"

    def test_order(self):
        output = "systemd\ncode-insiders\n"
        assert le._editor_from_linux_processes(output) == "code-insiders"

    def test_no_substring_match(self):
        assert le._editor_from_linux_processes("vim-server\n") is None

    def test_none(self):
        assert le._editor_from_linux_processes("systemd\nbash\nsshd\n") is None


class TestPositionArgs:
    @pytest.mark.parametrize(
        "editor",
        [
            "atom",
            "Atom",
            "Atom Beta",
            "subl",
            "sublime",
            "sublime_text",
            "wstorm",
            "charm",
            "zed",
            "hx",
        ],
    )
    def test_colon_position(self, editor):
        assert position_args(editor, "file", 10, 5) == ["file:10:5"]

    def test_notepad_plus_plus(self):
        assert position_args("notepad++", "file", 10, 5) == ["-n10", "-c5", "file"]

    @pytest.mark.parametrize("editor", ["vim", "mvim", "nvim"])
    def test_vim(self, editor):
        assert position_args(editor, "file", 10, 5) == [
            "+call cursor(10, 5)",
            "file",
        ]

    @pytest.mark.parametrize("editor", ["joe", "gvim", "vi"])
    def test_plus_line(self, editor):
        assert position_args(editor, "file", 10, 5) == ["+10", "file"]

    @pytest.mark.parametrize("editor", ["emacs", "emacsclient", "micro"])
    def test_plus_line_colon_column(self, editor):
        assert position_args(editor, "file", 10, 5) == ["+10:5", "file"]

    def test_nano(self):
        assert position_args("nano", "file", 10, 5) == ["+10,5", "file"]

    @pytest.mark.parametrize("editor", ["rmate", "mate", "mine"])
    def test_line_option(self, editor):
        assert position_args(editor, "file", 10, 5) == ["--line", "10", "file"]

    @pytest.mark.parametrize(
        "editor",
        [
            "code",
            "Code",
            "code-insiders",
            "Code - Insiders",
            "codium",
            "trae",
            "antigravity",
            "cursor",
            "vscodium",
            "VSCodium",
        ],
    )
    def test_vscode_like(self, editor):
        assert position_args(editor, "file", 10, 5) == ["-r", "-g", "file:10:5"]

    @pytest.mark.parametrize(
        "editor", ["idea", "idea64", "webstorm", "pycharm", "clion", "rider"]
    )
    def test_jetbrains(self, editor):
        assert position_args(editor, "file", 10, 5) == [
            "--line",
            "10",
            "--column",
            "5",
            "file",
        ]

    def test_column_defaults_to_1(self):
        assert position_args("code", "file", 10) == ["-r", "-g", "file:10:1"]

    def test_posix_path(self):
        assert position_args("/usr/local/bin/code", "file", 10, 5) == [
            "-r",
            "-g",
            "file:10:5",
        ]

    def test_windows_path(self):
        assert position_args(r"C:\path\Code.exe", "file", 10, 5) == [
            "-r",
            "-g",
            "file:10:5",
        ]

    def test_windows_path_notepad_plus_plus(self):
        assert position_args(r"C:\tools\notepad++.exe", "file", 10, 5) == [
            "-n10",
            "-c5",
            "file",
        ]

    def test_strips_extension_case_insensitively(self):
        assert position_args("code.CMD", "file", 10, 5) == ["-r", "-g", "file:10:5"]

    def test_unknown(self):
        assert position_args("unknown", "file", 10, 5) == ["file"]

    def test_unknown_with_launch_editor_env(self, monkeypatch):
        monkeypatch.setenv("LAUNCH_EDITOR", "my-script")
        assert position_args("my-script", "file", 10, 5) == ["file", "10", "5"]


class TestLaunchEditor:
    def test_gui_editor(self, popen, example_file):
        process = launch_editor(example_file, 10, 5, editor="zed")

        assert process is popen.return_value
        args = popen.call_args.args[0]
        assert Path(args[0]).name == "zed"
        assert args[1:] == [f"{example_file}:10:5"]
        assert le._terminal_editor is None

    def test_no_line(self, popen, example_file):
        launch_editor(example_file, editor=["code", "--new-window"])

        assert popen.call_args.args[0][1:] == ["--new-window", str(example_file)]

    def test_line_without_column(self, popen, example_file):
        launch_editor(example_file, 10, editor="code")

        assert popen.call_args.args[0][1:] == ["-r", "-g", f"{example_file}:10:1"]

    def test_resolves_executable(self, popen, example_file):
        with mock.patch.object(shutil, "which", return_value="/opt/bin/zed"):
            launch_editor(example_file, 1, editor="zed")

        assert popen.call_args.args[0][0] == "/opt/bin/zed"

    def test_missing_file(self, popen, tmp_path):
        with pytest.raises(LaunchEditorError, match="File does not exist"):
            launch_editor(tmp_path / "missing.py", editor="zed")
        popen.assert_not_called()

    def test_no_editor(self, popen, example_file, no_running_editor):
        with pytest.raises(LaunchEditorError, match="Could not find an editor"):
            launch_editor(example_file)
        popen.assert_not_called()

    def test_editor_not_found(self, example_file):
        with (
            mock.patch.object(subprocess, "Popen", side_effect=FileNotFoundError),
            pytest.raises(LaunchEditorError, match="Could not run 'nope'"),
        ):
            launch_editor(example_file, editor="nope")

    def test_real_process(self, example_file, caplog):
        # Use a real process, to check the failure reporting thread.
        command = [sys.executable, "-c", "import sys; sys.exit(3)"]
        with caplog.at_level(logging.WARNING, logger="launch_editor"):
            process = launch_editor(example_file, editor=command)
            for thread in threading.enumerate():
                if thread.name == f"launch_editor-wait-{process.pid}":
                    thread.join()

        assert process.returncode == 3
        assert caplog.messages == [
            f"Could not open example.py in the editor: {sys.executable!r} "
            + "exited with code 3."
        ]

    def test_report_failure_success(self, caplog):
        process = mock.Mock()
        process.wait.return_value = 0
        with caplog.at_level(logging.WARNING, logger="launch_editor"):
            le._report_failure(process, "zed", "/a.py")
        assert caplog.records == []

    def test_terminal_editor(self, popen, example_file):
        launch_editor(example_file, 10, 5, editor="vim")

        assert popen.call_args.args[0][1:] == ["+call cursor(10, 5)", str(example_file)]
        assert le._terminal_editor is popen.return_value

    def test_terminal_editor_already_open(self, popen, example_file, monkeypatch):
        running = mock.Mock()
        running.poll.return_value = None
        monkeypatch.setattr(le, "_terminal_editor", running)

        with pytest.raises(LaunchEditorError, match="vim is already open"):
            launch_editor(example_file, editor="vim")
        popen.assert_not_called()

    def test_terminal_editor_previous_exited(self, popen, example_file, monkeypatch):
        exited = mock.Mock()
        exited.poll.return_value = 0
        monkeypatch.setattr(le, "_terminal_editor", exited)

        launch_editor(example_file, editor="vim")

        assert le._terminal_editor is popen.return_value

    def test_gui_editor_while_terminal_editor_open(
        self, popen, example_file, monkeypatch
    ):
        running = mock.Mock()
        running.poll.return_value = None
        monkeypatch.setattr(le, "_terminal_editor", running)

        launch_editor(example_file, editor="code")

        popen.assert_called_once()
        assert le._terminal_editor is running

    def test_wsl_uses_relative_path(self, popen, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(platform, "release", lambda: "5.15.0-microsoft-WSL2")
        monkeypatch.setattr(os.path, "exists", lambda path: True)
        monkeypatch.chdir("/")

        launch_editor("/mnt/c/code/app.py", 3, editor="zed")

        assert popen.call_args.args[0][1:] == ["mnt/c/code/app.py:3:1"]

    def test_mnt_path_outside_wsl(self, popen, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(platform, "release", lambda: "6.1.0-generic")
        monkeypatch.setattr(os.path, "exists", lambda path: True)

        launch_editor("/mnt/c/code/app.py", 3, editor="zed")

        assert popen.call_args.args[0][1:] == ["/mnt/c/code/app.py:3:1"]


class TestLaunchEditorWindows:
    @pytest.fixture(autouse=True)
    def windows(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")

    def test_unc_path(self, popen):
        with pytest.raises(LaunchEditorError, match="UNC paths are not supported"):
            launch_editor(r"\\server\share\file.py", editor="code")
        popen.assert_not_called()

    def test_exe(self, popen, example_file):
        with mock.patch.object(shutil, "which", return_value=r"C:\z\zed.exe"):
            launch_editor(example_file, 2, editor="zed")

        assert popen.call_args.args[0] == [r"C:\z\zed.exe", f"{example_file}:2:1"]

    def test_batch_file(self, popen, example_file):
        with mock.patch.object(shutil, "which", return_value=r"C:\VS Code\code.CMD"):
            launch_editor(example_file, 2, editor="code")

        assert popen.call_args.args[0] == (
            rf'"C:\VS Code\code.CMD" "-r" "-g" "{example_file}:2:1"'
        )

    @pytest.mark.parametrize("char", ['"', "%", "!", "\n", "\r"])
    def test_batch_file_unsafe_argument(self, popen, tmp_path, char):
        path = tmp_path / f"a{char}b.py"
        with (
            mock.patch.object(os.path, "exists", return_value=True),
            mock.patch.object(shutil, "which", return_value=r"C:\bin\code.cmd"),
            pytest.raises(LaunchEditorError, match="Cannot safely pass"),
        ):
            launch_editor(path, editor="code")
        popen.assert_not_called()

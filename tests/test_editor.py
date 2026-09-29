from __future__ import annotations

import subprocess
import sys
from unittest import mock

import pytest

from profiling_explorer import editor
from profiling_explorer.editor import (
    EditorError,
    editor_from_linux_processes,
    editor_from_macos_processes,
    guess_editor,
    launch_editor,
    position_args,
)


@pytest.fixture(autouse=True)
def no_env_editor(monkeypatch):
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(editor, "_terminal_editor", None)


@pytest.fixture
def no_running_editor(monkeypatch):
    monkeypatch.setattr(editor, "_guess_running_editor", lambda: None)


class TestGuessEditor:
    def test_specified(self):
        assert guess_editor("code --new-window") == ["code", "--new-window"]

    def test_specified_beats_running(self, monkeypatch):
        monkeypatch.setattr(editor, "_guess_running_editor", lambda: "zed")
        assert guess_editor("code") == ["code"]

    def test_running(self, monkeypatch):
        monkeypatch.setattr(editor, "_guess_running_editor", lambda: "zed")
        monkeypatch.setenv("EDITOR", "vim")
        assert guess_editor(None) == ["zed"]

    def test_visual(self, monkeypatch, no_running_editor):
        monkeypatch.setenv("VISUAL", "code --wait")
        monkeypatch.setenv("EDITOR", "vim")
        assert guess_editor(None) == ["code", "--wait"]

    def test_editor(self, monkeypatch, no_running_editor):
        monkeypatch.setenv("EDITOR", "vim")
        assert guess_editor(None) == ["vim"]

    def test_none(self, no_running_editor):
        assert guess_editor(None) == []


class TestGuessRunningEditor:
    def test_linux(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        result = subprocess.CompletedProcess([], 0, stdout="bash\ncode\nps\n")
        with mock.patch.object(subprocess, "run", return_value=result) as run:
            assert editor._guess_running_editor() == "code"
        assert run.call_args.args[0][0] == "ps"

    def test_macos(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        result = subprocess.CompletedProcess(
            [], 0, stdout="/Applications/Zed.app/Contents/MacOS/zed\n"
        )
        with mock.patch.object(subprocess, "run", return_value=result):
            assert editor._guess_running_editor() == "zed"

    def test_other_platform(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        assert editor._guess_running_editor() is None

    def test_ps_fails(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        with mock.patch.object(subprocess, "run", side_effect=OSError):
            assert editor._guess_running_editor() is None


class TestEditorFromProcesses:
    def test_linux(self):
        assert editor_from_linux_processes("bash\npycharm.sh\n") == "pycharm"

    def test_linux_substring_does_not_match(self):
        assert editor_from_linux_processes("vim-server\n") is None

    def test_linux_none(self):
        assert editor_from_linux_processes("bash\nps\n") is None

    def test_macos_exact(self):
        output = "/Applications/Visual Studio Code.app/Contents/MacOS/Electron\n"
        assert editor_from_macos_processes(output) == "code"

    def test_macos_outside_applications_uses_cli(self):
        output = "/Users/me/Applications/Cursor.app/Contents/MacOS/Cursor\n"
        assert editor_from_macos_processes(output) == "cursor"

    def test_macos_outside_applications_uses_running_path(self):
        path = "/Users/me/Applications/PyCharm.app/Contents/MacOS/pycharm"
        assert editor_from_macos_processes(path + "\n") == path

    def test_macos_none(self):
        assert editor_from_macos_processes("/bin/zsh\n") is None


class TestPositionArgs:
    @pytest.mark.parametrize(
        ("command", "expected"),
        [
            ("code", ["--reuse-window", "--goto", "/a.py:3"]),
            ("/usr/bin/cursor", ["--reuse-window", "--goto", "/a.py:3"]),
            ("code.cmd", ["--reuse-window", "--goto", "/a.py:3"]),
            ("subl", ["/a.py:3"]),
            ("zed", ["/a.py:3"]),
            ("pycharm", ["--line", "3", "/a.py"]),
            ("pycharm64.exe", ["--line", "3", "/a.py"]),
            ("mate", ["--line", "3", "/a.py"]),
            ("vim", ["+3", "/a.py"]),
            ("nvim", ["+3", "/a.py"]),
            ("emacsclient", ["+3", "/a.py"]),
            ("notepad++.exe", ["-n3", "/a.py"]),
            ("unknown-editor", ["/a.py"]),
        ],
    )
    def test_editors(self, command, expected):
        assert position_args(command, "/a.py", 3) == expected


class TestLaunchEditor:
    def test_no_editor(self, no_running_editor):
        with pytest.raises(EditorError, match="Could not find your editor"):
            launch_editor("/a.py", 3, None)

    def test_gui_editor(self):
        with mock.patch.object(subprocess, "Popen") as popen:
            popen.return_value.wait.return_value = 0
            launch_editor("/a.py", 3, "zed --new")

        args = popen.call_args.args[0]
        assert args[0].endswith("zed")
        assert args[1:] == ["--new", "/a.py:3"]
        assert editor._terminal_editor is None

    def test_gui_editor_failure_reported(self, capsys):
        process = mock.Mock()
        process.wait.return_value = 1
        editor._report_failure(process, "zed")
        assert "'zed' exited with code 1" in capsys.readouterr().err

    def test_command_not_found(self):
        with (
            mock.patch.object(subprocess, "Popen", side_effect=FileNotFoundError),
            pytest.raises(EditorError, match="Could not run 'nope'"),
        ):
            launch_editor("/a.py", 3, "nope")

    def test_terminal_editor(self):
        with mock.patch.object(subprocess, "Popen") as popen:
            launch_editor("/a.py", 3, "vim")

        assert popen.call_args.args[0][1:] == ["+3", "/a.py"]
        assert editor._terminal_editor is popen.return_value

    def test_terminal_editor_already_open(self, monkeypatch):
        running = mock.Mock()
        running.poll.return_value = None
        monkeypatch.setattr(editor, "_terminal_editor", running)

        with (
            mock.patch.object(subprocess, "Popen") as popen,
            pytest.raises(EditorError, match="vim is already open"),
        ):
            launch_editor("/a.py", 3, "vim")

        popen.assert_not_called()

    def test_terminal_editor_previous_exited(self, monkeypatch):
        exited = mock.Mock()
        exited.poll.return_value = 0
        monkeypatch.setattr(editor, "_terminal_editor", exited)

        with mock.patch.object(subprocess, "Popen") as popen:
            launch_editor("/a.py", 3, "vim")

        assert editor._terminal_editor is popen.return_value

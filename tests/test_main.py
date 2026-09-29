from __future__ import annotations

import subprocess
import sys
from unittest import mock

import pytest

import launch_editor as le
from launch_editor import __main__ as main_module
from launch_editor.__main__ import main


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("LAUNCH_EDITOR", "VISUAL", "EDITOR"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(le, "_guess_running_editor", lambda: None)


def test_help_subprocess():
    proc = subprocess.run(
        [sys.executable, "-m", "launch_editor", "--help"],
        check=True,
        capture_output=True,
    )

    assert proc.stdout.startswith(b"usage: python -m launch_editor ")


def test_guess(capsys, monkeypatch):
    monkeypatch.setenv("VISUAL", "code --wait")
    assert main(["--guess"]) == 0
    assert capsys.readouterr().out == "code --wait\n"


def test_guess_editor_option(capsys):
    assert main(["--guess", "--editor", "zed"]) == 0
    assert capsys.readouterr().out == "zed\n"


def test_guess_none(capsys):
    assert main(["--guess"]) == 1
    assert capsys.readouterr().err == "No editor found.\n"


def test_file_required(capsys):
    with pytest.raises(SystemExit):
        main([])
    assert "FILE is required." in capsys.readouterr().err


@pytest.mark.parametrize(
    ("arg", "expected"),
    [
        ("a.py", ("a.py", None, None)),
        ("a.py:12", ("a.py", 12, None)),
        ("a.py:12:4", ("a.py", 12, 4)),
        ("C:/a.py:12", ("C:/a.py", 12, None)),
    ],
)
def test_open(arg, expected):
    with mock.patch.object(main_module, "launch_editor") as launch:
        launch.return_value.wait.return_value = 0
        assert main([arg, "--editor", "zed"]) == 0

    launch.assert_called_once_with(*expected, editor="zed")


def test_open_returns_editor_exit_code():
    with mock.patch.object(main_module, "launch_editor") as launch:
        launch.return_value.wait.return_value = 2
        assert main(["a.py"]) == 2


def test_open_error(capsys, tmp_path):
    assert main([str(tmp_path / "missing.py"), "--editor", "zed"]) == 1
    assert "File does not exist" in capsys.readouterr().err

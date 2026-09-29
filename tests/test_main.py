from __future__ import annotations

import os
import pstats
import subprocess
import sys
from pathlib import Path

import django
import pytest

from profiling_explorer import (
    __main__,  # noqa: F401
    config,
    views,
)
from profiling_explorer import main as main_module
from profiling_explorer import settings as project_settings


def test_main_help_subprocess():
    proc = subprocess.run(
        [sys.executable, "-m", "profiling_explorer", "--help"],
        check=True,
        capture_output=True,
    )

    assert proc.stdout.startswith(b"usage: profiling-explorer ")


def test_main_defaults(monkeypatch):
    stats_calls = []
    build_profile_calls = []
    setup_calls = []
    command_calls = []
    built_profile = object()

    def fake_stats(filename):
        stats = ("stats", filename)
        stats_calls.append(filename)
        return stats

    def fake_build_profile(stats, filename):
        build_profile_calls.append((stats, filename))
        return built_profile

    def fake_setup():
        setup_calls.append(())

    def fake_call_command(*args, **kwargs):
        command_calls.append((args, kwargs))

    monkeypatch.setattr(sys, "argv", ["profiling-explorer", "example.pstats"])
    monkeypatch.setattr(pstats, "Stats", fake_stats)
    monkeypatch.setattr(views, "build_profile", fake_build_profile)
    monkeypatch.setattr(django, "setup", fake_setup)
    monkeypatch.setattr(main_module, "call_command", fake_call_command)
    monkeypatch.setattr(project_settings, "DEBUG", True, raising=False)
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)

    assert main_module.main() == 0
    assert stats_calls == ["example.pstats"]
    assert build_profile_calls == [(("stats", "example.pstats"), "example.pstats")]
    assert views.profile is built_profile
    assert project_settings.DEBUG is False  # type: ignore[attr-defined]
    assert os.environ["DJANGO_SETTINGS_MODULE"] == "profiling_explorer.settings"
    assert setup_calls == [()]
    assert command_calls == [
        (("runserver", "127.0.0.1:8099", "--nothreading", "--noreload"), {})
    ]


def test_main_dev_mode(monkeypatch):
    stats_calls = []
    build_profile_calls = []
    setup_calls = []
    command_calls = []
    built_profile = object()

    def fake_stats(filename):
        stats = ("stats", filename)
        stats_calls.append(filename)
        return stats

    def fake_build_profile(stats, filename):
        build_profile_calls.append((stats, filename))
        return built_profile

    def fake_setup():
        setup_calls.append(())

    def fake_call_command(*args, **kwargs):
        command_calls.append((args, kwargs))

    monkeypatch.setattr(pstats, "Stats", fake_stats)
    monkeypatch.setattr(views, "build_profile", fake_build_profile)
    monkeypatch.setattr(django, "setup", fake_setup)
    monkeypatch.setattr(main_module, "call_command", fake_call_command)
    monkeypatch.setattr(project_settings, "DEBUG", False, raising=False)
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)

    assert main_module.main(["--port", "8123", "--dev", "dev.pstats"]) == 0
    assert stats_calls == ["dev.pstats"]
    assert build_profile_calls == [(("stats", "dev.pstats"), "dev.pstats")]
    assert views.profile is built_profile
    assert project_settings.DEBUG is True  # type: ignore[attr-defined]
    assert os.environ["DJANGO_SETTINGS_MODULE"] == "profiling_explorer.settings"
    assert setup_calls == [()]
    assert command_calls == [(("runserver", "127.0.0.1:8123", "--nothreading"), {})]


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path / "profiling-explorer" / "config.toml"


@pytest.fixture
def fake_run(monkeypatch):
    monkeypatch.setattr(pstats, "Stats", lambda filename: None)
    monkeypatch.setattr(views, "build_profile", lambda stats, filename: None)
    monkeypatch.setattr(django, "setup", lambda: None)
    monkeypatch.setattr(main_module, "call_command", lambda *a, **k: None)
    monkeypatch.setattr(views, "editor", "unset")


def write_config(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(content)


def test_main_no_editor(fake_run):
    assert main_module.main(["example.pstats"]) == 0
    assert views.editor is None


def test_main_editor_cli(fake_run):
    assert main_module.main(["--editor", "code -n", "example.pstats"]) == 0
    assert views.editor == "code -n"


def test_main_editor_from_config(fake_run, isolated_config):
    write_config(isolated_config, 'editor = "zed"\n')
    assert main_module.main(["example.pstats"]) == 0
    assert views.editor == "zed"


def test_main_editor_cli_overrides_config(fake_run, isolated_config):
    write_config(isolated_config, 'editor = "zed"\n')
    assert main_module.main(["--editor", "code", "example.pstats"]) == 0
    assert views.editor == "code"


def test_main_editor_invalid_command(fake_run, capsys):
    with pytest.raises(SystemExit):
        main_module.main(["--editor", "code '", "example.pstats"])

    assert "Invalid editor command" in capsys.readouterr().err


def test_main_config_invalid_toml(fake_run, isolated_config, capsys):
    write_config(isolated_config, "editor = \n")
    with pytest.raises(SystemExit):
        main_module.main(["example.pstats"])

    assert "Invalid TOML in" in capsys.readouterr().err


def test_main_config_editor_not_string(fake_run, isolated_config, capsys):
    write_config(isolated_config, "editor = 1\n")
    with pytest.raises(SystemExit):
        main_module.main(["example.pstats"])

    assert "'editor' in" in capsys.readouterr().err


def test_config_path_default(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_CONFIG_HOME")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config.config_path() == (
        tmp_path / ".config" / "profiling-explorer" / "config.toml"
    )

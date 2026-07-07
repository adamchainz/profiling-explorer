from __future__ import annotations

import os
import pstats
import subprocess
import sys

import django

from profiling_explorer import (
    __main__,  # noqa: F401
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

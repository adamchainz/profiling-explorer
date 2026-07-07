from __future__ import annotations

import webbrowser
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

from django.core.management.commands.runserver import Command as RunserverCommand
from django.test import SimpleTestCase

from profiling_explorer.management.commands import runserver


class RunserverTests(SimpleTestCase):
    def test_handle_stores_use_reloader(self):
        calls = []

        def fake_handle(self, *args, **options):
            calls.append((self, args, options))

        with mock.patch.object(RunserverCommand, "handle", fake_handle):
            command = runserver.Command()
            command.handle("127.0.0.1:8099", use_reloader=True)

        assert command.use_reloader is True
        assert calls == [(command, ("127.0.0.1:8099",), {"use_reloader": True})]

    def test_on_bind_opens_browser_without_reloader(self):
        urls: list[str] = []
        output = StringIO()

        command = runserver.Command()
        command.addr = "127.0.0.1"
        command.stdout = StringIO()  # type: ignore [assignment]
        command.use_reloader = False

        with (
            mock.patch.object(webbrowser, "open", urls.append),
            redirect_stdout(output),
        ):
            command.on_bind(8099)

        assert command.stdout.getvalue() == (
            "profiling-explorer running at http://127.0.0.1:8099/\n"
            "Press CTRL+C to quit."
        )
        assert output.getvalue() == "Opening in web browser…\n"
        assert urls == ["http://127.0.0.1:8099"]

    def test_on_bind_with_reloader_does_not_open_browser(self):
        urls: list[str] = []
        output = StringIO()

        command = runserver.Command()
        command.addr = "127.0.0.1"
        command.stdout = StringIO()  # type: ignore [assignment]
        command.use_reloader = True

        with (
            mock.patch.object(webbrowser, "open", urls.append),
            redirect_stdout(output),
        ):
            command.on_bind(8099)

        assert command.stdout.getvalue() == (
            "profiling-explorer running at http://127.0.0.1:8099/\n"
            "Press CTRL+C to quit."
        )
        assert output.getvalue() == ""
        assert urls == []

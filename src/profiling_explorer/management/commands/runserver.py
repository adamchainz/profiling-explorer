from __future__ import annotations

import webbrowser

from django.core.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    def on_bind(self, server_port: int) -> None:
        super().on_bind(server_port)
        webbrowser.open(f"http://{self.addr}:{server_port}")  # type: ignore[attr-defined]

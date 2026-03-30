from __future__ import annotations

from django.core.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    def on_bind(self, server_port: int) -> None:
        super().on_bind(server_port)
        # open in browser
        import webbrowser

        webbrowser.open(f"http://{self.addr}:{server_port}")  # type: ignore[attr-defined]

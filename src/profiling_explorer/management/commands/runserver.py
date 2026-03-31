from __future__ import annotations

import webbrowser
from typing import Any

from django.core.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        self.use_reloader = options["use_reloader"]
        super().handle(*args, **options)

    def on_bind(self, server_port: int) -> None:
        super().on_bind(server_port)
        if not self.use_reloader:
            webbrowser.open(f"http://{self.addr}:{server_port}")  # type: ignore[attr-defined]

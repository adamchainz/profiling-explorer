from __future__ import annotations

import logging
import webbrowser
from typing import Any

from django.core.management.commands.runserver import Command as RunserverCommand
from django.utils.log import RequireDebugTrue

logger = logging.getLogger("django.server")
logger.filters.append(RequireDebugTrue())


class Command(RunserverCommand):
    addr: str

    def handle(self, *args: Any, **options: Any) -> None:
        self.use_reloader = options["use_reloader"]
        super().handle(*args, **options)

    def on_bind(self, server_port: int) -> None:
        self.stdout.write(
            f"profiling-explorer running at http://{self.addr}:{server_port}/\n"
            "Press CTRL+C to quit."
        )
        if not self.use_reloader:
            print("Opening in web browser…")
            webbrowser.open(f"http://{self.addr}:{server_port}")

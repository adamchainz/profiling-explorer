from __future__ import annotations

import pstats
from importlib.resources import open_binary

from django.http import FileResponse
from django.shortcuts import render

# Values set by main.py
filenames: list[str] = []
stats = pstats.Stats()


def index(request):
    return render(
        request,
        "index.html",
        {
            "filenames": filenames,
            "stats": stats,
        },
    )


def file(request, *, filename):
    return FileResponse(open_binary("profiling_explorer", f"static/{filename}"))

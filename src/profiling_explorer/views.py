from __future__ import annotations

import os
import pstats
import re
from dataclasses import dataclass
from importlib.resources import open_binary

from django.http import FileResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

# Values set by main.py
filenames: list[str] = []
stats = pstats.Stats()


@dataclass
class Row:
    total_calls: int
    tottime_ms: int
    cumtime_ms: int
    filename: str
    full_filename: str
    lineno: int
    funcname: str


_STRIP_PREFIX_RE = re.compile(
    r"""
    ^
    .*
    (?:
        # virtualenv packages
        /site-packages/
        |
        # standard library
        lib/python3\.\d+/
    )
    """,
    re.VERBOSE,
)


def _shorten_filename(filename: str) -> str:
    match = _STRIP_PREFIX_RE.match(filename)
    if match:
        return filename[match.end() :]
    return os.path.relpath(filename)


def _build_rows(s: pstats.Stats) -> list[Row]:
    rows = []
    for key in s.fcn_list:
        filename, lineno, funcname = key
        _, total_calls, tottime, cumtime, _ = s.stats[key]
        if filename == "~":
            # Built-in / C-level function: pstats uses "~" as a fake path.
            # Mirror pstats' func_std_string: strip <…> angle brackets and
            # wrap in {…} braces; show no file/line location.
            if funcname.startswith("<") and funcname.endswith(">"):
                funcname = f"{{{funcname[1:-1]}}}"
            short_filename = ""
            full_filename = ""
        else:
            short_filename = _shorten_filename(filename)
            full_filename = filename
        rows.append(
            Row(
                total_calls=total_calls,
                tottime_ms=round(tottime * 1000),
                cumtime_ms=round(cumtime * 1000),
                filename=short_filename,
                full_filename=full_filename,
                lineno=lineno,
                funcname=funcname,
            )
        )
    return rows


def index(request):
    return render(
        request,
        "index.html",
        {
            "filenames": filenames,
            "rows": _build_rows(stats),
        },
    )


@require_GET
def file(request, *, filename):
    return FileResponse(open_binary("profiling_explorer", f"static/{filename}"))


@require_GET
def favicon(request):
    return HttpResponse(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            + '<text y=".9em" font-size="90">🗺️</text>'
            + "</svg>"
        ),
        content_type="image/svg+xml",
    )

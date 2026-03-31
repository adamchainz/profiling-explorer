from __future__ import annotations

import os
import pstats
import re
from dataclasses import dataclass
from importlib.resources import open_binary
from operator import attrgetter

from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@dataclass
class Row:
    total_calls: int
    tottime_ms: int
    cumtime_ms: int
    filename: str
    full_filename: str
    lineno: int
    funcname: str


@dataclass
class Profile:
    filename: str
    total_calls: int
    total_time_ms: int
    rows: list[Row]
    sort_col: str
    sort_desc: bool


# Populated by main()
profile: Profile = None  # type: ignore[assignment]


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


def build_profile(s: pstats.Stats, path: str) -> Profile:
    s.sort_stats("cumulative")
    rows = []
    for key in s.fcn_list:  # type: ignore[attr-defined]
        filename, lineno, funcname = key
        _, total_calls, tottime, cumtime, _ = s.stats[key]  # type: ignore[attr-defined]
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
                tottime_ms=round(tottime * 1_000),
                cumtime_ms=round(cumtime * 1_000),
                filename=short_filename,
                full_filename=full_filename,
                lineno=lineno,
                funcname=funcname,
            )
        )
    return Profile(
        filename=path,
        total_calls=s.total_calls,  # type: ignore[attr-defined]
        total_time_ms=round(s.total_tt * 1000),  # type: ignore[attr-defined]
        rows=rows,
        sort_col="cumtime",
        sort_desc=True,
    )


_SORT_FIELDS = {
    "calls": "total_calls",
    "tottime": "tottime_ms",
    "cumtime": "cumtime_ms",
}


def index(request: HttpRequest) -> HttpResponse:
    sort_param = request.GET.get("sort", "-cumtime")
    sort_desc = not sort_param.startswith("+")
    sort_col = sort_param.lstrip("+-")
    if sort_col not in _SORT_FIELDS:
        sort_col = "cumtime"
        sort_desc = True

    if profile.sort_col != sort_col or profile.sort_desc != sort_desc:
        profile.rows.sort(key=attrgetter(_SORT_FIELDS[sort_col]), reverse=sort_desc)

        profile.sort_col = sort_col
        profile.sort_desc = sort_desc

    def col_config(key: str, label: str) -> dict[str, str]:
        config = {"key": key, "label": label}
        if sort_col == key:
            config["indicator"] = "↓" if sort_desc else "↑"
            config["next_sort"] = f"+{key}" if sort_desc else f"-{key}"
        else:
            config["indicator"] = ""
            config["next_sort"] = f"-{key}"
        return config

    return render(
        request,
        "index.html",
        {
            "profile": profile,
            "rows": profile.rows,
            "columns": [
                col_config("calls", "calls"),
                col_config("tottime", "internal ms"),
                col_config("cumtime", "cumulative ms"),
            ],
        },
    )


@require_GET
def file(request: HttpRequest, *, filename: str) -> FileResponse:
    return FileResponse(open_binary("profiling_explorer", f"static/{filename}"))


@require_GET
def favicon(request: HttpRequest) -> HttpResponse:
    return HttpResponse(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            + '<text y=".9em" font-size="90">🗺️</text>'
            + "</svg>"
        ),
        content_type="image/svg+xml",
    )

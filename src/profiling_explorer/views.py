from __future__ import annotations

import os
import pstats
import re
from dataclasses import dataclass
from importlib.resources import files as resource_files
from operator import attrgetter
from urllib.parse import urlencode

from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@dataclass
class Row:
    calls: int
    calls_pct: float
    internal_ms: int
    cumulative_ms: int
    cumulative_ms_pct: float
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
    total_time_ms = round(s.total_tt * 1000)  # type: ignore[attr-defined]
    rows = []
    for key in s.fcn_list:  # type: ignore[attr-defined]
        filename, lineno, funcname = key
        _, calls, tottime, cumtime, _ = s.stats[key]  # type: ignore[attr-defined]
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
        cumulative_ms = round(cumtime * 1_000)
        rows.append(
            Row(
                calls=calls,
                calls_pct=(
                    min(100.0, calls / s.total_calls * 100) if s.total_calls else 0.0  # type: ignore[attr-defined]
                ),
                internal_ms=round(tottime * 1_000),
                cumulative_ms=cumulative_ms,
                cumulative_ms_pct=min(100.0, cumulative_ms / total_time_ms * 100)
                if total_time_ms
                else 0.0,
                filename=short_filename,
                full_filename=full_filename,
                lineno=lineno,
                funcname=funcname,
            )
        )
    return Profile(
        filename=path,
        total_calls=s.total_calls,  # type: ignore[attr-defined]
        total_time_ms=total_time_ms,
        rows=rows,
        sort_col="cumtime",
        sort_desc=True,
    )


PAGE_SIZE = 200


def index(request: HttpRequest) -> HttpResponse:
    sort_col, sort_desc, sort_param = _apply_sort(request)

    q = request.GET.get("q", "").strip()
    filtered_rows = profile.rows
    if q:
        filtered_rows = [r for r in filtered_rows if q in r.filename or q in r.funcname]

    offset = int(request.GET.get("offset", 0))
    page_rows = filtered_rows[offset : offset + PAGE_SIZE]

    next_url = None
    next_offset = offset + PAGE_SIZE
    if next_offset < len(filtered_rows):
        params: dict[str, str | int] = {"sort": sort_param, "offset": next_offset}
        if q:
            params["q"] = q
        next_url = "/?" + urlencode(params)

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
            "rows": page_rows,
            "next_url": next_url,
            "q": q,
            "columns": [
                col_config("calls", "calls"),
                col_config("internal_ms", "internal ms"),
                col_config("cumulative_ms", "cumulative ms"),
            ],
        },
    )


def _apply_sort(request: HttpRequest) -> tuple[str, bool, str]:
    sort_param = request.GET.get("sort", "-cumtime")
    sort_desc = not sort_param.startswith("+")
    sort_col = sort_param.lstrip("+-")
    if sort_col not in {"calls", "internal_ms", "cumulative_ms"}:
        sort_col = "cumtime"
        sort_desc = True
        sort_param = "-cumtime"
    if profile.sort_col != sort_col or profile.sort_desc != sort_desc:
        profile.rows.sort(
            key=attrgetter(sort_col, "filename", "lineno", "funcname"),
            reverse=sort_desc,
        )
        profile.sort_col = sort_col
        profile.sort_desc = sort_desc
    return sort_col, sort_desc, sort_param


@require_GET
def file(request: HttpRequest, *, filename: str) -> FileResponse:
    return FileResponse(
        resource_files("profiling_explorer")
        .joinpath("static")
        .joinpath(filename)
        .open("rb"),
    )


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

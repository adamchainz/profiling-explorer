from __future__ import annotations

import hashlib
import os
import pstats
import re
from dataclasses import dataclass
from importlib.resources import files as resource_files
from typing import Any
from urllib.parse import urlencode

from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@dataclass(slots=True)
class RowStats:
    calls: int
    calls_pct: float
    internal_ms: int | None
    cumulative_ms: int
    cumulative_ms_pct: float


@dataclass(slots=True)
class EdgeStats(RowStats):
    pass


@dataclass(slots=True)
class Row(RowStats):
    id: str
    filename: str
    full_filename: str
    lineno: int
    funcname: str


@dataclass(slots=True)
class Profile:
    filename: str
    total_calls: int
    total_time_ms: int
    rows: list[Row]
    rows_by_id: dict[str, Row]
    callers_map: dict[str, dict[str, EdgeStats]]
    callees_map: dict[str, dict[str, EdgeStats]]


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
    if filename == "":
        return ""
    match = _STRIP_PREFIX_RE.match(filename)
    if match:
        return filename[match.end() :]
    return os.path.relpath(filename)


def _row_id(full_filename: str, lineno: int, funcname: str) -> str:
    return hashlib.sha256(f"{full_filename}:{lineno}:{funcname}".encode()).hexdigest()[
        :12
    ]


def _row_id_from_pstats_key(key: tuple[str, int, str]) -> str:
    filename, lineno, funcname = key
    full_filename = "" if filename == "~" else filename
    return _row_id(full_filename, lineno, funcname)


def build_profile(s: pstats.Stats, path: str) -> Profile:
    s.sort_stats("cumulative")
    total_calls: int = s.total_calls  # type: ignore[attr-defined]
    total_time_ms = round(s.total_tt * 1000)  # type: ignore[attr-defined]
    rows = []
    rows_by_id = {}
    for key in s.fcn_list:  # type: ignore[attr-defined]
        filename, lineno, funcname = key
        _, calls, tottime, cumtime, _ = s.stats[key]  # type: ignore[attr-defined]
        if filename == "~":
            if funcname.startswith("<") and funcname.endswith(">"):
                funcname = f"{{{funcname[1:-1]}}}"
            short_filename = ""
            full_filename = ""
        else:
            short_filename = _shorten_filename(filename)
            full_filename = filename
        row_id = _row_id(full_filename, lineno, funcname)
        cumulative_ms = round(cumtime * 1_000)
        row = Row(
            id=row_id,
            calls=calls,
            calls_pct=min(100.0, calls / total_calls * 100) if total_calls else 0.0,
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
        rows.append(row)
        rows_by_id[row_id] = row

    def make_edge(enc: int, etc: float) -> EdgeStats:
        cumulative_ms = round(etc * 1_000)
        return EdgeStats(
            calls=enc,
            calls_pct=min(100.0, enc / total_calls * 100) if total_calls else 0.0,
            internal_ms=None,
            cumulative_ms=cumulative_ms,
            cumulative_ms_pct=(
                min(100.0, cumulative_ms / total_time_ms * 100)
                if total_time_ms
                else 0.0
            ),
        )

    callers_map: dict[str, dict[str, EdgeStats]] = {}
    callees_map: dict[str, dict[str, EdgeStats]] = {}
    for (filename, lineno, funcname), (*_, callers) in s.stats.items():  # type: ignore[attr-defined]
        full_filename = "" if filename == "~" else filename
        callee_id = _row_id(full_filename, lineno, funcname)
        for caller_key, (enc, _, __, etc) in callers.items():
            caller_id = _row_id_from_pstats_key(caller_key)
            edge = make_edge(enc, etc)
            callers_map.setdefault(callee_id, {})[caller_id] = edge
            callees_map.setdefault(caller_id, {})[callee_id] = edge

    return Profile(
        filename=path,
        total_calls=total_calls,
        total_time_ms=total_time_ms,
        rows=rows,
        rows_by_id=rows_by_id,
        callers_map=callers_map,
        callees_map=callees_map,
    )


def _build_edge_rows(
    edges: dict[str, EdgeStats],
) -> list[tuple[Row, EdgeStats]]:
    result = [
        (row, edge)
        for row_id, edge in edges.items()
        if (row := profile.rows_by_id.get(row_id)) is not None
    ]
    result.sort(key=lambda pair: pair[1].cumulative_ms, reverse=True)
    return result


PAGE_SIZE = 200

_VALID_SORT_COLS = {"calls", "internal_ms", "cumulative_ms"}


def _render_table(
    request: HttpRequest,
    rows: list[Row],
    template: str,
    extra_context: dict[str, Any],
    edge_stats: dict[str, EdgeStats] | None = None,
) -> HttpResponse:
    sort_param = request.GET.get("sort", "-cumulative_ms")
    sort_desc = not sort_param.startswith("+")
    sort_col = sort_param.lstrip("+-")
    if sort_col not in _VALID_SORT_COLS:
        sort_col = "cumulative_ms"
        sort_desc = True
        sort_param = "-cumulative_ms"

    q = request.GET.get("q", "").strip()
    filtered_rows = rows
    if q:
        filtered_rows = [r for r in rows if q in r.filename or q in r.funcname]

    if edge_stats is None:
        sorted_rows = sorted(
            filtered_rows,
            key=lambda r: (getattr(r, sort_col), r.filename, r.lineno, r.funcname),
            reverse=sort_desc,
        )
    else:
        sorted_rows = sorted(
            filtered_rows,
            key=lambda r: edge_stats[r.id].cumulative_ms,
            reverse=True,
        )

    offset = int(request.GET.get("offset", 0))
    page_rows = sorted_rows[offset : offset + PAGE_SIZE]

    next_url = None
    next_offset = offset + PAGE_SIZE
    if next_offset < len(sorted_rows):
        params: dict[str, str | int] = {"sort": sort_param, "offset": next_offset}
        if q:
            params["q"] = q
        next_url = request.path + "?" + urlencode(params)

    def col_config(key: str, label: str) -> dict[str, str]:
        config = {"key": key, "label": label}
        if sort_col == key:
            config["indicator"] = "↓" if sort_desc else "↑"
            config["next_sort"] = f"+{key}" if sort_desc else f"-{key}"
        else:
            config["indicator"] = ""
            config["next_sort"] = f"-{key}"
        return config

    context = {
        "profile": profile,
        "rows": page_rows,
        "next_url": next_url,
        "q": q,
        "columns": [
            col_config("calls", "calls"),
            col_config("internal_ms", "internal ms"),
            col_config("cumulative_ms", "cumulative ms"),
        ],
        **extra_context,
    }
    if edge_stats is not None:
        context["rows_with_edges"] = [(r, edge_stats[r.id]) for r in page_rows]

    return render(request, template, context)


def index(request: HttpRequest) -> HttpResponse:
    return _render_table(request, profile.rows, "index.html", {})


def _callers_callees_view(
    request: HttpRequest,
    focal_row: Row,
    edges: dict[str, EdgeStats],
    opposite_url: str,
    heading: str,
    opposite_label: str,
) -> HttpResponse:
    rows_with_edges = _build_edge_rows(edges)
    rows = [r for r, _ in rows_with_edges]
    edge_stats: dict[str, EdgeStats] = {r.id: e for r, e in rows_with_edges}

    return _render_table(
        request,
        rows,
        "callers_callees.html",
        {
            "focal_row": focal_row,
            "heading": heading,
            "opposite_label": opposite_label,
            "opposite_url": opposite_url,
        },
        edge_stats=edge_stats,
    )


@require_GET
def callers_view(request: HttpRequest, row_id: str) -> HttpResponse:
    focal_row = profile.rows_by_id.get(row_id)
    if focal_row is None:
        raise Http404()
    return _callers_callees_view(
        request,
        focal_row,
        profile.callers_map.get(row_id, {}),
        opposite_url=f"/callees/{row_id}/",
        heading="Callers",
        opposite_label="view callees →",
    )


@require_GET
def callees_view(request: HttpRequest, row_id: str) -> HttpResponse:
    focal_row = profile.rows_by_id.get(row_id)
    if focal_row is None:
        raise Http404()
    return _callers_callees_view(
        request,
        focal_row,
        profile.callees_map.get(row_id, {}),
        opposite_url=f"/callers/{row_id}/",
        heading="Callees",
        opposite_label="← view callers",
    )


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

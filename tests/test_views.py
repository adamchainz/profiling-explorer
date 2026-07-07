from __future__ import annotations

import pstats
from typing import cast
from unittest import mock

from django.test import SimpleTestCase

from profiling_explorer import views


class IndexTests(SimpleTestCase):
    def test_index(self):
        response = self.client.get("/")
        assert response.status_code == 200
        assert b"test.pstats" in response.content

    def test_filter_invalid_sort_and_pagination(self):
        with mock.patch.object(views, "PAGE_SIZE", 1):
            response = self.client.get("/", {"sort": "invalid", "q": "json"})
            assert response.status_code == 200
            assert b'value="json"' in response.content
            assert (
                b'data-url="/?sort=-cumulative_ms&amp;offset=1&amp;q=json"'
                in response.content
            )

            response = self.client.get("/", {"sort": "+calls"})
            assert response.status_code == 200
            assert b'data-url="/?sort=%2Bcalls&amp;offset=1"' in response.content


class CallersTests(SimpleTestCase):
    def test_callers_view(self):
        row_id = next(iter(views.profile.callers_map))

        response = self.client.get(f"/callers/{row_id}/")

        assert response.status_code == 200
        assert b"Callers of" in response.content

    def test_callers_view_404(self):
        response = self.client.get("/callers/missing/")

        assert response.status_code == 404


class CalleesTests(SimpleTestCase):
    def test_callees_view(self):
        row_id = next(iter(views.profile.callees_map))

        response = self.client.get(f"/callees/{row_id}/", {"sort": "+calls"})

        assert response.status_code == 200
        assert b"Callees of" in response.content

    def test_callees_view_404(self):
        response = self.client.get("/callees/missing/")

        assert response.status_code == 404


class RowTests(SimpleTestCase):
    def test_build_edge_rows_ignores_missing_rows(self):
        edge = views.RowStats(
            calls=1,
            calls_pct=1.0,
            internal_ms=None,
            cumulative_ms=1,
            cumulative_ms_pct=1.0,
        )

        assert views._build_edge_rows({"missing": edge}) == []

    def test_shorten_filename_function_special_cases(self):
        assert views._shorten_filename_function("~", "<built-in method len>") == (
            "",
            "",
            "{built-in method len}",
        )
        assert views._shorten_filename_function("~", "plain") == ("", "", "plain")
        assert views._shorten_filename_function("", "func") == ("", "", "func")

    def test_row_id_from_pstats_key(self):
        assert views._row_id_from_pstats_key(("~", 1, "func")) == views._row_id(
            "", 1, "func"
        )
        assert views._row_id_from_pstats_key(
            ("example.py", 1, "func")
        ) == views._row_id("example.py", 1, "func")


class BuildProfileTests(SimpleTestCase):
    def test_build_profile_with_zero_totals(self):
        key = ("example.py", 1, "func")
        caller_key = ("caller.py", 2, "caller")

        class ZeroTotalsStats:
            total_calls = 0
            total_tt = 0.0
            fcn_list = [key]
            stats = {key: (0, 0, 0.0, 0.0, {caller_key: (0, 0, 0.0, 0.0)})}

            def sort_stats(self, sort):
                self.sort = sort

        stats = ZeroTotalsStats()

        profile = views.build_profile(cast(pstats.Stats, stats), "empty.pstats")

        assert stats.sort == "cumulative"
        assert profile.total_calls == 0
        assert profile.total_time_ms == 0
        assert profile.rows[0].calls_pct == 0.0
        assert profile.rows[0].cumulative_ms_pct == 0.0
        assert profile.callers_map[profile.rows[0].id]


class FileTests(SimpleTestCase):
    def test_styles_css(self):
        response = self.client.get("/styles.css")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/css"
        content = response.getvalue()
        assert content.startswith(b":root {")

    def test_script_js(self):
        response = self.client.get("/script.js")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/javascript"
        content = response.getvalue()
        assert len(content) > 0


class FaviconTests(SimpleTestCase):
    def test_favicon(self):
        response = self.client.get("/favicon.ico")
        assert response.status_code == 200
        assert response["Content-Type"] == "image/svg+xml"
        assert response.content.startswith(b"<svg")

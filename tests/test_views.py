from __future__ import annotations

from django.test import SimpleTestCase


class IndexTests(SimpleTestCase):
    def test_index(self):
        response = self.client.get("/")
        assert response.status_code == 200
        assert b"test.pstats" in response.content


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

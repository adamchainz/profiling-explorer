from __future__ import annotations

from django.test import SimpleTestCase

from profiling_explorer.templatetags.profiling_explorer_tags import pct, pct_class, sub


class TemplateTagTests(SimpleTestCase):
    def test_sub(self):
        assert sub(5, 3) == 2

    def test_pct(self):
        assert pct(12.34) == "12.3%"

    def test_pct_class(self):
        assert pct_class(0.01) == "pct-0"
        assert pct_class(101.0) == "pct-20"

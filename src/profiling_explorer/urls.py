from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("favicon.ico", views.favicon),
    path("styles.css", views.file, {"filename": "styles.css"}),
    path("script.js", views.file, {"filename": "script.js"}),
]

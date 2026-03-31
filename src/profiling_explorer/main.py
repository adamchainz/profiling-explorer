from __future__ import annotations

import argparse
import os
import pstats
import sys
from collections.abc import Sequence

import django
from django.conf import settings
from django.core.management import call_command

from profiling_explorer import views


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog="profiling-explorer", allow_abbrev=False)
    parser.suggest_on_error = True  # type: ignore[attr-defined]
    parser.add_argument(
        "filename",
        metavar="FILE",
        help="The pstats data file to explore.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8099,
        metavar="PORT",
        help="Port for the local web server (default: 8099).",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        default=False,
        help="Run in development mode (enables server reload and debug mode).",
    )
    args = parser.parse_args(argv)

    views.profile = views.build_profile(pstats.Stats(args.filename), args.filename)

    settings.configure(
        DEBUG=args.dev,
        ALLOWED_HOSTS=["*"],  # Disable host header validation
        ROOT_URLCONF="profiling_explorer.urls",
        SECRET_KEY="we-dont-use-any-secret-features-so-whatever",
        INSTALLED_APPS=[
            "profiling_explorer",
            "django.contrib.humanize",
        ],
        MIDDLEWARE=[
            "django.middleware.common.CommonMiddleware",
        ],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {
                    "builtins": [
                        "profiling_explorer.templatetags.profiling_explorer_tags",
                        "django.contrib.humanize.templatetags.humanize",
                    ],
                },
            }
        ],
    )
    # Hide development server warning
    # https://docs.djangoproject.com/en/stable/ref/django-admin/#envvar-DJANGO_RUNSERVER_HIDE_WARNING
    os.environ["DJANGO_RUNSERVER_HIDE_WARNING"] = "true"

    django.setup()

    call_command(
        "runserver",
        f"127.0.0.1:{args.port}",
        "--nothreading",
        *(() if args.dev else ("--noreload",)),
    )

    return 0

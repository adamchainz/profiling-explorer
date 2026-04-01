from __future__ import annotations

import os

# Hide development server warning
# https://docs.djangoproject.com/en/stable/ref/django-admin/#envvar-DJANGO_RUNSERVER_HIDE_WARNING
os.environ["DJANGO_RUNSERVER_HIDE_WARNING"] = "true"

# Disable host header validation
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "profiling_explorer",
    "django.contrib.humanize",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "profiling_explorer.urls"

SECRET_KEY = "we-dont-use-any-secret-features-so-whatever"

TEMPLATES = [
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
]

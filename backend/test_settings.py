"""Use an isolated in-memory database for automated Django API tests."""

from .settings import *  # noqa: F403


DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

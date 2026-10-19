"""Local Django settings; the database password stays in the ignored .env."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import dotenv_values

# Local development only; public hosting needs separate production settings.
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

ROOT_URLCONF = "backend.urls"
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "captures",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

BASE_DIR = Path(__file__).resolve().parent.parent
DB_VALUES = {
    "DB_HOST": "127.0.0.1",
    "DB_PORT": "5432",
    "DB_NAME": "pothole_db",
    "DB_USER": "pothole_app",
    **dotenv_values(BASE_DIR / ".env", interpolate=False),
    **os.environ,
}
SECRET_KEY = DB_VALUES.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "Set DJANGO_SECRET_KEY in the environment or run "
        "python -m scripts.configure_django_secret."
    )

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_VALUES["DB_NAME"],
        "USER": DB_VALUES["DB_USER"],
        "PASSWORD": DB_VALUES.get("DB_PASSWORD") or "",
        "HOST": DB_VALUES["DB_HOST"],
        "PORT": DB_VALUES["DB_PORT"],
        "OPTIONS": {"connect_timeout": 3},
    }
}

"""Create a stable private Django signing key in the ignored local .env file."""

import os
from pathlib import Path

from django.core.management.utils import get_random_secret_key
from dotenv import dotenv_values, set_key


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def main() -> int:
    if os.environ.get("DJANGO_SECRET_KEY"):
        print("DJANGO_SECRET_KEY is already set in the environment.")
        return 0

    if dotenv_values(ENV_FILE, interpolate=False).get("DJANGO_SECRET_KEY"):
        print("DJANGO_SECRET_KEY is already set in the ignored .env file.")
        return 0

    try:
        set_key(
            ENV_FILE,
            "DJANGO_SECRET_KEY",
            get_random_secret_key(),
            quote_mode="always",
        )
    except OSError:
        print("Could not save the private key to .env. Check file access.")
        return 1

    print("Created a private Django signing key in the ignored .env file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

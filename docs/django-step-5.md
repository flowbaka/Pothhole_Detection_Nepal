# Django lesson 5: keep the signing key private

Django uses `SECRET_KEY` to sign security-sensitive values. A fixed key committed to Git would be known to everyone who can read the repository. This lesson makes each local checkout use a random, stable key stored outside Git.

Run this once in the project folder, after installing `requirements.txt`:

```powershell
.\.pothholevenv\Scripts\python.exe -m scripts.configure_django_secret
```

The script in `scripts/configure_django_secret.py` checks for an existing `DJANGO_SECRET_KEY` in the process environment or `.env`. If one exists, it leaves it unchanged. Otherwise `get_random_secret_key()` generates a strong value and `set_key()` saves it in the Git-ignored `.env`. The command never prints the value.

In `backend/settings.py`, `DB_VALUES` combines local `.env` settings with process environment variables; the latter take priority. `SECRET_KEY = DB_VALUES.get("DJANGO_SECRET_KEY")` reads the value. `ImproperlyConfigured` stops startup if it is missing, rather than silently using a public fallback. `.env.example` names the setting but contains no secret.

Checks performed: the first run created a local key, the repeated run left it in place, Django's normal check and nine tests passed, and the deployment check no longer reported a weak key. The key itself was not printed or committed. The deployment check still warns about `DEBUG=True` and HTTPS-only settings because this server is for local development. Do not host it publicly with these settings. Authenticated upload permissions and production deployment configuration are separate future steps.

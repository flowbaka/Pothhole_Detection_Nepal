# Django lesson 6: an owner-only session API

This step adds `GET` and `POST /api/capture-sessions/` for **session metadata only**. It does not upload video or GPS readings.

## How the request works

1. `backend/urls.py` sends the path to `CaptureSessionListCreateView`.
2. Django REST Framework's `TokenAuthentication` reads the `Authorization: Token ...` header. `IsAuthenticated` rejects requests with no valid token.
3. `get_queryset()` filters by `owner=request.user`, so a rider lists only their own journeys.
4. On `POST`, `CaptureSessionSerializer` accepts `started_at` and `ended_at` with an explicit UTC offset or `Z`. Its `validate()` method rejects an end time that is not later than the start. The database constraint remains a second layer of protection.
5. `perform_create()` sets `owner` from the authenticated user; the client cannot choose another owner. `id` and `created_at` are read-only response fields.

`backend/settings.py` registers REST Framework and its token table. Its API defaults accept JSON, return JSON, and require token authentication. `TIME_ZONE = "UTC"` and `USE_TZ = True` keep stored timestamps consistent. `backend/test_settings.py` gives automated API tests an isolated in-memory SQLite database, leaving the real PostgreSQL data untouched.

The token is a credential. Never put one in Git, a screenshot or an ordinary chat message. No public token-issuing endpoint was added, because a login endpoint would need its own rate limits and security review. The current server listens on `127.0.0.1` for local development; mobile token use will require trusted HTTPS. Django REST Framework's [authentication guide](https://www.django-rest-framework.org/api-guide/authentication/) describes this requirement.

## Validation

```powershell
.\.pothholevenv\Scripts\python.exe manage.py check
.\.pothholevenv\Scripts\python.exe manage.py test backend captures --settings=backend.test_settings
.\.pothholevenv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Thirteen automated tests passed. They check anonymous denial, ownership on create and list, invalid timestamps, the existing model rules, and response headers. Token migrations were applied to local PostgreSQL. The API tests used SQLite; they are not phone tests and do not verify HTTPS or uploads.

## Next lesson

Add a private upload flow with strict file-size and media checks, then link the file and GPS readings to an authenticated session. Do not accept or publish raw route data through the public map.

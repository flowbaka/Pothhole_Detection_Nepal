# Django lesson 3: a private capture session

This step creates a database row for **one recorded journey**. It does not accept a video, GPS readings or public reports yet. The older iPhone browser page is a separate experiment.

## What each file does

`backend/settings.py` lists `django.contrib.contenttypes` and `django.contrib.auth` so Django can create users and link a journey to its owner. It lists `captures` so Django discovers the new model. Security, CSRF and clickjacking middleware are enabled for future HTTP endpoints. There is still no login or upload endpoint.

`captures/apps.py` names the app. `captures/models.py` contains the table definition:

| Code | Meaning |
|---|---|
| `class CaptureSession(models.Model)` | One Python object corresponds to one database row. |
| `id = models.UUIDField(...)` | Random, non-sequential session identifier; `uuid.uuid4` is called when a new row is created. |
| `owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)` | Each session belongs to a Django user. `PROTECT` stops accidental deletion of a user while sessions still reference them. |
| `started_at`, `ended_at` | Actual recording start/end timestamps; these will later anchor video and GPS readings. |
| `created_at = models.DateTimeField(auto_now_add=True)` | Time the database row was first saved, which can be later than recording. |
| `CheckConstraint(...)` | PostgreSQL rejects a row unless `ended_at > started_at`, including writes that bypass Python validation. |
| `clean()` | Gives a readable validation error for an invalid interval before a database insert. |

The fields use timezone-aware datetimes when Django's timezone support is enabled. Keep device timestamps in a consistent UTC form when an upload endpoint is added. The UUID does not grant access by itself: a future API must authenticate users and check ownership before returning or changing a session.

`captures/migrations/0001_initial.py` is Django's generated schema instruction. `migrate` applied it to local PostgreSQL alongside Django's `auth` and `contenttypes` tables. The existing untracked coordinate-only `reports/models.py` draft was neither changed nor migrated.

## Checks performed

```powershell
.\.pothholevenv\Scripts\python.exe manage.py check
.\.pothholevenv\Scripts\python.exe manage.py test backend captures
.\.pothholevenv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.pothholevenv\Scripts\python.exe manage.py showmigrations captures
.\.pothholevenv\Scripts\python.exe manage.py check --deploy
```

The tests cover existing JSON routes, protective response headers, and both valid and invalid session intervals. A temporary transaction also confirmed that PostgreSQL rejects an invalid interval; its test user was rolled back. Django's deployment check still warns about the local development `SECRET_KEY`, `DEBUG=True`, and HTTPS-only settings (redirect, HSTS and CSRF cookie). Do not expose this development server publicly. A private production key, HTTPS configuration and authenticated API permissions are future milestones.

## Next lesson

Add timestamped GPS readings related to a capture session. We will first explain each field and its relationship to `CaptureSession`, then create and test its migration. No phone test is needed for this database-only lesson.

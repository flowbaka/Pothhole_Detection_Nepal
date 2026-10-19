# Django lesson 4: GPS readings for a journey

A journey can have many location readings. The new `GPSReading` model stores one reading per row; its `session` field links it to the `CaptureSession` from lesson 3. There is no upload endpoint or public route for this data yet.

## Read the code

| Code in `captures/models.py` | Meaning |
|---|---|
| `ForeignKey(CaptureSession, ...)` | One session can have many readings; each reading belongs to exactly one session. |
| `on_delete=models.CASCADE` | Deleting a session also deletes its route readings. |
| `related_name="gps_readings"` | `session.gps_readings.all()` retrieves that session's readings. |
| `captured_at = models.DateTimeField()` | The device reading's timestamp, separate from database creation or upload time. |
| `latitude`, `longitude` | Decimal degrees, with Python validators for -90 to 90 and -180 to 180. |
| `accuracy_m` | The device's estimated horizontal accuracy in metres; it must be positive. It is not a guarantee of pothole-position accuracy. |
| `models.Index(fields=["session", "captured_at"])` | Helps retrieve one journey's route in time order. |
| `CheckConstraint(...)` | PostgreSQL also rejects invalid coordinate ranges and nonpositive accuracy if code bypasses Python validation. |

The database does not force every reading to fall between the session's start and end. A location reading just before recording can be useful evidence; later processing must inspect gaps, timestamps and GPS accuracy rather than silently treating every reading as synchronized. Do not infer a pothole's exact road position from a single phone coordinate.

`captures/migrations/0002_gpsreading.py` creates the PostgreSQL table, index and check constraint. Raw routes remain private: no view, serializer or map endpoint exposes these rows. A future authenticated API must verify session ownership before accepting or returning readings.

## Verification

```powershell
.\.pothholevenv\Scripts\python.exe manage.py check
.\.pothholevenv\Scripts\python.exe manage.py test backend captures
.\.pothholevenv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.pothholevenv\Scripts\python.exe manage.py showmigrations captures
```

The automated tests cover invalid latitude and zero accuracy. A separate PostgreSQL transaction confirmed its constraint rejects both; all test rows were rolled back. No phone behavior was tested in this lesson.

## Next lesson

Design an authenticated upload workflow for a session's video and GPS readings. Before accepting files, we must decide request limits, allowed media types, storage location, ownership checks and how to reject malformed timestamps. The current development server and secret key are not configured for public hosting.

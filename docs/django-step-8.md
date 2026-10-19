# Django lesson 8: upload a journey's GPS readings

An authenticated rider can now `POST /api/capture-sessions/<session UUID>/gps-readings/` with JSON containing a `readings` array. One request saves one complete batch of location readings for an owned session. The route data is private and is not returned by the session-list API.

Example shape, using **illustrative coordinates only**:

```json
{
  "readings": [
    {
      "captured_at": "2026-10-19T10:00:01Z",
      "latitude": "26.452500",
      "longitude": "87.271800",
      "accuracy_m": "12.50"
    }
  ]
}
```

`GPSReadingSerializer` in `captures/serializers.py` validates each timestamp, coordinate and accuracy. `OffsetDateTimeField` requires an explicit offset or `Z`; this avoids silently guessing a device's timezone. `GPSBatchSerializer` requires 1–600 readings. This limit covers the proposal's five-minute, approximately once-per-second collection goal while bounding a request's database work.

`GPSBatchUploadView` in `captures/views.py` checks ownership before parsing the payload, then validates the **entire** batch. It locks the owned session inside `transaction.atomic()`, rejects a repeat submission, and uses `bulk_create()` to save all rows together. If any item is invalid, no row is saved. The PostgreSQL coordinate and accuracy constraint remains a second layer of protection.

The database does not pretend that GPS is a pothole's exact location. Some readings can precede recording; processing must inspect timestamp gaps and reported accuracy. This endpoint does not align video frames, detect potholes, or publish a map point.

## Checks

```powershell
.\.pothholevenv\Scripts\python.exe manage.py check
.\.pothholevenv\Scripts\python.exe manage.py test backend captures --settings=backend.test_settings
.\.pothholevenv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Eighteen automated tests passed. They cover anonymous denial, ownership, duplicate prevention, full-batch rejection for a bad item, timezone and coordinate validation, and the 600-reading cap. The tests used an isolated SQLite database, not a phone or a real GPS trace. No schema migration is needed for this lesson because `GPSReading` was created in lesson 4.

## Next lesson

Add a safe, local workflow for creating a test rider and issuing a token without exposing a password or token in Git. Then test a **synthetic** end-to-end upload through the running local API. Real phone uploads must use trusted HTTPS.

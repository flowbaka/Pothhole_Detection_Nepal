# Django lesson 13: check journey inputs before processing

The upload-status route reports saved metadata. This new input check also verifies that the referenced video exists and is nonempty, then checks the saved GPS timestamps against the journey interval. It is a read-only summary: it does not change recordings, schedule a worker, decode video or detect potholes.

## Run it locally

After importing a recording, use the session ID printed by the importer:

```powershell
.\.pothholevenv\Scripts\python.exe manage.py check_capture_inputs YOUR_SESSION_ID
```

This command is intended for the local project operator. The API version requires the rider's token:

```text
GET /api/capture-sessions/<session-id>/input-check/
```

Another rider receives 404. An anonymous request receives 401. The response contains no coordinates, absolute timestamps, storage paths or video download URL.

## Understand the files in order

1. `captures/input_checks.py` contains `check_session_inputs(session)`. A session is a Python model object representing one journey row. The function reads its file reference and GPS timestamps, calculates a summary, and returns a Python dictionary.
2. `session.video.storage.exists(...)` checks for the file. `storage.size(...) > 0` checks that it is nonempty. A stored filename alone does not establish that the file is still there. Storage errors produce a fixed issue code instead of exposing a private path.
3. `order_by("captured_at").values_list("captured_at", flat=True)` asks Django's ORM for sorted timestamps only. Coordinates are not needed for this check.
4. The `during` list includes readings acquired between Start and Stop, including both boundaries. Other readings are counted separately. A Python `set` removes duplicates, so comparing its length with the list length identifies repeated acquisition timestamps.
5. `boundaries` includes Start, the in-recording timestamps, and Stop. Subtracting adjacent times finds the gaps; `max(...)` selects the largest. This includes the initial wait for GPS and the final uncovered period.
6. `CaptureSessionInputCheckView.get()` in `captures/views.py` finds the authenticated owner's session before calling the function. `backend/urls.py` connects the URL to this view.
7. `check_capture_inputs.py` is a Django management command. It calls the same function and uses `json.dumps(..., indent=2)` to print its dictionary as readable JSON.
8. `captures/test_input_checks.py` uses an isolated database, temporary files, invented coordinates and a synthetic MP4 header. The tests exercise missing/empty files, edge gaps, duplicate/outside readings, ownership and sanitized storage errors.

## Python syntax used in this lesson

| Code | What it means |
|---|---|
| `issues = []` | Start an empty list that will hold issue codes. |
| `issues.append("video_missing")` | Add one issue to the end of the list. |
| `if not session.video:` | Run this branch when no video name has been stored. |
| `try: ... except OSError:` | Attempt the file check and handle an operating-system failure with a fixed response. |
| `list(queryset)` | Execute the database query and collect its values into a Python list. |
| `[value for value in timestamps if ...]` | Build a new list containing only values that satisfy the condition. This is a list comprehension. |
| `len(timestamps)` | Count the items in a list. |
| `set(during)` | Build a collection containing each distinct timestamp once. |
| `[session.started_at, *during, session.ended_at]` | Build one list and unpack every item from `during` into the middle. |
| `zip(boundaries, boundaries[1:])` | Pair each time with the time immediately after it. `[1:]` means all items except the first. |
| `(right - left).total_seconds()` | Subtract two datetimes and express the resulting duration in seconds. |
| `max(...)` | Select the largest gap. |
| `return {...}` | Give the calling view or command a dictionary containing the result. |

For a ten-second recording with readings at seconds 0, 5 and 10, the boundary list is equivalent to `[0, 0, 5, 10, 10]`. Pairing adjacent entries gives `(0, 0)`, `(0, 5)`, `(5, 10)` and `(10, 10)`. The gaps are 0, 5, 5 and 0 seconds, so the largest gap is 5 seconds. A reading exactly at Start or Stop creates a zero-length edge gap, which is expected.

## Interpret the result

| Status | Meaning |
|---|---|
| `missing_inputs` | Video is missing/unavailable, or fewer than two GPS readings fall within the recording. |
| `review_inputs` | Inputs are present, but timestamps or gaps need review. |
| `inputs_present` | These limited file-availability and timestamp checks found no issues. |

| Issue | Meaning |
|---|---|
| `video_missing` | No video reference has been saved. |
| `video_unavailable` | The referenced file is missing, empty or inaccessible. |
| `gps_too_few` | Fewer than two GPS readings fall inside the recording interval. |
| `gps_outside_recording` | Some saved readings were acquired before Start or after Stop. |
| `gps_duplicate_timestamps` | In-recording readings repeat an acquisition timestamp. |
| `gps_gap_review` | A gap, including either recording edge, exceeds five seconds. |

The five-second threshold is an experiment review prompt, not a validated road-mapping standard. `inputs_present` does not prove video playability, GPS accuracy, first-frame alignment or pothole detection. This summary is a snapshot; a future worker must validate its inputs again when it runs.

## Synthetic example

A ten-second test journey with a nonempty synthetic file and GPS readings at 0, 5 and 10 seconds produces:

```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "inputs_present",
  "video_available": true,
  "gps_readings_during": 3,
  "gps_readings_outside": 0,
  "largest_gap_s": 5.0,
  "issues": []
}
```

Run all Django tests with:

```powershell
.\.pothholevenv\Scripts\python.exe manage.py test backend captures --settings=backend.test_settings
```

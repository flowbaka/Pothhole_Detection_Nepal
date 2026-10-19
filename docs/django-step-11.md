# Django lesson 11: confirm both uploads for one journey

The Django API can now answer `GET /api/capture-sessions/<session-id>/upload-status/` for an authenticated rider. Its response has the session ID, a `video_uploaded` boolean, and a `gps_reading_count`. For example:

```json
{"session_id":"<session-id>","video_uploaded":true,"gps_reading_count":4}
```

This means the server stored a file reference and four GPS rows for that journey. It does **not** mean the video was decoded, the readings were aligned to frames, or a pothole was detected.

## Read the code in order

1. `backend/urls.py` maps the path to `CaptureSessionUploadStatusView`.
2. The view's `get()` method in `captures/views.py` handles the GET request. `get_object_or_404(CaptureSession, pk=session_id, owner=request.user)` finds a journey belonging to the authenticated rider. Another rider gets 404, so this endpoint does not reveal whether the journey ID exists.
3. `bool(session.video)` reports whether a video file path is stored. `session.gps_readings.count()` asks the database for the number of saved readings. The response includes neither the route coordinates nor a video download URL.
4. `CompleteUploadWorkflowTests` in `captures/tests.py` creates a synthetic journey through the API, uploads a tiny MP4-shaped fixture and one GPS reading, then checks the status before, between and after the uploads. It also checks that another rider and an anonymous request cannot read the status.

The synthetic video only has an MP4 header. This test proves that the API routes, ownership checks and database/file-storage calls work together; it cannot prove that a real video plays or that GPS matches its frames. The test uses a temporary media directory and isolated test database, leaving your recordings untouched.

Run the automated check with:

```powershell
.\.pothholevenv\Scripts\python.exe manage.py test backend captures --settings=backend.test_settings
```

The iPhone browser recorder still saves files locally; it does not upload to this Django API yet. Do not put a rider token in a public webpage or send it over plain network HTTP.

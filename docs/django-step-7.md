# Django lesson 7: private video upload

An authenticated rider can now send one MP4 file to `PUT /api/capture-sessions/<session UUID>/video/` as multipart form data with a field named `video`. This is a backend upload endpoint, not a phone app or a video-processing worker.

## Read the code

| Code | Purpose |
|---|---|
| `CaptureSession.video` | Stores the private file's relative storage path in PostgreSQL. |
| `video_uploaded_at` | Records when the file reached the server, separate from the journey's recording times. |
| `video_upload_path()` | Ignores the client filename and writes under `uploads/capture-videos/<session UUID>/video.mp4`. |
| `MEDIA_ROOT` | Keeps footage in the ignored `uploads/` directory. No URL serves that directory. |
| `MultiPartParser` | Reads multipart uploads and makes the file available in `request.FILES`. |
| `MAX_VIDEO_BYTES` | Sets a 300 MiB limit. The view checks declared request size before parsing and actual file size after parsing. A production reverse proxy must enforce its own body limit too. |
| MP4 header check | Requires `.mp4` and an `ftyp` box near the beginning. This is only a shallow container check; it does not prove the video is decodable or safe for a media processor. |
| `owner=request.user` lookup | Hides another rider's session with a 404 response. |
| `select_for_update()` | Locks the session row while checking whether a video already exists, preventing two uploads from replacing each other on PostgreSQL. |
| `transaction.atomic()` | Saves the row as one database transaction; an attempted file cleanup runs if that save fails. |

The API does not return the private path. There is no video download or public media route. Raw footage should remain restricted, and a future processing worker must decode it in a controlled environment and handle faces and license plates before any evidence is published.

## Checks

```powershell
.\.pothholevenv\Scripts\python.exe manage.py check
.\.pothholevenv\Scripts\python.exe manage.py test backend captures --settings=backend.test_settings
.\.pothholevenv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.pothholevenv\Scripts\python.exe manage.py showmigrations captures
```

The automated tests use synthetic MP4-like bytes and a temporary media folder. They verify authentication, owner isolation, private storage path, rejection of invalid or oversized files, and duplicate-upload handling. They do **not** establish that a real video decodes or that an actual phone can upload. Migration `0003` adds the two video fields to local PostgreSQL.

## Next lesson

Add an owner-only batch API for the GPS readings that belong to an already-created session. Validate every timestamp, coordinate and accuracy before saving the batch together. Then test a real phone upload over trusted HTTPS; do not send a token over plain network HTTP.

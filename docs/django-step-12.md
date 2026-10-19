# Django lesson 12: bring an iPhone experiment into Django

The browser recorder exports a paired MP4 and JSON file. The local `import_phone_export` command can validate that pair and, only with `--apply`, copy its MP4 and in-recording GPS readings into a private Django capture session. This is a bridge for the iPhone **feasibility experiment**. It is not the proposed Android collector or a pothole-detection step.

## What the code does

1. `source_test_id` in `captures/models.py` stores the recorder's `phone-test-...` ID. It is unique so a second run cannot silently duplicate the journey. Ordinary API-created sessions leave it empty. Migration `0004` adds this optional column without changing existing captures.
2. `import_phone_export.py` reads the JSON you name, checks the recorder's timing fields, then requires a matching MP4 beside it with the original filename, byte count and MP4 header. These checks do not decode the video or prove frame alignment.
3. It selects only location readings whose acquisition timestamps fall between recording Start and Stop. The pre-recording warm-up readings stay in your original JSON but are not stored as journey GPS rows.
4. Without `--apply`, the command prints counts and review-flag count but changes no database row or file. With `--apply`, it finds the named active rider, validates the times and GPS fields, then saves one session, the video and GPS rows. A database transaction and file cleanup cover failures during saving.
5. The synthetic tests create a fake export in a temporary folder. They check the dry run, import, owner-only upload status, duplicate rejection and mismatched-video rejection. They do not open your real recordings.

## Try one export when you are ready

After applying migrations, run the dry run with an existing local rider username and the path to one JSON. Keep the paired MP4 in the same folder with the filename recorded in the JSON.

```powershell
.\.pothholevenv\Scripts\python.exe manage.py migrate
.\.pothholevenv\Scripts\python.exe manage.py import_phone_export YOUR_RIDER_NAME 'data\YOUR_PHONE_TEST.json'
```

If the counts and review flags look right, add `--apply` to that same command to save it. The command does not print coordinates or absolute timestamps. It does not send anything to GitHub. Do not commit `data/` or `uploads/`.

The importer accepts MP4 only and a maximum of 600 readings captured during recording. The browser test may still have timing and GPS uncertainty. The imported session is private research evidence, not a verified road hazard.

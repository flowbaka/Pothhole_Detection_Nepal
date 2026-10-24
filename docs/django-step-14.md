# Django lesson 14: decode a private journey video

The input check from lesson 13 verifies file availability and GPS timing. This milestone adds actual video decoding with PyAV, the Python interface to FFmpeg. It reads the first video stream through to its end, subject to limits, and prints basic properties. It does not detect potholes, match GPS to frames, or save images from the recording.

## Run it

Install the updated requirements in the project's virtual environment, then use the ID of an already uploaded or imported session:

```powershell
.\.pothholevenv\Scripts\python.exe -m pip install -r requirements.txt
.\.pothholevenv\Scripts\python.exe manage.py inspect_capture_video YOUR_SESSION_ID
```

The PyAV package is installed in the virtual environment, not copied into Git. No new database migration is needed. This is a local operator command; there is no new HTTP decoding endpoint. The existing website and upload API remain available while the command runs.

## Follow the code file by file

1. `captures/management/commands/inspect_capture_video.py` declares a Django command. `uuid.UUID` validates its session-ID argument. `CaptureSession.objects.filter(...).first()` finds the session. The command calls `inspect_session_video()` and prints the returned dictionary as JSON.
2. `captures/video_inspection.py` gets the file's resolved local path and requires it to stay inside `MEDIA_ROOT`. Missing, empty, inaccessible or oversized files produce fixed result codes. No raw storage path is returned.
3. `subprocess.run()` launches a separate Python process using `sys.executable`, which selects the same virtual-environment Python as the command. The arguments are a list, and no shell command is constructed. A 30-second timeout stops the child if it takes too long. Standard error is suppressed because native decoder messages can contain private filenames.
4. `captures/video_probe.py` is the child process. `av.open(..., format="mov")` selects the MP4/MOV reader. Its protocol list allows local files, and external media references are disabled. The first video stream's codec is configured with one decoding thread, a pixel limit and strict decoder error reporting.
5. `for frame in container.decode(stream)` asks FFmpeg to decode each frame. The loop counts frames, checks dimensions and reads presentation timestamps. It keeps summary values rather than collecting the frames into a list. The context manager closes the container on success or failure.
6. `frame.pts * frame.time_base` expresses a frame's presentation time in seconds. The span is the last presentation time minus the first. We do not calculate it by dividing frame count by frame rate, because actual frame spacing may vary.
7. The parent checks the child's exit code and JSON response, then returns only the allowed result fields. A native crash, timeout or malformed response becomes a fixed status without raw errors or paths.
8. `captures/test_video_inspection.py` generates tiny ordinary and fragmented H.264 MP4s from invented pixel values. It exercises real decoding, uneven presentation timestamps, truncated files, malformed headers, missing files, limits, timeouts, child crashes and private-path handling. The timeout/crash cases are simulated; the successful H.264 decode is real, using synthetic frames.

## Understand presentation timestamps

`pts` means presentation timestamp: when a frame should appear on the video's own timeline. `time_base` is the duration of one timestamp unit. Multiplying them converts that timestamp to seconds.

| Frame | PTS | Time base | Presentation time |
|---|---|---|---|
| First generated frame | 0 | 1/5 second | 0 seconds |
| Second generated frame | 1 | 1/5 second | 0.2 seconds |
| Tenth generated frame | 9 | 1/5 second | 1.8 seconds |

Another test uses PTS values 0, 1, 3 and 6 with the same time base. Its frames appear at 0, 0.2, 0.6 and 1.2 seconds. The gaps vary, so using a frame index and an assumed constant FPS would give the wrong timeline. These presentation times are relative media times; they do not by themselves tell us the corresponding phone GPS timestamp.

## Python syntax used here

| Code | Meaning |
|---|---|
| `with av.open(...) as container:` | Open the media container and close it when leaving the block. |
| `container.streams.video[0]` | Select the first video stream; audio is not selected for decoding. |
| `count += 1` | Increase the decoded-frame counter by one. |
| `first_time = last_time = None` | Initialize two variables to an unavailable value. |
| `float(frame.pts * frame.time_base)` | Convert an exact timestamp fraction to a number of seconds. |
| `math.isfinite(...)` | Reject infinite or undefined numbers before producing JSON. |
| `[sys.executable, "-m", ...]` | Build an argument list for another Python process, without a command shell. |
| `subprocess.PIPE` | Capture the child's small JSON response so the parent can read it. |
| `subprocess.DEVNULL` | Discard raw decoder error output. |
| `json.loads(process.stdout)` | Parse the child's JSON text into a Python object. |
| `{**result, "status": "decode_timeout"}` | Make a dictionary containing the session ID plus a fixed timeout status. |
| `key in RESULT_FIELDS` | Allow only the documented summary fields into the final report. |

The command computes its report on demand and does not save decoding results to the database. A later processing-job milestone can add persistent status and a task queue after real-file behavior is checked.

## What a successful result means

The generated ten-frame, 64-by-48-pixel test clip produces these properties:

```json
{
  "status": "decoded",
  "codec": "h264",
  "width_px": 64,
  "height_px": 48,
  "decoded_frames": 10,
  "average_fps": 5.0,
  "reported_duration_s": 2.0,
  "requested_duration_s": 2.0,
  "duration_difference_s": 0.0,
  "decoded_span_s": 1.8,
  "timestamps_increasing": true
}
```

The real command also includes the private session ID. These numbers describe a generated test clip, not a user's recording.

- `width_px` and `height_px` are encoded frame dimensions, not the phone's display orientation.
- `decoded_frames` is the number of frames the decoder actually returned from the first video stream.
- `average_fps` is the stream's reported average rate; it does not establish uniform spacing.
- `reported_duration_s` comes from stream metadata. It is separate from the browser's requested recording duration.
- `requested_duration_s` comes from the journey's saved Start and Stop times. `duration_difference_s` is the reported video duration minus that requested duration. A nonzero difference is information for review; no acceptance threshold or first-frame calibration is assumed.
- `decoded_span_s` runs from the first to the last frame's presentation time. For ten frames at five frames per second, those times are 0 through 1.8 seconds. The final frame's display interval explains why a reported duration can be 2.0 seconds.
- `timestamps_increasing` is false when any decoded timestamp is missing, repeated or decreases. In that case the span is returned as `null`.

`decoded` means the selected stream reached its end without a fatal decoder error within the configured limits. It does not guarantee detection quality, precise GPS alignment, all-track validity, or recovery of every possible corruption. FFmpeg can tolerate some media defects even while decoding.

## Limits and other results

The current local development limits are 300 MiB, 8,294,400 pixels per frame (the pixel count of 3840 x 2160, including portrait equivalents), 18,000 frames and 30 seconds of wall-clock time. They keep this check bounded; they are not a full operating-system security sandbox. Longer or slower videos can hit a limit even when their content is valid.

| Status | Meaning |
|---|---|
| `video_missing` | No video reference is saved. |
| `video_unavailable` | The file is missing, empty, inaccessible or outside local media storage. |
| `invalid_video` | The decoder could not read the selected MP4/MOV stream successfully. |
| `no_video_stream` / `no_video_frames` | No usable video stream or decoded frame was found. |
| `limits_exceeded` | The size, resolution or frame-count cap was exceeded. |
| `dimensions_changed` | Frame dimensions changed within the stream; this inspection does not support that case. |
| `decode_timeout` | The child did not finish within the time budget. |
| `decoder_failed` | The process could not start, crashed or returned an invalid report. |

Reports include no raw frames, arbitrary metadata tags, recording filenames or location data. No actual phone recordings were decoded during this milestone. Try the command on one imported recording before proceeding to the next video-processing milestone.

## References

- [PyAV installation and bundled FFmpeg](https://pypi.org/project/av/)
- [PyAV container decoding](https://pyav.basswood.io/docs/stable/api/container.html)
- [FFmpeg decoder and protocol options](https://www.ffmpeg.org/ffmpeg-all.html)

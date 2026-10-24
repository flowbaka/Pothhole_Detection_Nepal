"""Run local decoding outside the web process with a wall-clock time limit."""

import json
import math
import subprocess
import sys
from pathlib import Path

from django.conf import settings


DECODE_TIMEOUT_SECONDS = 30
MAX_VIDEO_BYTES = 300 * 1024 * 1024
RESULT_FIELDS = {
    "status", "codec", "width_px", "height_px", "decoded_frames", "average_fps",
    "reported_duration_s", "decoded_span_s", "timestamps_increasing",
}
CHILD_STATUSES = {
    "decoded", "invalid_video", "no_video_stream", "no_video_frames",
    "limits_exceeded", "dimensions_changed",
}


def valid_decoded_report(report):
    if not RESULT_FIELDS.issubset(report):
        return False
    for key in ("width_px", "height_px", "decoded_frames"):
        if type(report[key]) is not int or report[key] <= 0:
            return False
    if not isinstance(report["codec"], str) or not report["codec"]:
        return False
    if type(report["timestamps_increasing"]) is not bool:
        return False
    for key in ("average_fps", "reported_duration_s", "decoded_span_s"):
        value = report[key]
        if value is not None and (
            type(value) not in (int, float) or not math.isfinite(value) or value < 0
        ):
            return False
    return True


def inspect_session_video(session):
    result = {
        "session_id": str(session.pk),
        "requested_duration_s": round((session.ended_at - session.started_at).total_seconds(), 6),
    }
    if not session.video:
        return {**result, "status": "video_missing"}
    try:
        path = Path(session.video.path).resolve()
        if not path.is_relative_to(Path(settings.MEDIA_ROOT).resolve()) or not path.is_file():
            return {**result, "status": "video_unavailable"}
        size = path.stat().st_size
        if size == 0:
            return {**result, "status": "video_unavailable"}
        if size > MAX_VIDEO_BYTES:
            return {**result, "status": "limits_exceeded"}
    except (OSError, ValueError, NotImplementedError):
        return {**result, "status": "video_unavailable"}

    try:
        process = subprocess.run(
            [sys.executable, "-m", "captures.video_probe", str(path)],
            cwd=settings.BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=DECODE_TIMEOUT_SECONDS,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        return {**result, "status": "decode_timeout"}
    except OSError:
        return {**result, "status": "decoder_failed"}
    if process.returncode != 0:
        return {**result, "status": "decoder_failed"}
    try:
        decoded = json.loads(process.stdout)
    except (ValueError, UnicodeError):
        return {**result, "status": "decoder_failed"}
    if (
        not isinstance(decoded, dict)
        or not isinstance(decoded.get("status"), str)
        or decoded["status"] not in CHILD_STATUSES
    ):
        return {**result, "status": "decoder_failed"}
    if decoded["status"] != "decoded":
        return {**result, "status": decoded["status"]}
    if not valid_decoded_report(decoded):
        return {**result, "status": "decoder_failed"}
    report = {**result, **{key: value for key, value in decoded.items() if key in RESULT_FIELDS}}
    duration = report["reported_duration_s"]
    report["duration_difference_s"] = (
        round(duration - result["requested_duration_s"], 6) if duration is not None else None
    )
    return report

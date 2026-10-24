"""Read-only checks before a worker attempts video decoding and GPS matching."""


GAP_REVIEW_SECONDS = 5  # Experiment review prompt, not a validated road standard.


def check_session_inputs(session):
    issues = []
    video_available = False
    if not session.video:
        issues.append("video_missing")
    else:
        try:
            storage = session.video.storage
            video_available = (
                storage.exists(session.video.name) and storage.size(session.video.name) > 0
            )
        except OSError:
            # Keep storage paths and operating-system errors out of API responses.
            video_available = False
        if not video_available:
            issues.append("video_unavailable")

    timestamps = list(
        session.gps_readings.order_by("captured_at").values_list("captured_at", flat=True)
    )
    during = [
        value for value in timestamps
        if session.started_at <= value <= session.ended_at
    ]
    outside_count = len(timestamps) - len(during)
    if len(during) < 2:
        issues.append("gps_too_few")
    if outside_count:
        issues.append("gps_outside_recording")
    if len(during) != len(set(during)):
        issues.append("gps_duplicate_timestamps")

    largest_gap = None
    if during:
        boundaries = [session.started_at, *during, session.ended_at]
        largest_gap = max(
            (right - left).total_seconds()
            for left, right in zip(boundaries, boundaries[1:])
        )
        if largest_gap > GAP_REVIEW_SECONDS:
            issues.append("gps_gap_review")

    if not video_available or len(during) < 2:
        status = "missing_inputs"
    elif issues:
        status = "review_inputs"
    else:
        status = "inputs_present"

    return {
        "session_id": str(session.pk),
        "status": status,
        "video_available": video_available,
        "gps_readings_during": len(during),
        "gps_readings_outside": outside_count,
        "largest_gap_s": round(largest_gap, 3) if largest_gap is not None else None,
        "issues": issues,
    }

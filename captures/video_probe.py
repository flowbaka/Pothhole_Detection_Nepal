"""Decode a bounded local MP4 in a child process; emit no frames or file paths."""

import json
import math
import sys

import av


MAX_PIXELS = 3840 * 2160
MAX_FRAMES = 18_000


def positive_number(value):
    if value is None:
        return None
    number = float(value)
    return round(number, 6) if math.isfinite(number) and number > 0 else None


def probe_video(path):
    # Force the MP4/MOV demuxer and disable external media references.
    with av.open(
        str(path),
        format="mov",
        options={"protocol_whitelist": "file", "enable_drefs": "0"},
    ) as container:
        if not container.streams.video:
            return {"status": "no_video_stream"}
        stream = container.streams.video[0]
        codec = stream.codec_context
        if codec.width * codec.height > MAX_PIXELS:
            return {"status": "limits_exceeded"}
        codec.thread_count = 1
        codec.options = {"max_pixels": str(MAX_PIXELS), "err_detect": "explode"}
        first_time = last_time = None
        width = height = 0
        count = 0
        timestamps_complete = True
        for frame in container.decode(stream):
            count += 1
            if count > MAX_FRAMES or frame.width * frame.height > MAX_PIXELS:
                return {"status": "limits_exceeded"}
            if count == 1:
                width, height = frame.width, frame.height
            elif (width, height) != (frame.width, frame.height):
                return {"status": "dimensions_changed"}
            if frame.pts is None or frame.time_base is None:
                timestamps_complete = False
            else:
                frame_time = float(frame.pts * frame.time_base)
                if not math.isfinite(frame_time) or (
                    last_time is not None and frame_time <= last_time
                ):
                    timestamps_complete = False
                if first_time is None:
                    first_time = frame_time
                last_time = frame_time

        if not count:
            return {"status": "no_video_frames"}
        span = None
        if timestamps_complete and first_time is not None and last_time is not None:
            span = round(last_time - first_time, 6)
        duration = None
        if stream.duration is not None and stream.time_base is not None:
            duration = positive_number(stream.duration * stream.time_base)
        return {
            "status": "decoded",
            "codec": codec.name,
            "width_px": width,
            "height_px": height,
            "decoded_frames": count,
            "average_fps": positive_number(stream.average_rate),
            "reported_duration_s": duration,
            "decoded_span_s": span,
            "timestamps_increasing": timestamps_complete,
        }


def main():
    try:
        result = probe_video(sys.argv[1])
    except (av.FFmpegError, OSError, ValueError, IndexError):
        result = {"status": "invalid_video"}
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()

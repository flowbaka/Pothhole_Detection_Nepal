import json
import subprocess
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import av
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings

from .models import CaptureSession
from .video_inspection import inspect_session_video
from .video_probe import probe_video


def make_synthetic_mp4(path, frame_pts=range(10), *, fragmented=False):
    """Generate a small H.264 clip; no camera footage or downloaded fixtures."""
    options = {"movflags": "frag_keyframe+empty_moov+default_base_moof"} if fragmented else {}
    with av.open(str(path), mode="w", format="mp4", options=options) as output:
        stream = output.add_stream("libx264", rate=5)
        stream.width = 64
        stream.height = 48
        stream.pix_fmt = "yuv420p"
        stream.options = {"preset": "ultrafast", "crf": "30"}
        for index, pts in enumerate(frame_pts):
            frame = av.VideoFrame(64, 48, "yuv420p")
            for plane, value in zip(frame.planes, (16 + index * 10, 128, 128)):
                plane.update(bytes([value]) * plane.buffer_size)
            frame.pts = pts
            frame.time_base = Fraction(1, 5)
            for packet in stream.encode(frame):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)


class CaptureVideoInspectionTests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        settings = override_settings(MEDIA_ROOT=self.media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        user = get_user_model().objects.create_user("decode_owner")
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.session = CaptureSession.objects.create(
            owner=user, started_at=start, ended_at=start + timedelta(seconds=10)
        )

    def save_real_synthetic_clip(self, *, fragmented=False):
        path = Path(self.media.name) / "generated.mp4"
        make_synthetic_mp4(path, fragmented=fragmented)
        with path.open("rb") as handle:
            self.session.video.save("video.mp4", File(handle))
        return path

    def test_decodes_a_real_generated_h264_clip_in_a_child_process(self):
        self.save_real_synthetic_clip()
        output = StringIO()
        call_command("inspect_capture_video", str(self.session.pk), stdout=output)
        result = json.loads(output.getvalue())
        self.assertEqual(result["status"], "decoded")
        self.assertEqual(result["decoded_frames"], 10)
        self.assertEqual((result["width_px"], result["height_px"]), (64, 48))
        self.assertEqual(result["codec"], "h264")
        self.assertAlmostEqual(result["average_fps"], 5)
        self.assertAlmostEqual(result["reported_duration_s"], 2)
        self.assertEqual(result["requested_duration_s"], 10)
        self.assertAlmostEqual(result["duration_difference_s"], -8)
        self.assertAlmostEqual(result["decoded_span_s"], 1.8)
        self.assertTrue(result["timestamps_increasing"])
        self.assertNotIn(self.media.name, output.getvalue())
        self.assertNotIn(self.session.video.name, output.getvalue())
        self.assertEqual(CaptureSession.objects.count(), 1)

    def test_a_container_header_alone_is_not_a_decodable_video(self):
        self.session.video.save("header.mp4", ContentFile(b"\x00\x00\x00\x18ftypisom"))
        result = inspect_session_video(self.session)
        self.assertEqual(result["status"], "invalid_video")

    def test_fragmented_mp4_is_also_decodable(self):
        self.save_real_synthetic_clip(fragmented=True)
        result = inspect_session_video(self.session)
        self.assertEqual(result["status"], "decoded")
        self.assertEqual(result["decoded_frames"], 10)
        self.assertAlmostEqual(result["decoded_span_s"], 1.8)

    def test_a_truncated_mp4_is_rejected(self):
        self.save_real_synthetic_clip()
        stored = Path(self.session.video.path)
        content = stored.read_bytes()
        stored.write_bytes(content[:len(content) // 2])
        self.assertEqual(inspect_session_video(self.session)["status"], "invalid_video")

    def test_missing_and_empty_files_do_not_start_a_decoder(self):
        with patch("captures.video_inspection.subprocess.run") as run:
            self.assertEqual(inspect_session_video(self.session)["status"], "video_missing")
            self.session.video.save("empty.mp4", ContentFile(b""))
            self.assertEqual(inspect_session_video(self.session)["status"], "video_unavailable")
            Path(self.session.video.path).unlink()
            self.assertEqual(inspect_session_video(self.session)["status"], "video_unavailable")
            run.assert_not_called()

    def test_timeout_and_native_crash_return_fixed_results(self):
        self.session.video.save("header.mp4", ContentFile(b"\x00\x00\x00\x18ftypisom"))
        with patch(
            "captures.video_inspection.subprocess.run",
            side_effect=subprocess.TimeoutExpired("private-path", 30),
        ):
            self.assertEqual(inspect_session_video(self.session)["status"], "decode_timeout")
        with patch(
            "captures.video_inspection.subprocess.run",
            return_value=subprocess.CompletedProcess([], 1, b"", b"private-path"),
        ):
            self.assertEqual(inspect_session_video(self.session)["status"], "decoder_failed")

    def test_paths_outside_media_root_are_not_decoded(self):
        self.session.video.name = "video.mp4"
        with (
            patch("django.core.files.storage.FileSystemStorage.path", return_value=str(Path(self.media.name).parent)),
            patch("captures.video_inspection.subprocess.run") as run,
        ):
            self.assertEqual(inspect_session_video(self.session)["status"], "video_unavailable")
            run.assert_not_called()

    def test_frame_and_resolution_limits_stop_the_probe(self):
        path = self.save_real_synthetic_clip()
        with patch("captures.video_probe.MAX_FRAMES", 2):
            self.assertEqual(probe_video(path)["status"], "limits_exceeded")
        with patch("captures.video_probe.MAX_PIXELS", 16):
            self.assertEqual(probe_video(path)["status"], "limits_exceeded")

    def test_variable_frame_spacing_uses_timestamps_for_the_span(self):
        path = Path(self.media.name) / "variable.mp4"
        make_synthetic_mp4(path, frame_pts=[0, 1, 3, 6])
        result = probe_video(path)
        self.assertEqual(result["status"], "decoded")
        self.assertEqual(result["decoded_frames"], 4)
        self.assertAlmostEqual(result["decoded_span_s"], 1.2)

    def test_malformed_child_output_does_not_escape_into_the_report(self):
        self.session.video.save("header.mp4", ContentFile(b"\x00\x00\x00\x18ftypisom"))
        for payload in (
            b"private-error-text", b"[]", b'{"status":"unknown","path":"private"}',
            b'{"status":"decoded"}',
            b'{"status":[]}',
        ):
            with self.subTest(payload=payload), patch(
                "captures.video_inspection.subprocess.run",
                return_value=subprocess.CompletedProcess([], 0, payload, b""),
            ):
                result = inspect_session_video(self.session)
                self.assertEqual(
                    result,
                    {"session_id": str(self.session.pk), "requested_duration_s": 10.0, "status": "decoder_failed"},
                )

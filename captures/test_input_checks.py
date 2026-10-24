import json
from datetime import datetime, timedelta, timezone
from io import StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from .models import CaptureSession, GPSReading


class CaptureInputCheckTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("input_owner")
        cls.other = get_user_model().objects.create_user("input_other")
        cls.token = Token.objects.create(user=cls.owner)
        cls.other_token = Token.objects.create(user=cls.other)

    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.session = CaptureSession.objects.create(
            owner=self.owner, started_at=start, ended_at=start + timedelta(seconds=10)
        )
        self.url = f"/api/capture-sessions/{self.session.pk}/input-check/"
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def add_video(self):
        # A synthetic header proves file availability only, never video decoding.
        self.session.video.save("synthetic.mp4", ContentFile(b"\x00\x00\x00\x18ftypisom"))

    def add_readings(self, offsets):
        GPSReading.objects.bulk_create(
            GPSReading(
                session=self.session,
                captured_at=self.session.started_at + timedelta(seconds=offset),
                latitude="10.123456",
                longitude="20.654321",
                accuracy_m="12.50",
            )
            for offset in offsets
        )

    def test_missing_inputs_are_reported_without_writing_records(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "missing_inputs")
        self.assertEqual(response.data["issues"], ["video_missing", "gps_too_few"])
        self.assertIsNone(response.data["largest_gap_s"])
        self.assertEqual(CaptureSession.objects.count(), 1)
        self.assertEqual(GPSReading.objects.count(), 0)

    def test_present_inputs_have_a_coordinate_free_summary(self):
        self.add_video()
        self.add_readings([0, 5, 10])
        response = self.client.get(self.url)
        self.assertEqual(
            response.data,
            {
                "session_id": str(self.session.pk),
                "status": "inputs_present",
                "video_available": True,
                "gps_readings_during": 3,
                "gps_readings_outside": 0,
                "largest_gap_s": 5.0,
                "issues": [],
            },
        )
        self.assertNotIn("10.123456", response.content.decode())
        self.assertNotIn(self.session.video.name, response.content.decode())
        self.assertEqual(self.session.gps_readings.count(), 3)

    def test_a_saved_path_does_not_prove_the_video_file_exists(self):
        self.session.video.name = "capture-videos/private-missing/video.mp4"
        self.session.save(update_fields=["video"])
        self.add_readings([0, 5, 10])
        response = self.client.get(self.url)
        self.assertEqual(response.data["status"], "missing_inputs")
        self.assertEqual(response.data["issues"], ["video_unavailable"])
        self.assertFalse(response.data["video_available"])

    def test_duplicate_and_outside_readings_need_review(self):
        self.add_video()
        self.add_readings([-1, 1, 1, 9, 11])
        response = self.client.get(self.url)
        self.assertEqual(response.data["status"], "review_inputs")
        self.assertEqual(response.data["gps_readings_during"], 3)
        self.assertEqual(response.data["gps_readings_outside"], 2)
        self.assertEqual(response.data["largest_gap_s"], 8)
        self.assertEqual(
            response.data["issues"],
            ["gps_outside_recording", "gps_duplicate_timestamps", "gps_gap_review"],
        )

    def test_gaps_include_the_recording_start_and_end(self):
        self.add_video()
        for offsets in ([6, 7, 8], [2, 3, 4]):
            with self.subTest(offsets=offsets):
                self.session.gps_readings.all().delete()
                self.add_readings(offsets)
                response = self.client.get(self.url)
                self.assertEqual(response.data["largest_gap_s"], 6)
                self.assertEqual(response.data["issues"], ["gps_gap_review"])

    def test_storage_errors_do_not_expose_private_details(self):
        self.add_video()
        with patch(
            "django.core.files.storage.FileSystemStorage.exists",
            side_effect=OSError("private-storage-path-do-not-print"),
        ):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("video_unavailable", response.data["issues"])
        self.assertNotIn("private-storage-path", response.content.decode())

    def test_an_empty_video_file_is_reported_as_unavailable(self):
        self.session.video.save("empty.mp4", ContentFile(b""))
        self.add_readings([0, 5, 10])
        response = self.client.get(self.url)
        self.assertEqual(response.data["status"], "missing_inputs")
        self.assertEqual(response.data["issues"], ["video_unavailable"])

    def test_local_command_produces_the_same_private_summary(self):
        self.add_video()
        self.add_readings([0, 5, 10])
        output = StringIO()
        call_command("check_capture_inputs", str(self.session.pk), stdout=output)
        self.assertEqual(json.loads(output.getvalue()), self.client.get(self.url).data)

    def test_only_the_owner_can_trigger_the_check(self):
        with patch("captures.views.check_session_inputs") as check:
            self.assertEqual(APIClient().get(self.url).status_code, 401)
            self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.other_token.key}")
            self.assertEqual(self.client.get(self.url).status_code, 404)
            check.assert_not_called()

from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from .models import CaptureSession, GPSReading


class CaptureSessionTimeTests(SimpleTestCase):
    def test_rejects_a_session_that_ends_before_it_starts(self):
        start = timezone.now()
        session = CaptureSession(started_at=start, ended_at=start - timedelta(seconds=1))

        with self.assertRaises(ValidationError):
            session.clean()

    def test_accepts_a_session_with_forward_moving_time(self):
        start = timezone.now()
        session = CaptureSession(started_at=start, ended_at=start + timedelta(seconds=1))

        session.clean()


class GPSReadingValidationTests(SimpleTestCase):
    def test_rejects_out_of_range_latitude(self):
        reading = GPSReading(
            captured_at=timezone.now(),
            latitude=Decimal("91"),
            longitude=Decimal("87.2718"),
            accuracy_m=Decimal("12.5"),
        )

        with self.assertRaises(ValidationError) as error:
            reading.full_clean(exclude=["session"], validate_constraints=False)
        self.assertIn("latitude", error.exception.message_dict)

    def test_rejects_zero_accuracy(self):
        reading = GPSReading(
            captured_at=timezone.now(),
            latitude=Decimal("26.4525"),
            longitude=Decimal("87.2718"),
            accuracy_m=Decimal("0"),
        )

        with self.assertRaises(ValidationError) as error:
            reading.full_clean(exclude=["session"], validate_constraints=False)
        self.assertIn("accuracy_m", error.exception.message_dict)


class CaptureSessionAPITests(APITestCase):
    url = "/api/capture-sessions/"

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("rider_one")
        cls.other_user = get_user_model().objects.create_user("rider_two")
        cls.token = Token.objects.create(user=cls.user)

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_anonymous_requests_cannot_list_or_create_sessions(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.get(self.url).status_code, 401)
        self.assertEqual(anonymous.post(self.url, {}, format="json").status_code, 401)

    def test_created_session_belongs_to_authenticated_user(self):
        response = self.client.post(
            self.url,
            {
                "started_at": "2026-10-19T10:00:00Z",
                "ended_at": "2026-10-19T10:01:00Z",
                "owner": self.other_user.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(CaptureSession.objects.get(pk=response.data["id"]).owner, self.user)

    def test_list_only_returns_own_sessions(self):
        start = timezone.now()
        own = CaptureSession.objects.create(
            owner=self.user, started_at=start, ended_at=start + timedelta(minutes=1)
        )
        CaptureSession.objects.create(
            owner=self.other_user,
            started_at=start,
            ended_at=start + timedelta(minutes=1),
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [str(own.pk)])

    def test_rejects_invalid_or_ambiguous_times(self):
        for start, end in [
            ("2026-10-19T10:00:00Z", "2026-10-19T09:59:00Z"),
            ("2026-10-19T10:00:00", "2026-10-19T10:01:00Z"),
        ]:
            response = self.client.post(
                self.url,
                {"started_at": start, "ended_at": end},
                format="json",
            )
            self.assertEqual(response.status_code, 400)
        self.assertEqual(CaptureSession.objects.count(), 0)


class CaptureVideoUploadTests(APITestCase):
    mp4_header = b"\x00\x00\x00\x18ftypisom"

    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("upload_owner")
        cls.other = get_user_model().objects.create_user("upload_other")
        cls.token = Token.objects.create(user=cls.owner)

    def setUp(self):
        start = timezone.now()
        self.session = CaptureSession.objects.create(
            owner=self.owner, started_at=start, ended_at=start + timedelta(minutes=1)
        )
        self.url = f"/api/capture-sessions/{self.session.pk}/video/"
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def upload(self, content=None, name="recording.mp4"):
        video = SimpleUploadedFile(
            name, self.mp4_header if content is None else content, content_type="video/mp4"
        )
        return self.client.put(self.url, {"video": video}, format="multipart")

    def test_only_owner_can_upload_and_video_is_not_public(self):
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            anonymous = APIClient()
            self.assertEqual(
                anonymous.put(
                    self.url,
                    {"video": SimpleUploadedFile("x.mp4", self.mp4_header)},
                    format="multipart",
                ).status_code,
                401,
            )
            self.client.credentials(
                HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.other).key}"
            )
            self.assertEqual(self.upload().status_code, 404)
            self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

            response = self.upload(name="../../private.mp4")

            self.assertEqual(response.status_code, 201)
            self.session.refresh_from_db()
            self.assertEqual(
                self.session.video.name,
                f"capture-videos/{self.session.pk}/video.mp4",
            )
            self.assertTrue((Path(root) / self.session.video.name).is_file())
            self.assertNotIn("video", self.client.get("/api/capture-sessions/").data[0])
            self.assertEqual(self.upload().status_code, 409)

    def test_rejects_bad_header_extension_and_oversized_file(self):
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            self.assertEqual(self.upload(content=b"not an mp4 file").status_code, 400)
            self.assertEqual(self.upload(name="video.exe").status_code, 400)
            with patch("captures.views.MAX_VIDEO_BYTES", 8):
                self.assertEqual(self.upload().status_code, 413)
            with (
                patch("captures.views.MAX_VIDEO_BYTES", len(self.mp4_header)),
                patch("captures.views.MAX_MULTIPART_OVERHEAD_BYTES", 0),
            ):
                self.assertEqual(self.upload().status_code, 413)
            self.session.refresh_from_db()
            self.assertFalse(self.session.video)
            self.assertEqual(list(Path(root).rglob("*")), [])

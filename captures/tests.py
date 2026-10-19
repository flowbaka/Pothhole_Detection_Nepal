from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
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

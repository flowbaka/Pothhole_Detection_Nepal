from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.utils import timezone

from .models import CaptureSession


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

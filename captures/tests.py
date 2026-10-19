from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.utils import timezone

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

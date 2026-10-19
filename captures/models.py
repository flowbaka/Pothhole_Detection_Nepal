import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q


class CaptureSession(models.Model):
    """Private metadata for one recorded journey; video upload comes later."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(ended_at__gt=F("started_at")),
                name="capture_session_ends_after_start",
            )
        ]

    def clean(self):
        super().clean()
        if self.started_at and self.ended_at and self.ended_at <= self.started_at:
            raise ValidationError({"ended_at": "End time must be after start time."})


class GPSReading(models.Model):
    """A private, timestamped phone location from one capture session."""

    session = models.ForeignKey(
        CaptureSession, on_delete=models.CASCADE, related_name="gps_readings"
    )
    captured_at = models.DateTimeField()
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    accuracy_m = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )

    class Meta:
        indexes = [models.Index(fields=["session", "captured_at"])]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(latitude__gte=-90)
                    & Q(latitude__lte=90)
                    & Q(longitude__gte=-180)
                    & Q(longitude__lte=180)
                    & Q(accuracy_m__gt=0)
                ),
                name="gps_reading_valid_coordinates_and_accuracy",
            )
        ]

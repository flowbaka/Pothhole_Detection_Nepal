import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
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

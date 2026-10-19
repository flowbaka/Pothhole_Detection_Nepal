import re

from rest_framework import serializers

from .models import CaptureSession


class OffsetDateTimeField(serializers.DateTimeField):
    """Require an explicit UTC offset from a recording device."""

    def to_internal_value(self, value):
        if not isinstance(value, str) or not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", value):
            raise serializers.ValidationError("Include a timezone offset or Z.")
        return super().to_internal_value(value)


class CaptureSessionSerializer(serializers.ModelSerializer):
    started_at = OffsetDateTimeField()
    ended_at = OffsetDateTimeField()

    class Meta:
        model = CaptureSession
        fields = ["id", "started_at", "ended_at", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        if attrs["ended_at"] <= attrs["started_at"]:
            raise serializers.ValidationError(
                {"ended_at": "End time must be after start time."}
            )
        return attrs

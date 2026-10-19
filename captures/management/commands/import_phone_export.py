"""Import one local iPhone recorder experiment without printing its locations."""

import json
import uuid
from datetime import datetime, timezone as utc_timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.utils import timezone

from captures.models import CaptureSession, GPSReading
from captures.views import MAX_VIDEO_BYTES
from scripts.inspect_recording import analyze


MAX_JSON_BYTES = 5 * 1024 * 1024


def instant(epoch_ms):
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=utc_timezone.utc)
    except (OverflowError, OSError, ValueError) as error:
        raise CommandError("The export contains an invalid recording time.") from error


class Command(BaseCommand):
    help = "Validate one paired MP4/JSON phone export; use --apply to import it privately."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Existing local rider account")
        parser.add_argument("json_file", type=Path, help="Path to the recorder's JSON export")
        parser.add_argument("--apply", action="store_true", help="Write the validated export to Django")

    def handle(self, *args, **options):
        source = options["json_file"].resolve()
        try:
            if not source.is_file() or source.stat().st_size > MAX_JSON_BYTES:
                raise CommandError("Choose one JSON export smaller than 5 MiB.")
            data = json.loads(source.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise CommandError("Cannot read a valid phone-export JSON file.") from error

        try:
            summary = analyze(data)
        except ValueError as error:
            raise CommandError(f"The phone export failed its timing check: {error}") from error

        test_id = data.get("test_id")
        if not isinstance(test_id, str) or not test_id.startswith("phone-test-"):
            raise CommandError("The phone export has no valid test ID.")
        try:
            uuid.UUID(test_id.removeprefix("phone-test-"))
        except ValueError as error:
            raise CommandError("The phone export has no valid test ID.") from error
        if len(test_id) > 50 or data.get("video_filename") != f"{test_id}.mp4":
            raise CommandError("The matching MP4 must keep its original filename.")
        if not str(data.get("video_mime_type", "")).startswith("video/mp4"):
            raise CommandError("This importer accepts MP4 exports only.")

        video_path = source.parent / f"{test_id}.mp4"
        if video_path.resolve().parent != source.parent:
            raise CommandError("The matching MP4 must be beside the JSON export.")
        try:
            size = video_path.stat().st_size
            with video_path.open("rb") as video_file:
                header = video_file.read(12)
        except OSError as error:
            raise CommandError("The matching MP4 is missing or unreadable.") from error
        if (
            size == 0
            or size > MAX_VIDEO_BYTES
            or size != data.get("video_bytes")
            or len(header) < 12
            or header[4:8] != b"ftyp"
            or int.from_bytes(header[:4], "big") < 8
        ):
            raise CommandError("The MP4 failed its size or container-header check.")

        start_ms = data["recording_start_requested"]["epoch_ms"]
        stop_ms = data["recording_stop_requested"]["epoch_ms"]
        if stop_ms <= start_ms:
            raise CommandError("The recording end must follow its start.")
        readings = [
            item for item in data["locations"]
            if start_ms <= item["timestamp_epoch_ms"] <= stop_ms
        ]
        if not 1 <= len(readings) <= 600:
            raise CommandError("The recording needs 1 to 600 in-window GPS readings.")

        owner = get_user_model().objects.filter(username=options["username"], is_active=True).first()
        if owner is None:
            raise CommandError("Choose an existing active local rider account.")
        if CaptureSession.objects.filter(source_test_id=test_id).exists():
            raise CommandError("This phone export was already imported.")

        session = CaptureSession(
            owner=owner,
            source_test_id=test_id,
            started_at=instant(start_ms),
            ended_at=instant(stop_ms),
        )
        try:
            session.full_clean()
        except ValidationError as error:
            raise CommandError("The recording times or test ID are invalid.") from error
        gps_rows = []
        for item in readings:
            try:
                row = GPSReading(
                    session=session,
                    captured_at=instant(item["timestamp_epoch_ms"]),
                    latitude=Decimal(str(item["latitude"])).quantize(Decimal("0.000001")),
                    longitude=Decimal(str(item["longitude"])).quantize(Decimal("0.000001")),
                    accuracy_m=Decimal(str(item["accuracy_m"])).quantize(Decimal("0.01")),
                )
                row.full_clean(exclude=["session"], validate_unique=False, validate_constraints=False)
            except (InvalidOperation, ValidationError) as error:
                raise CommandError("A GPS reading is outside the supported precision or range.") from error
            gps_rows.append(row)

        self.stdout.write(
            f"Validated MP4 and {len(readings)} in-window GPS readings; "
            f"{len(summary['flags'])} review flags. No coordinates were printed."
        )
        if not options["apply"]:
            self.stdout.write("Dry run only. Add --apply to import this experiment.")
            return

        try:
            with transaction.atomic():
                session.save()
                with video_path.open("rb") as video_file:
                    session.video.save("video.mp4", File(video_file), save=False)
                session.video_uploaded_at = timezone.now()
                session.save(update_fields=["video", "video_uploaded_at"])
                GPSReading.objects.bulk_create(gps_rows)
        except IntegrityError as error:
            if session.video.name:
                session.video.storage.delete(session.video.name)
            raise CommandError("The experiment could not be saved; check for a duplicate import.") from error
        except Exception:
            if session.video.name:
                session.video.storage.delete(session.video.name)
            raise

        self.stdout.write(self.style.SUCCESS(f"Imported private experiment session {session.pk}."))

"""Inspect one private local video without publishing frames or metadata tags."""

import json
import uuid

from django.core.management.base import BaseCommand, CommandError

from captures.models import CaptureSession
from captures.video_inspection import inspect_session_video


class Command(BaseCommand):
    help = "Decode a local journey's MP4 within limits and print basic video properties."

    def add_arguments(self, parser):
        parser.add_argument("session_id", type=uuid.UUID)

    def handle(self, *args, **options):
        session = CaptureSession.objects.filter(pk=options["session_id"]).first()
        if session is None:
            raise CommandError("Journey not found.")
        self.stdout.write(json.dumps(inspect_session_video(session), indent=2))

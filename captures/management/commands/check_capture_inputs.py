"""Inspect one private journey locally without printing route coordinates."""

import json
import uuid

from django.core.management.base import BaseCommand, CommandError

from captures.input_checks import check_session_inputs
from captures.models import CaptureSession


class Command(BaseCommand):
    help = "Summarize one journey's video availability and GPS timing for local review."

    def add_arguments(self, parser):
        parser.add_argument("session_id", type=uuid.UUID)

    def handle(self, *args, **options):
        session = CaptureSession.objects.filter(pk=options["session_id"]).first()
        if session is None:
            raise CommandError("Journey not found.")
        self.stdout.write(json.dumps(check_session_inputs(session), indent=2))

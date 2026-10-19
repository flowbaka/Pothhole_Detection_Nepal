"""Create a non-admin rider locally and show their API token once."""

from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = "Create a local test rider and show one private API token."

    def handle(self, *args, **options):
        username = input("Rider username: ").strip()
        if not username:
            raise CommandError("A username is required.")

        user = get_user_model()(username=username)
        password = getpass("Rider password (hidden): ")
        try:
            validate_password(password, user=user)
            user.set_password(password)
            user.full_clean()
        except ValidationError as error:
            raise CommandError("; ".join(error.messages)) from error

        with transaction.atomic():
            user.save()
            token = Token.objects.create(user=user)

        self.stdout.write("Rider created. Copy this token privately; it will not be shown again:")
        self.stdout.write(token.key)

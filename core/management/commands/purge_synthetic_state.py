from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import SyntheticSession


class Command(BaseCommand):
    help = "Delete expired synthetic-only Increment 2 state."

    def handle(self, *args, **options):
        deleted, _ = SyntheticSession.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write(f"Deleted {deleted} expired synthetic state records.")

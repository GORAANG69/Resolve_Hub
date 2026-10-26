from django.core.management.base import BaseCommand
from apps.institutions.models import Institution
from apps.institutions.risk import compute_risk


class Command(BaseCommand):
    help = "Compute explainable risk scores for all active institutions (idempotent)."

    def handle(self, *args, **options):
        institutions = Institution.objects.filter(is_active=True)
        count = 0
        for inst in institutions:
            compute_risk(inst)
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Computed risk scores for {count} institutions.")
        )

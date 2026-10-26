from django.core.management.base import BaseCommand
from apps.complaints.escalation import run_escalation_check


class Command(BaseCommand):
    help = "Run SLA check and upward escalations (L1/L2/L3) across active grievances (idempotent)."

    def handle(self, *args, **options):
        events = run_escalation_check()
        self.stdout.write(
            self.style.SUCCESS(f"SLA Autopilot check complete: {len(events)} new escalation events triggered.")
        )

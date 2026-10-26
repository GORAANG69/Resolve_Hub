from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Role
from apps.complaints.integrations.cpgrams import FileCPGRAMSAdapter
from apps.complaints.models import Complaint, SourceChannel
from apps.complaints.services import register_complaint
from apps.institutions.models import Institution


class Command(BaseCommand):
    help = "Import grievances from CPGRAMS export file (CSV or JSON) idempotently."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to export file (.csv or .json)")

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        adapter = FileCPGRAMSAdapter(file_path)
        items = adapter.fetch_new_grievances()

        User = get_user_model()
        created = 0
        skipped = 0

        for item in items:
            ext_ref = item.get("external_reference")
            if not ext_ref:
                continue

            # Idempotency check via external_reference
            if Complaint.objects.filter(external_reference=ext_ref).exists():
                skipped += 1
                continue

            # Find or create user
            email = item.get("complainant_email") or f"cpgrams-{ext_ref.lower()}@cpgrams.gov.in"
            user = User.objects.filter(email=email).first()
            if not user:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    full_name=item.get("complainant_name", "CPGRAMS Complainant"),
                    mobile_number=item.get("complainant_mobile", ""),
                    role=Role.STUDENT,
                    is_active=True,
                )

            # Match institution
            inst_query = item.get("institution_name_or_id", "")
            institution = (
                Institution.objects.filter(aicte_id=inst_query).first()
                or Institution.objects.filter(name__icontains=inst_query).first()
            )

            register_complaint(
                submitting_user=user,
                institution=institution,
                subject=item.get("subject", "CPGRAMS Complaint"),
                description=item.get("description", "Details from CPGRAMS grievance portal."),
                source_channel=SourceChannel.CPGRAMS,
                external_reference=ext_ref,
                consent_given=True,
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"CPGRAMS import complete: {created} imported, {skipped} already existed.")
        )

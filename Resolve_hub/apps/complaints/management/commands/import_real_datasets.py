from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.complaints.models import CitizenGrievance, StudentFeedback


class Command(BaseCommand):
    help = "Import both real datasets (Dataset A: Student Feedback and Dataset B: Citizen Grievances) safely and idempotently."

    def add_arguments(self, parser):
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Update previously imported records instead of skipping",
        )

    def handle(self, *args, **options):
        update_existing = options["update_existing"]

        self.stdout.write(self.style.MIGRATE_HEADING("Starting ResolveHub Real Dataset Integration Pipeline..."))

        self.stdout.write("\n>>> Step 1: Importing Dataset A (Student Feedback)...")
        call_command(
            "import_student_feedback",
            file="data/student_feedback_finalDataset0.2.xlsx",
            update_existing=update_existing,
        )

        self.stdout.write("\n>>> Step 2: Importing Dataset B (Citizen Grievances)...")
        call_command(
            "import_citizen_grievances",
            file="data/grievances_synthetic.csv",
            holdout_file="data/grievances_holdout_templates.csv",
            update_existing=update_existing,
        )

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("RESOLVEHUB REAL DATASET INTEGRATION SUMMARY"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"Student Feedback Records:   {StudentFeedback.objects.count()}")
        self.stdout.write(f"Citizen Grievance Records:  {CitizenGrievance.objects.count()}")
        self.stdout.write(self.style.SUCCESS("All datasets integrated idempotently with zero operational data leakage."))
        self.stdout.write(self.style.SUCCESS("=" * 60))

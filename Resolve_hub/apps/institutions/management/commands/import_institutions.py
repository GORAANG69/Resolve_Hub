import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from apps.institutions.models import Institution, InstitutionType


class Command(BaseCommand):
    help = "Import institutions from a CSV file (aicte_id,name,state,district,institution_type)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to CSV file to import.")

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        valid_types = {t.value: t.value for t in InstitutionType}
        created = 0
        updated = 0

        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                aicte_id = row.get("aicte_id", "").strip()
                name = row.get("name", "").strip()
                state = row.get("state", "").strip()
                district = row.get("district", "").strip()
                raw_type = row.get("institution_type", "ENGINEERING").strip().upper()
                inst_type = valid_types.get(raw_type, InstitutionType.OTHER)

                if not aicte_id or not name:
                    continue

                obj, is_new = Institution.objects.update_or_create(
                    aicte_id=aicte_id,
                    defaults={
                        "name": name,
                        "state": state,
                        "district": district,
                        "institution_type": inst_type,
                        "is_active": True,
                    },
                )
                if is_new:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"Import complete: {created} created, {updated} updated.")
        )

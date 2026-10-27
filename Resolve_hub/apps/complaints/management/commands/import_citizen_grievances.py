import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.complaints.models import CitizenGrievance
from apps.triage.classifier import detect_language


class Command(BaseCommand):
    help = (
        "Idempotently import multilingual citizen grievances from Dataset B "
        "(abhisheksingh016/citizen-grievance-dataset, CSV format)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="data/grievances_synthetic.csv",
            help="Path to main synthetic grievances CSV (default: data/grievances_synthetic.csv)",
        )
        parser.add_argument(
            "--holdout-file",
            default="data/grievances_holdout_templates.csv",
            help="Path to holdout templates CSV (default: data/grievances_holdout_templates.csv)",
        )
        parser.add_argument(
            "--batch",
            default="abhisheksingh016/citizen-grievance-dataset",
            help="Source batch identifier for provenance tracking",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Update previously imported records instead of skipping",
        )
        parser.add_argument(
            "--skip-holdout",
            action="store_true",
            help="Skip importing holdout templates file",
        )

    def handle(self, *args, **options):
        main_file = Path(options["file"])
        holdout_file = Path(options["holdout_file"])
        batch_id = options["batch"]
        update_existing = options["update_existing"]
        skip_holdout = options["skip_holdout"]

        if not main_file.exists():
            raise CommandError(f"Main dataset file not found at: {main_file}")

        files_to_process = [(main_file, "synthetic")]
        if not skip_holdout and holdout_file.exists():
            files_to_process.append((holdout_file, "holdout_templates"))

        total_rows_read = 0
        total_inserted = 0
        total_updated = 0
        total_skipped = 0
        total_invalid = 0
        total_duplicates = 0

        for fpath, ftype in files_to_process:
            self.stdout.write(f"Processing {ftype} file: {fpath}...")
            inserted, updated, skipped, invalid, dups, count = self._import_file(
                fpath, ftype, batch_id, update_existing
            )
            total_rows_read += count
            total_inserted += inserted
            total_updated += updated
            total_skipped += skipped
            total_invalid += invalid
            total_duplicates += dups

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("CITIZEN GRIEVANCE IMPORT REPORT (DATASET B)"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"Source batch:        {batch_id}")
        self.stdout.write(f"Total rows read:     {total_rows_read}")
        self.stdout.write(f"Records inserted:    {total_inserted}")
        self.stdout.write(f"Records updated:     {total_updated}")
        self.stdout.write(f"Duplicates detected: {total_duplicates}")
        self.stdout.write(f"Records skipped:     {total_skipped}")
        self.stdout.write(f"Invalid / empty:     {total_invalid}")
        self.stdout.write(f"Total in database:   {CitizenGrievance.objects.count()}")
        self.stdout.write(self.style.SUCCESS("=" * 60))

    def _import_file(self, file_path: Path, source_type: str, batch_id: str, update_existing: bool):
        inserted = 0
        updated = 0
        skipped = 0
        invalid = 0
        duplicates = 0
        count = 0

        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = [fn.strip().lower() for fn in (reader.fieldnames or [])]

            id_col = "grievance_id" if "grievance_id" in fieldnames else None
            text_col = "text" if "text" in fieldnames else None
            cat_col = "category" if "category" in fieldnames else None

            if not (id_col and text_col and cat_col):
                raise CommandError(
                    f"File {file_path} missing required columns: grievance_id, text, category"
                )

            batch_records = []
            for row in reader:
                count += 1
                gid = (row.get("grievance_id") or "").strip()
                text = (row.get("text") or "").strip()
                cat = (row.get("category") or "").strip()

                if not gid or not text:
                    invalid += 1
                    continue

                lang = detect_language(text)

                batch_records.append({
                    "grievance_id": gid,
                    "text": text,
                    "category": cat or "General",
                    "language": lang,
                    "source_file": file_path.name,
                    "source_batch": batch_id,
                })

                if len(batch_records) >= 500:
                    ins, upd, skp, dup = self._persist_batch(batch_records, update_existing)
                    inserted += ins
                    updated += upd
                    skipped += skp
                    duplicates += dup
                    batch_records = []

            if batch_records:
                ins, upd, skp, dup = self._persist_batch(batch_records, update_existing)
                inserted += ins
                updated += upd
                skipped += skp
                duplicates += dup

        return inserted, updated, skipped, invalid, duplicates, count

    def _persist_batch(self, records, update_existing: bool):
        inserted = 0
        updated = 0
        skipped = 0
        duplicates = 0

        gids = [r["grievance_id"] for r in records]
        existing_map = {
            g.grievance_id: g
            for g in CitizenGrievance.objects.filter(grievance_id__in=gids)
        }

        to_create = []

        with transaction.atomic():
            for r in records:
                gid = r["grievance_id"]
                if gid in existing_map:
                    duplicates += 1
                    if update_existing:
                        obj = existing_map[gid]
                        obj.text = r["text"]
                        obj.category = r["category"]
                        obj.language = r["language"]
                        obj.source_file = r["source_file"]
                        obj.source_batch = r["source_batch"]
                        obj.save(update_fields=[
                            "text", "category", "language", "source_file", "source_batch"
                        ])
                        updated += 1
                    else:
                        skipped += 1
                else:
                    to_create.append(CitizenGrievance(
                        grievance_id=gid,
                        text=r["text"],
                        category=r["category"],
                        language=r["language"],
                        source_file=r["source_file"],
                        source_batch=r["source_batch"],
                    ))
                    inserted += 1

            if to_create:
                CitizenGrievance.objects.bulk_create(to_create, ignore_conflicts=True)

        return inserted, updated, skipped, duplicates

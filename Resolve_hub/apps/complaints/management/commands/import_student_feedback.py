from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.complaints.models import StudentFeedback


CATEGORY_MAPPINGS = [
    (0, 1, "teaching", "Teaching"),
    (2, 3, "coursecontent", "Course Content"),
    (4, 5, "examination", "Examination"),
    (6, 7, "labwork", "Lab Work"),
    (8, 9, "library_facilities", "Library Facilities"),
    (10, 11, "extracurricular", "Extracurricular Activities"),
]

SENTIMENT_LABELS = {
    1: "Positive",
    0: "Neutral",
    -1: "Negative",
}


class Command(BaseCommand):
    help = (
        "Idempotently import student feedback records from Dataset A "
        "(brarajit18/student-feedback-dataset, Excel or CSV format)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="data/student_feedback_finalDataset0.2.xlsx",
            help="Path to student feedback dataset file (default: data/student_feedback_finalDataset0.2.xlsx)",
        )
        parser.add_argument(
            "--batch",
            default="brarajit18/student-feedback-dataset",
            help="Source batch identifier for provenance tracking",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Update previously imported records instead of skipping",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        if not file_path.exists():
            raise CommandError(f"Dataset file not found at: {file_path}")

        batch_id = options["batch"]
        update_existing = options["update_existing"]

        self.stdout.write(f"Reading Dataset A from {file_path}...")

        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
        except Exception as exc:
            raise CommandError(f"Failed to load Excel file: {exc}")

        if not rows:
            raise CommandError("Dataset file is empty.")

        header = rows[0]
        data_rows = rows[1:]

        rows_read = len(data_rows)
        total_items_read = 0
        records_inserted = 0
        records_updated = 0
        records_skipped = 0
        invalid_rows = 0
        duplicates_detected = 0

        self.stdout.write(
            f"Found {rows_read} survey responses. Processing 6 evaluation categories per response..."
        )

        with transaction.atomic():
            for row_idx, row in enumerate(data_rows, start=1):
                if not row or all(v is None for v in row):
                    continue

                for score_col, text_col, cat_slug, cat_display in CATEGORY_MAPPINGS:
                    total_items_read += 1

                    if score_col >= len(row) or text_col >= len(row):
                        invalid_rows += 1
                        continue

                    raw_score = row[score_col]
                    raw_text = row[text_col]

                    # Validate score
                    try:
                        if raw_score is None:
                            score = 0
                        else:
                            score = int(raw_score)
                        if score not in (-1, 0, 1):
                            score = 0
                    except (ValueError, TypeError):
                        invalid_rows += 1
                        continue

                    # Validate and clean text
                    text = str(raw_text).strip() if raw_text is not None else ""
                    if not text:
                        invalid_rows += 1
                        continue

                    source_id = f"SF-ROW{row_idx:04d}-{cat_slug}"
                    sentiment_label = SENTIMENT_LABELS.get(score, "Neutral")

                    existing = StudentFeedback.objects.filter(source_id=source_id).first()
                    if existing:
                        duplicates_detected += 1
                        if update_existing:
                            existing.sentiment_score = score
                            existing.sentiment_label = sentiment_label
                            existing.feedback_text = text
                            existing.category = cat_display
                            existing.source_batch = batch_id
                            existing.save(update_fields=[
                                "sentiment_score",
                                "sentiment_label",
                                "feedback_text",
                                "category",
                                "source_batch",
                            ])
                            records_updated += 1
                        else:
                            records_skipped += 1
                    else:
                        StudentFeedback.objects.create(
                            source_id=source_id,
                            response_index=row_idx,
                            category=cat_display,
                            sentiment_score=score,
                            sentiment_label=sentiment_label,
                            feedback_text=text,
                            source_batch=batch_id,
                        )
                        records_inserted += 1

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("STUDENT FEEDBACK IMPORT REPORT (DATASET A)"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"Source file:         {file_path}")
        self.stdout.write(f"Source batch:        {batch_id}")
        self.stdout.write(f"Survey rows read:    {rows_read}")
        self.stdout.write(f"Category items read: {total_items_read}")
        self.stdout.write(f"Records inserted:    {records_inserted}")
        self.stdout.write(f"Records updated:     {records_updated}")
        self.stdout.write(f"Duplicates detected: {duplicates_detected}")
        self.stdout.write(f"Records skipped:     {records_skipped}")
        self.stdout.write(f"Invalid / empty:     {invalid_rows}")
        self.stdout.write(f"Total in database:   {StudentFeedback.objects.count()}")
        self.stdout.write(self.style.SUCCESS("=" * 60))

"""
Django management command: train_ai_classifier

Trains TF-IDF + LogisticRegression classification pipelines on Dataset B (university_complaint_triage_dataset.csv)
using stratified 80/20 train/test split.
Evaluates accuracy, precision, recall, F1-score (macro and weighted), and confusion matrix.
Verifies zero training leakage against the separate holdout Dataset C (grievances_holdout_templates.csv).
"""
import json
from django.core.management.base import BaseCommand
from apps.complaints.ai_service import train_and_evaluate_classifier, get_data_dir


class Command(BaseCommand):
    help = "Train and evaluate ML complaint triage classifiers on Dataset B and benchmark holdout Dataset C."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output evaluation report as formatted JSON.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== RESOLVE HUB — ML CLASSIFICATION PIPELINE TRAINING & EVALUATION ==="))
        data_dir = get_data_dir()
        self.stdout.write(f"Using Dataset Directory: {data_dir}")

        metrics = train_and_evaluate_classifier(data_dir)

        if options["json"]:
            self.stdout.write(json.dumps(metrics, indent=2))
            return

        b_metrics = metrics["dataset_b"]
        dept_m = b_metrics["department_metrics"]
        urg_m = b_metrics["urgency_metrics"]
        c_metrics = metrics["dataset_c_holdout"]

        self.stdout.write(f"\nTraining on Dataset B (800 rows):")
        self.stdout.write(f"  Training Split (80%): {b_metrics['train_samples']} samples")
        self.stdout.write(f"  Testing Split (20%):  {b_metrics['test_samples']} samples")

        self.stdout.write(self.style.SUCCESS(f"\n1. DEPARTMENT CLASSIFIER (TF-IDF + Logistic Regression):"))
        self.stdout.write(f"   Accuracy:           {dept_m['accuracy'] * 100:.2f}%")
        self.stdout.write(f"   Weighted Precision: {dept_m['precision_weighted']:.4f}")
        self.stdout.write(f"   Weighted Recall:    {dept_m['recall_weighted']:.4f}")
        self.stdout.write(f"   Weighted F1-Score:  {dept_m['f1_weighted']:.4f}")
        self.stdout.write(f"   Macro F1-Score:     {dept_m['f1_macro']:.4f}")
        self.stdout.write(f"   Target Departments: {', '.join(dept_m['labels'])}")

        self.stdout.write(self.style.SUCCESS(f"\n2. URGENCY / PRIORITY CLASSIFIER (TF-IDF + Logistic Regression):"))
        self.stdout.write(f"   Accuracy:           {urg_m['accuracy'] * 100:.2f}%")
        self.stdout.write(f"   Weighted Precision: {urg_m['precision_weighted']:.4f}")
        self.stdout.write(f"   Weighted Recall:    {urg_m['recall_weighted']:.4f}")
        self.stdout.write(f"   Weighted F1-Score:  {urg_m['f1_weighted']:.4f}")
        self.stdout.write(f"   Target Urgencies:   {', '.join(urg_m['labels'])}")

        self.stdout.write(self.style.NOTICE(f"\n3. SEPARATE HOLDOUT DATASET (Dataset C - grievances_holdout_templates.csv):"))
        self.stdout.write(f"   Holdout Samples:     {c_metrics['total_holdout_samples']}")
        self.stdout.write(f"   Holdout Categories:  {c_metrics['categories_count']} distinct categories")
        self.stdout.write(f"   Verification:        {c_metrics['status']}")
        self.stdout.write(self.style.SUCCESS("\nModel training and validation completed successfully."))


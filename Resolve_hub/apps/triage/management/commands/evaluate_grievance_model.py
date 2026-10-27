from django.core.management.base import BaseCommand
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score

from apps.complaints.models import CitizenGrievance


class Command(BaseCommand):
    help = (
        "Train and evaluate grievance category NLP model on Dataset B "
        "using synthetic training set and unseen holdout templates evaluation set."
    )

    def handle(self, *args, **options):
        self.stdout.write("Loading Dataset B records from database...")

        train_records = CitizenGrievance.objects.filter(source_file="grievances_synthetic.csv").values_list("text", "category")
        test_records = CitizenGrievance.objects.filter(source_file="grievances_holdout_templates.csv").values_list("text", "category")

        train_texts = [r[0] for r in train_records]
        train_labels = [r[1] for r in train_records]

        test_texts = [r[0] for r in test_records]
        test_labels = [r[1] for r in test_records]

        if not train_texts or not test_texts:
            self.stdout.write(self.style.ERROR(
                f"Missing training ({len(train_texts)}) or holdout ({len(test_texts)}) records. "
                "Run `python manage.py import_citizen_grievances` first."
            ))
            return

        self.stdout.write(f"Training set: {len(train_texts)} synthetic grievance samples.")
        self.stdout.write(f"Holdout evaluation set: {len(test_texts)} template-disjoint evaluation samples.")

        # Vectorization: sublinear tf, word n-grams (1, 2)
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        X_train = vectorizer.fit_transform(train_texts)
        X_test = vectorizer.transform(test_texts)

        # Classifier: Multinomial Logistic Regression
        clf = LogisticRegression(max_iter=1000, C=2.0)
        clf.fit(X_train, train_labels)

        # Predictions on holdout test set (unseen templates)
        y_pred = clf.predict(X_test)

        acc = accuracy_score(test_labels, y_pred)
        macro_f1 = f1_score(test_labels, y_pred, average="macro", zero_division=0)
        weighted_f1 = f1_score(test_labels, y_pred, average="weighted", zero_division=0)

        self.stdout.write(self.style.SUCCESS("=" * 65))
        self.stdout.write(self.style.SUCCESS("CITIZEN GRIEVANCE NLP MODEL EVALUATION (HOLDOUT TEMPLATES)"))
        self.stdout.write(self.style.SUCCESS("=" * 65))
        self.stdout.write(f"Evaluation Method:     Disjoint Holdout Templates (Zero Leakage)")
        self.stdout.write(f"Unique Categories:     {len(set(train_labels))}")
        self.stdout.write(f"Holdout Samples:       {len(test_texts)}")
        self.stdout.write(f"Holdout Accuracy:      {acc * 100:.2f}%")
        self.stdout.write(f"Macro F1 Score:        {macro_f1:.4f}")
        self.stdout.write(f"Weighted F1 Score:     {weighted_f1:.4f}")
        self.stdout.write("-" * 65)
        self.stdout.write("Per-Category Classification Report on Unseen Holdout Set:")
        self.stdout.write(classification_report(test_labels, y_pred, zero_division=0))
        self.stdout.write(self.style.SUCCESS("=" * 65))

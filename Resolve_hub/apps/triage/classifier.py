from __future__ import annotations

import csv
import logging
import re
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_MODEL = None
_VECTORIZER = None


def detect_language(text: str) -> str:
    """
    Devanagari Unicode ratio heuristic:
    Range [\u0900-\u097F] is Devanagari.
    If ratio of Devanagari characters to total alpha characters >= 0.2 -> 'hi', else 'en'.
    """
    if not text:
        return "en"

    devanagari_count = len(re.findall(r"[\u0900-\u097F]", text))
    latin_count = len(re.findall(r"[a-zA-Z]", text))
    total_alpha = devanagari_count + latin_count

    if total_alpha == 0:
        return "en"

    if (devanagari_count / total_alpha) >= 0.2:
        return "hi"
    return "en"


def _load_and_train_model():
    global _MODEL, _VECTORIZER
    if _MODEL is not None and _VECTORIZER is not None:
        return _MODEL, _VECTORIZER

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    csv_path = Path(__file__).resolve().parent / "data" / "seed_training.csv"
    texts = []
    labels = []

    if csv_path.exists():
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                t = row.get("text", "").strip()
                cat = row.get("category", "").strip()
                if t and cat:
                    texts.append(t)
                    labels.append(cat)

    if not texts:
        logger.warning("No training data found in seed_training.csv.")
        return None, None

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    X = vectorizer.fit_transform(texts)
    model = LogisticRegression(max_iter=500, C=1.0)
    model.fit(X, labels)

    _VECTORIZER = vectorizer
    _MODEL = model
    return _MODEL, _VECTORIZER


KEYWORD_RULES = {
    "Harassment/Safety": [
        "ragging", "ragged", "harass", "harassment", "eve teasing", "threat",
        "abuse", "beaten", "assault", "violence", "caste", "slur", "blackmail",
        "रैगिंग", "उत्पीड़न", "छेड़छाड़", "धमकी", "मारपीट", "हमला", "हिंसा"
    ],
    "Fees": [
        "fee", "fees", "refund", "deposit", "caution", "tuition", "fine",
        "penalty", "capitation", "donation", "receipt", "overcharge",
        "फीस", "शुल्क", "रिफंड", "जुरमाना", "डोनेशन", "रसीद", "कॉशन"
    ],
    "Infrastructure": [
        "lab", "bench", "fan", "water", "washroom", "toilet", "light",
        "building", "leak", "ceiling", "bus", "hostel", "mess", "food",
        "कक्ष", "प्रयोगशाला", "पानी", "शौचालय", "पंखे", "भवन", "हॉस्टल", "मेस"
    ],
    "Faculty/Staff": [
        "faculty", "teacher", "professor", "lecturer", "staff", "clerk",
        "principal", "hod", "bribe", "bias", "absent",
        "शिक्षक", "प्रोफेसर", "संकाय", "कर्मचारी", "प्राचार्य", "रिश्वत", "अनुपस्थित"
    ],
    "Academic": [
        "syllabus", "exam", "marks", "attendance", "degree", "result",
        "grade", "semester", "curriculum", "lecture", "revaluation",
        "पाठ्यक्रम", "परीक्षा", "अंक", "उपस्थिति", "डिग्री", "परिणाम", "सेमेस्टर"
    ],
}


def predict_category(text: str) -> Tuple[str, float]:
    """
    Predict category using trained ML model, falling back to keyword rules.
    Returns (category_name, confidence).
    """
    norm_text = text.lower().strip()
    model, vectorizer = _load_and_train_model()

    if model is not None and vectorizer is not None:
        try:
            vec = vectorizer.transform([norm_text])
            probs = model.predict_proba(vec)[0]
            max_idx = probs.argmax()
            confidence = float(probs[max_idx])
            predicted_label = model.classes_[max_idx]
            return predicted_label, confidence
        except Exception as e:
            logger.warning("ML prediction failed: %s", e)

    # Keyword rule fallback
    for cat, keywords in KEYWORD_RULES.items():
        for kw in keywords:
            if kw in norm_text:
                return cat, 0.40

    return "Academic", 0.30

from __future__ import annotations

from typing import Any, Dict, List
from django.db.models import Avg, Count

from apps.complaints.models import CitizenGrievance, StudentFeedback


def get_student_feedback_analytics() -> Dict[str, Any]:
    """
    Compute database-derived aggregations for Dataset A (Student Feedback).
    Returns total responses, category breakdowns, and sentiment distribution.
    """
    total_records = StudentFeedback.objects.count()
    if total_records == 0:
        return {
            "total_records": 0,
            "unique_surveys": 0,
            "category_summary": [],
            "overall_sentiment": {"Positive": 0, "Neutral": 0, "Negative": 0},
            "sentiment_percentages": {"Positive": 0.0, "Neutral": 0.0, "Negative": 0.0},
        }

    unique_surveys = (
        StudentFeedback.objects.values("response_index").distinct().count()
    )

    # Category breakdown
    cat_qs = (
        StudentFeedback.objects.values("category")
        .annotate(
            total=Count("id"),
            avg_score=Avg("sentiment_score"),
            positive=Count("id", filter=StudentFeedback.objects.filter(sentiment_score=1).values("id")),
            neutral=Count("id", filter=StudentFeedback.objects.filter(sentiment_score=0).values("id")),
            negative=Count("id", filter=StudentFeedback.objects.filter(sentiment_score=-1).values("id")),
        )
        .order_by("category")
    )

    category_summary = []
    for c in cat_qs:
        total = c["total"]
        category_summary.append({
            "category": c["category"],
            "total": total,
            "avg_sentiment_score": round(c["avg_score"] or 0.0, 3),
            "positive": c["positive"],
            "neutral": c["neutral"],
            "negative": c["negative"],
            "positive_pct": round((c["positive"] / total * 100) if total else 0.0, 1),
            "neutral_pct": round((c["neutral"] / total * 100) if total else 0.0, 1),
            "negative_pct": round((c["negative"] / total * 100) if total else 0.0, 1),
        })

    # Overall sentiment distribution
    pos_count = StudentFeedback.objects.filter(sentiment_score=1).count()
    neu_count = StudentFeedback.objects.filter(sentiment_score=0).count()
    neg_count = StudentFeedback.objects.filter(sentiment_score=-1).count()

    return {
        "total_records": total_records,
        "unique_surveys": unique_surveys,
        "category_summary": category_summary,
        "overall_sentiment": {
            "Positive": pos_count,
            "Neutral": neu_count,
            "Negative": neg_count,
        },
        "sentiment_percentages": {
            "Positive": round((pos_count / total_records * 100) if total_records else 0.0, 1),
            "Neutral": round((neu_count / total_records * 100) if total_records else 0.0, 1),
            "Negative": round((neg_count / total_records * 100) if total_records else 0.0, 1),
        },
    }


def get_citizen_grievance_analytics() -> Dict[str, Any]:
    """
    Compute database-derived aggregations for Dataset B (Citizen Grievances).
    Returns total records, breakdown by CPGRAMS category, language, and dataset split.
    """
    total_records = CitizenGrievance.objects.count()
    if total_records == 0:
        return {
            "total_records": 0,
            "category_distribution": [],
            "language_distribution": {},
            "source_distribution": {},
        }

    # Category distribution across 14 CPGRAMS departments
    cat_data = list(
        CitizenGrievance.objects.values("category")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    for c in cat_data:
        c["percentage"] = round((c["count"] / total_records * 100), 1)

    # Language distribution
    lang_data = {
        item["language"]: item["count"]
        for item in CitizenGrievance.objects.values("language").annotate(count=Count("id"))
    }

    # Source file distribution (synthetic vs holdout)
    source_data = {
        item["source_file"]: item["count"]
        for item in CitizenGrievance.objects.values("source_file").annotate(count=Count("id"))
    }

    return {
        "total_records": total_records,
        "category_distribution": cat_data,
        "language_distribution": lang_data,
        "source_distribution": source_data,
    }

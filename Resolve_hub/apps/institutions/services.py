from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from django.conf import settings

if TYPE_CHECKING:
    from apps.complaints.models import ComplaintCategory
    from .models import Cell


def resolve_sla_hours(
    cell: Optional[Cell],
    category: Optional[ComplaintCategory] = None,
    priority: str = "MEDIUM",
) -> int:
    """
    Resolve SLA hours using the specificity ladder:
      1. Specific policy for (cell, category, priority)
      2. General policy for (cell, category=None, priority)
      3. Cell default_sla_hours
      4. Global DEFAULT_SLA_HOURS (default 168)
    """
    default_hours = getattr(settings, "DEFAULT_SLA_HOURS", 168)
    if not cell:
        return default_hours

    from .models import SLAPolicy

    # 1. Exact match with category
    if category is not None:
        policy = SLAPolicy.objects.filter(cell=cell, category=category, priority=priority).first()
        if policy:
            return policy.sla_hours

    # 2. Match without specific category
    policy = SLAPolicy.objects.filter(cell=cell, category__isnull=True, priority=priority).first()
    if policy:
        return policy.sla_hours

    # 3. Cell default
    if cell.default_sla_hours:
        return cell.default_sla_hours

    # 4. Global setting fallback
    return default_hours

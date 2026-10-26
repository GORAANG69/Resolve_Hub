from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from apps.accounts.models import Role


def can_officer_access_complaint(user, complaint) -> bool:
    """
    Check if an officer has permission to view or manage a specific complaint.
    - DIRECTOR, MEMBER_SECRETARY, ADMIN: can access all complaints.
    - BUREAU_HEAD: can access complaints assigned to cells belonging to their Bureau.
    - SECTION_HEAD: can access complaints assigned to their Cell.
    - Legacy HOD: can access complaints assigned to their Department.
    """
    if not (user.is_authenticated and user.is_officer):
        return False

    if user.role in (Role.DIRECTOR, Role.MEMBER_SECRETARY, Role.ADMIN):
        return True

    if user.role == Role.BUREAU_HEAD:
        if not user.bureau:
            return False
        return bool(complaint.cell and complaint.cell.bureau_id == user.bureau_id)

    if user.role == Role.SECTION_HEAD:
        if not user.cell:
            return False
        return bool(complaint.cell_id == user.cell_id)

    if user.role == Role.HOD:
        return bool(user.department and complaint.assigned_department == user.department)

    return False


def get_officer_complaints_queryset(user):
    """
    Return ownership/scope filtered queryset of complaints for this officer.
    """
    from apps.complaints.models import Complaint

    if not (user.is_authenticated and user.is_officer):
        return Complaint.objects.none()

    if user.role in (Role.DIRECTOR, Role.MEMBER_SECRETARY, Role.ADMIN):
        return Complaint.objects.all()

    if user.role == Role.BUREAU_HEAD:
        if not user.bureau:
            return Complaint.objects.none()
        return Complaint.objects.filter(cell__bureau=user.bureau)

    if user.role == Role.SECTION_HEAD:
        if not user.cell:
            return Complaint.objects.none()
        return Complaint.objects.filter(cell=user.cell)

    if user.role == Role.HOD:
        if not user.department:
            return Complaint.objects.none()
        return Complaint.objects.filter(assigned_department=user.department)

    return Complaint.objects.none()


def officer_required(view_func):
    """
    Decorator requiring an authenticated officer role.
    """
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_officer):
            raise PermissionDenied("Officer access required.")
        return view_func(request, *args, **kwargs)

    return _wrapped

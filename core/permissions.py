"""Server-side role and object-level authorization helpers.

Admin == Django is_staff/is_superuser. Faculty/student-coordinator/student
roles are derived from the Cohort's own relations (faculty_coordinator,
student_coordinators, students) rather than a separate role table, since
those relations are the single source of truth already used everywhere
else in this app.
"""
from django.db.models import Q
from rest_framework.permissions import BasePermission

from .models import AssessmentStatus


def is_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.is_staff))


def is_faculty_of(user, cohort):
    return bool(user and user.is_authenticated and cohort.faculty_coordinator_id == user.id)


def is_student_coordinator_of(user, cohort):
    return bool(user and user.is_authenticated and cohort.student_coordinators.filter(pk=user.pk).exists())


def is_member_of(user, cohort):
    return bool(user and user.is_authenticated and cohort.students.filter(pk=user.pk).exists())


def can_view_cohort(user, cohort):
    return (
        is_admin(user)
        or is_faculty_of(user, cohort)
        or is_student_coordinator_of(user, cohort)
        or is_member_of(user, cohort)
    )


def can_manage_cohort(user, cohort):
    return is_admin(user) or is_faculty_of(user, cohort)


def _coordinated_cohorts_filter(user):
    return Q(faculty_coordinator=user) | Q(student_coordinators=user)


def can_author_content(user):
    """Faculty/student coordinators and admins manage the question bank and assessments."""
    if is_admin(user):
        return True
    if not (user and user.is_authenticated):
        return False
    from .models import Cohort
    return Cohort.objects.filter(_coordinated_cohorts_filter(user)).exists()


def can_approve_content(user):
    """Only faculty coordinators and admins may approve question bank content."""
    if is_admin(user):
        return True
    if not (user and user.is_authenticated):
        return False
    from .models import Cohort
    return Cohort.objects.filter(faculty_coordinator=user).exists()


def can_publish_for_cohort(user, cohort):
    return (
        is_admin(user)
        or is_faculty_of(user, cohort)
        or cohort.publishing_coordinators.filter(pk=user.pk).exists()
    )


def can_edit_assessment(user, assessment):
    cohort = assessment.cohort
    return is_admin(user) or is_faculty_of(user, cohort) or is_student_coordinator_of(user, cohort)


PUBLISHED_ASSESSMENT_STATUSES = {
    AssessmentStatus.SCHEDULED,
    AssessmentStatus.ACTIVE,
    AssessmentStatus.CLOSED,
    AssessmentStatus.EVALUATED,
    AssessmentStatus.RELEASED,
}


def enforce_assessment_status(user, cohort, status):
    from django.core.exceptions import PermissionDenied
    if status in PUBLISHED_ASSESSMENT_STATUSES and not can_publish_for_cohort(user, cohort):
        raise PermissionDenied('You do not have permission to publish assessments for this cohort.')


def visible_cohorts(user):
    from .models import Cohort
    if is_admin(user):
        return Cohort.objects.all()
    if not (user and user.is_authenticated):
        return Cohort.objects.none()
    return Cohort.objects.filter(
        _coordinated_cohorts_filter(user) | Q(students=user)
    ).distinct()


def manageable_cohorts(user):
    from .models import Cohort
    if is_admin(user):
        return Cohort.objects.all()
    if not (user and user.is_authenticated):
        return Cohort.objects.none()
    return Cohort.objects.filter(_coordinated_cohorts_filter(user)).distinct()


class IsContentAuthor(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and can_author_content(request.user))


    
class IsCohortMember(BasePermission):
    """Object-level: user can view this specific cohort."""
    def has_object_permission(self, request, view, obj):
        return can_view_cohort(request.user, obj)


class CanManageCohort(BasePermission):
    def has_object_permission(self, request, view, obj):
        return can_manage_cohort(request.user, obj)


class CanEditAssessment(BasePermission):
    """Object-level: user can edit/publish this assessment."""
    def has_object_permission(self, request, view, obj):
        return can_edit_assessment(request.user, obj)


class IsAssessmentViewer(BasePermission):
    """Object-level: user can view this assessment (cohort access + status visibility)."""
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not can_view_cohort(user, obj.cohort):
            return False
        if not can_author_content(user) and obj.status in ['draft', 'pending', 'cancelled']:
            return False
        return True


class IsOwnAttemptOrPrivileged(BasePermission):
    """Object-level: user owns the attempt, or is admin/faculty of its cohort."""
    def has_object_permission(self, request, view, obj):
        user = request.user
        return (
            obj.student_id == user.id
            or is_admin(user)
            or is_faculty_of(user, obj.assessment.cohort)
        )


class CanGradeAttempt(BasePermission):
    def has_object_permission(self, request, view, obj):
        return is_admin(request.user) or is_faculty_of(request.user, obj.assessment.cohort)
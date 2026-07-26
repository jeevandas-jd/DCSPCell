from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    Answer,
    Assessment,
    AssessmentQuestion,
    Attempt,
    Choice,
    Cohort,
    CohortAssignmentHistory,
    CodingTestCase,
    Question,
    RoleAssignment,
    User,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'status', 'is_staff')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'register_number')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'first_name', 'last_name', 'photo', 'register_number', 'contact_phone', 'department', 'program', 'admission_year', 'graduation_year', 'preferred_role', 'placement_status')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Status & audit', {'fields': ('status', 'last_security_event')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'department', 'program', 'status')
    search_fields = ('code', 'name', 'department', 'program')
    list_filter = ('status', 'department', 'program')
    filter_horizontal = ('student_coordinators', 'publishing_coordinators', 'students')


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'cohort', 'created_at', 'revoked_at')
    list_filter = ('role',)
    search_fields = ('user__email', 'user__username', 'cohort__code', 'cohort__name')


@admin.register(CohortAssignmentHistory)
class CohortAssignmentHistoryAdmin(admin.ModelAdmin):
    list_display = ('cohort', 'user', 'role', 'assigned_at', 'removed_at')
    search_fields = ('cohort__code', 'user__email', 'role')
    list_filter = ('role',)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'question_type', 'topic', 'difficulty', 'approval_status', 'visible')
    list_filter = ('question_type', 'difficulty', 'approval_status', 'visible')
    search_fields = ('title', 'statement', 'topic', 'tags')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ()


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('question', 'text', 'is_correct', 'order')
    list_filter = ('is_correct',)
    search_fields = ('question__title', 'text')


@admin.register(CodingTestCase)
class CodingTestCaseAdmin(admin.ModelAdmin):
    list_display = ('question', 'is_public', 'points')
    list_filter = ('is_public',)
    search_fields = ('question__title',)


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'cohort', 'status', 'start_datetime', 'end_datetime')
    list_filter = ('status', 'result_release_policy', 'explanation_release_policy')
    search_fields = ('title', 'description', 'instructions', 'cohort__code', 'cohort__name')


@admin.register(AssessmentQuestion)
class AssessmentQuestionAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'question', 'order', 'marks')
    search_fields = ('assessment__title', 'question__title')


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'assessment', 'attempt_number', 'status', 'submitted_at', 'score')
    list_filter = ('status',)
    search_fields = ('student__email', 'assessment__title')


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'assessment_question', 'is_correct', 'awarded_marks', 'submitted_at')
    search_fields = ('attempt__student__email', 'assessment_question__question__title')

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserStatus(models.TextChoices):
    INVITED = 'invited', _('Invited')
    ACTIVE = 'active', _('Active')
    SUSPENDED = 'suspended', _('Suspended')
    GRADUATED = 'graduated', _('Graduated')
    ARCHIVED = 'archived', _('Archived')


class RoleType(models.TextChoices):
    ADMIN = 'admin', _('Admin')
    FACULTY_COORDINATOR = 'faculty_coordinator', _('Faculty Coordinator')
    STUDENT_COORDINATOR = 'student_coordinator', _('Student Coordinator')
    STUDENT = 'student', _('Student')


class User(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    status = models.CharField(
        max_length=16,
        choices=UserStatus.choices,
        default=UserStatus.INVITED,
    )
    photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    register_number = models.CharField(max_length=64, blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    department = models.CharField(max_length=128, blank=True)
    program = models.CharField(max_length=128, blank=True)
    admission_year = models.PositiveSmallIntegerField(blank=True, null=True)
    graduation_year = models.PositiveSmallIntegerField(blank=True, null=True)
    preferred_role = models.CharField(max_length=128, blank=True)
    placement_status = models.CharField(max_length=64, blank=True)
    last_security_event = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.get_full_name() or self.email


class CohortStatus(models.TextChoices):
    DRAFT = 'draft', _('Draft')
    ACTIVE = 'active', _('Active')
    COMPLETED = 'completed', _('Completed')
    ARCHIVED = 'archived', _('Archived')


class Cohort(models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32, unique=True)
    department = models.CharField(max_length=128, blank=True)
    program = models.CharField(max_length=128, blank=True)
    admission_year = models.PositiveSmallIntegerField(blank=True, null=True)
    graduation_year = models.PositiveSmallIntegerField(blank=True, null=True)
    section = models.CharField(max_length=32, blank=True)
    academic_year = models.CharField(max_length=32, blank=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=16,
        choices=CohortStatus.choices,
        default=CohortStatus.DRAFT,
    )
    faculty_coordinator = models.ForeignKey(
        'core.User',
        blank=True,
        null=True,
        related_name='faculty_cohorts',
        on_delete=models.SET_NULL,
    )
    student_coordinators = models.ManyToManyField(
        'core.User',
        blank=True,
        related_name='student_coordinator_cohorts',
    )
    publishing_coordinators = models.ManyToManyField(
        'core.User',
        blank=True,
        related_name='publishing_cohorts',
        help_text=_('Student coordinators explicitly granted permission to publish assessments for this cohort.'),
    )
    students = models.ManyToManyField(
        'core.User',
        blank=True,
        related_name='student_cohorts',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-academic_year', 'name']

    def __str__(self):
        return f'{self.code} - {self.name}'


class RoleAssignment(models.Model):
    user = models.ForeignKey(
        'core.User',
        related_name='assignments',
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=32, choices=RoleType.choices)
    cohort = models.ForeignKey(
        'core.Cohort',
        blank=True,
        null=True,
        related_name='role_assignments',
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'role', 'cohort')

    def __str__(self):
        cohort_label = str(self.cohort) if self.cohort else 'global'
        return f'{self.user.email} as {self.role} on {cohort_label}'


class CohortAssignmentHistory(models.Model):
    cohort = models.ForeignKey(
        'core.Cohort',
        related_name='assignment_history',
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        'core.User',
        related_name='cohort_history',
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=32, choices=RoleType.choices)
    assigned_at = models.DateTimeField(default=timezone.now)
    removed_at = models.DateTimeField(blank=True, null=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        return f'{self.user.email} {self.role} for {self.cohort} at {self.assigned_at}'


class QuestionType(models.TextChoices):
    SINGLE_CHOICE = 'single_choice', _('Single Choice')
    MULTIPLE_CHOICE = 'multiple_choice', _('Multiple Choice')
    NUMERICAL = 'numerical', _('Numerical')
    SHORT_ANSWER = 'short_answer', _('Short Answer')
    CODING = 'coding', _('Coding')


class ApprovalStatus(models.TextChoices):
    DRAFT = 'draft', _('Draft')
    PENDING = 'pending', _('Pending Approval')
    APPROVED = 'approved', _('Approved')
    REJECTED = 'rejected', _('Rejected')


class DifficultyLevel(models.TextChoices):
    EASY = 'easy', _('Easy')
    MEDIUM = 'medium', _('Medium')
    HARD = 'hard', _('Hard')


class Question(models.Model):
    title = models.CharField(max_length=256)
    statement = models.TextField()
    question_type = models.CharField(max_length=32, choices=QuestionType.choices)
    topic = models.CharField(max_length=128, blank=True)
    subtopic = models.CharField(max_length=128, blank=True)
    tags = models.JSONField(default=list, blank=True)
    difficulty = models.CharField(max_length=16, choices=DifficultyLevel.choices, default=DifficultyLevel.MEDIUM)
    positive_marks = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    negative_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    default_time_minutes = models.PositiveSmallIntegerField(default=5)
    explanation = models.TextField(blank=True)
    correct_numeric_answer = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True,
        help_text=_('Exact expected value for numerical-answer questions.'),
    )
    correct_text_answer = models.CharField(
        max_length=512, blank=True,
        help_text=_('Expected text for short-answer questions (case-insensitive exact match).'),
    )
    author = models.ForeignKey('core.User', blank=True, null=True, related_name='authored_questions', on_delete=models.SET_NULL)
    reviewer = models.ForeignKey('core.User', blank=True, null=True, related_name='reviewed_questions', on_delete=models.SET_NULL)
    approval_status = models.CharField(max_length=16, choices=ApprovalStatus.choices, default=ApprovalStatus.DRAFT)
    version = models.PositiveIntegerField(default=1)
    visible = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Coding-specific fields
    input_format = models.TextField(blank=True)
    output_format = models.TextField(blank=True)
    constraints = models.TextField(blank=True)
    example = models.TextField(blank=True)
    supported_languages = models.JSONField(default=list, blank=True)
    time_limit_seconds = models.PositiveSmallIntegerField(blank=True, null=True)
    memory_limit_mb = models.PositiveSmallIntegerField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Choice(models.Model):
    question = models.ForeignKey('core.Question', related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=512)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text


class CodingTestCase(models.Model):
    question = models.ForeignKey('core.Question', related_name='coding_test_cases', on_delete=models.CASCADE)
    input_data = models.TextField()
    expected_output = models.TextField()
    is_public = models.BooleanField(default=False)
    points = models.DecimalField(max_digits=5, decimal_places=2, default=1)

    def __str__(self):
        return f'Case for {self.question.title} ({"public" if self.is_public else "private"})'


class AssessmentStatus(models.TextChoices):
    DRAFT = 'draft', _('Draft')
    PENDING = 'pending', _('Pending')
    SCHEDULED = 'scheduled', _('Scheduled')
    ACTIVE = 'active', _('Active')
    CLOSED = 'closed', _('Closed')
    EVALUATED = 'evaluated', _('Evaluated')
    RELEASED = 'released', _('Released')
    CANCELLED = 'cancelled', _('Cancelled')
    ARCHIVED = 'archived', _('Archived')


class ReleasePolicy(models.TextChoices):
    IMMEDIATE = 'immediate', _('Immediate')
    SCHEDULED = 'scheduled', _('Scheduled')
    MANUAL = 'manual', _('Manual')


class Assessment(models.Model):
    title = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    cohort = models.ForeignKey('core.Cohort', related_name='assessments', on_delete=models.PROTECT)
    creator = models.ForeignKey('core.User', related_name='created_assessments', on_delete=models.SET_NULL, null=True, blank=True)
    approver = models.ForeignKey('core.User', related_name='approved_assessments', on_delete=models.SET_NULL, null=True, blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(blank=True, null=True)
    max_attempts = models.PositiveSmallIntegerField(default=1)
    total_marks = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    pass_mark = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    randomize_question_order = models.BooleanField(default=False)
    result_release_policy = models.CharField(max_length=16, choices=ReleasePolicy.choices, default=ReleasePolicy.IMMEDIATE)
    explanation_release_policy = models.CharField(max_length=16, choices=ReleasePolicy.choices, default=ReleasePolicy.IMMEDIATE)
    result_release_at = models.DateTimeField(
        blank=True, null=True,
        help_text=_('Used when result release policy is "scheduled".'),
    )
    explanation_release_at = models.DateTimeField(
        blank=True, null=True,
        help_text=_('Used when explanation release policy is "scheduled".'),
    )
    status = models.CharField(max_length=16, choices=AssessmentStatus.choices, default=AssessmentStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_datetime', 'title']

    def __str__(self):
        return self.title

    def is_within_window(self, at=None):
        at = at or timezone.now()
        return self.start_datetime <= at <= self.end_datetime

    def _release_visible(self, policy, release_at, at):
        if policy == ReleasePolicy.MANUAL:
            return self.status == AssessmentStatus.RELEASED
        if policy == ReleasePolicy.SCHEDULED:
            return bool(release_at) and at >= release_at
        return at >= self.end_datetime

    def results_visible(self, at=None):
        at = at or timezone.now()
        return self._release_visible(self.result_release_policy, self.result_release_at, at)

    def explanations_visible(self, at=None):
        at = at or timezone.now()
        return self._release_visible(self.explanation_release_policy, self.explanation_release_at, at)


class AssessmentQuestion(models.Model):
    assessment = models.ForeignKey('core.Assessment', related_name='assessment_questions', on_delete=models.CASCADE)
    question = models.ForeignKey('core.Question', related_name='assessment_links', on_delete=models.PROTECT)
    order = models.PositiveSmallIntegerField(default=0)
    marks = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        unique_together = ('assessment', 'question')
        ordering = ['order']

    def __str__(self):
        return f'{self.assessment.title} - {self.question.title}'


class AttemptStatus(models.TextChoices):
    IN_PROGRESS = 'in_progress', _('In Progress')
    SUBMITTED = 'submitted', _('Submitted')
    EVALUATED = 'evaluated', _('Evaluated')
    CANCELLED = 'cancelled', _('Cancelled')


class Attempt(models.Model):
    assessment = models.ForeignKey('core.Assessment', related_name='attempts', on_delete=models.CASCADE)
    student = models.ForeignKey('core.User', related_name='attempts', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=16, choices=AttemptStatus.choices, default=AttemptStatus.IN_PROGRESS)
    score = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    time_taken_seconds = models.PositiveIntegerField(blank=True, null=True)
    attempt_number = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('assessment', 'student', 'attempt_number')

    def __str__(self):
        return f'{self.student.email} attempt {self.attempt_number} on {self.assessment.title}'

    @property
    def deadline(self):
        end = self.assessment.end_datetime
        if self.assessment.duration_minutes:
            candidate = self.created_at + timezone.timedelta(minutes=self.assessment.duration_minutes)
            return min(end, candidate)
        return end

    @property
    def is_expired(self):
        return self.status == AttemptStatus.IN_PROGRESS and timezone.now() > self.deadline


class Answer(models.Model):
    attempt = models.ForeignKey('core.Attempt', related_name='answers', on_delete=models.CASCADE)
    assessment_question = models.ForeignKey('core.AssessmentQuestion', related_name='answers', on_delete=models.CASCADE)
    selected_choice = models.ForeignKey('core.Choice', blank=True, null=True, on_delete=models.SET_NULL)
    selected_choices = models.ManyToManyField('core.Choice', blank=True, related_name='selected_in_answers')
    numeric_answer = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    text_answer = models.TextField(blank=True)
    code_answer = models.TextField(blank=True)
    awarded_marks = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    feedback = models.TextField(blank=True)
    is_correct = models.BooleanField(blank=True, null=True)
    submitted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('attempt', 'assessment_question')

    def __str__(self):
        return f'Answer for {self.assessment_question.question.title} in {self.attempt}'

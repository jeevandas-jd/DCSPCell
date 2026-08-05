from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
from rest_framework import permissions, viewsets

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status as http_status

from .forms import AssessmentForm, AssessmentStatusForm, CohortForm, QuestionForm
from .models import (
    Answer,
    ApprovalStatus,
    Assessment,
    AssessmentStatus,
    Attempt,
    AttemptStatus,
    Cohort,
    Question,
    QuestionType,
    User
)
from .permissions import (
    IsContentAuthor,
    IsOwnAttemptOrPrivileged,
    can_approve_content,
    can_author_content,
    can_edit_assessment,
    can_manage_cohort,
    can_publish_for_cohort,
    can_view_cohort,
    enforce_assessment_status,
    is_admin,
    is_faculty_of,
    is_member_of,
    manageable_cohorts,
    visible_cohorts,
)
from .serializers import AssessmentSerializer, AttemptSerializer, CohortSerializer, QuestionSerializer,QuestionWriteSerializer
from .services import evaluate_attempt, finalize_attempt

from rest_framework import generics, permissions
from .serializers import UserRegistrationSerializer

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    
class AdminRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied('Only administrators can perform this action.')
        return super().dispatch(request, *args, **kwargs)


class ContentAuthorRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not can_author_content(request.user):
            raise PermissionDenied('Only faculty or coordinators can manage this content.')
        return super().dispatch(request, *args, **kwargs)


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return super().get(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        cohorts = visible_cohorts(user)
        context['cohort_count'] = cohorts.count()
        context['question_count'] = Question.objects.count() if can_author_content(user) else 0
        context['assessment_count'] = Assessment.objects.filter(cohort__in=cohorts).count()
        context['attempt_count'] = (
            Attempt.objects.count() if is_admin(user) else Attempt.objects.filter(student=user).count()
        )
        return context


class CohortListView(LoginRequiredMixin, ListView):
    model = Cohort
    template_name = 'core/cohort_list.html'
    context_object_name = 'cohorts'

    def get_queryset(self):
        return visible_cohorts(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_create'] = is_admin(self.request.user)
        return context


class CohortDetailView(LoginRequiredMixin, DetailView):
    model = Cohort
    template_name = 'core/cohort_detail.html'
    context_object_name = 'cohort'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not can_view_cohort(self.request.user, obj):
            raise PermissionDenied('You do not have access to this cohort.')
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cohort = self.get_object()
        assessments = cohort.assessments.order_by('-start_datetime')
        if not can_author_content(self.request.user):
            assessments = assessments.exclude(
                status__in=[AssessmentStatus.DRAFT, AssessmentStatus.PENDING, AssessmentStatus.CANCELLED]
            )
        context['assessments'] = assessments
        context['student_coordinators'] = cohort.student_coordinators.all()
        context['students'] = cohort.students.all()
        context['can_manage'] = is_admin(self.request.user)
        return context


class CohortCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Cohort
    form_class = CohortForm
    template_name = 'core/cohort_form.html'
    success_url = reverse_lazy('core:cohort-list')
    extra_context = {'title': 'Create'}


class CohortUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Cohort
    form_class = CohortForm
    template_name = 'core/cohort_form.html'
    success_url = reverse_lazy('core:cohort-list')
    extra_context = {'title': 'Edit'}


class QuestionListView(LoginRequiredMixin, ContentAuthorRequiredMixin, ListView):
    model = Question
    template_name = 'core/question_list.html'
    context_object_name = 'questions'

    def get_queryset(self):
        user = self.request.user
        qs = Question.objects.filter(is_archived=False)
        if can_approve_content(user):
            return qs
        return qs.filter(Q(visible=True, approval_status=ApprovalStatus.APPROVED) | Q(author=user))


class QuestionDetailView(LoginRequiredMixin, ContentAuthorRequiredMixin, DetailView):
    model = Question
    template_name = 'core/question_detail.html'
    context_object_name = 'question'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        question = self.get_object()
        context['choices'] = question.choices.all()
        context['coding_test_cases'] = question.coding_test_cases.all()
        return context


class QuestionCreateView(LoginRequiredMixin, ContentAuthorRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'core/question_form.html'
    success_url = reverse_lazy('core:question-list')
    extra_context = {'title': 'Create'}
    # handle api/questions/create from postman, which doesn't use a form but still needs the user context for author and approval_status
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    """
    instructions for api testing
    """ 

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.author = self.request.user
        if not can_approve_content(self.request.user):
            form.instance.approval_status = ApprovalStatus.DRAFT
        return super().form_valid(form)


class QuestionUpdateView(LoginRequiredMixin, ContentAuthorRequiredMixin, UpdateView):
    model = Question
    form_class = QuestionForm
    template_name = 'core/question_form.html'
    success_url = reverse_lazy('core:question-list')
    extra_context = {'title': 'Edit'}

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if not (can_approve_content(user) or obj.author_id == user.id):
            raise PermissionDenied('You can only edit questions you authored.')
        return obj

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not can_approve_content(self.request.user) and form.instance.approval_status == ApprovalStatus.APPROVED:
            form.instance.approval_status = ApprovalStatus.PENDING
        return super().form_valid(form)


class AssessmentListView(LoginRequiredMixin, ListView):
    model = Assessment
    template_name = 'core/assessment_list.html'
    context_object_name = 'assessments'

    def get_queryset(self):
        user = self.request.user
        qs = Assessment.objects.filter(cohort__in=visible_cohorts(user)).select_related('cohort')
        if not can_author_content(user):
            qs = qs.exclude(status__in=[AssessmentStatus.DRAFT, AssessmentStatus.PENDING, AssessmentStatus.CANCELLED])
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_create'] = can_author_content(self.request.user)
        return context


class AssessmentDetailView(LoginRequiredMixin, DetailView):
    model = Assessment
    template_name = 'core/assessment_detail.html'
    context_object_name = 'assessment'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if not can_view_cohort(user, obj.cohort):
            raise PermissionDenied('You do not have access to this assessment.')
        if not can_author_content(user) and obj.status in [
            AssessmentStatus.DRAFT,
            AssessmentStatus.PENDING,
            AssessmentStatus.CANCELLED,
        ]:
            raise PermissionDenied('This assessment is not available.')
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assessment = self.get_object()
        user = self.request.user
        now = timezone.now()
        context['now'] = now
        context['can_manage'] = can_edit_assessment(user, assessment)
        if user.is_authenticated:
            user_attempts = Attempt.objects.filter(student=user, assessment=assessment)
            context['attempts_count'] = user_attempts.count()
            context['max_attempts_reached'] = context['attempts_count'] >= (assessment.max_attempts or 1)
            context['can_start_attempt'] = (
                is_member_of(user, assessment.cohort)
                and assessment.status == AssessmentStatus.ACTIVE
                and assessment.is_within_window(now)
                and not context['max_attempts_reached']
            )
        return context


class AttemptCreateView(LoginRequiredMixin, CreateView):
    model = Attempt
    fields = []
    template_name = 'core/attempt_create.html'

    def dispatch(self, request, *args, **kwargs):
        self.assessment = get_object_or_404(Assessment, pk=kwargs['pk'])
        if not is_member_of(request.user, self.assessment.cohort):
            raise PermissionDenied('You are not part of the cohort for this assessment.')
        now = timezone.now()
        if self.assessment.status != AssessmentStatus.ACTIVE or not self.assessment.is_within_window(now):
            raise PermissionDenied('This assessment is not currently active.')
        existing = Attempt.objects.filter(student=request.user, assessment=self.assessment).count()
        if existing >= (self.assessment.max_attempts or 1):
            raise PermissionDenied('Maximum attempt limit reached.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assessment'] = self.assessment
        context['attempts_count'] = Attempt.objects.filter(student=self.request.user, assessment=self.assessment).count()
        context['max_attempts'] = self.assessment.max_attempts or 1
        context['max_attempts_reached'] = context['attempts_count'] >= context['max_attempts']
        return context

    def form_valid(self, form):
        form.instance.assessment = self.assessment
        form.instance.student = self.request.user
        form.instance.attempt_number = Attempt.objects.filter(student=self.request.user, assessment=self.assessment).count() + 1
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('core:attempt-detail', kwargs={'pk': self.object.pk})


class AssessmentCreateView(LoginRequiredMixin, ContentAuthorRequiredMixin, CreateView):
    model = Assessment
    form_class = AssessmentForm
    template_name = 'core/assessment_form.html'
    success_url = reverse_lazy('core:assessment-list')
    extra_context = {'title': 'Create'}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        enforce_assessment_status(self.request.user, form.instance.cohort, form.instance.status)
        form.instance.creator = self.request.user
        return super().form_valid(form)


class AssessmentUpdateView(LoginRequiredMixin, ContentAuthorRequiredMixin, UpdateView):
    template_name = 'core/assessment_form.html'
    success_url = reverse_lazy('core:assessment-list')
    extra_context = {'title': 'Edit'}

    def get_object(self, queryset=None):
        obj = get_object_or_404(Assessment, pk=self.kwargs['pk'])
        if not can_edit_assessment(self.request.user, obj):
            raise PermissionDenied('You do not have permission to edit this assessment.')
        return obj

    def get_form_class(self):
        if self.object.attempts.exists():
            return AssessmentStatusForm
        return AssessmentForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['locked'] = self.object.attempts.exists()
        return context

    def form_valid(self, form):
        status = form.cleaned_data.get('status', self.object.status)
        enforce_assessment_status(self.request.user, self.object.cohort, status)
        return super().form_valid(form)


class AttemptListView(LoginRequiredMixin, ListView):
    model = Attempt
    template_name = 'core/attempt_list.html'
    context_object_name = 'attempts'

    def get_queryset(self):
        if is_admin(self.request.user):
            return Attempt.objects.all()
        return Attempt.objects.filter(student=self.request.user)


class AttemptDetailView(LoginRequiredMixin, DetailView):
    model = Attempt
    template_name = 'core/attempt_detail.html'
    context_object_name = 'attempt'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        allowed = obj.student_id == user.id or is_admin(user) or is_faculty_of(user, obj.assessment.cohort)
        if not allowed:
            raise PermissionDenied('You do not have permission to view this attempt.')
        return obj

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.is_expired:
            finalize_attempt(self.object, auto=True)
            messages.warning(request, 'Time expired — your attempt was submitted automatically.')
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempt = self.object
        assessment = attempt.assessment
        user = self.request.user
        is_privileged = is_admin(user) or is_faculty_of(user, assessment.cohort)

        context['assessment_questions'] = (
            assessment.assessment_questions.select_related('question')
            .prefetch_related('question__choices')
            .order_by('order')
        )
        answers = attempt.answers.select_related('assessment_question__question', 'selected_choice').prefetch_related(
            'selected_choices'
        )
        context['answers_by_aq'] = {answer.assessment_question_id: answer for answer in answers}
        context['deadline'] = attempt.deadline
        context['is_privileged'] = is_privileged
        context['results_visible'] = is_privileged or (
            attempt.status == AttemptStatus.EVALUATED and assessment.results_visible()
        )
        context['explanations_visible'] = is_privileged or (
            attempt.status == AttemptStatus.EVALUATED and assessment.explanations_visible()
        )
        context['can_grade'] = is_privileged and attempt.status == AttemptStatus.SUBMITTED
        return context


class AnswerSaveView(LoginRequiredMixin, View):
    def post(self, request, pk, aq_id):
        attempt = get_object_or_404(Attempt, pk=pk)
        if attempt.student_id != request.user.id:
            raise PermissionDenied('This is not your attempt.')
        if attempt.is_expired:
            finalize_attempt(attempt, auto=True)
            messages.warning(request, 'Time expired — your attempt was submitted automatically.')
            return redirect('core:attempt-detail', pk=attempt.pk)
        if attempt.status != AttemptStatus.IN_PROGRESS:
            messages.info(request, 'This attempt has already been submitted.')
            return redirect('core:attempt-detail', pk=attempt.pk)

        aq = get_object_or_404(attempt.assessment.assessment_questions, pk=aq_id)
        answer, _ = Answer.objects.get_or_create(attempt=attempt, assessment_question=aq)
        question = aq.question

        if question.question_type == QuestionType.SINGLE_CHOICE:
            choice_id = request.POST.get('choice') or None
            answer.selected_choice_id = choice_id
        elif question.question_type == QuestionType.MULTIPLE_CHOICE:
            answer.save()
            answer.selected_choices.set(request.POST.getlist('choices'))
        elif question.question_type == QuestionType.NUMERICAL:
            value = request.POST.get('numeric_answer', '').strip()
            answer.numeric_answer = value or None
        elif question.question_type == QuestionType.SHORT_ANSWER:
            answer.text_answer = request.POST.get('text_answer', '')
        elif question.question_type == QuestionType.CODING:
            answer.code_answer = request.POST.get('code_answer', '')

        answer.submitted_at = timezone.now()
        answer.save()
        messages.success(request, f'Answer saved for question {aq.order}.')
        return redirect(reverse('core:attempt-detail', kwargs={'pk': attempt.pk}) + f'#q-{aq.pk}')


class AttemptSubmitView(LoginRequiredMixin, View):
    def post(self, request, pk):
        attempt = get_object_or_404(Attempt, pk=pk)
        if attempt.student_id != request.user.id:
            raise PermissionDenied('This is not your attempt.')
        if attempt.status == AttemptStatus.IN_PROGRESS:
            finalize_attempt(attempt, auto=False)
            messages.success(request, 'Assessment submitted.')
        return redirect('core:attempt-detail', pk=attempt.pk)


class AttemptGradeView(LoginRequiredMixin, View):
    """Minimal manual grading for coding (and other ungraded) answers, by faculty/admin only."""

    def dispatch(self, request, *args, **kwargs):
        self.attempt = get_object_or_404(Attempt, pk=kwargs['pk'])
        user = request.user
        if not (is_admin(user) or is_faculty_of(user, self.attempt.assessment.cohort)):
            raise PermissionDenied('Only faculty or admins may grade attempts.')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        pending = self.attempt.answers.filter(
            assessment_question__question__question_type=QuestionType.CODING, is_correct__isnull=True
        )
        for answer in pending:
            marks_key = f'marks_{answer.pk}'
            feedback_key = f'feedback_{answer.pk}'
            if marks_key not in request.POST:
                continue
            raw_marks = request.POST.get(marks_key, '').strip()
            if raw_marks == '':
                continue
            try:
                marks = float(raw_marks)
            except ValueError:
                messages.error(request, f'Invalid marks for answer {answer.pk}.')
                continue
            answer.awarded_marks = marks
            answer.is_correct = marks > 0
            answer.feedback = request.POST.get(feedback_key, '')
            answer.save(update_fields=['awarded_marks', 'is_correct', 'feedback'])

        evaluate_attempt(self.attempt)
        messages.success(request, 'Grading saved.')
        return redirect('core:attempt-detail', pk=self.attempt.pk)


class CohortViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CohortSerializer

    def get_queryset(self):
        return visible_cohorts(self.request.user)


class QuestionViewSet(viewsets.ModelViewSet):  # was ReadOnlyModelViewSet
    permission_classes = [IsContentAuthor]

    def get_queryset(self):
        if can_approve_content(self.request.user):
            return Question.objects.filter(is_archived=False)
        return Question.objects.filter(is_archived=False).filter(
            Q(visible=True, approval_status=ApprovalStatus.APPROVED) | Q(author=self.request.user)
        )

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return QuestionWriteSerializer
        return QuestionSerializer

class AssessmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AssessmentSerializer
    permission_classes = [IsContentAuthor]

    def get_queryset(self):
        return Assessment.objects.filter(cohort__in=visible_cohorts(self.request.user)).select_related('cohort')



class AttemptViewSet(viewsets.ModelViewSet):
    serializer_class = AttemptSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnAttemptOrPrivileged]

    def get_queryset(self):
        user = self.request.user
        qs = Attempt.objects.select_related('assessment', 'student')
        return qs if is_admin(user) else qs.filter(student=user)

    @action(detail=True, methods=['post'], url_path='answers/(?P<aq_id>[^/.]+)')
    def submit_answer(self, request, pk=None, aq_id=None):
        attempt = self.get_object()  # runs IsOwnAttemptOrPrivileged
        if attempt.student_id != request.user.id:
            return Response({'detail': 'Not your attempt.'}, status=http_status.HTTP_403_FORBIDDEN)
        if attempt.is_expired:
            finalize_attempt(attempt, auto=True)
            return Response({'detail': 'Time expired; attempt auto-submitted.'}, status=http_status.HTTP_409_CONFLICT)
        if attempt.status != AttemptStatus.IN_PROGRESS:
            return Response({'detail': 'Attempt already submitted.'}, status=http_status.HTTP_409_CONFLICT)

        aq = get_object_or_404(attempt.assessment.assessment_questions, pk=aq_id)
        answer, _ = Answer.objects.get_or_create(attempt=attempt, assessment_question=aq)

        serializer = AnswerSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(answer=answer, question=aq.question)
        return Response(AnswerSerializer(answer).data)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        attempt = self.get_object()
        if attempt.student_id != request.user.id:
            return Response({'detail': 'Not your attempt.'}, status=http_status.HTTP_403_FORBIDDEN)
        if attempt.status == AttemptStatus.IN_PROGRESS:
            finalize_attempt(attempt, auto=False)
        return Response(AttemptSerializer(attempt).data)
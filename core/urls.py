from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AnswerSaveView,
    AssessmentCreateView,
    AssessmentDetailView,
    AssessmentListView,
    AssessmentUpdateView,
    AssessmentViewSet,
    AttemptCreateView,
    AttemptDetailView,
    AttemptGradeView,
    AttemptListView,
    AttemptSubmitView,
    AttemptViewSet,
    CohortCreateView,
    CohortDetailView,
    CohortListView,
    CohortUpdateView,
    CohortViewSet,
    DashboardView,
    HomeView,
    QuestionCreateView,
    QuestionDetailView,
    QuestionListView,
    QuestionUpdateView,
    QuestionViewSet,
    UserRegistrationView,
)

app_name = 'core'

router = DefaultRouter()
# basenames are prefixed with "api-" so their auto-generated URL names
# (e.g. "cohort-detail") never collide with the plain web view names
# (e.g. "cohort-detail") registered below in this same "core" namespace.
router.register(r'cohorts', CohortViewSet, basename='api-cohort')
router.register(r'questions', QuestionViewSet, basename='api-question')
router.register(r'assessments', AssessmentViewSet, basename='api-assessment')
router.register(r'attempts', AttemptViewSet, basename='api-attempt')
urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('cohorts/', CohortListView.as_view(), name='cohort-list'),
    path('cohorts/create/', CohortCreateView.as_view(), name='cohort-create'),
    path('cohorts/<int:pk>/', CohortDetailView.as_view(), name='cohort-detail'),
    path('cohorts/<int:pk>/edit/', CohortUpdateView.as_view(), name='cohort-update'),
    path('questions/', QuestionListView.as_view(), name='question-list'),
    path('questions/create/', QuestionCreateView.as_view(), name='question-create'),
    path('questions/<int:pk>/edit/', QuestionUpdateView.as_view(), name='question-update'),
    path('questions/<int:pk>/', QuestionDetailView.as_view(), name='question-detail'),
    path('assessments/', AssessmentListView.as_view(), name='assessment-list'),
    path('assessments/create/', AssessmentCreateView.as_view(), name='assessment-create'),
    path('assessments/<int:pk>/edit/', AssessmentUpdateView.as_view(), name='assessment-update'),
    path('assessments/<int:pk>/', AssessmentDetailView.as_view(), name='assessment-detail'),
    path('assessments/<int:pk>/start/', AttemptCreateView.as_view(), name='assessment-start'),
    path('attempts/', AttemptListView.as_view(), name='attempt-list'),
    path('attempts/<int:pk>/', AttemptDetailView.as_view(), name='attempt-detail'),
    path('attempts/<int:pk>/submit/', AttemptSubmitView.as_view(), name='attempt-submit'),
    path('attempts/<int:pk>/grade/', AttemptGradeView.as_view(), name='attempt-grade'),
    path('attempts/<int:pk>/questions/<int:aq_id>/save/', AnswerSaveView.as_view(), name='answer-save'),
    path('api/register/', UserRegistrationView.as_view(), name='api-user-register'),
    path('api/', include(router.urls)),
]

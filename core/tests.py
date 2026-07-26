from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Answer,
    Assessment,
    AssessmentQuestion,
    Attempt,
    AttemptStatus,
    Choice,
    Cohort,
    Question,
    ReleasePolicy,
    User,
)
from .services import finalize_attempt


def make_cohort(**kwargs):
    defaults = {'name': 'Cohort', 'code': f'C{Cohort.objects.count() + 1}'}
    defaults.update(kwargs)
    return Cohort.objects.create(**defaults)


def make_assessment(cohort, **kwargs):
    now = timezone.now()
    defaults = {
        'title': 'Assessment',
        'cohort': cohort,
        'start_datetime': now - timezone.timedelta(hours=1),
        'end_datetime': now + timezone.timedelta(hours=1),
        'max_attempts': 1,
        'total_marks': 10,
        'pass_mark': 5,
        'status': 'active',
    }
    defaults.update(kwargs)
    return Assessment.objects.create(**defaults)


class CoreSmokeTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_assessment_start_view_allows_cohort_member(self):
        user = User.objects.create_user(username='testuser2', email='start@example.com', password='testpassword')
        cohort = make_cohort(name='Start Cohort')
        cohort.students.add(user)
        assessment = make_assessment(cohort, title='Active Assessment')
        self.client.login(email='start@example.com', password='testpassword')
        response = self.client.get(reverse('core:assessment-start', kwargs={'pk': assessment.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Begin Assessment')

    def test_assessment_start_post_creates_attempt(self):
        user = User.objects.create_user(username='testuser3', email='post@example.com', password='testpassword')
        cohort = make_cohort(name='Post Cohort')
        cohort.students.add(user)
        assessment = make_assessment(cohort, title='Post Assessment')
        self.client.login(email='post@example.com', password='testpassword')
        response = self.client.post(reverse('core:assessment-start', kwargs={'pk': assessment.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Attempt.objects.filter(student=user, assessment=assessment).count(), 1)
        self.assertRedirects(response, reverse('core:attempt-detail', kwargs={'pk': Attempt.objects.get(student=user, assessment=assessment).pk}))

    def test_assessment_start_rejects_non_member(self):
        user = User.objects.create_user(username='outsider', email='outsider@example.com', password='testpassword')
        cohort = make_cohort(name='Private Cohort')
        assessment = make_assessment(cohort, title='Private Assessment')
        self.client.login(email='outsider@example.com', password='testpassword')
        response = self.client.post(reverse('core:assessment-start', kwargs={'pk': assessment.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Attempt.objects.filter(student=user, assessment=assessment).count(), 0)


class CohortPermissionTests(TestCase):
    def test_cohort_create_requires_admin(self):
        user = User.objects.create_user(username='plain', email='plain@example.com', password='testpassword')
        self.client.login(email='plain@example.com', password='testpassword')
        response = self.client.post(reverse('core:cohort-create'), {'name': 'X', 'code': 'X1', 'status': 'draft'})
        self.assertEqual(response.status_code, 403)

    def test_cohort_create_allows_admin(self):
        admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='testpassword')
        self.client.login(email='admin@example.com', password='testpassword')
        response = self.client.post(reverse('core:cohort-create'), {'name': 'X', 'code': 'X1', 'status': 'draft'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Cohort.objects.filter(code='X1').exists())

    def test_cohort_list_scoped_to_visible_cohorts(self):
        user = User.objects.create_user(username='member', email='member@example.com', password='testpassword')
        visible = make_cohort(name='Mine')
        visible.students.add(user)
        make_cohort(name='Not Mine')
        self.client.login(email='member@example.com', password='testpassword')
        response = self.client.get(reverse('core:cohort-list'))
        self.assertContains(response, 'Mine')
        self.assertNotContains(response, 'Not Mine')

    def test_cohort_detail_denied_for_non_member(self):
        user = User.objects.create_user(username='outsider2', email='outsider2@example.com', password='testpassword')
        cohort = make_cohort(name='Hidden Cohort')
        self.client.login(email='outsider2@example.com', password='testpassword')
        response = self.client.get(reverse('core:cohort-detail', kwargs={'pk': cohort.pk}))
        self.assertEqual(response.status_code, 403)


class QuestionBankPermissionTests(TestCase):
    def test_student_cannot_view_question_bank(self):
        user = User.objects.create_user(username='stud', email='stud@example.com', password='testpassword')
        self.client.login(email='stud@example.com', password='testpassword')
        response = self.client.get(reverse('core:question-list'))
        self.assertEqual(response.status_code, 403)

    def test_faculty_can_view_question_bank(self):
        user = User.objects.create_user(username='fac', email='fac@example.com', password='testpassword')
        cohort = make_cohort(name='Faculty Cohort', faculty_coordinator=user)
        self.client.login(email='fac@example.com', password='testpassword')
        response = self.client.get(reverse('core:question-list'))
        self.assertEqual(response.status_code, 200)

    def test_student_coordinator_question_forced_to_draft(self):
        user = User.objects.create_user(username='coord', email='coord@example.com', password='testpassword')
        cohort = make_cohort(name='Coord Cohort')
        cohort.student_coordinators.add(user)
        self.client.login(email='coord@example.com', password='testpassword')
        response = self.client.post(reverse('core:question-create'), {
            'title': 'Q1',
            'statement': 'Statement',
            'question_type': 'single_choice',
            'difficulty': 'medium',
            'positive_marks': '1',
            'negative_marks': '0',
            'default_time_minutes': '5',
            'approval_status': 'approved',
            'tags': '',
            'supported_languages': '',
        })
        self.assertEqual(response.status_code, 302)
        question = Question.objects.get(title='Q1')
        self.assertEqual(question.approval_status, 'draft')


class EvaluationTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username='eval_student', email='eval@example.com', password='testpassword')
        self.cohort = make_cohort(name='Eval Cohort')
        self.cohort.students.add(self.student)
        self.assessment = make_assessment(self.cohort, title='Eval Assessment', result_release_policy=ReleasePolicy.IMMEDIATE)
        self.question = Question.objects.create(
            title='2+2',
            statement='What is 2+2?',
            question_type='single_choice',
            positive_marks=Decimal('2'),
            negative_marks=Decimal('1'),
        )
        self.correct_choice = Choice.objects.create(question=self.question, text='4', is_correct=True)
        Choice.objects.create(question=self.question, text='5', is_correct=False)
        self.aq = AssessmentQuestion.objects.create(assessment=self.assessment, question=self.question, order=1, marks=Decimal('2'))

    def test_correct_answer_awards_full_marks_on_submit(self):
        self.client.login(email='eval@example.com', password='testpassword')
        self.client.post(reverse('core:assessment-start', kwargs={'pk': self.assessment.pk}))
        attempt = Attempt.objects.get(student=self.student, assessment=self.assessment)
        self.client.post(reverse('core:answer-save', kwargs={'pk': attempt.pk, 'aq_id': self.aq.pk}), {'choice': self.correct_choice.pk})
        self.client.post(reverse('core:attempt-submit', kwargs={'pk': attempt.pk}))
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, AttemptStatus.EVALUATED)
        self.assertEqual(attempt.score, Decimal('2'))

    def test_wrong_answer_applies_negative_marks(self):
        wrong_choice = Choice.objects.get(question=self.question, text='5')
        self.client.login(email='eval@example.com', password='testpassword')
        self.client.post(reverse('core:assessment-start', kwargs={'pk': self.assessment.pk}))
        attempt = Attempt.objects.get(student=self.student, assessment=self.assessment)
        self.client.post(reverse('core:answer-save', kwargs={'pk': attempt.pk, 'aq_id': self.aq.pk}), {'choice': wrong_choice.pk})
        self.client.post(reverse('core:attempt-submit', kwargs={'pk': attempt.pk}))
        attempt.refresh_from_db()
        self.assertEqual(attempt.score, Decimal('-1'))

    def test_results_hidden_before_release_and_visible_after(self):
        future_assessment = make_assessment(
            self.cohort,
            title='Future Close',
            end_datetime=timezone.now() + timezone.timedelta(hours=2),
            result_release_policy=ReleasePolicy.IMMEDIATE,
        )
        aq = AssessmentQuestion.objects.create(assessment=future_assessment, question=self.question, order=1, marks=Decimal('2'))
        self.client.login(email='eval@example.com', password='testpassword')
        self.client.post(reverse('core:assessment-start', kwargs={'pk': future_assessment.pk}))
        attempt = Attempt.objects.get(student=self.student, assessment=future_assessment)
        self.client.post(reverse('core:answer-save', kwargs={'pk': attempt.pk, 'aq_id': aq.pk}), {'choice': self.correct_choice.pk})
        self.client.post(reverse('core:attempt-submit', kwargs={'pk': attempt.pk}))
        response = self.client.get(reverse('core:attempt-detail', kwargs={'pk': attempt.pk}))
        self.assertContains(response, 'Results have not been released')

        future_assessment.end_datetime = timezone.now() - timezone.timedelta(minutes=1)
        future_assessment.save()
        response = self.client.get(reverse('core:attempt-detail', kwargs={'pk': attempt.pk}))
        self.assertNotContains(response, 'Results have not been released')

    def test_expired_attempt_auto_finalizes_on_access(self):
        assessment = make_assessment(
            self.cohort,
            title='Auto Expire',
            duration_minutes=1,
        )
        aq = AssessmentQuestion.objects.create(assessment=assessment, question=self.question, order=1, marks=Decimal('2'))
        attempt = Attempt.objects.create(assessment=assessment, student=self.student, attempt_number=1)
        Attempt.objects.filter(pk=attempt.pk).update(created_at=timezone.now() - timezone.timedelta(minutes=5))
        attempt.refresh_from_db()
        self.assertTrue(attempt.is_expired)
        self.client.login(email='eval@example.com', password='testpassword')
        self.client.get(reverse('core:attempt-detail', kwargs={'pk': attempt.pk}))
        attempt.refresh_from_db()
        self.assertNotEqual(attempt.status, AttemptStatus.IN_PROGRESS)

    def test_unanswered_question_does_not_crash_results_page(self):
        assessment = make_assessment(self.cohort, title='Unanswered Demo', end_datetime=timezone.now() - timezone.timedelta(minutes=1))
        AssessmentQuestion.objects.create(assessment=assessment, question=self.question, order=1, marks=Decimal('2'))
        attempt = Attempt.objects.create(assessment=assessment, student=self.student, attempt_number=1, status=AttemptStatus.SUBMITTED, score=Decimal('0'))
        self.client.login(email='eval@example.com', password='testpassword')
        response = self.client.get(reverse('core:attempt-detail', kwargs={'pk': attempt.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Not answered')

    def test_zero_score_and_marks_render_as_zero_not_pending(self):
        assessment = make_assessment(self.cohort, title='Zero Score Demo', end_datetime=timezone.now() - timezone.timedelta(minutes=1))
        aq = AssessmentQuestion.objects.create(assessment=assessment, question=self.question, order=1, marks=Decimal('2'))
        attempt = Attempt.objects.create(assessment=assessment, student=self.student, attempt_number=1, status=AttemptStatus.EVALUATED, score=Decimal('0'))
        wrong_choice = Choice.objects.get(question=self.question, text='5')
        Answer.objects.create(attempt=attempt, assessment_question=aq, selected_choice=wrong_choice, is_correct=False, awarded_marks=Decimal('0'))
        self.client.login(email='eval@example.com', password='testpassword')
        response = self.client.get(reverse('core:attempt-detail', kwargs={'pk': attempt.pk}))
        self.assertContains(response, 'Score:</strong> 0.00')
        self.assertContains(response, 'Awarded marks:</strong> 0.00')
        self.assertNotContains(response, 'Pending evaluation')

    def test_coding_answer_stays_pending_until_manual_grade(self):
        coding_question = Question.objects.create(
            title='Reverse a string',
            statement='Write a function...',
            question_type='coding',
            positive_marks=Decimal('5'),
        )
        assessment = make_assessment(self.cohort, title='Coding Assessment')
        aq = AssessmentQuestion.objects.create(assessment=assessment, question=coding_question, order=1, marks=Decimal('5'))
        self.client.login(email='eval@example.com', password='testpassword')
        self.client.post(reverse('core:assessment-start', kwargs={'pk': assessment.pk}))
        attempt = Attempt.objects.get(student=self.student, assessment=assessment)
        self.client.post(reverse('core:answer-save', kwargs={'pk': attempt.pk, 'aq_id': aq.pk}), {'code_answer': 'def f(): pass'})
        self.client.post(reverse('core:attempt-submit', kwargs={'pk': attempt.pk}))
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, AttemptStatus.SUBMITTED)
        self.assertIsNone(attempt.score)

        faculty = User.objects.create_user(username='grader', email='grader@example.com', password='testpassword')
        self.cohort.faculty_coordinator = faculty
        self.cohort.save()
        self.client.login(email='grader@example.com', password='testpassword')
        answer = Answer.objects.get(attempt=attempt, assessment_question=aq)
        self.client.post(reverse('core:attempt-grade', kwargs={'pk': attempt.pk}), {f'marks_{answer.pk}': '5'})
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, AttemptStatus.EVALUATED)
        self.assertEqual(attempt.score, Decimal('5'))


class ApiPermissionTests(TestCase):
    def test_api_requires_authentication(self):
        response = self.client.get('/api/attempts/')
        self.assertIn(response.status_code, (401, 403))

    def test_question_api_requires_content_author(self):
        user = User.objects.create_user(username='apistud', email='apistud@example.com', password='testpassword')
        self.client.login(email='apistud@example.com', password='testpassword')
        response = self.client.get('/api/questions/')
        self.assertEqual(response.status_code, 403)

    def test_attempt_api_scoped_to_own_attempts(self):
        owner = User.objects.create_user(username='owner', email='owner@example.com', password='testpassword')
        other = User.objects.create_user(username='other', email='other@example.com', password='testpassword')
        cohort = make_cohort(name='Api Cohort')
        cohort.students.add(owner)
        assessment = make_assessment(cohort, title='Api Assessment')
        Attempt.objects.create(assessment=assessment, student=owner, attempt_number=1)
        self.client.login(email='other@example.com', password='testpassword')
        response = self.client.get('/api/attempts/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

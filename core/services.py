"""Auto-evaluation and attempt finalization.

Coding answers are stored but never auto-graded here — this app never
executes untrusted student code; coding submissions stay pending until a
faculty member records marks manually.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Attempt, AttemptStatus, QuestionType


def evaluate_answer(answer):
    aq = answer.assessment_question
    question = aq.question
    marks = aq.marks
    negative = question.negative_marks

    if question.question_type == QuestionType.SINGLE_CHOICE:
        if answer.selected_choice_id is None:
            answer.is_correct = None
            answer.awarded_marks = Decimal('0')
        else:
            correct = answer.selected_choice.is_correct
            answer.is_correct = correct
            answer.awarded_marks = marks if correct else -negative

    elif question.question_type == QuestionType.MULTIPLE_CHOICE:
        selected_ids = set(answer.selected_choices.values_list('id', flat=True))
        if not selected_ids:
            answer.is_correct = None
            answer.awarded_marks = Decimal('0')
        else:
            correct_ids = set(question.choices.filter(is_correct=True).values_list('id', flat=True))
            correct = selected_ids == correct_ids
            answer.is_correct = correct
            answer.awarded_marks = marks if correct else -negative

    elif question.question_type == QuestionType.NUMERICAL:
        if answer.numeric_answer is None:
            answer.is_correct = None
            answer.awarded_marks = Decimal('0')
        else:
            correct = (
                question.correct_numeric_answer is not None
                and answer.numeric_answer == question.correct_numeric_answer
            )
            answer.is_correct = correct
            answer.awarded_marks = marks if correct else -negative

    elif question.question_type == QuestionType.SHORT_ANSWER:
        if not answer.text_answer:
            answer.is_correct = None
            answer.awarded_marks = Decimal('0')
        else:
            correct = bool(question.correct_text_answer) and (
                answer.text_answer.strip().lower() == question.correct_text_answer.strip().lower()
            )
            answer.is_correct = correct
            answer.awarded_marks = marks if correct else -negative

    else:
        return

    answer.save(update_fields=['is_correct', 'awarded_marks'])


def evaluate_attempt(attempt):
    """Auto-grade every objective answer and finalize the score if nothing is left pending manual/coding evaluation."""
    answers = attempt.answers.select_related('assessment_question__question', 'selected_choice').prefetch_related(
        'selected_choices'
    )
    all_evaluated = True
    total = Decimal('0')
    for answer in answers:
        question = answer.assessment_question.question
        if question.question_type == QuestionType.CODING:
            if answer.is_correct is None:
                all_evaluated = False
            else:
                total += answer.awarded_marks or Decimal('0')
            continue
        evaluate_answer(answer)
        total += answer.awarded_marks or Decimal('0')

    if all_evaluated:
        attempt.score = total
        attempt.status = AttemptStatus.EVALUATED
        attempt.save(update_fields=['score', 'status'])


def finalize_attempt(attempt, *, auto=False):
    """Submit an in-progress attempt (idempotent) and run evaluation."""
    if attempt.status != AttemptStatus.IN_PROGRESS:
        return attempt
    with transaction.atomic():
        locked = Attempt.objects.select_for_update().get(pk=attempt.pk)
        if locked.status != AttemptStatus.IN_PROGRESS:
            return locked
        now = timezone.now()
        locked.submitted_at = min(now, locked.deadline) if auto else now
        locked.time_taken_seconds = int((locked.submitted_at - locked.created_at).total_seconds())
        locked.status = AttemptStatus.SUBMITTED
        locked.save(update_fields=['submitted_at', 'time_taken_seconds', 'status'])
        evaluate_attempt(locked)
    return locked

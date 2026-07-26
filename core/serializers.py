from rest_framework import serializers

from .models import Answer, Assessment, AssessmentQuestion, Attempt, Choice, Cohort, Question, RoleAssignment, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'status', 'department', 'program']


class CohortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cohort
        fields = ['id', 'name', 'code', 'department', 'program', 'status']


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct', 'order']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'title', 'statement', 'question_type', 'topic', 'subtopic', 'tags', 'difficulty', 'positive_marks', 'negative_marks', 'default_time_minutes', 'explanation', 'approval_status', 'visible', 'created_at', 'updated_at', 'choices']


class AssessmentQuestionSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)

    class Meta:
        model = AssessmentQuestion
        fields = ['id', 'question', 'order', 'marks']


class AssessmentSerializer(serializers.ModelSerializer):
    assessment_questions = AssessmentQuestionSerializer(many=True, read_only=True)
    cohort = CohortSerializer(read_only=True)

    class Meta:
        model = Assessment
        fields = ['id', 'title', 'description', 'instructions', 'cohort', 'creator', 'approver', 'start_datetime', 'end_datetime', 'duration_minutes', 'max_attempts', 'total_marks', 'pass_mark', 'randomize_question_order', 'result_release_policy', 'explanation_release_policy', 'status', 'assessment_questions']


class AssessmentSummarySerializer(serializers.ModelSerializer):
    """Slim, answer-free assessment representation safe to nest anywhere (e.g. inside attempts)."""

    class Meta:
        model = Assessment
        fields = ['id', 'title', 'cohort', 'status', 'start_datetime', 'end_datetime']


class AttemptSerializer(serializers.ModelSerializer):
    assessment = AssessmentSummarySerializer(read_only=True)
    student = UserSerializer(read_only=True)

    class Meta:
        model = Attempt
        fields = ['id', 'assessment', 'student', 'created_at', 'submitted_at', 'status', 'score', 'time_taken_seconds', 'attempt_number']


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'attempt', 'assessment_question', 'selected_choice', 'selected_choices', 'numeric_answer', 'text_answer', 'code_answer', 'awarded_marks', 'feedback', 'is_correct', 'submitted_at']

from rest_framework import serializers
from django.utils import timezone
from .models import Answer, Assessment, AssessmentQuestion, Attempt, Choice, Cohort, Question, RoleAssignment, User
from django.contrib.auth.password_validation import validate_password


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password', 'first_name', 'last_name', 'department', 'program']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)  # hashes it properly
        user.save()
        return user
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'status', 'department', 'program']


class CohortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cohort
        fields = ['id', 'name', 'code', 'department', 'program', 'status']


from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    Answer, Assessment, AssessmentQuestion, Attempt, Choice,
    Cohort, Question, QuestionType, User,
)


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct', 'order']


class ChoiceWriteSerializer(serializers.ModelSerializer):
    """Used nested inside QuestionWriteSerializer for create/update."""
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct', 'order']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            'id', 'title', 'statement', 'question_type', 'topic', 'subtopic',
            'tags', 'difficulty', 'positive_marks', 'negative_marks',
            'default_time_minutes', 'explanation', 'approval_status', 'visible',
            'created_at', 'updated_at', 'choices',
        ]
        read_only_fields = ['approval_status', 'created_at', 'updated_at']


class QuestionWriteSerializer(serializers.ModelSerializer):
    """Handles create/update including nested choices, mirroring QuestionForm's intent."""
    choices = ChoiceWriteSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            'id', 'title', 'statement', 'question_type', 'topic', 'subtopic',
            'tags', 'difficulty', 'positive_marks', 'negative_marks',
            'default_time_minutes', 'explanation', 'correct_numeric_answer',
            'correct_text_answer', 'visible', 'choices',
            'input_format', 'output_format', 'constraints', 'example',
            'supported_languages', 'time_limit_seconds', 'memory_limit_mb',
        ]

    def validate(self, attrs):
        q_type = attrs.get('question_type', getattr(self.instance, 'question_type', None))
        choices = self.initial_data.get('choices')
        if q_type in (QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE) and not choices and not self.instance:
            raise serializers.ValidationError({'choices': 'At least one choice is required for choice-based questions.'})
        return attrs

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        request = self.context['request']
        validated_data['author'] = request.user
        # mirror QuestionCreateView.form_valid: non-approvers start as draft
        from .permissions import can_approve_content
        if not can_approve_content(request.user):
            validated_data['approval_status'] = 'draft'
        question = Question.objects.create(**validated_data)
        for choice_data in choices_data:
            choice_data.pop('id', None)
            Choice.objects.create(question=question, **choice_data)
        return question

    def update(self, instance, validated_data):
        choices_data = validated_data.pop('choices', None)
        request = self.context['request']
        from .permissions import can_approve_content
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        # mirror QuestionUpdateView: non-approver edit on approved content resets to pending
        if not can_approve_content(request.user) and instance.approval_status == 'approved':
            instance.approval_status = 'pending'
        instance.save()

        if choices_data is not None:
            existing_ids = {c.get('id') for c in choices_data if c.get('id')}
            instance.choices.exclude(id__in=existing_ids).delete()
            for choice_data in choices_data:
                choice_id = choice_data.pop('id', None)
                if choice_id:
                    Choice.objects.filter(id=choice_id, question=instance).update(**choice_data)
                else:
                    Choice.objects.create(question=instance, **choice_data)
        return instance

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

class AssessmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment
        fields = [
            'id', 'title', 'description', 'instructions', 'cohort',
            'start_datetime', 'end_datetime', 'duration_minutes', 'max_attempts',
            'total_marks', 'pass_mark', 'randomize_question_order',
            'result_release_policy', 'explanation_release_policy',
            'result_release_at', 'explanation_release_at', 'status',
        ]

    def validate(self, attrs):
        from .permissions import enforce_assessment_status
        from django.core.exceptions import PermissionDenied
        cohort = attrs.get('cohort', getattr(self.instance, 'cohort', None))
        status = attrs.get('status', getattr(self.instance, 'status', None))
        request = self.context['request']
        try:
            enforce_assessment_status(request.user, cohort, status)
        except PermissionDenied as e:
            raise serializers.ValidationError(str(e))
        return attrs

    def create(self, validated_data):
        validated_data['creator'] = self.context['request'].user
        return super().create(validated_data)

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
class AnswerSubmitSerializer(serializers.Serializer):
    """Mirrors AnswerSaveView's per-question-type branching."""
    choice = serializers.IntegerField(required=False, allow_null=True)
    choices = serializers.ListField(child=serializers.IntegerField(), required=False)
    numeric_answer = serializers.DecimalField(max_digits=12, decimal_places=4, required=False, allow_null=True)
    text_answer = serializers.CharField(required=False, allow_blank=True)
    code_answer = serializers.CharField(required=False, allow_blank=True)

    def save(self, *, answer, question):
        if question.question_type == QuestionType.SINGLE_CHOICE:
            answer.selected_choice_id = self.validated_data.get('choice')
        elif question.question_type == QuestionType.MULTIPLE_CHOICE:
            answer.save()
            answer.selected_choices.set(self.validated_data.get('choices', []))
        elif question.question_type == QuestionType.NUMERICAL:
            answer.numeric_answer = self.validated_data.get('numeric_answer')
        elif question.question_type == QuestionType.SHORT_ANSWER:
            answer.text_answer = self.validated_data.get('text_answer', '')
        elif question.question_type == QuestionType.CODING:
            answer.code_answer = self.validated_data.get('code_answer', '')
        answer.submitted_at = timezone.now()
        answer.save()
        return answer
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Assessment, AssessmentQuestion, Cohort, Question
from .permissions import is_admin, manageable_cohorts


class CohortForm(forms.ModelForm):
    class Meta:
        model = Cohort
        fields = [
            'name',
            'code',
            'department',
            'program',
            'admission_year',
            'graduation_year',
            'section',
            'academic_year',
            'start_date',
            'end_date',
            'status',
            'faculty_coordinator',
            'student_coordinators',
            'students',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'student_coordinators': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'students': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }


class QuestionForm(forms.ModelForm):
    tags = forms.CharField(
        required=False,
        label=_('Tags'),
        help_text=_('Comma-separated list of tags'),
    )

    class Meta:
        model = Question
        fields = [
            'title',
            'statement',
            'question_type',
            'topic',
            'subtopic',
            'tags',
            'difficulty',
            'positive_marks',
            'negative_marks',
            'default_time_minutes',
            'explanation',
            'question_type',
            'correct_numeric_answer',
            'correct_text_answer',
            'input_format',
            'output_format',
            'constraints',
            'example',
            'supported_languages',
            'time_limit_seconds',
            'memory_limit_mb',
            'approval_status',
            'visible',
        ]
        widgets = {
            'statement': forms.Textarea(attrs={'rows': 4}),
            'explanation': forms.Textarea(attrs={'rows': 3}),
            'constraints': forms.Textarea(attrs={'rows': 3}),
            'example': forms.Textarea(attrs={'rows': 3}),
            'supported_languages': forms.TextInput(attrs={'placeholder': 'python,java,csharp'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_tags(self):
        tags = self.cleaned_data.get('tags', '')
        if not tags:
            return []
        return [tag.strip() for tag in tags.split(',') if tag.strip()]

    def clean_supported_languages(self):
        languages = self.cleaned_data.get('supported_languages')
        if not languages:
            return []
        if isinstance(languages, str):
            return [lang.strip() for lang in languages.split(',') if lang.strip()]
        return languages


class AssessmentForm(forms.ModelForm):
    questions = forms.ModelMultipleChoiceField(
        queryset=Question.objects.filter(visible=True, approval_status='approved'),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        help_text=_('Choose questions to include in this assessment.'),
    )

    class Meta:
        model = Assessment
        fields = [
            'title',
            'description',
            'instructions',
            'cohort',
            'start_datetime',
            'end_datetime',
            'duration_minutes',
            'max_attempts',
            'total_marks',
            'pass_mark',
            'randomize_question_order',
            'result_release_policy',
            'explanation_release_policy',
            'result_release_at',
            'explanation_release_at',
            'status',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'instructions': forms.Textarea(attrs={'rows': 3}),
            'start_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'result_release_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'explanation_release_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and not is_admin(user):
            self.fields['cohort'].queryset = manageable_cohorts(user)
        if self.instance and self.instance.pk:
            self.fields['questions'].initial = [aq.question_id for aq in self.instance.assessment_questions.all()]

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            self.save_questions(instance)
        return instance

    def save_questions(self, instance):
        if instance.attempts.exists():
            # An assessment's question set is frozen once any student has attempted it.
            return
        selected_questions = self.cleaned_data.get('questions', [])
        instance.assessment_questions.all().delete()
        new_assessment_questions = []
        for index, question in enumerate(selected_questions, start=1):
            new_assessment_questions.append(
                AssessmentQuestion(
                    assessment=instance,
                    question=question,
                    order=index,
                    marks=question.positive_marks,
                )
            )
        AssessmentQuestion.objects.bulk_create(new_assessment_questions)

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_datetime')
        end = cleaned_data.get('end_datetime')
        if start and end and end <= start:
            self.add_error('end_datetime', _('End datetime must be after start datetime.'))
        return cleaned_data


class AssessmentStatusForm(forms.ModelForm):
    """Limited edit form used once an assessment has attempts: content and schedule are frozen."""

    class Meta:
        model = Assessment
        fields = ['status', 'result_release_at', 'explanation_release_at']
        widgets = {
            'result_release_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'explanation_release_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

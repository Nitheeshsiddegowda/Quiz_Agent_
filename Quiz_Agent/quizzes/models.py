from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class QuizSource(models.Model):
    """A PDF and the questions extracted from it."""
    pdf_name = models.CharField(max_length=255)
    pdf_file = models.FileField(upload_to="quiz_sources/", blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.pdf_name


class Question(models.Model):
    """A single-answer multiple-choice question from a quiz source."""

    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    source = models.ForeignKey(
        QuizSource, on_delete=models.CASCADE, related_name="questions"
    )
    question_text = models.TextField()
    subject = models.CharField(max_length=100, blank=True, default="", db_index=True)
    topic = models.CharField(max_length=100, blank=True, default="", db_index=True)
    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        blank=True,
        default="",
        db_index=True,
    )
    explanation = models.TextField(blank=True, default="")
    answer_text = models.TextField(
        blank=True,
        help_text="Legacy answer text retained for existing records.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question_text[:60]


class QuestionOption(models.Model):
    """One selectable answer option for a single-answer question."""

    class OptionKey(models.TextChoices):
        A = "A", "A"
        B = "B", "B"
        C = "C", "C"
        D = "D", "D"

    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="options"
    )
    option_key = models.CharField(max_length=1, choices=OptionKey.choices)
    option_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("option_key",)
        constraints = [
            models.UniqueConstraint(
                fields=("question", "option_key"),
                name="unique_option_key_per_question",
            ),
            models.CheckConstraint(
                check=Q(option_key__in=("A", "B", "C", "D")),
                name="valid_question_option_key",
            ),
        ]

    def clean(self):
        super().clean()
        if not self.is_correct or not self.question_id:
            return

        other_correct_option_exists = QuestionOption.objects.filter(
            question_id=self.question_id,
            is_correct=True,
        ).exclude(pk=self.pk).exists()
        if other_correct_option_exists:
            raise ValidationError(
                {"is_correct": "A question can have only one correct option."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.option_key}. {self.option_text[:60]}"

from django.db import models


class QuizSource(models.Model):
    """One row per PDF that was uploaded."""
    pdf_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.pdf_name


class Question(models.Model):
    """One row per question+answer pair extracted from a PDF."""
    source = models.ForeignKey(
        QuizSource, on_delete=models.CASCADE, related_name="questions"
    )
    question_text = models.TextField()
    answer_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question_text[:60]

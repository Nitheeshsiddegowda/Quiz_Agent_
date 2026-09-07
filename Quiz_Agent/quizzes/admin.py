from django.contrib import admin
from .models import QuizSource, Question


@admin.register(QuizSource)
class QuizSourceAdmin(admin.ModelAdmin):
    list_display = ("id", "pdf_name", "uploaded_at")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "question_text", "source", "created_at")
    search_fields = ("question_text", "answer_text")
    list_filter = ("source",)

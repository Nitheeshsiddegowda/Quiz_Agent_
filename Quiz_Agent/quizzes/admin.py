from django.contrib import admin
from .models import Question, QuestionOption, QuizSource


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 0


@admin.register(QuizSource)
class QuizSourceAdmin(admin.ModelAdmin):
    list_display = ("id", "pdf_name", "pdf_file", "uploaded_at")
    search_fields = ("pdf_name",)
    ordering = ("-uploaded_at",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "question_text",
        "source",
        "subject",
        "topic",
        "difficulty",
        "created_at",
    )
    search_fields = ("question_text", "subject", "topic", "explanation", "answer_text")
    list_filter = ("source", "subject", "topic", "difficulty")
    inlines = (QuestionOptionInline,)


@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "option_key", "option_text", "is_correct")
    list_filter = ("is_correct",)
    search_fields = ("question__question_text", "option_text")

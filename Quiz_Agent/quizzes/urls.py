from django.urls import path
from . import views

urlpatterns = [
    path("", views.upload_pdf, name="upload_pdf"),
    path("quiz/", views.quiz_setup, name="quiz_setup"),
    path("quiz/take/", views.quiz_take, name="quiz_take"),
    path("quiz/submit/", views.quiz_submit, name="quiz_submit"),
    path("quiz/results/", views.quiz_result, name="quiz_result"),
]

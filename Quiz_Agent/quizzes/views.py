import os
import tempfile
from datetime import datetime, timedelta

from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import PDFUploadForm
from .models import Question, QuestionOption, QuizSource
from .utils import extract_text_from_pdf, parse_questions


def upload_pdf(request):
    if request.method == "POST":
        form = PDFUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_file = form.cleaned_data["pdf_file"]

            # Save the upload to a temp file so pdfplumber can open it
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                for chunk in pdf_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            try:
                pdf_text = extract_text_from_pdf(tmp_path)

                if not pdf_text.strip():
                    messages.error(
                        request,
                        "Couldn't read any text from that PDF "
                        "(it may be a scanned image, not real text)."
                    )
                    return redirect("upload_pdf")

                qa_list = parse_questions(pdf_text)

                if not qa_list:
                    messages.warning(
                        request,
                        "No question/answer pairs were found in this PDF."
                    )
                    return redirect("upload_pdf")

                with transaction.atomic():
                    source = QuizSource.objects.create(
                        pdf_name=pdf_file.name,
                        pdf_file=pdf_file,
                    )

                    created_count = 0

                    for item in qa_list:
                        q = (item.get("question") or "").strip()
                        raw_answer = item.get("answer")
                        answer = raw_answer.strip().upper() if raw_answer else None
                        options = item.get("options") or {}

                        # Validate that question text and all four options are present
                        if (
                            not q
                            or len(options) != 4
                            or not all(options.get(k) for k in ("A", "B", "C", "D"))
                        ):
                            continue

                        # If an answer was parsed but does not match any option, treat as missing
                        if answer and answer not in options:
                            answer = None

                        question = Question.objects.create(
                            source=source,
                            question_text=q,
                            answer_text=answer or "",
                        )

                        for option_key in ("A", "B", "C", "D"):
                            option_text = (options.get(option_key) or "").strip()

                            QuestionOption.objects.create(
                                question=question,
                                option_key=option_key,
                                option_text=option_text,
                                is_correct=(option_key == answer) if answer else False,
                            )

                        created_count += 1

                messages.success(
                    request,
                    f"Done! Saved {created_count} question(s) from '{pdf_file.name}'."
                )

            except Exception as e:
                messages.error(request, f"Something went wrong: {e}")

            finally:
                os.remove(tmp_path)

            return redirect("upload_pdf")
    else:
        form = PDFUploadForm()

    recent_questions = (
        Question.objects.select_related("source").order_by("-created_at")[:50]
    )
    return render(
        request,
        "quizzes/upload.html",
        {"form": form, "questions": recent_questions},
    )


def quiz_setup(request):
    """Display quiz setup screen to choose question source and time limit."""
    sources = (
        QuizSource.objects.annotate(question_count=Count("questions"))
        .filter(question_count__gt=0)
        .order_by("-uploaded_at")
    )
    total_questions = Question.objects.count()

    return render(
        request,
        "quizzes/quiz_setup.html",
        {
            "sources": sources,
            "total_questions": total_questions,
        },
    )


def quiz_take(request):
    """Handle starting a quiz (POST) and taking the active exam (GET)."""
    if request.method == "POST":
        source_id = request.POST.get("source_id", "").strip()
        time_limit_str = request.POST.get("time_limit", "600").strip()

        if source_id and source_id != "all":
            source = QuizSource.objects.filter(id=source_id).first()
            if not source:
                messages.error(request, "Selected quiz source was not found.")
                return redirect("quiz_setup")
            questions = Question.objects.filter(source=source).order_by("id")
            source_name = source.pdf_name
        else:
            source_id = "all"
            source_name = "All Available Questions"
            questions = Question.objects.all().order_by("id")

        question_ids = list(questions.values_list("id", flat=True))
        if not question_ids:
            messages.warning(request, "No questions found for the selected quiz.")
            return redirect("quiz_setup")

        try:
            time_limit_seconds = int(time_limit_str)
            if time_limit_seconds <= 0:
                time_limit_seconds = None
        except (ValueError, TypeError):
            time_limit_seconds = 600

        start_time = timezone.now()
        deadline = (
            start_time + timedelta(seconds=time_limit_seconds)
            if time_limit_seconds
            else None
        )

        request.session["active_quiz"] = {
            "source_id": source_id,
            "source_name": source_name,
            "question_ids": question_ids,
            "start_time": start_time.isoformat(),
            "deadline": deadline.isoformat() if deadline else None,
            "time_limit_seconds": time_limit_seconds,
        }
        return redirect("quiz_take")

    # GET request: render the active exam
    active_quiz = request.session.get("active_quiz")
    if not active_quiz or not active_quiz.get("question_ids"):
        messages.info(request, "Please select and start a quiz first.")
        return redirect("quiz_setup")

    question_ids = active_quiz["question_ids"]
    questions = (
        Question.objects.filter(id__in=question_ids)
        .prefetch_related("options")
        .order_by("id")
    )

    remaining_seconds = None
    is_timed = False
    if active_quiz.get("deadline"):
        is_timed = True
        deadline = datetime.fromisoformat(active_quiz["deadline"])
        remaining_seconds = max(
            0, int((deadline - timezone.now()).total_seconds())
        )

    return render(
        request,
        "quizzes/quiz_take.html",
        {
            "questions": questions,
            "source_name": active_quiz.get("source_name", "Quiz"),
            "is_timed": is_timed,
            "remaining_seconds": remaining_seconds,
            "time_limit_seconds": active_quiz.get("time_limit_seconds"),
        },
    )


def quiz_submit(request):
    """Validate submitted answers, enforce deadline, score exam, and store result snapshot."""
    if request.method != "POST":
        return redirect("quiz_setup")

    active_quiz = request.session.get("active_quiz")
    if not active_quiz or not active_quiz.get("question_ids"):
        # If user refreshes or hits submit after submission, redirect to last result
        if "last_quiz_result" in request.session:
            return redirect("quiz_result")
        messages.error(request, "No active quiz was found to submit.")
        return redirect("quiz_setup")

    submission_time = timezone.now()
    start_time = datetime.fromisoformat(active_quiz["start_time"])
    elapsed_seconds = max(0, int((submission_time - start_time).total_seconds()))

    # Server deadline check with 10-second grace period
    is_timed_out = False
    if active_quiz.get("deadline"):
        deadline = datetime.fromisoformat(active_quiz["deadline"])
        grace_period = timedelta(seconds=10)
        if submission_time > (deadline + grace_period):
            is_timed_out = True

    # Pop active quiz immediately to prevent repeated submission of the same attempt
    request.session.pop("active_quiz", None)

    question_ids = active_quiz["question_ids"]
    questions = (
        Question.objects.filter(id__in=question_ids)
        .prefetch_related("options")
        .order_by("id")
    )

    total_questions = len(questions)
    graded_questions = 0
    ungraded_questions = 0
    correct_count = 0
    incorrect_count = 0
    unattempted_count = 0
    question_results = []

    for q in questions:
        options = list(q.options.all().order_by("option_key"))
        options_dict = {opt.option_key: opt.option_text for opt in options}
        correct_opt = next((opt for opt in options if opt.is_correct), None)
        correct_key = correct_opt.option_key if correct_opt else None

        # Accept answer only for this specific question
        raw_answer = request.POST.get(f"question_{q.id}")
        submitted_key = raw_answer.strip().upper() if raw_answer else None

        # Validate that submitted option actually exists for this question
        if submitted_key and submitted_key not in options_dict:
            submitted_key = None

        if correct_key is None:
            # Ungraded: no designated correct answer in database
            ungraded_questions += 1
            status = "ungraded"
        elif submitted_key is None:
            # Unattempted: question has a key, but user left it blank
            graded_questions += 1
            unattempted_count += 1
            status = "unattempted"
        elif submitted_key == correct_key:
            # Correct
            graded_questions += 1
            correct_count += 1
            status = "correct"
        else:
            # Incorrect
            graded_questions += 1
            incorrect_count += 1
            status = "incorrect"

        question_results.append(
            {
                "question_id": q.id,
                "question_text": q.question_text,
                "options": options_dict,
                "selected_option": submitted_key,
                "correct_option": correct_key,
                "status": status,
                "explanation": q.explanation,
            }
        )

    score_percentage = (
        round((correct_count / graded_questions) * 100, 1)
        if graded_questions > 0
        else None
    )

    result_snapshot = {
        "source_name": active_quiz.get("source_name", "Quiz"),
        "total_questions": total_questions,
        "graded_questions": graded_questions,
        "ungraded_questions": ungraded_questions,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "unattempted_count": unattempted_count,
        "score_percentage": score_percentage,
        "time_taken_seconds": elapsed_seconds,
        "is_timed_out": is_timed_out,
        "questions": question_results,
    }

    request.session["last_quiz_result"] = result_snapshot
    return redirect("quiz_result")


def quiz_result(request):
    """Render the completed quiz result snapshot from session."""
    result = request.session.get("last_quiz_result")
    if not result:
        messages.info(request, "No quiz results available.")
        return redirect("quiz_setup")

    seconds = result.get("time_taken_seconds", 0)
    minutes = seconds // 60
    rem_seconds = seconds % 60
    if minutes > 0:
        formatted_time = f"{minutes}m {rem_seconds}s"
    else:
        formatted_time = f"{rem_seconds}s"

    return render(
        request,
        "quizzes/quiz_result.html",
        {
            "result": result,
            "formatted_time": formatted_time,
        },
    )

import os
import tempfile

from django.shortcuts import render, redirect
from django.contrib import messages

from .models import QuizSource, Question
from .forms import PDFUploadForm
from .utils import extract_text_from_pdf, parse_questions
from .models import QuizSource, Question, QuestionOption


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

                source = QuizSource.objects.create(
                    pdf_name=pdf_file.name,
                    pdf_file=pdf_file,
                )

                created_count = 0

                for item in qa_list:
                    q = (item.get("question") or "").strip()
                    answer = (item.get("answer") or "").strip().upper()
                    options = item.get("options") or {}

                    if not q or answer not in options:
                        continue

                    question = Question.objects.create(
                        source=source,
                        question_text=q,
                        answer_text=answer,
                    )

                    for option_key in ("A", "B", "C", "D"):
                        option_text = (options.get(option_key) or "").strip()

                        QuestionOption.objects.create(
                            question=question,
                            option_key=option_key,
                            option_text=option_text,
                            is_correct=(option_key == answer),
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



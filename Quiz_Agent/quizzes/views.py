import os
import tempfile

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

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

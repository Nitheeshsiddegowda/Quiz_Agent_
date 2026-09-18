"""Utilities for the local-first PDF processing flow."""

import pdfplumber


def extract_text_from_pdf(file_path):
    """Read every page of a PDF and return all extracted text as one string."""
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def parse_questions(pdf_text):
    """Parse numbered MCQs with A-D options and an Answer line."""
    import re

    questions = []

    # Split whenever a new numbered question starts.
    blocks = re.split(r"(?m)(?=^\d+\.\s+)", pdf_text.strip())

    for block in blocks:
        block = block.strip()

        if not block:
            continue

        question_match = re.match(
            r"^\d+\.\s+(.+?)(?=\nA\.\s+)",
            block,
            re.DOTALL,
        )

        if not question_match:
            continue

        question_text = question_match.group(1).strip()

        options = {}
        for key in ("A", "B", "C", "D"):
            option_match = re.search(
                rf"(?m)^{key}\.\s+(.+?)(?=\n[A-D]\.\s+|\nAnswer:\s*)",
                block,
                re.DOTALL,
            )

            if option_match:
                options[key] = option_match.group(1).strip()

        answer_match = re.search(
            r"(?mi)^Answer:\s*([A-D])\s*$",
            block,
        )

        if (
            len(options) == 4
            and set(options.keys()) == {"A", "B", "C", "D"}
            and answer_match
        ):
            questions.append(
                {
                    "question": question_text,
                    "options": options,
                    "answer": answer_match.group(1).upper(),
                }
            )

    return questions

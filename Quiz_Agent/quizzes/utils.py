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
    """Placeholder for the future local question-extraction parser."""
    raise NotImplementedError(
        "Question extraction parser will be implemented in a later phase."
    )

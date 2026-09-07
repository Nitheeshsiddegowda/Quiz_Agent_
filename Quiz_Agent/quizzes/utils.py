"""
This file contains the "AI Agent" logic for Day 1:
1. extract_text_from_pdf   -> pulls raw text out of the uploaded PDF
2. parse_questions_with_gemini -> sends that text to Gemini and asks it
   to return clean, structured question/answer pairs as JSON,
   no matter what format the original PDF used.
"""

import json
import pdfplumber
import google.generativeai as genai
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)


def extract_text_from_pdf(file_path):
    """Reads every page of the PDF and returns all text as one string."""
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def parse_questions_with_gemini(pdf_text):
    """
    Sends the raw PDF text to Gemini and asks it to identify every
    question + answer pair, regardless of how it was formatted in
    the original PDF (numbered list, Q:/A: labels, MCQs, etc).

    Returns a Python list of dicts: [{"question": ..., "answer": ...}, ...]
    """
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
You are given raw text extracted from a PDF that contains quiz questions
and their answers. The formatting may vary a lot: numbered questions,
"Q:"/"A:" labels, multiple choice questions, plain paragraphs, tables, etc.

Your task: find EVERY question and its correct answer in this text, and
return ONLY a valid JSON array. No markdown, no code fences, no extra
commentary, no explanation text -- just the JSON array itself.

Format each item exactly like this:
[
  {{"question": "full question text here", "answer": "full answer text here"}}
]

Rules:
- If a question has multiple-choice options, include the options inside
  the question text.
- If the source only marks the answer as a letter/option (e.g. "Answer: B"),
  write out the full text of that option as the answer, if you can
  determine it from the options given.
- Do not skip any question, and do not invent questions that are not
  present in the text.
- Return [] if you find no valid questions.

PDF TEXT:
\"\"\"
{pdf_text}
\"\"\"
"""

    response = model.generate_content(prompt)
    raw_output = response.text.strip()

    # Gemini sometimes wraps output in ```json ... ``` even when told not to.
    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`")
        if raw_output.lower().startswith("json"):
            raw_output = raw_output[4:].strip()

    try:
        qa_list = json.loads(raw_output)
    except json.JSONDecodeError:
        raise ValueError(
            "Gemini did not return valid JSON. Raw response was:\n" + raw_output
        )

    if not isinstance(qa_list, list):
        raise ValueError("Gemini response was valid JSON but not a list.")

    return qa_list

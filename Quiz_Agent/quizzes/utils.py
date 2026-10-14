"""Utilities for the local-first PDF processing flow."""

import re
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


def clean_multiline_text(text):
    """Normalize multiline text by joining soft-wrapped lines while preserving paragraphs."""
    if not text:
        return ""
    paragraphs = text.strip().split("\n\n")
    cleaned_paragraphs = []
    for p in paragraphs:
        lines = [line.strip() for line in p.splitlines() if line.strip()]
        if lines:
            cleaned_paragraphs.append(" ".join(lines))
    return "\n\n".join(cleaned_paragraphs)


# Question start pattern:
# Matches lines starting with:
# - Prefixes: Q1. , Q1: , Q.1 , Question 1. , Question 1: , Question 1 -
# - Number in parentheses: (1) , (12)
# - Number with delimiter: 1. , 1) , 1: , 1 -
QUESTION_START_PATTERN = re.compile(
    r"(?m)(?=^(?:(?:q(?:uestion)?\.?\s*\d+\s*(?:[\.\)\:\-]\s*|\s+))|(?:\(\d+\)\s*[\.\:\-]?\s+)|(?:\d+\s*(?:[\.\)\:]|\-)\s+)))",
    re.IGNORECASE,
)

# Strips the leading question number / prefix from the start of a matched block:
QUESTION_HEADER_PATTERN = re.compile(
    r"^(?:(?:q(?:uestion)?\.?\s*\d+\s*(?:[\.\)\:\-]\s*|\s+))|(?:\(\d+\)\s*[\.\:\-]?\s+)|(?:\d+\s*(?:[\.\)\:]|\-)\s+))",
    re.IGNORECASE,
)

# Option header pattern:
# Matches at the start of a line:
# A. , A) , A: , (A) , [A] , and lowercase equivalents a. , a) , (a)
OPTION_HEADER_PATTERN = re.compile(
    r"(?m)^(?:\(([A-Da-d])\)|\[([A-Da-d])\]|([A-Da-d])[\.\)\:])\s+"
)

# Answer line pattern:
# Matches: Answer: A , Ans: B , Correct Answer: C , Answer - D , Ans. (A) , Answer: A.
ANSWER_PATTERN = re.compile(
    r"(?mi)^(?:correct\s+answer|answer\s*key|answer|ans)[\s\:\.\-]+(?:\(([A-Da-d])\)|\[([A-Da-d])\]|([A-Da-d]))(?:\.|\)|\s|$)"
)


def parse_questions(pdf_text):
    """Parse MCQs with support for varied numbering, option styles, and answer formats."""
    if not pdf_text or not pdf_text.strip():
        return []

    questions = []
    blocks = QUESTION_START_PATTERN.split(pdf_text.strip())

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        header_match = QUESTION_HEADER_PATTERN.match(block)
        if not header_match:
            continue

        body = block[header_match.end():]

        opt_matches = []
        for m in OPTION_HEADER_PATTERN.finditer(body):
            key = (m.group(1) or m.group(2) or m.group(3)).upper()
            opt_matches.append((key, m.start(), m.end()))

        # Require exactly four options in A, B, C, D sequence
        seq = [m[0] for m in opt_matches]
        if seq != ["A", "B", "C", "D"]:
            continue

        q_raw = body[:opt_matches[0][1]]
        opt_a_raw = body[opt_matches[0][2]:opt_matches[1][1]]
        opt_b_raw = body[opt_matches[1][2]:opt_matches[2][1]]
        opt_c_raw = body[opt_matches[2][2]:opt_matches[3][1]]
        remainder = body[opt_matches[3][2]:]

        ans_match = ANSWER_PATTERN.search(remainder)
        if ans_match:
            opt_d_raw = remainder[:ans_match.start()]
            answer = (ans_match.group(1) or ans_match.group(2) or ans_match.group(3)).upper()
        else:
            # Check if answer was declared before options
            ans_pre = ANSWER_PATTERN.search(q_raw)
            if ans_pre:
                answer = (ans_pre.group(1) or ans_pre.group(2) or ans_pre.group(3)).upper()
                q_raw = q_raw[:ans_pre.start()] + q_raw[ans_pre.end():]
                opt_d_raw = remainder
            else:
                opt_d_raw = remainder
                answer = None

        q_text = clean_multiline_text(q_raw)
        options = {
            "A": clean_multiline_text(opt_a_raw),
            "B": clean_multiline_text(opt_b_raw),
            "C": clean_multiline_text(opt_c_raw),
            "D": clean_multiline_text(opt_d_raw),
        }

        # Validate that question and all 4 options are non-empty
        if not q_text or len(options) != 4 or not all(options.values()):
            continue

        questions.append({
            "question": q_text,
            "options": options,
            "answer": answer,
        })

    return questions

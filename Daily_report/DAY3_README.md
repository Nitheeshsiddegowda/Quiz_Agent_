# Day 3 — Local Question Parser

**Date:** 18 September 2026
**Branch:** `day-3-local-question-parser`

## Goal

Implement a local question parser so the Quiz_Agent can convert extracted PDF text into structured MCQ data **without using any external AI API**.

---

## What Was Completed

### 1. Local MCQ Parser

Implemented `parse_questions()` in:

```text
Quiz_Agent/quizzes/utils.py
```

The parser currently supports the project’s standard format:

```text
1. Question text
A. Option A
B. Option B
C. Option C
D. Option D
Answer: A
```

It extracts:

* Question text
* Options A, B, C and D
* Correct answer

Answers are normalized to uppercase.

Invalid/incomplete questions are skipped.

---

### 2. Database Integration

Updated:

```text
Quiz_Agent/quizzes/views.py
```

The PDF upload flow now performs:

```text
PDF
 ↓
pdfplumber
 ↓
Extracted text
 ↓
parse_questions()
 ↓
Question
 ↓
QuestionOption
```

For every valid question:

* One `Question` record is created.
* Four `QuestionOption` records are created.
* The correct option is marked with `is_correct=True`.

---

### 3. PDF Upload Test

Tested the complete flow using an 8-question sample PDF.

Result:

```text
Questions:       8
QuestionOptions: 32
```

Correct answer mappings were verified successfully.

---

### 4. Automated Tests

Created:

```text
Quiz_Agent/quizzes/tests.py
```

Added tests for:

* Single question parsing
* Multiple question parsing
* Invalid question handling
* Lowercase answer normalization

Test command:

```powershell
python manage.py test quizzes
```

Result:

```text
Ran 4 tests
OK
```

---

### 5. Git Cleanup

Updated `.gitignore` to exclude uploaded PDF files:

```text
Quiz_Agent/quiz_sources/
```

This prevents user-uploaded quiz PDFs from being committed to Git.

Also verified:

```powershell
git diff --check
```

No errors reported.

---

## Files Changed

```text
.gitignore
Quiz_Agent/quizzes/utils.py
Quiz_Agent/quizzes/views.py
Quiz_Agent/quizzes/tests.py
Daily_report/DAY3_README.md
```

---

## Current Status

| Component                 | Status         |
| ------------------------- | -------------- |
| PDF text extraction       | ✅              |
| Local question parser     | ✅              |
| Question database storage | ✅              |
| Option database storage   | ✅              |
| Correct answer mapping    | ✅              |
| Parser unit tests         | ✅              |
| External AI API           | ❌ Not required |

---

## Current Parser Limitation

The parser currently expects a consistent numbered MCQ format with **A-D options and an `Answer:` line**.

Support for different PDF/question formats can be improved later.

---

## Next Step

**Day 4:** Improve the question-processing pipeline and begin building the quiz/exam functionality on top of the stored questions.

# Day 4 — Parser Validation and Realistic Question Formats

**Date:** 14 October 2026
**Branch:** `day-4-parser-validation`
**Commit:** `0c46a1e`

---

## 1. Day 4 Objective

The primary objective of Day 4 was to harden and enhance the local question-parsing engine before building the quiz-taking and examination features.

The goals included:
* Supporting realistic question numbering styles (`1.`, `1)`, `1:`, `1 -`, `(1)`, `Q1.`, `Question 1:`).
* Supporting diverse option labeling formats (`A.`, `A)`, `(A)`, `[A]`, and lowercase equivalents `a.`, `a)`, `(a)`).
* Normalizing all option keys to standard uppercase (`A`, `B`, `C`, `D`) for database compatibility.
* Expanding answer-key recognition (`Answer:`, `Ans:`, `Correct Answer:`, `Answer -`, with optional parentheses or punctuation).
* Correctly parsing multiline questions and options by joining soft-wrapped lines while preserving formatting.
* Handling missing answers gracefully: preserving valid questions and options in the database without inventing arbitrary answers or marking spurious options as correct.
* Filtering out document noise (headers, instructions, page numbers) and discarding incomplete or malformed questions without data corruption.
* Adding a comprehensive automated test suite and verifying regression against the existing sample test PDF.

---

## 2. Starting State of the Project

At the end of Day 3:
* The project had a local question parser in `Quiz_Agent/quizzes/utils.py` relying on strict regex patterns.
* Only questions starting exactly with `^\d+\.\s+` and options starting strictly with `^[A-D]\.\s+` were supported.
* Only exact answer lines matching `^Answer:\s*([A-D])\s*$` were recognized.
* Any variation in punctuation (e.g. `(A)`, `1)`, `Ans: B`) caused questions to be skipped.
* Questions without an answer key were silently discarded during upload ingestion in `views.py`.
* 4 unit tests existed in `quizzes/tests.py`, all passing.
* The sample 8-question PDF (`quiz_sources/quiz_parser_test.pdf`) was processed successfully under standard formatting.

---

## 3. Problems Identified in the Existing Parser

1. **Option Format Inflexibility:** Realistic PDFs frequently use `(A)`, `A)`, or lowercase `a.`, `a)`. The Day 3 parser rejected all of these.
2. **Numbering Format Inflexibility:** Common numbering styles like `1)`, `1:`, `1 -`, `(1)`, `Q1.`, or `Question 1:` failed to match `^\d+\.\s+`.
3. **Rigid Answer-Key Matching:** Realistic answer keys frequently use abbreviations (`Ans:`, `Ans.`) or alternative phrases (`Correct Answer:`, `Answer -`, `Answer: (B)`), which were not recognized.
4. **Multiline Formatting:** PDF text extraction wraps lines based on page margins. Indented continuation lines or multiline options were not cleanly normalized into single readable sentences.
5. **Silent Discard of Questions with Missing Answers:** In `quizzes/views.py`, the condition `if not q or answer not in options: continue` completely discarded questions that had valid question text and 4 complete options simply because no answer key was present in the source text.
6. **Lack of Transaction Atomicity:** Multiple questions and options were inserted in a loop without database transaction protection.

---

## 4. Files Inspected and Modified

### Inspected:
* `Quiz_Agent/quizzes/models.py`
* `Quiz_Agent/quizzes/admin.py`
* `Quiz_Agent/quizzes/forms.py`
* `Quiz_Agent/quizzes/migrations/0001_initial.py`
* `Quiz_Agent/quizzes/migrations/0002_question_difficulty_question_explanation_and_more.py`
* `Quiz_Agent/quiz_sources/quiz_parser_test.pdf`

### Modified:
1. `Quiz_Agent/quizzes/utils.py`
   * Refactored `parse_questions()` to support multiple question prefixes, flexible option headers, flexible answer markers, and multiline joining.
   * Added `clean_multiline_text()` helper to normalize soft-wrapped text cleanly.
2. `Quiz_Agent/quizzes/views.py`
   * Wrapped upload persistence in `transaction.atomic()`.
   * Preserved questions with missing answers (`answer_text=""`, all options `is_correct=False`).
   * Cleaned up duplicate model imports.
3. `Quiz_Agent/quizzes/templates/quizzes/upload.html`
   * Updated title and subtitle to accurately describe the local-first extraction architecture.
4. `Quiz_Agent/quizzes/tests.py`
   * Expanded test coverage from 4 tests to 15 tests covering all new features, edge cases, missing answers, and database persistence.
5. `Daily_report/DAY4_README.md`
   * Created this Day 4 technical report.

---

## 5. Implementation Changes

### A. Multiline Normalization
Added `clean_multiline_text(text)`:
```python
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
```
This joins text wrapped across lines due to PDF layout into single readable strings, while preserving deliberate paragraph breaks.

### B. Flexible Question Segmentation
Enhanced regular expressions to detect question boundaries without ambiguity:
```python
QUESTION_START_PATTERN = re.compile(
    r"(?m)(?=^(?:(?:q(?:uestion)?\.?\s*\d+\s*(?:[\.\)\:\-]\s*|\s+))|(?:\(\d+\)\s*[\.\:\-]?\s+)|(?:\d+\s*(?:[\.\)\:]|\-)\s+)))",
    re.IGNORECASE,
)
```
* Supports `1.`, `1)`, `1:`, `1 -`, `(1)`, `Q1.`, `Q1:`, `Q.1`, `Question 1.`, `Question 1:`, `Question 1 -`.
* Excludes decimals (e.g. `3.14 is pi`) and non-question lines starting with years (e.g. `1991 was a great year`).

### C. Flexible Option Header Matching & Normalization
```python
OPTION_HEADER_PATTERN = re.compile(
    r"(?m)^(?:\(([A-Da-d])\)|\[([A-Da-d])\]|([A-Da-d])[\.\)\:])\s+"
)
```
* Matches `A.`, `A)`, `A:`, `(A)`, `[A]`, `a.`, `a)`, `(a)`.
* Automatically normalizes extracted option keys to standard uppercase: `'A'`, `'B'`, `'C'`, `'D'`.
* Ensures options strictly follow the `['A', 'B', 'C', 'D']` sequence.

### D. Flexible Answer-Key Matching
```python
ANSWER_PATTERN = re.compile(
    r"(?mi)^(?:correct\s+answer|answer\s*key|answer|ans)[\s\:\.\-]+(?:\(([A-Da-d])\)|\[([A-Da-d])\]|([A-Da-d]))(?:\.|\)|\s|$)"
)
```
* Recognizes `Answer: A`, `Ans: B`, `Correct Answer: C`, `Answer - D`, `Ans. (A)`, `Answer: A.`.
* Normalizes the answer to uppercase.
* If an answer line is missing, `answer` is set to `None`.

### E. Handling Missing Answers & Database Persistence
In `quizzes/views.py`:
* When `answer` is recognized and valid, `question.answer_text` stores the key, and the corresponding option is marked `is_correct=True`.
* When `answer` is `None` (no answer key found in the document):
  * The question text and all 4 options are preserved in the database.
  * `question.answer_text` is set to `""`.
  * All four `QuestionOption` records are saved with `is_correct=False`.
  * This satisfies `QuestionOption.clean()` (which enforces *at most one* correct option) and preserves data for instructor review in Django Admin without guessing answers.

---

## 6. How the Parsing Flow Works After the Changes

```text
Raw Extracted PDF Text
         ↓
QUESTION_START_PATTERN.split()
         ↓
For each block:
   1. Match and strip question header (e.g. "1. ", "Q1: ", "(1) ")
   2. Scan for options matching OPTION_HEADER_PATTERN
   3. Verify exactly 4 options exist in sequence A, B, C, D
   4. Extract Question Text (from block start to Option A)
   5. Extract Options A, B, C, D text slices
   6. Search for Answer Key after Option D (or in header)
   7. Clean and normalize multiline text
   8. If valid, return {"question": ..., "options": {"A": ..., "B": ..., "C": ..., "D": ...}, "answer": "..." or None}
         ↓
views.py (upload_pdf inside transaction.atomic()):
   1. Create QuizSource
   2. Create Question (answer_text=answer or "")
   3. Create 4 QuestionOptions (is_correct=(key == answer) if answer else False)
```

---

## 7. Supported Question and Option Formats

### Question Numbering:
* `1. What is Python?`
* `1) What is Python?`
* `1: What is Python?`
* `1 - What is Python?`
* `(1) What is Python?`
* `Q1. What is Python?`
* `Q1: What is Python?`
* `Q.1 What is Python?`
* `Question 1. What is Python?`
* `Question 1: What is Python?`
* `Question 1 - What is Python?`

### Option Labels:
* `A.`, `B.`, `C.`, `D.`
* `A)`, `B)`, `C)`, `D)`
* `(A)`, `(B)`, `(C)`, `(D)`
* `[A]`, `[B]`, `[C]`, `[D]`
* `a.`, `b.`, `c.`, `d.`
* `a)`, `b)`, `c)`, `d)`
* `(a)`, `(b)`, `(c)`, `(d)`

---

## 8. Answer-Key Handling

Supported Answer-Key Formats:
* `Answer: A`
* `Ans: B`
* `Ans. C`
* `Correct Answer: D`
* `Answer - A`
* `Answer: (B)`
* `Ans: [C]`
* `Answer: A.`

When an answer key is matched:
* The answer is extracted, stripped, and converted to uppercase.
* If trailing explanations follow on the same line, the letter answer is still extracted cleanly.
* In the database, the matched `QuestionOption` has `is_correct=True`.

When no answer key exists:
* `answer` is set to `None`.
* The question and its options are still saved to the database.
* All options have `is_correct=False`.
* `question.answer_text` is `""`.

---

## 9. Error and Incomplete-Question Handling

* **Missing Options:** If a question has fewer than 4 options (e.g. only A and B), it is treated as malformed and safely skipped.
* **Empty Option or Question Text:** If any option or the question text itself is empty, the question is discarded.
* **Unrelated Content:** Document preambles, instructions, and trailing footers (e.g. `Page 1 of 10`) are ignored because they do not match the required question header or option sequence.
* **Missing Answers:** Distinquished from malformed questions. Questions with all 4 options but without an answer key are preserved with `answer=None`, preventing loss of valid quiz questions.

---

## 10. Tests Added

Expanded `Quiz_Agent/quizzes/tests.py` from 4 to 15 tests:

1. `test_parse_single_question`: Verifies standard single question parsing.
2. `test_parse_multiple_questions`: Verifies multiple question extraction.
3. `test_invalid_question_is_skipped`: Verifies incomplete questions are dropped.
4. `test_answer_is_normalized_to_uppercase`: Verifies lowercase answers normalize to uppercase.
5. `test_multiline_question_and_options`: Verifies multiline question statements and options join cleanly.
6. `test_option_format_parentheses_and_brackets`: Verifies `(A)`-`(D)` and `[A]`-`[D]` formats.
7. `test_option_format_trailing_parenthesis_and_lowercase`: Verifies `a)`-`d)` formats.
8. `test_question_numbering_variations`: Verifies `1)`, `Q2:`, `Question 3 -`, and `(4)` styles.
9. `test_answer_key_variations`: Verifies `Ans:`, `Correct Answer:`, `Answer -`, and `Ans. (A)`.
10. `test_question_with_missing_answer_is_preserved`: Verifies questions without answers yield `answer: None`.
11. `test_incomplete_questions_missing_options_are_skipped`: Verifies 3-option and empty-option blocks are skipped.
12. `test_empty_or_whitespace_input`: Verifies parser handles empty and whitespace strings gracefully.
13. `test_unrelated_text_and_headers_ignored`: Verifies examination titles, instructions, and page numbers are ignored.
14. `test_sample_pdf_fixture_parsing`: Verifies the sample test PDF (`quiz_parser_test.pdf`) produces all 8 questions with correct answers (`['A', 'B', 'C', 'D', 'A', 'B', 'C', 'B']`).
15. `test_saving_question_with_and_without_answer`: Verifies database persistence for both answered and unanswered questions with `QuestionOption` integrity constraints.

---

## 11. Commands Executed and Their Actual Results

### Test Execution Command:
```powershell
python manage.py test quizzes
```
**Output:**
```text
Found 15 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
...............
----------------------------------------------------------------------
Ran 15 tests in 0.101s

OK
Destroying test database for alias 'default'...
```

### Django System Check Command:
```powershell
python manage.py check
```
**Output:**
```text
System check identified no issues (0 silenced).
```

### Git Diff Check Command:
```powershell
git diff --check
```
**Output:**
*(Exited with code 0, no errors reported)*

---

## 12. Before-and-After Validation Results

| Feature / Behavior | Day 3 Baseline | Day 4 Completed State |
| :--- | :--- | :--- |
| **Question Numbering** | Only `1. ` format | `1.`, `1)`, `1:`, `1 -`, `(1)`, `Q1.`, `Question 1:`, etc. |
| **Option Formats** | Only `A.`, `B.`, `C.`, `D.` | `A.`, `A)`, `(A)`, `[A]`, `a.`, `a)`, `(a)`, normalized to A–D |
| **Answer-Key Formats** | Only `Answer: [A-D]` | `Answer:`, `Ans:`, `Correct Answer:`, `Answer -`, `Ans. (A)` |
| **Multiline Handling** | Basic multiline (raw newlines kept) | Soft-wrapped lines joined cleanly; paragraphs preserved |
| **Missing Answers** | Silently dropped during upload | Preserved in database with `is_correct=False` for all options |
| **Upload Transaction** | Non-atomic batch inserts | Atomic transaction wrapping all records |
| **Unit Test Coverage** | 4 tests | 15 tests (all passing) |
| **External AI API** | None (Local-first) | None (Local-first preserved) |

---

## 13. Limitations That Remain

1. **Fixed 4-Option MCQ Focus:** The parser is tailored specifically to 4-option multiple-choice questions (A, B, C, D). True/False or 5-option questions are currently filtered out.
2. **Tabular or Multi-Column Layouts:** Complex multi-column PDF layouts where `pdfplumber` interleaves column text horizontally may require layout-aware text extraction in future iterations.
3. **Question Metadata Extraction:** Fields on `Question` such as `difficulty`, `subject`, and `topic` are preserved on the model but are not yet auto-detected from PDF text headers.

---

## 14. Git Branch and Commit Information

* **Branch:** `day-4-parser-validation`
* **Commit:** `0c46a1e`
* **Commit Message:** `"Improve local question parser validation"`
* **Base Commit:** `c77e21b` (`main`)

---

## 15. What Was Completed Today

* Upgraded `parse_questions()` to handle realistic question numbering, option labeling, multiline text, and answer-key variations.
* Maintained 100% normalization to standard uppercase option keys (`A`, `B`, `C`, `D`).
* Updated upload persistence to save valid questions with missing answers safely inside an atomic transaction.
* Expanded test suite from 4 to 15 automated unit and integration tests.
* Confirmed the 8-question sample PDF continues to parse and map answers with 100% accuracy.
* Documented the complete Day 4 milestone in `Daily_report/DAY4_README.md`.

---

## 16. What Remains for the Next Development Day (Day 5)

Day 5 will focus on building the **Quiz / Exam Engine**:
1. Quiz generation views (selecting questions by source, topic, or difficulty).
2. Interactive quiz-taking template and timer.
3. Student response submission and scoring engine.
4. Results view and answer review summary.

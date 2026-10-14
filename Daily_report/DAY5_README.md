# Day 5 — Quiz/Exam Engine Foundation

**Date:** 14 October 2026
**Branch:** `day-5-quiz-engine-foundation`

---

## 1. Day 5 Objective

The primary objective of Day 5 was to build the foundation for conducting timed and untimed multiple-choice quizzes and examinations using questions already extracted and stored in the database.

Key requirements included:
* Selecting questions by specific `QuizSource` PDF or across all available sources in original database order.
* Server-enforced countdown timer with a 10-second grace period for network latency, while using JavaScript strictly for visual display and automatic form submission.
* Strict submission validation: accepting answers only for questions belonging to the active exam session and verifying that every submitted option belongs to its corresponding question.
* Clear scoring rules distinguishing Correct, Incorrect, Unattempted, and Ungraded questions (questions without answer keys), excluding ungraded questions from the score denominator and preventing division by zero.
* Storing only lightweight, JSON-serializable state in Django sessions without premature database migrations or models.
* Providing a question-by-question review interface displaying user choices, correct answers, and explanations.

---

## 2. Starting State of the Project

At the end of Day 4:
* PDF upload, selectable text extraction via `pdfplumber`, regex-based local parsing, and relational MySQL persistence for `QuizSource`, `Question`, and `QuestionOption` were complete.
* 15 automated unit and integration tests existed in `quizzes/tests.py`, all passing.
* No quiz-taking views, URLs, or templates existed; only `upload_pdf` at root path `""`.
* Questions were present in the database, but there was no way for a user to select, take, submit, or score an exam.

---

## 3. Problems and Gaps Identified for Quiz Execution

1. **No Exam Setup or Selection View:** Users had no way to choose a specific PDF source or configure timer settings.
2. **Missing Quiz-Taking Interface:** No view rendered questions with interactive radio options A–D.
3. **No Time Limit Enforcement:** No mechanism existed to track start time, calculate remaining duration, or auto-submit on expiration.
4. **No Answer Evaluation Engine:** No backend logic compared submitted choices against `QuestionOption.is_correct=True`.
5. **Handling of Questions Without Answer Keys:** Day 4 added support for preserving questions without answer keys (`is_correct=False` for all options). Without explicit handling, these questions would either falsely count as incorrect or cause division-by-zero errors if all questions were ungraded.
6. **Replay / Resubmission Vulnerabilities:** Refreshing or clicking back after submission could re-evaluate or corrupt scores without session state isolation.

---

## 4. Files Inspected and Modified / Created

### Inspected:
* `Quiz_Agent/quiz_project/settings.py` (verified MySQL configuration and `SessionMiddleware`)
* `Quiz_Agent/quiz_project/urls.py` (verified root routing to `quizzes.urls`)
* `Quiz_Agent/quizzes/models.py` (verified `Question` and `QuestionOption` fields)

### Created:
1. `Quiz_Agent/quizzes/templates/quizzes/quiz_setup.html`: Quiz setup interface for choosing sources and time limits.
2. `Quiz_Agent/quizzes/templates/quizzes/quiz_take.html`: Interactive exam-taking interface with sticky header, radio inputs, and JavaScript countdown timer.
3. `Quiz_Agent/quizzes/templates/quizzes/quiz_result.html`: Scorecard summary, time taken, late submission warnings, and question-by-question review.
4. `Daily_report/DAY5_README.md`: Comprehensive Day 5 documentation.

### Modified:
1. `Quiz_Agent/quizzes/views.py`: Implemented `quiz_setup`, `quiz_take`, `quiz_submit`, and `quiz_result` views with server timer validation and scoring rules.
2. `Quiz_Agent/quizzes/urls.py`: Registered routes for `/quiz/`, `/quiz/take/`, `/quiz/submit/`, and `/quiz/results/`.
3. `Quiz_Agent/quizzes/templates/quizzes/upload.html`: Added top navigation bar linking to the Quiz Engine.
4. `Quiz_Agent/quizzes/tests.py`: Added `QuizEngineTests` with 17 integration test cases covering the entire quiz lifecycle.

---

## 5. Implementation Changes

### A. Session State Management
Only JSON-serializable primitives are stored in `request.session`:
* **`active_quiz`:** Stores `source_id`, `source_name`, `question_ids` list, `start_time` (ISO), `deadline` (ISO or None), and `time_limit_seconds`.
* **`last_quiz_result`:** Stores `total_questions`, `graded_questions`, `ungraded_questions`, `correct_count`, `incorrect_count`, `unattempted_count`, `score_percentage`, `time_taken_seconds`, `is_timed_out`, and the `questions` review list.

### B. Server-Enforced Timer & Grace Period
* The server computes the deadline upon starting the quiz: `deadline = start_time + timedelta(seconds=time_limit)`.
* On submission, the server checks if `timezone.now() > deadline + timedelta(seconds=10)`.
* If exceeded, `is_timed_out = True` is recorded and a prominent warning banner is displayed on the results page.
* If untimed (`time_limit == 0`), `deadline` is `None` and elapsed time is tracked without a cutoff.
* JavaScript acts purely as a client-side convenience, displaying remaining minutes/seconds and calling `form.submit()` when time expires.

### C. Whitelisting and Option Validation
* On submit, only question IDs present in `session['active_quiz']['question_ids']` are processed.
* Each submitted choice is validated against the question's available options (`A`, `B`, `C`, `D`). Invalid or unlisted options are stripped and receive no credit.

### D. Idempotency & Resubmission Prevention
* `request.session.pop("active_quiz", None)` is executed immediately upon processing a submission.
* Subsequent POST requests or browser refreshes redirect directly to `quiz_result` without double-evaluating.

---

## 6. How the Quiz Execution Flow Works

```text
1. User navigates to /quiz/ (quiz_setup)
   ↓ Selects Source (or "All") and Time Limit (5m, 10m, 15m, or Untimed)
2. Form posts to /quiz/take/ (quiz_take)
   ↓ Server fetches questions in database order, initializes session['active_quiz']
   ↓ Redirects (PRG) to GET /quiz/take/
3. User takes exam on /quiz/take/
   ↓ Client countdown displays remaining time (submits automatically on 00:00)
   ↓ User selects radio buttons for questions
4. Form posts to /quiz/submit/ (quiz_submit)
   ↓ Server checks deadline + 10s grace period
   ↓ Server compares answers against QuestionOption.is_correct
   ↓ Server computes score metrics and pops active_quiz
   ↓ Stores result snapshot in session['last_quiz_result']
   ↓ Redirects to /quiz/results/
5. User reviews results on /quiz/results/ (quiz_result)
   ↓ View displays score %, fraction correct, time taken, and per-question explanations
```

---

## 7. Supported Question Selection, Timer, and Validation Rules

* **Question Scope:**
  * Specific PDF source (e.g. `quiz_parser_test.pdf`).
  * "All Available Sources" (aggregates all questions in the database).
* **Question Ordering:** Guaranteed original database order (`order_by("id")`).
* **Time Limits:**
  * 5 Minutes (`300` seconds)
  * 10 Minutes (`600` seconds, default)
  * 15 Minutes (`900` seconds)
  * Untimed (`0` seconds)
* **Option Validation:** Validated against existing options for that question. Non-existent keys (e.g. `'Z'`) are safely rejected.
* **Empty Question Handling:** If 0 questions are available, the user is warned and cannot start an empty quiz.

---

## 8. Scoring Rules and Formula

Every question is categorized into one of four states:
* **Correct:** User choice matches `is_correct=True`.
* **Incorrect:** User choice does not match `is_correct=True`.
* **Unattempted:** User made no selection for a gradable question.
* **Ungraded:** Question has no correct answer key in the database (`is_correct=False` for all options).

### Formula:
$$\text{Graded Questions} = \text{Total Questions} - \text{Ungraded Questions}$$

$$\text{Score Percentage} = \begin{cases} \left( \frac{\text{Correct}}{\text{Graded Questions}} \right) \times 100 & \text{if } \text{Graded Questions} > 0 \\ \text{N/A} & \text{if } \text{Graded Questions} = 0 \end{cases}$$

Ungraded questions are explicitly excluded from the score denominator, preventing students from being penalized for questions lacking answer keys. When zero gradable questions exist, `score_percentage` is `None` ("N/A"), preventing `ZeroDivisionError`.

---

## 9. Error and Edge-Case Handling

* **Tampered Form Submissions:** Question IDs submitted that were not part of the active quiz session are ignored.
* **Expired Timer:** Submissions received after deadline plus 10 seconds grace period are scored, but flagged with a red banner: *"Time Expired: This exam was submitted after the allowed deadline plus the 10-second grace period."*
* **Double Submission / Replay:** Popping `active_quiz` ensures refreshing or pressing back redirects cleanly to results.
* **Zero Questions in Database:** Renders an informative empty-state card with a button directing the user to the PDF upload page.
* **Direct Access to /quiz/take/ without Session:** Safely redirects to `/quiz/` with an informational message.

---

## 10. Tests Added

Added `QuizEngineTests` in `quizzes/tests.py` with 17 integration tests:

1. `test_quiz_setup_empty_database`: Verifies empty-state rendering when no questions exist.
2. `test_quiz_setup_with_sources`: Verifies listing sources with question counts.
3. `test_quiz_take_source_selection_and_order`: Verifies selecting a specific source loads only its questions in database order.
4. `test_quiz_take_all_sources`: Verifies selecting "all" loads all questions in database order.
5. `test_quiz_take_renders_all_options`: Verifies questions and radio options A–D render in HTML.
6. `test_quiz_take_redirects_if_no_active_quiz`: Direct GET without active session redirects to setup.
7. `test_perfect_score_submission`: 100% score calculation and results rendering.
8. `test_mixed_score_submission`: Correct evaluation of correct, incorrect, and unattempted answers.
9. `test_ungraded_question_excluded_from_denominator`: Verifies ungraded questions do not count against the score.
10. `test_zero_gradable_questions_division_by_zero_prevention`: Prevents division by zero when no questions have answer keys.
11. `test_invalid_option_submission_handled`: Non-existent option keys (e.g. `'Z'`) are rejected and receive no credit.
12. `test_tampered_question_id_ignored`: Foreign question IDs in POST payload are ignored.
13. `test_timed_out_submission_flagged`: Submissions beyond deadline + 10s grace period are flagged as timed out.
14. `test_submission_within_grace_period_not_timed_out`: Submissions within 10s grace period are accepted without late penalty.
15. `test_untimed_quiz_submission`: Untimed exam workflow scores accurately without a deadline.
16. `test_resubmission_idempotency`: Second submission redirects to results without double-evaluation.
17. `test_quiz_result_view_redirects_if_no_result`: Direct GET to `/quiz/results/` without session redirects to setup.

---

## 11. Commands Executed and Their Actual Results

### Automated Test Suite:
```powershell
python manage.py test quizzes
```
**Output:**
```text
Found 32 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
................................
----------------------------------------------------------------------
Ran 32 tests in 0.792s

OK
Destroying test database for alias 'default'...
```

### Django System Check:
```powershell
python manage.py check
```
**Output:**
```text
System check identified no issues (0 silenced).
```

### Git Diff Check:
```powershell
git diff --check
```
**Output:**
*(Exited with code 0, no errors reported)*

### Manual Full Workflow Verification:
* Executed automated end-to-end client verification covering:
  * `/quiz/` setup page rendering (HTTP 200).
  * `/quiz/take/` active exam rendering with sticky timer (HTTP 200).
  * `/quiz/submit/` answer evaluation and redirection (HTTP 302).
  * `/quiz/results/` score card and question review rendering (HTTP 200).
  * Untimed quiz execution (`is_timed_out: False`).
  * Late submission enforcement (`is_timed_out: True`, "Time Expired" banner displayed).
* **Result:** All manual workflow checks passed with 100% expected behavior.

---

## 12. Before-and-After Validation Results

| Component / Feature | Day 4 Baseline | Day 5 Completed State |
| :--- | :--- | :--- |
| **Quiz Setup Interface** | None | `/quiz/` with source and time limit selectors |
| **Exam Taking Interface** | None | `/quiz/take/` with sticky countdown timer and radio choices A–D |
| **Timer Enforcement** | None | Server-authoritative start/deadline with 10s grace period |
| **Submission Scoring** | None | `/quiz/submit/` with exact evaluation against `is_correct=True` |
| **Ungraded Question Handling** | Saved with `is_correct=False` | Excluded from score denominator; division-by-zero prevented |
| **Results & Answer Review** | None | `/quiz/results/` with score %, metric cards, and explanations |
| **Navigation** | Upload page only | Top navigation between Upload and Quiz |
| **Total Test Suite** | 15 tests | 32 tests (100% passing) |
| **Database Migrations** | None added | None added (zero schema changes) |

---

## 13. Limitations That Remain

1. **Session-Only Persistence for Results:** Quiz attempts and results are stored in the user's session snapshot rather than a persistent database table (`QuizAttempt`). History is lost if the session expires or another quiz is started.
2. **User Authentication:** Exams are open and local; user accounts, student tracking, and role-based permissions are not yet implemented.
3. **Question Randomization:** Questions and options are served strictly in original database order; shuffling is deferred.
4. **Issue #4 (Duplicate Upload Display):** Explicitly preserved for future resolution per project instructions.

---

## 14. Git Branch and Commit Information

* **Branch:** `day-5-quiz-engine-foundation`
* **Commit:** `ea129b8`
* **Base Commit:** `e8eaaec` (`main`)
* **Staged / Modified Files:**
  * `Quiz_Agent/quizzes/views.py`
  * `Quiz_Agent/quizzes/urls.py`
  * `Quiz_Agent/quizzes/templates/quizzes/upload.html`
  * `Quiz_Agent/quizzes/templates/quizzes/quiz_setup.html`
  * `Quiz_Agent/quizzes/templates/quizzes/quiz_take.html`
  * `Quiz_Agent/quizzes/templates/quizzes/quiz_result.html`
  * `Quiz_Agent/quizzes/tests.py`
  * `Daily_report/DAY5_README.md`

---

## 15. What Was Completed Today

* Built complete, working Quiz Engine Foundation from selection to exam-taking, submission, scoring, and review.
* Implemented authoritative server-side timer validation with client countdown and 10s grace period.
* Implemented scoring engine excluding ungraded questions and preventing division by zero.
* Added 17 new automated tests (total 32 passing tests).
* Verified the complete workflow end-to-end.
* Created comprehensive documentation in `Daily_report/DAY5_README.md`.

---

## 16. What Remains for Future Development (Day 6+)

1. **Persistent Quiz History & Analytics:** Introduce a `QuizAttempt` / `QuizAnswer` model to persist scores across sessions.
2. **User Authentication & Accounts:** Multi-user support, student logins, and instructor views.
3. **Randomization & Shuffling:** Optional shuffling of question order and option choices.
4. **Weak-Topic Analysis:** Diagnostic breakdown of performance by `subject` and `topic`.

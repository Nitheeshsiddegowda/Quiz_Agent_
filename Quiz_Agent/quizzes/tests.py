import os
from datetime import datetime, timedelta
from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Question, QuestionOption, QuizSource
from .utils import extract_text_from_pdf, parse_questions


class ParseQuestionsTests(SimpleTestCase):
    def test_parse_single_question(self):
        pdf_text = """1. What is Python?
A. A programming language
B. A database
C. An operating system
D. A web browser
Answer: A"""

        result = parse_questions(pdf_text)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["question"], "What is Python?")
        self.assertEqual(
            result[0]["options"],
            {
                "A": "A programming language",
                "B": "A database",
                "C": "An operating system",
                "D": "A web browser",
            },
        )
        self.assertEqual(result[0]["answer"], "A")

    def test_parse_multiple_questions(self):
        pdf_text = """1. What is Python?
A. A programming language
B. A database
C. An operating system
D. A web browser
Answer: A

2. Which database is relational?
A. MongoDB
B. MySQL
C. Redis
D. Neo4j
Answer: B"""

        result = parse_questions(pdf_text)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["answer"], "A")
        self.assertEqual(result[1]["answer"], "B")

    def test_invalid_question_is_skipped(self):
        pdf_text = """1. Valid question?
A. Option one
B. Option two
C. Option three
D. Option four
Answer: A

2. Invalid question?
A. Option one
B. Option two
Answer: B"""

        result = parse_questions(pdf_text)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["question"], "Valid question?")

    def test_answer_is_normalized_to_uppercase(self):
        pdf_text = """1. What does SQL stand for?
A. Structured Query Language
B. Simple Question Language
C. System Query Logic
D. Structured Question List
Answer: a"""

        result = parse_questions(pdf_text)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["answer"], "A")

    def test_multiline_question_and_options(self):
        pdf_text = """12. Which of the following methods is used to
    retrieve an element from a Python dictionary?
A. append() method for list
   structures
B. get()
C. push()
D. insert()
Answer: B"""

        result = parse_questions(pdf_text)

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["question"],
            "Which of the following methods is used to retrieve an element from a Python dictionary?",
        )
        self.assertEqual(
            result[0]["options"]["A"],
            "append() method for list structures",
        )
        self.assertEqual(result[0]["answer"], "B")

    def test_option_format_parentheses_and_brackets(self):
        pdf_text = """1. Choose the correct option:
(A) First option
(B) Second option
(C) Third option
(D) Fourth option
Answer: (B)

2. Another question:
[A] Option Alpha
[B] Option Beta
[C] Option Gamma
[D] Option Delta
Answer: [C]"""

        result = parse_questions(pdf_text)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["options"]["A"], "First option")
        self.assertEqual(result[0]["answer"], "B")
        self.assertEqual(result[1]["options"]["C"], "Option Gamma")
        self.assertEqual(result[1]["answer"], "C")

    def test_option_format_trailing_parenthesis_and_lowercase(self):
        pdf_text = """1) Which syntax is valid?
a) Option one
b) Option two
c) Option three
d) Option four
Ans: c"""

        result = parse_questions(pdf_text)

        self.assertEqual(len(result), 1)
        self.assertIn("A", result[0]["options"])
        self.assertEqual(result[0]["options"]["A"], "Option one")
        self.assertEqual(result[0]["answer"], "C")

    def test_question_numbering_variations(self):
        pdf_text = """1) First style?
A. One
B. Two
C. Three
D. Four
Answer: A

Q2: Second style?
A. One
B. Two
C. Three
D. Four
Answer: B

Question 3 - Third style?
A. One
B. Two
C. Three
D. Four
Answer: C

(4) Fourth style?
A. One
B. Two
C. Three
D. Four
Answer: D"""

        result = parse_questions(pdf_text)

        self.assertEqual(len(result), 4)
        self.assertEqual(result[0]["question"], "First style?")
        self.assertEqual(result[1]["question"], "Second style?")
        self.assertEqual(result[2]["question"], "Third style?")
        self.assertEqual(result[3]["question"], "Fourth style?")

    def test_answer_key_variations(self):
        pdf_text = """1. Question one?
A. A
B. B
C. C
D. D
Ans: B

2. Question two?
A. A
B. B
C. C
D. D
Correct Answer: C

3. Question three?
A. A
B. B
C. C
D. D
Answer - D

4. Question four?
A. A
B. B
C. C
D. D
Ans. (A)"""

        result = parse_questions(pdf_text)

        self.assertEqual(len(result), 4)
        self.assertEqual(result[0]["answer"], "B")
        self.assertEqual(result[1]["answer"], "C")
        self.assertEqual(result[2]["answer"], "D")
        self.assertEqual(result[3]["answer"], "A")

    def test_question_with_missing_answer_is_preserved(self):
        pdf_text = """1. Valid question without an answer provided?
A. Option A
B. Option B
C. Option C
D. Option D

2. Valid question with an answer?
A. Option A
B. Option B
C. Option C
D. Option D
Answer: B"""

        result = parse_questions(pdf_text)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["question"], "Valid question without an answer provided?")
        self.assertIsNone(result[0]["answer"])
        self.assertEqual(result[1]["answer"], "B")

    def test_incomplete_questions_missing_options_are_skipped(self):
        pdf_text = """1. Incomplete question with only 3 options?
A. Option A
B. Option B
C. Option C
Answer: A

2. Question with empty option text?
A.
B. Option B
C. Option C
D. Option D
Answer: B"""

        result = parse_questions(pdf_text)

        self.assertEqual(len(result), 0)

    def test_empty_or_whitespace_input(self):
        self.assertEqual(parse_questions(""), [])
        self.assertEqual(parse_questions("   \n\t   \n"), [])
        self.assertEqual(parse_questions(None), [])

    def test_unrelated_text_and_headers_ignored(self):
        pdf_text = """EXAMINATION PAPER 2026
Instructions: Read all questions carefully before answering.
Each question carries 1 mark.

1. What is the output of print(2 ** 3)?
A. 6
B. 8
C. 9
D. 5
Answer: B

Page 1 of 10
General Knowledge Section"""

        result = parse_questions(pdf_text)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["question"], "What is the output of print(2 ** 3)?")
        self.assertEqual(result[0]["answer"], "B")

    def test_sample_pdf_fixture_parsing(self):
        pdf_path = os.path.join(settings.BASE_DIR, "quiz_sources", "quiz_parser_test.pdf")
        if not os.path.exists(pdf_path):
            self.skipTest(f"Sample PDF fixture not found at {pdf_path}")

        extracted_text = extract_text_from_pdf(pdf_path)
        questions = parse_questions(extracted_text)

        self.assertEqual(len(questions), 8)
        expected_answers = ["A", "B", "C", "D", "A", "B", "C", "B"]
        for i, q in enumerate(questions):
            self.assertEqual(q["answer"], expected_answers[i])
            self.assertEqual(len(q["options"]), 4)
            self.assertEqual(set(q["options"].keys()), {"A", "B", "C", "D"})


class PersistenceIntegrationTests(TestCase):
    def test_saving_question_with_and_without_answer(self):
        source = QuizSource.objects.create(pdf_name="test_integration.pdf")

        # Case 1: Question with valid answer
        q_answered = Question.objects.create(
            source=source,
            question_text="Answered question?",
            answer_text="B",
        )
        for key in ("A", "B", "C", "D"):
            QuestionOption.objects.create(
                question=q_answered,
                option_key=key,
                option_text=f"Option {key}",
                is_correct=(key == "B"),
            )

        self.assertEqual(q_answered.options.filter(is_correct=True).count(), 1)
        self.assertEqual(q_answered.options.get(is_correct=True).option_key, "B")

        # Case 2: Question with missing answer preserved
        q_unanswered = Question.objects.create(
            source=source,
            question_text="Unanswered question?",
            answer_text="",
        )
        for key in ("A", "B", "C", "D"):
            QuestionOption.objects.create(
                question=q_unanswered,
                option_key=key,
                option_text=f"Option {key}",
                is_correct=False,
            )

        self.assertEqual(q_unanswered.options.filter(is_correct=True).count(), 0)
        self.assertEqual(q_unanswered.options.count(), 4)


class QuizEngineTests(TestCase):
    def _create_question(self, source, text, answer_key=None, explanation=""):
        q = Question.objects.create(
            source=source,
            question_text=text,
            answer_text=answer_key or "",
            explanation=explanation,
        )
        for key in ("A", "B", "C", "D"):
            QuestionOption.objects.create(
                question=q,
                option_key=key,
                option_text=f"{key} option for {text}",
                is_correct=(key == answer_key) if answer_key else False,
            )
        return q

    def test_quiz_setup_empty_database(self):
        response = self.client.get(reverse("quiz_setup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No questions found in the database")

    def test_quiz_setup_with_sources(self):
        s1 = QuizSource.objects.create(pdf_name="sample_quiz.pdf")
        self._create_question(s1, "Question 1", "A")
        self._create_question(s1, "Question 2", "B")

        response = self.client.get(reverse("quiz_setup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "sample_quiz.pdf")
        self.assertContains(response, "2 questions")

    def test_quiz_take_source_selection_and_order(self):
        s1 = QuizSource.objects.create(pdf_name="first.pdf")
        q1 = self._create_question(s1, "Q1", "A")
        q2 = self._create_question(s1, "Q2", "B")

        s2 = QuizSource.objects.create(pdf_name="second.pdf")
        self._create_question(s2, "Q3", "C")

        # Select only s1
        response = self.client.post(
            reverse("quiz_take"),
            {"source_id": s1.id, "time_limit": "600"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "first.pdf")
        self.assertContains(response, "Q1")
        self.assertContains(response, "Q2")
        self.assertNotContains(response, "Q3")

        session_active = self.client.session.get("active_quiz")
        self.assertIsNotNone(session_active)
        self.assertEqual(session_active["question_ids"], [q1.id, q2.id])

    def test_quiz_take_all_sources(self):
        s1 = QuizSource.objects.create(pdf_name="source1.pdf")
        q1 = self._create_question(s1, "Question Alpha", "A")
        s2 = QuizSource.objects.create(pdf_name="source2.pdf")
        q2 = self._create_question(s2, "Question Beta", "B")

        response = self.client.post(
            reverse("quiz_take"),
            {"source_id": "all", "time_limit": "300"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Question Alpha")
        self.assertContains(response, "Question Beta")
        session_active = self.client.session.get("active_quiz")
        self.assertEqual(session_active["question_ids"], [q1.id, q2.id])

    def test_quiz_take_renders_all_options(self):
        s = QuizSource.objects.create(pdf_name="test.pdf")
        q = self._create_question(s, "What is Python?", "A")

        self.client.post(reverse("quiz_take"), {"source_id": s.id, "time_limit": "600"})
        response = self.client.get(reverse("quiz_take"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"question_{q.id}")
        for key in ("A", "B", "C", "D"):
            self.assertContains(response, f'value="{key}"')

    def test_quiz_take_redirects_if_no_active_quiz(self):
        response = self.client.get(reverse("quiz_take"))
        self.assertRedirects(response, reverse("quiz_setup"))

    def test_perfect_score_submission(self):
        s = QuizSource.objects.create(pdf_name="quiz.pdf")
        q1 = self._create_question(s, "Q1", "A")
        q2 = self._create_question(s, "Q2", "C")

        # Start quiz
        self.client.post(reverse("quiz_take"), {"source_id": s.id, "time_limit": "600"})

        # Submit perfect answers
        response = self.client.post(
            reverse("quiz_submit"),
            {f"question_{q1.id}": "A", f"question_{q2.id}": "C"},
            follow=True,
        )
        self.assertRedirects(response, reverse("quiz_result"))
        result = self.client.session.get("last_quiz_result")

        self.assertIsNotNone(result)
        self.assertEqual(result["total_questions"], 2)
        self.assertEqual(result["graded_questions"], 2)
        self.assertEqual(result["correct_count"], 2)
        self.assertEqual(result["incorrect_count"], 0)
        self.assertEqual(result["unattempted_count"], 0)
        self.assertEqual(result["score_percentage"], 100.0)
        self.assertFalse(result["is_timed_out"])
        self.assertContains(response, "100.0%")

    def test_mixed_score_submission(self):
        s = QuizSource.objects.create(pdf_name="quiz.pdf")
        q1 = self._create_question(s, "Q1", "A")
        q2 = self._create_question(s, "Q2", "B")
        q3 = self._create_question(s, "Q3", "C")

        self.client.post(reverse("quiz_take"), {"source_id": s.id, "time_limit": "600"})

        # Submit: q1 correct ('A'), q2 incorrect ('D'), q3 unattempted (missing)
        response = self.client.post(
            reverse("quiz_submit"),
            {f"question_{q1.id}": "A", f"question_{q2.id}": "D"},
            follow=True,
        )
        self.assertRedirects(response, reverse("quiz_result"))
        result = self.client.session.get("last_quiz_result")

        self.assertEqual(result["total_questions"], 3)
        self.assertEqual(result["graded_questions"], 3)
        self.assertEqual(result["correct_count"], 1)
        self.assertEqual(result["incorrect_count"], 1)
        self.assertEqual(result["unattempted_count"], 1)
        self.assertEqual(result["score_percentage"], 33.3)

    def test_ungraded_question_excluded_from_denominator(self):
        s = QuizSource.objects.create(pdf_name="quiz.pdf")
        q1 = self._create_question(s, "Q1", "A")
        q2 = self._create_question(s, "Q2", "B")
        q3_ungraded = self._create_question(s, "Q3", answer_key=None)  # No answer key

        self.client.post(reverse("quiz_take"), {"source_id": s.id, "time_limit": "600"})

        # Both graded questions answered correctly
        response = self.client.post(
            reverse("quiz_submit"),
            {f"question_{q1.id}": "A", f"question_{q2.id}": "B", f"question_{q3_ungraded.id}": "C"},
            follow=True,
        )
        result = self.client.session.get("last_quiz_result")

        self.assertEqual(result["total_questions"], 3)
        self.assertEqual(result["graded_questions"], 2)
        self.assertEqual(result["ungraded_questions"], 1)
        self.assertEqual(result["correct_count"], 2)
        # 2 correct out of 2 graded = 100.0% (NOT 2/3 = 66.7%)
        self.assertEqual(result["score_percentage"], 100.0)

    def test_zero_gradable_questions_division_by_zero_prevention(self):
        s = QuizSource.objects.create(pdf_name="quiz.pdf")
        q1 = self._create_question(s, "Q1", answer_key=None)
        q2 = self._create_question(s, "Q2", answer_key=None)

        self.client.post(reverse("quiz_take"), {"source_id": s.id, "time_limit": "600"})

        response = self.client.post(
            reverse("quiz_submit"),
            {f"question_{q1.id}": "A", f"question_{q2.id}": "B"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        result = self.client.session.get("last_quiz_result")

        self.assertEqual(result["graded_questions"], 0)
        self.assertEqual(result["ungraded_questions"], 2)
        self.assertIsNone(result["score_percentage"])
        self.assertContains(response, "N/A")
        self.assertContains(response, "No gradable questions")

    def test_invalid_option_submission_handled(self):
        s = QuizSource.objects.create(pdf_name="quiz.pdf")
        q1 = self._create_question(s, "Q1", "A")

        self.client.post(reverse("quiz_take"), {"source_id": s.id, "time_limit": "600"})

        # Submitting an option key 'Z' that doesn't exist
        self.client.post(reverse("quiz_submit"), {f"question_{q1.id}": "Z"})
        result = self.client.session.get("last_quiz_result")

        # Invalid option is stripped and treated as unattempted
        self.assertEqual(result["correct_count"], 0)
        self.assertEqual(result["unattempted_count"], 1)

    def test_tampered_question_id_ignored(self):
        s = QuizSource.objects.create(pdf_name="quiz.pdf")
        q1 = self._create_question(s, "Q1", "A")

        self.client.post(reverse("quiz_take"), {"source_id": s.id, "time_limit": "600"})

        # Submit answer for active question + extra bogus question ID
        self.client.post(
            reverse("quiz_submit"),
            {f"question_{q1.id}": "A", "question_99999": "A"},
        )
        result = self.client.session.get("last_quiz_result")

        self.assertEqual(result["total_questions"], 1)
        self.assertEqual(result["correct_count"], 1)

    def test_timed_out_submission_flagged(self):
        s = QuizSource.objects.create(pdf_name="quiz.pdf")
        q1 = self._create_question(s, "Q1", "A")

        # Start quiz
        self.client.post(reverse("quiz_take"), {"source_id": s.id, "time_limit": "300"})

        # Manually alter session to simulate submission beyond deadline + 10s grace
        session = self.client.session
        active = session["active_quiz"]
        past_time = timezone.now() - timedelta(seconds=350)
        past_deadline = past_time + timedelta(seconds=300)  # expired 50s ago (> 10s grace)
        active["start_time"] = past_time.isoformat()
        active["deadline"] = past_deadline.isoformat()
        session["active_quiz"] = active
        session.save()

        response = self.client.post(
            reverse("quiz_submit"),
            {f"question_{q1.id}": "A"},
            follow=True,
        )
        result = self.client.session.get("last_quiz_result")

        self.assertTrue(result["is_timed_out"])
        self.assertContains(response, "Time Expired")

    def test_submission_within_grace_period_not_timed_out(self):
        s = QuizSource.objects.create(pdf_name="quiz.pdf")
        q1 = self._create_question(s, "Q1", "A")

        self.client.post(reverse("quiz_take"), {"source_id": s.id, "time_limit": "300"})

        # Simulate submission 5 seconds past deadline (within 10s grace period)
        session = self.client.session
        active = session["active_quiz"]
        past_time = timezone.now() - timedelta(seconds=305)
        past_deadline = past_time + timedelta(seconds=300)  # expired 5s ago (<= 10s grace)
        active["start_time"] = past_time.isoformat()
        active["deadline"] = past_deadline.isoformat()
        session["active_quiz"] = active
        session.save()

        response = self.client.post(
            reverse("quiz_submit"),
            {f"question_{q1.id}": "A"},
            follow=True,
        )
        result = self.client.session.get("last_quiz_result")

        self.assertFalse(result["is_timed_out"])
        self.assertNotContains(response, "Time Expired")

    def test_untimed_quiz_submission(self):
        s = QuizSource.objects.create(pdf_name="quiz.pdf")
        q1 = self._create_question(s, "Q1", "A")

        # Untimed (time_limit = 0)
        self.client.post(reverse("quiz_take"), {"source_id": s.id, "time_limit": "0"})
        session = self.client.session
        self.assertIsNone(session["active_quiz"]["deadline"])

        response = self.client.post(
            reverse("quiz_submit"),
            {f"question_{q1.id}": "A"},
            follow=True,
        )
        result = self.client.session.get("last_quiz_result")
        self.assertFalse(result["is_timed_out"])
        self.assertEqual(result["correct_count"], 1)

    def test_resubmission_idempotency(self):
        s = QuizSource.objects.create(pdf_name="quiz.pdf")
        q1 = self._create_question(s, "Q1", "A")

        self.client.post(reverse("quiz_take"), {"source_id": s.id, "time_limit": "600"})
        # First submission
        self.client.post(reverse("quiz_submit"), {f"question_{q1.id}": "A"})
        self.assertNotIn("active_quiz", self.client.session)

        # Second submission (e.g. browser back/refresh)
        response = self.client.post(reverse("quiz_submit"), {f"question_{q1.id}": "A"})
        self.assertRedirects(response, reverse("quiz_result"))

    def test_quiz_result_view_redirects_if_no_result(self):
        response = self.client.get(reverse("quiz_result"))
        self.assertRedirects(response, reverse("quiz_setup"))

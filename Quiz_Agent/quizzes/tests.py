import os
from django.conf import settings
from django.test import SimpleTestCase, TestCase

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

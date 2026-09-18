from django.test import SimpleTestCase

from .utils import parse_questions


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
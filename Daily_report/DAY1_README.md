# Day 1 — Local-First Quiz Application Foundation

## Overview

This phase established the initial foundation of the Quiz Agent application.

The main objective was to move the project toward a **local-first quiz generation architecture**, where uploaded PDF files are processed locally and quiz questions are stored in the application's database.

The project previously contained an external AI dependency for processing uploaded PDF content. That dependency was removed during this phase.

The application now provides the foundation for:

* PDF upload
* Local PDF text extraction
* MySQL database integration
* Quiz source management
* Question management
* Multiple-choice option management
* Question difficulty
* Question explanations
* Django admin management
* Database migrations
* Future local question parsing
* Future quiz/exam functionality
* Future Quiz Agent functionality

The actual question extraction parser and quiz engine are intentionally deferred to later development phases.

---

# 1. Project Architecture

The intended architecture is local-first.

```text
PDF Upload
    ↓
Django Application
    ↓
Local PDF Text Extraction
    ↓
Local Question Parser
    ↓
Question Validation
    ↓
MySQL Database
    ↓
Quiz / Exam Engine
    ↓
Results & Analytics
    ↓
Quiz Agent
```

The external AI processing dependency has been removed from the current implementation.

The application does not send uploaded PDF text to an external AI service.

---

# 2. Current Project Flow

The current application flow is:

```text
User
  ↓
Upload PDF
  ↓
Django receives PDF
  ↓
PDF is saved as a QuizSource
  ↓
pdfplumber extracts selectable text
  ↓
Local question parser
  ↓
Parser currently pending
```

At the moment, the parser does not automatically create questions from the extracted text.

This is intentional.

The project first establishes a stable database and upload foundation before implementing question parsing.

---

# 3. External AI Dependency Removal

The previous implementation contained an external AI dependency for processing uploaded quiz content.

During this phase:

* The external AI dependency was removed.
* Uploaded PDF text is no longer sent to an external AI service.
* The project no longer depends on an external AI API key for PDF processing.
* The question extraction process is being redesigned around local processing.

This is important because the long-term project goal is to create a quiz application that can operate without requiring external AI API keys.

The planned approach is:

```text
PDF
 ↓
Local extraction
 ↓
Own parser
 ↓
Validation
 ↓
Database
```

A local/open-source language model may be considered later for advanced agent functionality, but it is not part of the current implementation.

---

# 4. PDF Upload

The Django application retains the PDF upload functionality.

The upload page allows the user to select a PDF file and submit it to the application.

The uploaded file is handled by Django and associated with a `QuizSource` record.

The source record stores information about the uploaded PDF.

The current source model includes:

* PDF name
* Uploaded PDF file
* Creation timestamp

The uploaded PDF is stored using Django's `FileField`.

The upload path is configured using:

```text
quiz_sources/
```

---

# 5. PDF Text Extraction

The project uses `pdfplumber` for local PDF text extraction.

The current process is:

```text
Uploaded PDF
     ↓
pdfplumber
     ↓
Extract selectable text
     ↓
Pass extracted text to local parser
```

This allows the application to process PDFs without sending their contents to an external AI service.

The current implementation focuses on selectable text-based PDFs.

The actual conversion of extracted text into structured multiple-choice questions is still pending.

---

# 6. Local Question Parser

A local question parser has been reserved in the application architecture.

The parser will eventually be responsible for identifying information such as:

```text
Question
Option A
Option B
Option C
Option D
Correct Answer
Explanation
Subject
Topic
Difficulty
```

For example, the intended structured representation is:

```text
Question:
What is the capital of India?

Options:
A. Mumbai
B. Bengaluru
C. New Delhi
D. Chennai

Correct Answer:
C

Explanation:
New Delhi is the capital of India.
```

The parser itself has not yet been implemented.

Currently, the application reports that the local question extraction parser is pending.

This prevents incomplete or unreliable parsing logic from being mixed into the initial database foundation.

---

# 7. Database Integration

The application is configured to use MySQL as the primary database.

Database configuration is managed through environment variables.

The project uses a `.env` file for local configuration.

The repository contains an `.env.example` file so that the required environment variables can be understood without committing actual credentials.

The actual `.env` file is ignored by Git.

This prevents database credentials and other local configuration values from being committed to the repository.

---

# 8. Database Models

The initial database structure was created to support structured quiz content.

The main models are:

```text
QuizSource
    ↓
Question
    ↓
QuestionOption
```

The relationships allow one uploaded PDF to contain many questions and each question to contain multiple answer options.

---

# 9. QuizSource Model

`QuizSource` represents an uploaded quiz/question source.

It stores the uploaded PDF and basic source information.

The model contains information such as:

* PDF name
* PDF file
* Creation timestamp

The PDF file is optional at the database-field level so that source records can be handled flexibly during application development.

The source-to-question relationship allows questions extracted from a PDF to be associated with their original source.

---

# 10. Question Model

The `Question` model represents an individual quiz question.

The current question structure supports:

* Subject
* Topic
* Difficulty
* Explanation
* Optional legacy answer text
* Associated quiz source
* Creation timestamp

The difficulty field supports three values:

```text
easy
medium
hard
```

This will later allow the application to generate exams based on difficulty.

For example:

```text
Easy
Medium
Hard
```

The explanation field is intended to store an explanation for the correct answer.

This will later be useful for:

* Reviewing incorrect answers
* Learning after an exam
* Generating explanations
* Identifying weak areas
* Quiz Agent responses

---

# 11. QuestionOption Model

The `QuestionOption` model represents the multiple-choice answers belonging to a question.

Each question can have options such as:

```text
A
B
C
D
```

Each option stores:

* Question relationship
* Option key
* Option text
* Whether the option is correct
* Creation timestamp
* Ordering information

The option key is restricted to:

```text
A
B
C
D
```

This provides a consistent structure for multiple-choice questions.

---

# 12. Question and Option Relationship

The relationship between questions and options is:

```text
Question
   │
   ├── Option A
   ├── Option B
   ├── Option C
   └── Option D
```

A question can therefore contain multiple `QuestionOption` records.

When a question is deleted, its associated options are also deleted through the configured cascade relationship.

Similarly, when a quiz source is deleted, the questions belonging to that source and their options are removed through the configured cascade relationships.

This keeps the database structure consistent.

---

# 13. Option Validation

The application includes validation to prevent invalid multiple-choice data.

The option key is restricted to the supported choices:

```text
A, B, C, D
```

A question should not contain more than one correct answer.

The Django model/admin validation is designed to reject situations where multiple options for the same question are marked as correct.

The database design intentionally avoids relying on a portable conditional unique constraint for the single-correct-answer rule because of MySQL compatibility considerations.

Therefore, future bulk question imports must also validate that exactly one correct option exists for each question.

---

# 14. Database Migrations

Django migrations were created for the database structure.

The initial migration creates the core quiz database tables.

A subsequent migration adds the additional question metadata and related fields.

The current migration structure includes:

```text
0001_initial.py
0002_question_difficulty_question_explanation_and_more.py
```

These migrations allow the database schema to be reproduced consistently in another development environment.

---

# 15. Django Admin

The Django admin interface was updated to make the quiz database easier to manage.

Question options can be managed through an inline interface associated with questions.

The admin configuration also supports question metadata such as:

* Subject
* Topic
* Difficulty
* Explanation
* Options

Filtering and ordering functionality were added to make question management easier as the database grows.

This will become useful during development because questions can be inspected and corrected directly through Django admin.

---

# 16. Environment Configuration

The project contains:

```text
.env
.env.example
```

The `.env` file contains local environment-specific configuration.

The `.env.example` file documents the expected configuration structure without containing real secrets.

The actual `.env` file must never be committed to Git.

The repository `.gitignore` is configured to prevent environment files and Python-generated cache files from being committed.

---

# 17. Important Repository Structure

The project currently follows this structure:

```text
Quiz_Agent/
│
├── .gitignore
├── Daily_report/
│   └── DAY1_README.md
│
└── Quiz_Agent/
    │
    ├── manage.py
    ├── .env
    ├── .env.example
    ├── requirements.txt
    │
    ├── quizzes/
    │   ├── admin.py
    │   ├── apps.py
    │   ├── forms.py
    │   ├── models.py
    │   ├── utils.py
    │   ├── views.py
    │   ├── urls.py
    │   │
    │   ├── migrations/
    │   │   ├── 0001_initial.py
    │   │   ├── 0002_question_difficulty_question_explanation_and_more.py
    │   │   └── __init__.py
    │   │
    │   └── templates/
    │       └── quizzes/
    │           └── upload.html
    │
    └── quiz_project/
        ├── settings.py
        ├── urls.py
        ├── asgi.py
        └── wsgi.py
```

`Daily_report/` is kept outside the Django application directory.

All future daily reports will be stored inside this directory.

---

# 18. Files Updated During This Phase

The major files involved in this phase include:

### `quizzes/models.py`

Defines:

* `QuizSource`
* `Question`
* `QuestionOption`

and their relationships and validation.

### `quizzes/views.py`

Handles the PDF upload flow and creates the `QuizSource` record with the uploaded PDF.

### `quizzes/utils.py`

Contains the PDF extraction and the placeholder for the future local question parser.

### `quizzes/admin.py`

Configures Django admin management for questions and options.

### `quizzes/forms.py`

Contains the PDF upload form.

### `quiz_project/settings.py`

Contains Django configuration including database and media-related settings.

### `.env.example`

Documents the required environment configuration.

### `requirements.txt`

Contains the Python packages required by the project.

### Django migrations

Record the database schema changes.

---

# 19. Testing Performed

The Django project was tested using the Django system check command.

Command:

```text
python Quiz_Agent/manage.py check
```

Result:

```text
System check identified no issues (0 silenced).
```

This confirmed that the Django project configuration and registered applications did not contain system-check errors.

---

# 20. PDF Upload Testing

The development server was also used to test the PDF upload page.

The upload page successfully displayed the local parser status.

The current expected behavior after uploading a PDF is that the application extracts available text and reports that the question extraction parser is still pending.

No questions are automatically saved yet because the parser has intentionally not been implemented.

This behavior is expected at this stage.

---

# 21. Git Workflow Used

The work was developed using a branch-based Git workflow.

The development flow was:

```text
main
  ↓
development branch
  ↓
implementation
  ↓
testing
  ↓
commit
  ↓
push
  ↓
Pull Request
  ↓
review
  ↓
merge
  ↓
main
```

The implementation was committed and pushed to GitHub.

A Pull Request was created from the development branch to `main`.

The changes were reviewed and the Pull Request was merged successfully.

After merging:

* Local `main` was synchronized with `origin/main`.
* The working tree was verified as clean.
* The old development branch was deleted locally.
* The old development branch was deleted from GitHub.

The current main branch is therefore the clean baseline for future development.

---

# 22. Security Considerations

The project follows several basic security practices from the beginning.

### Environment secrets

Real environment configuration is stored in `.env`.

The `.env` file is ignored by Git.

### External AI

Uploaded PDF text is not sent to an external AI service in the current architecture.

### Git repository

Generated Python cache files and environment files are excluded from version control.

These practices will be maintained as the project grows.

---

# 23. Current Limitations

The following functionality is **not implemented yet**:

* Automatic question extraction
* Question parsing
* Answer detection from PDF
* Automatic subject detection
* Automatic topic detection
* Automatic difficulty classification
* Automatic explanation extraction
* Bulk database insertion from PDF
* Quiz/exam engine
* Timer
* User authentication
* Exam results
* Performance analytics
* Weak-topic detection
* Adaptive quizzes
* Natural-language Quiz Agent
* Local LLM integration

These features will be implemented incrementally.

---

# 24. Current Status

At the end of this phase, the application has a stable foundation for building the actual quiz system.

Current status:

| Component                      | Status       |
| ------------------------------ | ------------ |
| Django project                 | Completed    |
| PDF upload page                | Completed    |
| Local PDF extraction           | Completed    |
| External AI dependency removal | Completed    |
| MySQL configuration            | Completed    |
| QuizSource model               | Completed    |
| Question model                 | Completed    |
| QuestionOption model           | Completed    |
| Difficulty field               | Completed    |
| Explanation field              | Completed    |
| Question-option validation     | Completed    |
| Django migrations              | Completed    |
| Django admin configuration     | Completed    |
| Basic Django testing           | Completed    |
| Local question parser          | Pending      |
| Automatic question storage     | Pending      |
| Quiz engine                    | Pending      |
| Exam timer                     | Pending      |
| Results/analytics              | Pending      |
| Quiz Agent                     | Pending      |
| Local LLM                      | Future phase |

---

# 25. What Was Learned

The main concepts covered during this phase were:

### Django Models

How Django models represent database tables and relationships.

### Foreign Keys

How questions can be associated with their source PDF and options can be associated with questions.

### Cascade Relationships

How related records can be removed when their parent records are deleted.

### Django Migrations

How database schema changes are tracked and applied.

### Django Admin

How Django admin can be customized for managing application data.

### FileField

How Django handles uploaded files.

### Environment Variables

How database credentials and other configuration values can be kept outside source code.

### PDF Processing

How `pdfplumber` can be used to extract selectable text from PDF documents.

### Git Branching

How development can be isolated using branches.

### Pull Requests

How changes can be reviewed before being merged into the main branch.

---

# 26. Final Result

The project now has a clean local-first foundation.

The current architecture is:

```text
                    ┌─────────────────┐
                    │   User uploads  │
                    │       PDF       │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Django Upload   │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ QuizSource      │
                    │ Database Record │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │  pdfplumber     │
                    │ Local Extraction│
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Local Question  │
                    │     Parser      │
                    │    [PENDING]    │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │     MySQL       │
                    │                 │
                    │ Question        │
                    │ QuestionOption  │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Future Quiz /   │
                    │ Exam Engine     │
                    └─────────────────┘
```

The most important outcome of this phase is that the project is now ready for the next major development step: **building the local question parser and converting extracted PDF text into structured quiz questions.**

---

# 27. Next Phase

The next development phase will focus on the **local question parser**.

The planned flow is:

```text
PDF
 ↓
Extract text
 ↓
Identify questions
 ↓
Identify options A-D
 ↓
Identify correct answer
 ↓
Identify explanation
 ↓
Validate question
 ↓
Save to MySQL
```

The parser should be designed carefully so that it can handle the expected PDF question format reliably before moving on to the quiz/exam engine.

---

# Conclusion

This initial phase established the foundation required for the Quiz Agent project.

The project has moved from an external-AI-dependent PDF workflow toward a local-first architecture with:

* Django
* Local PDF extraction
* MySQL
* Structured quiz models
* Question options
* Validation
* Django admin
* Environment-based configuration
* Git-based development workflow

The foundation is now merged into `main` and can be used as the starting point for future daily development.

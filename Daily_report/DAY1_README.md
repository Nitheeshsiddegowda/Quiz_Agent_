# Day 1 — PDF Upload Agent

## What we built today (in simple words)

We built the **very first piece** of your Quiz app: a page where you upload a PDF,
and an AI "agent" reads it, figures out every question and its answer — no
matter how the PDF is formatted — and saves them into your MySQL database.

Here's the journey of one PDF, step by step:

1. You open the upload page and pick a PDF file.
2. Django saves the file to a temporary spot and reads all the text out of it
   (using a library called `pdfplumber`).
3. That raw text is sent to **Google Gemini** with an instruction like:
   *"Find every question and answer in this text, in whatever format it's
   written, and give it back to me as clean JSON."*
4. Gemini replies with a clean list of `{question, answer}` pairs.
5. Django loops through that list and saves each pair into the database,
   linked to the PDF it came from.
6. The page refreshes and shows you a success message + a table of the
   most recently saved questions.

This is "AI-powered" parsing — meaning it doesn't care if your PDF says
"Q1) ... Ans:" or "1. ... Correct answer:" or has multiple-choice options —
Gemini reads it the way a human would and extracts the meaning, not just
the pattern.

## What was created

```
Quiz_Agent/
├── manage.py                          # Django's command-line tool
├── requirements.txt                   # Python packages this project needs
├── .env.example                       # Template for your secret keys/config
├── quiz_project/                      # Project-level settings
│   ├── settings.py                    # Database, installed apps, Gemini key
│   ├── urls.py
│   ├── wsgi.py / asgi.py
├── quizzes/                           # Our app (this is where features live)
│   ├── models.py                      # Database tables: QuizSource, Question
│   ├── admin.py                       # Lets you view saved data in /admin
│   ├── forms.py                       # The PDF upload form
│   ├── utils.py                       # The "agent" — PDF reading + Gemini call
│   ├── views.py                       # Glues everything together
│   ├── urls.py                        # App routes
│   └── templates/quizzes/upload.html  # The web page (HTML + CSS)
```

Two database tables were created:
- **QuizSource** — one row per PDF you upload (its name, upload time).
- **Question** — one row per question/answer pair, linked to the PDF it came from.

## One-time setup (do this once)

### 1. Install Python packages
Open a terminal inside the `Quiz_Agent` folder and run:
```bash
pip install -r requirements.txt
```

### 2. Create the MySQL database
Open MySQL (via terminal or a tool like MySQL Workbench) and run:
```sql
CREATE DATABASE quiz_agent_db CHARACTER SET utf8mb4;
```

### 3. Set up your secret keys
Copy `.env.example` to a new file named `.env` in the same folder, and fill in:
- `GEMINI_API_KEY` — your Gemini API key
- `DB_USER`, `DB_PASSWORD` — your MySQL login details
- `SECRET_KEY` — any random string (this is Django's internal secret, not your Gemini key)

### 4. Create the database tables
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. (Optional) Create an admin login
This lets you view saved questions at `/admin` in a nice table:
```bash
python manage.py createsuperuser
```

## How to run it (every time you work on this)

```bash
cd Quiz_Agent
python manage.py runserver
```

Then open your browser to: **http://127.0.0.1:8000/**

## How to use it

1. Click "Choose File" and pick a PDF that has questions and answers in it.
2. Click "Upload & Extract".
3. Wait a few seconds — the AI is reading and parsing your PDF.
4. You'll see a green success message with how many questions were saved.
5. Scroll down to see them in the table.
6. (Optional) Go to `http://127.0.0.1:8000/admin/` and log in with the
   superuser account you created, to browse/edit/delete questions directly.

## Notes / things to know

- If a PDF is a **scanned image** (not real selectable text), this version
  can't read it yet — we can add OCR support in a future day if you need it.
- Every PDF you upload is kept as its own "source" — so later we can add a
  feature to pick which PDF's questions to quiz yourself on.
- Your `.env` file has your real password/API key in it — never share it or
  commit it to GitHub. `.env.example` is the safe, shareable template.

## Coming up next

Tell me the Day 2 feature whenever you're ready, and we'll build it on top
of exactly this same project.

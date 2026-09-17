# Day 1 — Local-first PDF Upload Foundation

The project retains its Django PDF-upload page and PDF text extraction. The
previous external AI dependency has been removed; no uploaded text is sent to
an external AI service.

## Current flow

1. Upload a PDF.
2. Django saves it temporarily and extracts selectable text with `pdfplumber`.
3. If text is available, the application reports that the local question
   extraction parser is pending.

The local parser, validation, persistence of extracted questions, quiz engine,
and agent are intentionally deferred to later phases.

## Setup

Install packages from the `Quiz_Agent` folder:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set only your Django and MySQL values.
Never commit `.env`; it is ignored by Git.

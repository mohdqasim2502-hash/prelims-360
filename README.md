# Prelims 360° — UPSC CSE 2027

A responsive Flask + SQLite starter application for a UPSC Prelims preparation workspace.

## Included
- Dashboard and navigation
- Searchable PYQ library (database-backed)
- Trend-analysis shell that avoids unsupported claims when data is incomplete
- Static keyword encyclopedia
- Daily current-affairs editorial structure
- Five-question interactive quiz demo
- CSAT module landing page
- User registration/login, bookmarks, notes, attempts and progress tracking
- SQLite persistence

## Important content-integrity note
This package intentionally does **not** claim to contain all UPSC CSE Prelims papers from 2016–2025 or a complete daily current-affairs feed. It contains one illustrative PYQ and one illustrative keyword/news record. The sample PYQ is not marked officially verified. Populate the database only from original UPSC question papers and UPSC's official final answer keys. Keep source URL, paper/year, answer-key reference and verification status for each imported question. Do not label coaching answers as official.

## Run locally
1. Install Python 3.10+.
2. Create and activate a virtual environment.
3. Run `pip install -r requirements.txt`.
4. Run `python app.py`.
5. Open `http://127.0.0.1:5000`.

## Before deployment
- Set a strong random `SECRET_KEY` environment variable.
- Use HTTPS and a production WSGI server (e.g. Gunicorn).
- Configure secure cookies, CSRF protection, rate limiting, backups and database migrations.
- Replace SQLite with PostgreSQL for multi-user production workloads.
- Add an admin-only content management interface and moderation workflow.
- Add a scheduled ingestion pipeline for current affairs; every item must retain publication date and primary-source URL.
- Add source documents and an audit log for every PYQ answer-key verification.
- Add automated tests for answer correctness, data import and authentication.

## Data model
`pyqs`: original question, options, answer, explanation, year, subject, topic, difficulty, source and verification flag.
`current_affairs`: publication date, title, category, summary, static linkage, source and keywords.
`keywords`: term, subject, definition, provisions and linked PYQ.
`attempts`, `bookmarks`, `notes`, `users`: personal study records.

## Accuracy policy
For a question to be marked verified, store the official UPSC final answer key reference and verify the question-paper set/series mapping. Preserve exact question wording and options. If the official key is unavailable or ambiguous, label the record "unverified" and explain the uncertainty.

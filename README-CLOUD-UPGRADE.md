# Prelims 360° — Cloud upgrade package

This package upgrades the existing Flask application from local SQLite storage to PostgreSQL and adds account-backed cloud storage for notes, bookmarks, quiz attempts, planner tasks, revision items and mistake tracking.

## Files to replace in the existing GitHub repository

- `app.py`
- `requirements.txt`
- `render.yaml`
- `templates/index.html`
- Add `static/cloud-auth.js`

Keep the existing `static/app.js` and `static/style.css` from the current repository.

## Database provider

Use Neon PostgreSQL (persistent free tier subject to provider limits) and put its pooled or direct connection string in Render as `DATABASE_URL`. The value must start with `postgresql://` or `postgres://`. Never put database credentials in GitHub.

## Render environment

`render.yaml` generates `SECRET_KEY` automatically. Add `DATABASE_URL` manually in Render → your service → Environment. The app will fail safely rather than silently fall back to temporary SQLite storage if it is missing.

## Deployment

After the files are committed to the connected GitHub `main` branch, Render auto-deploys. Test:
- `/health` returns `{"status":"ok","database":"connected"}`
- Register a username with a password of at least 10 characters.
- Sign out, sign back in, and test from a second device/browser.
- Notes/bookmarks/attempts/planner/revision/mistakes are stored per account in PostgreSQL.

## Important migration note

This package creates a new PostgreSQL database schema. Existing accounts/data in the old Render SQLite file are not automatically copied. Do not delete the old service or database until any important old data has been exported. The existing demo PYQ/keyword/news seed records are not automatically migrated; re-import verified source data separately.

## Security and limits

- Passwords are stored as Werkzeug password hashes, not plaintext.
- Session cookies are HttpOnly, Secure and SameSite=Lax.
- Personal-data endpoints require authentication and filter by the current user.
- Use HTTPS (Render provides it).
- Do not share `DATABASE_URL`, Render API keys, GitHub tokens or passwords in chat.
- Free web services can sleep; a free database plan can have provider-specific pause/expiry limits. Check the database provider's current terms before using it for irreplaceable study records.

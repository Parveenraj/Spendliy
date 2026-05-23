# Spec: Registration

## Overview
This step wires up the registration form so new users can actually create an
account. The `GET /register` route and `register.html` template already exist
from the project scaffold; this step adds the `POST /register` handler that
validates the submitted data, creates the user record (with a hashed password),
starts a session, and redirects the user. It also adds the two database helper
functions (`get_user_by_email` and `create_user`) that the route will delegate
to.

## Depends on
- Step 1 — Database setup (`users` table, `get_db()`, `werkzeug` available)

## Routes
- `POST /register` — validate form data, create user, start session, redirect — public

The existing `GET /register` route is **not** changed except to pass any
validation error back to the template via a local `error` variable.

## Database changes
No new tables or columns.

Two new helper functions must be added to `database/db.py`:

| Function | Signature | Description |
|---|---|---|
| `get_user_by_email` | `(email: str) -> sqlite3.Row \| None` | Return the full user row for the given email, or `None` if not found. |
| `create_user` | `(name: str, email: str, password: str) -> int` | Hash the password, insert a new row into `users`, and return the new `user_id`. |

## Templates
- **Modify:** `templates/register.html`
  - Fix the hardcoded `action="/register"` → `action="{{ url_for('register') }}"` (CLAUDE.md forbids hardcoded URLs)
  - The existing `{% if error %}` block is already in place — no further changes needed

## Files to change
- `app.py`
  - Add `request`, `redirect`, `session`, `url_for`, `flash` to the Flask import
  - Set `app.secret_key` (use `os.urandom(24)` for development; add `import os` if not present)
  - Convert `GET /register` to accept `GET` and `POST` methods (`methods=["GET", "POST"]`)
  - Implement the `POST` branch inside the `register()` view function
- `database/db.py`
  - Add `get_user_by_email(email)` function
  - Add `create_user(name, email, password)` function
- `templates/register.html`
  - Replace hardcoded `action="/register"` with `action="{{ url_for('register') }}"`

## Files to create
None.

## New dependencies
No new pip packages. `werkzeug.security` (`generate_password_hash`) is already
imported in `database/db.py` and available via the existing `requirements.txt`.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only — never f-strings in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash` inside
  `create_user()`; plain-text passwords must never be stored or logged
- All DB logic lives in `database/db.py` — the route only calls helpers
- Use `url_for()` for every internal link and form `action` — never hardcode URLs
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- `abort(400)` for malformed requests; re-render `register.html` with an `error`
  string for user-facing validation failures (duplicate email, short password, etc.)
- After a successful registration, store `session["user_id"] = user_id` and
  redirect to `url_for("landing")` — this redirect target will be updated to
  the dashboard in a later step

### POST /register logic (step-by-step)
1. Read `name`, `email`, `password` from `request.form`; strip whitespace
2. Validate:
   - All three fields must be non-empty → error: `"All fields are required."`
   - `password` must be ≥ 8 characters → error: `"Password must be at least 8 characters."`
3. Call `get_user_by_email(email)`; if a row is returned → error: `"An account with that email already exists."`
4. Call `create_user(name, email, password)` → returns `user_id`
5. Set `session["user_id"] = user_id`
6. Redirect to `url_for("landing")`

On any validation failure, re-render `register.html` with the `error` string
**and** repopulate `name` and `email` so the user does not have to retype them:
```python
return render_template("register.html", error=error, name=name, email=email)
```
Update `register.html` to carry `value="{{ name or '' }}"` / `value="{{ email or '' }}"` on those inputs.

## Definition of done
- [ ] Submitting the form with all valid fields creates a new row in `users` (verify with `sqlite3 spendly.db "SELECT * FROM users;"`)
- [ ] The new user's password is stored as a hash, not plain text
- [ ] After successful registration the browser is redirected to the landing page (`/`)
- [ ] Submitting a duplicate email re-renders the form with the error message "An account with that email already exists."
- [ ] Submitting with a password shorter than 8 characters re-renders the form with the error message "Password must be at least 8 characters."
- [ ] Submitting with any field blank re-renders the form with the error message "All fields are required."
- [ ] Previously filled `name` and `email` values are preserved in the form on validation failure (user does not lose their input)
- [ ] The form `action` attribute uses `url_for('register')`, not a hardcoded string
- [ ] No SQL queries appear in `app.py` — all DB access is through `database/db.py` helpers
- [ ] `pytest` passes with no new failures

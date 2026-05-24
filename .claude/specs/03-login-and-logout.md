# Spec: Login and Logout

## Overview
This step wires up the login form and logout route so registered users can
authenticate and end their session. The `GET /login` route and `login.html`
template already exist as scaffolding; this step adds the `POST /login` handler
that validates credentials against the stored password hash, starts a session,
and redirects the user. It also implements `GET /logout` (currently a string
stub) to clear the session and redirect to the landing page. Finally, `base.html`
is updated so the navbar reflects the user's logged-in state.

## Depends on
- Step 1 — Database setup (`users` table, `get_db()`)
- Step 2 — Registration (`get_user_by_email()`, `session["user_id"]` pattern,
  `app.secret_key`)

## Routes
- `POST /login` — validate credentials, start session, redirect — public
- `GET /logout` — clear session, redirect to landing — public

The existing `GET /login` route is **not** changed except to accept both methods.

## Database changes
No new tables or columns.

One new helper function must be added to `database/db.py`:

| Function | Signature | Description |
|---|---|---|
| `verify_login` | `(email: str, password: str) -> sqlite3.Row \| None` | Fetch the user by email; if found and the password matches the stored hash, return the full user row. Otherwise return `None`. |

`check_password_hash` from `werkzeug.security` must be added to the import line
in `database/db.py`.

## Templates
- **Modify:** `templates/login.html`
  - Fix hardcoded `action="/login"` → `action="{{ url_for('login') }}"`
  - Add `value="{{ email or '' }}"` to the email input (sticky value on error)
  - Password input: **no value attribute** — never repopulate passwords

- **Modify:** `templates/base.html`
  - Update the `nav-links` block to show different links based on login state:
    - **Logged out** (no `session.user_id`): existing "Sign in" + "Get started" links
    - **Logged in** (`session.user_id` set): show user name from `session.user_name`
      and a "Sign out" link pointing to `url_for('logout')`

## Files to change
- `app.py`
  - Add `verify_login` to the db import line
  - Convert `GET /login` to `methods=["GET", "POST"]` and implement the POST branch
  - Rewrite `GET /logout` stub to clear session and redirect
  - At login **and** registration success: also store `session["user_name"]` so
    `base.html` can display the user's name without an extra DB query
- `database/db.py`
  - Add `check_password_hash` to the `werkzeug.security` import
  - Add `verify_login(email, password)` function
- `templates/login.html`
  - Fix hardcoded action URL
  - Add sticky email value
- `templates/base.html`
  - Conditional nav links based on `session.user_id`

## Files to create
None.

## New dependencies
No new pip packages. `werkzeug.security.check_password_hash` is available via
the existing `werkzeug==3.1.6` in `requirements.txt`.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only — never f-strings in SQL
- Password verification done with `check_password_hash` inside `verify_login()`
  in `database/db.py` — never in the route
- All DB logic lives in `database/db.py` — the route only calls helpers
- Use `url_for()` for every internal link and form `action` — never hardcode URLs
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- On invalid credentials re-render `login.html` with a deliberately vague error:
  `"Invalid email or password."` — never reveal which field was wrong
- After successful login: store `session["user_id"]` and `session["user_name"]`,
  redirect to `url_for("landing")`
- Logout must call `session.clear()` (not just `session.pop`) to wipe all keys,
  then redirect to `url_for("landing")`
- Also store `session["user_name"]` in the existing `register()` route's success
  path so newly registered users see their name in the nav immediately

### POST /login logic (step-by-step)
1. Read `email`, `password` from `request.form`; strip whitespace
2. Validate both fields non-empty → error: `"All fields are required."`
3. Call `verify_login(email, password)`:
   - If `None` → error: `"Invalid email or password."`
4. No error → set `session["user_id"] = user["id"]` and
   `session["user_name"] = user["name"]`
5. `return redirect(url_for("landing"))`
6. Error path: `return render_template("login.html", error=error, email=email)`

### GET /logout logic
1. `session.clear()`
2. `return redirect(url_for("landing"))`

### verify_login helper logic
1. Call `get_user_by_email(email)` — reuse the existing helper
2. If no user → return `None`
3. If `check_password_hash(user["password_hash"], password)` is `True` → return
   the user row
4. Otherwise → return `None`

## Definition of done
- [ ] `GET /login` still loads the login form (200)
- [ ] Submitting the login form with empty fields re-renders with "All fields are required."
- [ ] Submitting with a valid email but wrong password re-renders with "Invalid email or password."
- [ ] Submitting with a non-existent email re-renders with "Invalid email or password." (same message — no account enumeration)
- [ ] Submitting valid credentials (`demo@spendly.com` / `demo123`) redirects to `/`
- [ ] After login, `session["user_id"]` and `session["user_name"]` are set
- [ ] After login, the navbar shows the user's name and a "Sign out" link instead of "Sign in" / "Get started"
- [ ] Visiting `GET /logout` clears the session and redirects to `/`
- [ ] After logout, the navbar reverts to showing "Sign in" and "Get started"
- [ ] The login form `action` uses `url_for('login')`, not a hardcoded string
- [ ] Email value is preserved in the form on validation/credential failure
- [ ] Newly registered users (Step 2 flow) also see their name in the nav after registration
- [ ] No SQL queries appear in `app.py`
- [ ] `pytest` passes with no new failures

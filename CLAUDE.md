# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate virtual environment (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the development server (port 5001)
python app.py

# Run tests
pytest

# Run a single test file
pytest tests/test_auth.py
```

## Architecture

This is a Flask web app called **Spendly** — a personal expense tracker. It uses SQLite via a custom `database/db.py` module and Jinja2 templates.

**app.py** is the single entry point: it defines all routes and creates the Flask app. There is no blueprint structure yet.

**database/db.py** (stub — to be implemented) must export three functions:
- `get_db()` — returns a SQLite connection with `row_factory` set and foreign keys enabled
- `init_db()` — creates all tables using `CREATE TABLE IF NOT EXISTS`
- `seed_db()` — inserts sample data for development

**Templates** all extend `templates/base.html`, which includes the navbar, footer, and links to `static/css/style.css` and `static/js/main.js`. Page-specific JS goes in a `{% block scripts %}` block.

**Planned route progression** (stubs already exist in app.py):
- Steps 1–2: database setup and auth routes (`/register`, `/login`, `/logout` with POST handling)
- Step 3: session management
- Step 4: `/profile`
- Steps 7–9: `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`

Login and register forms POST to `/login` and `/register` respectively and expect an `error` variable in the template context when validation fails.

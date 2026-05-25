# Spec: Date Filter for Profile Page

## Overview
This feature adds a date range filter to the profile page so users can narrow the
transactions table — and the summary stats — down to a specific time window. The
filter is submitted as GET query-string parameters (`date_from` and `date_to`),
keeping the URL bookmarkable and avoiding any session state. When no filter is
active the page behaves exactly as it does today (all-time data). The route already
exists; only the query helpers, the route handler, and the template need updating.

## Depends on
- Step 04 — Profile Page (template and route in place)
- Step 05 — Backend Routes for Profile Page (query helpers in `database/queries.py`)

## Routes
No new routes.

The existing `GET /profile` route is updated to read optional `date_from` and
`date_to` query-string parameters and pass them through to the query helpers.

## Database changes
No database changes.

The `expenses.date` column already stores dates as `YYYY-MM-DD` strings, which
SQLite compares lexicographically — date range filtering works without schema
changes.

## Templates
- **Modify:** `templates/profile.html`
  - Add a date-filter form above the Transaction History section
  - Two `<input type="date">` fields: **From** (`date_from`) and **To** (`date_to`)
  - A **Filter** submit button and a **Clear** link that returns to `/profile`
  - Show an active-filter banner ("Showing results from … to …") when a filter is in effect
  - The Transaction History table and Summary Stats section must reflect the
    filtered data; the Category Breakdown section is also filtered
  - Preserve pre-filled values in the date inputs when the form is re-rendered

## Files to change
- `app.py` — extract `date_from` / `date_to` from `request.args`; pass them to query helpers; forward them to the template for pre-filling
- `database/queries.py` — update `get_recent_transactions`, `get_summary_stats`, and `get_category_breakdown` to accept optional `date_from` / `date_to` keyword arguments and apply `WHERE expenses.date BETWEEN ? AND ?` when provided
- `templates/profile.html` — add filter form and active-filter banner (see Templates above)

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only — never interpolate dates into SQL strings
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- The filter form must use `method="get"` and `action="{{ url_for('profile') }}"` — no POST, no JavaScript required
- Query helpers must keep their existing signatures backward-compatible (all new parameters are keyword-only with `None` defaults); callers that omit them get the same results as today
- When only one of `date_from` / `date_to` is supplied, treat the missing bound as open-ended (no lower or upper limit respectively)
- Date validation: if either value is non-empty but not a valid `YYYY-MM-DD` string, flash an error and ignore the filter (do not crash)
- `date_from` and `date_to` must be passed to the template context so the form inputs are pre-filled after submission
- The Clear link must be a plain `<a href="{{ url_for('profile') }}">Clear</a>` — not a button with JS

## Definition of done
- [ ] Visiting `/profile` with no query parameters shows the same data as before (no regression)
- [ ] Visiting `/profile?date_from=2025-01-01&date_to=2025-12-31` filters transactions, stats, and category breakdown to that year
- [ ] The **From** and **To** inputs are pre-filled with the submitted values after filtering
- [ ] The active-filter banner appears when at least one date bound is active and is absent otherwise
- [ ] Clicking **Clear** removes the filter and returns to the full-data view
- [ ] Supplying only `date_from` shows all expenses on or after that date (open upper bound)
- [ ] Supplying only `date_to` shows all expenses on or before that date (open lower bound)
- [ ] An invalid date value (e.g. `date_from=not-a-date`) shows a flash error and renders the unfiltered page
- [ ] Summary stats (total spent, transaction count, top category) update to reflect the filtered date range
- [ ] Category breakdown percentages still sum to 100 when a filter is active

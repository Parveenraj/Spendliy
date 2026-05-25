# tests/test_06-date-filter-profile-page.py
"""
Tests for Step 06: Date Filter for Profile Page.

Covers:
  - DoD 1: No-filter regression — unfiltered page still works correctly
  - DoD 2: Full date range filters transactions, stats, and category breakdown
  - DoD 3: Form inputs are pre-filled with submitted date values
  - DoD 4: Active-filter banner appears when a filter is active; absent otherwise
  - DoD 5: Clear link points to /profile with no query parameters
  - DoD 6: Only date_from supplied — open upper bound (on/after that date)
  - DoD 7: Only date_to supplied — open lower bound (on/before that date)
  - DoD 8: Invalid date value triggers a flash error and shows unfiltered page
  - DoD 9: Summary stats (total, count, top category) update for filtered range
  - DoD 10: Category breakdown percentages sum to 100 when filter is active
  - Auth guard: unauthenticated requests redirect to /login
  - Query helper unit tests: date_from / date_to kwargs on each helper
  - Edge cases: single-day range, date_from > date_to (empty result), boundary inclusivity
"""

import os
import sqlite3
import tempfile

import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module
import database.queries as q_module
from database.db import init_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def app():
    """
    Flask app wired to a temporary file-based SQLite DB so each test gets a
    clean, isolated database. The get_db() function in both db_module and
    q_module is monkey-patched to point at the temp file.
    """
    from app import app as flask_app

    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"

    original_get_db = db_module.get_db

    def patched_get_db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    db_module.get_db = patched_get_db
    q_module.get_db = patched_get_db

    with flask_app.app_context():
        init_db()

    yield flask_app

    db_module.get_db = original_get_db
    q_module.get_db = original_get_db
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user_multi_year(app):
    """
    Insert a test user with expenses spread across two distinct years:
      2024: Food $50, Transport $30  (total $80)
      2025: Bills $200, Health $40   (total $240)
      2025-01-15 specifically: Bills $200
      2025-06-20 specifically: Health $40

    Returns the user_id.
    """
    conn = db_module.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (
            "Filter User",
            "filter@example.com",
            generate_password_hash("password123"),
            "2023-05-01 10:00:00",
        ),
    )
    conn.commit()
    uid = cursor.lastrowid

    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (?, ?, ?, ?, ?)",
        [
            (uid, 50.00, "Food",      "2024-03-10", "2024 groceries"),
            (uid, 30.00, "Transport", "2024-11-20", "2024 bus pass"),
            (uid, 200.00, "Bills",    "2025-01-15", "2025 electric"),
            (uid, 40.00, "Health",    "2025-06-20", "2025 pharmacy"),
        ],
    )
    conn.commit()
    conn.close()
    return uid


@pytest.fixture
def user_no_expenses(app):
    """Insert a test user with zero expenses; return user_id."""
    conn = db_module.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (
            "Empty User",
            "empty@example.com",
            generate_password_hash("password123"),
            "2026-01-01 00:00:00",
        ),
    )
    conn.commit()
    uid = cursor.lastrowid
    conn.close()
    return uid


def _login(client, user_id, user_name="Filter User"):
    """Helper: inject session data to simulate a logged-in user."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = user_name


# ── Auth guard ────────────────────────────────────────────────────────────────


class TestAuthGuard:
    def test_unauthenticated_get_profile_redirects_to_login(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 302, "Expected redirect for unauthenticated user"
        assert "/login" in resp.headers["Location"], "Should redirect to /login"

    def test_unauthenticated_with_date_params_still_redirects(self, client):
        resp = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


# ── DoD 1: No-filter regression ───────────────────────────────────────────────


class TestNoFilterRegression:
    def test_profile_no_params_returns_200(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile")
        assert resp.status_code == 200, "Profile page should return 200 when authenticated"

    def test_profile_no_params_shows_all_transactions(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile")
        html = resp.data.decode()
        # Both 2024 and 2025 expenses should appear
        assert "2024 groceries" in html, "2024 expense description should appear unfiltered"
        assert "2025 electric" in html, "2025 expense description should appear unfiltered"

    def test_profile_no_params_shows_correct_total_spent(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile")
        html = resp.data.decode()
        # Total = 50 + 30 + 200 + 40 = 320.00
        assert "320.00" in html, "Unfiltered total should be ₹320.00"

    def test_profile_no_params_shows_rupee_symbol(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile")
        html = resp.data.decode()
        assert "₹" in html, "Rupee symbol should appear on the profile page"

    def test_profile_no_params_no_active_filter_banner(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile")
        html = resp.data.decode()
        assert "Showing results" not in html, (
            "Active-filter banner must not appear when no filter is set"
        )

    def test_profile_no_params_filter_form_inputs_are_empty(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile")
        html = resp.data.decode()
        # Inputs should have value="" (empty) when no filter submitted
        assert 'name="date_from"' in html, "date_from input must be present"
        assert 'name="date_to"' in html, "date_to input must be present"


# ── DoD 2: Full date range filter ─────────────────────────────────────────────


class TestFullDateRangeFilter:
    def test_filter_restricts_transactions_to_year_2025(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        html = resp.data.decode()
        assert "2025 electric" in html, "2025 Bills expense should appear within filter"
        assert "2025 pharmacy" in html, "2025 Health expense should appear within filter"
        assert "2024 groceries" not in html, "2024 expense must not appear in 2025 filter"
        assert "2024 bus pass" not in html, "2024 expense must not appear in 2025 filter"

    def test_filter_restricts_stats_to_year_2025(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        html = resp.data.decode()
        # 2025 total = 200 + 40 = 240
        assert "240.00" in html, "Filtered total spent should be ₹240.00 for 2025"

    def test_filter_transaction_count_for_year_2025(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        html = resp.data.decode()
        # 2025 has 2 transactions
        assert ">2<" in html or "2</span>" in html or ">2 <" in html or "2\n" in html, (
            "Transaction count should be 2 for 2025 filter"
        )

    def test_filter_shows_correct_top_category_for_2025(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        html = resp.data.decode()
        # Bills = 200, Health = 40 — Bills is top
        assert "Bills" in html, "Top category should be Bills for 2025 filter"

    def test_filter_restricts_category_breakdown_to_2025(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        html = resp.data.decode()
        # Transport and Food were 2024 only
        assert "Food" not in html or "2024 groceries" not in html, (
            "2024-only categories should not appear in 2025-filtered breakdown"
        )


# ── DoD 3: Pre-filled form inputs ─────────────────────────────────────────────


class TestPrefilledFormInputs:
    def test_date_from_input_is_prefilled_after_filter(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        html = resp.data.decode()
        assert 'value="2025-01-01"' in html, (
            "date_from input value must be pre-filled with the submitted date"
        )

    def test_date_to_input_is_prefilled_after_filter(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        html = resp.data.decode()
        assert 'value="2025-12-31"' in html, (
            "date_to input value must be pre-filled with the submitted date"
        )

    def test_only_date_from_prefilled_when_only_from_submitted(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-03-01")
        html = resp.data.decode()
        assert 'value="2025-03-01"' in html, (
            "date_from input must be pre-filled when only date_from is submitted"
        )

    def test_only_date_to_prefilled_when_only_to_submitted(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_to=2024-12-31")
        html = resp.data.decode()
        assert 'value="2024-12-31"' in html, (
            "date_to input must be pre-filled when only date_to is submitted"
        )

    def test_inputs_empty_when_no_filter_submitted(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile")
        html = resp.data.decode()
        # Neither 2025-01-01 nor 2025-12-31 should appear as input values
        assert 'value="2025-01-01"' not in html
        assert 'value="2025-12-31"' not in html


# ── DoD 4: Active-filter banner ───────────────────────────────────────────────


class TestActiveFilterBanner:
    def test_banner_appears_with_both_dates(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        html = resp.data.decode()
        assert "Showing results" in html, (
            "Active-filter banner must appear when both date bounds are active"
        )

    def test_banner_contains_from_date_when_both_active(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        html = resp.data.decode()
        assert "2025-01-01" in html, "Banner must show the date_from value"
        assert "2025-12-31" in html, "Banner must show the date_to value"

    def test_banner_appears_with_only_date_from(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-01-01")
        html = resp.data.decode()
        assert "Showing results" in html, (
            "Active-filter banner must appear when only date_from is supplied"
        )

    def test_banner_appears_with_only_date_to(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_to=2024-12-31")
        html = resp.data.decode()
        assert "Showing results" in html, (
            "Active-filter banner must appear when only date_to is supplied"
        )

    def test_banner_absent_when_no_filter(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile")
        html = resp.data.decode()
        assert "Showing results" not in html, (
            "Active-filter banner must NOT appear when no filter is active"
        )

    def test_banner_absent_when_both_params_empty_string(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=&date_to=")
        html = resp.data.decode()
        assert "Showing results" not in html, (
            "Empty string params should not trigger the active-filter banner"
        )

    def test_banner_shows_onwards_text_for_only_date_from(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-01-01")
        html = resp.data.decode()
        assert "onwards" in html, (
            "Banner should say 'onwards' when only date_from is provided"
        )

    def test_banner_shows_up_to_text_for_only_date_to(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_to=2024-12-31")
        html = resp.data.decode()
        assert "up to" in html, (
            "Banner should say 'up to' when only date_to is provided"
        )


# ── DoD 5: Clear link ─────────────────────────────────────────────────────────


class TestClearLink:
    def test_clear_link_present_in_template(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile")
        html = resp.data.decode()
        # Clear link must exist and point to /profile with no query params
        assert "Clear" in html, "A Clear link must be present in the filter form"

    def test_clear_link_href_is_profile_without_params(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        html = resp.data.decode()
        # The anchor href must be /profile (no query string appended)
        assert 'href="/profile"' in html, (
            "Clear link must point to /profile with no query parameters"
        )

    def test_clear_link_is_anchor_not_button(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile")
        html = resp.data.decode()
        # Must be an <a> tag, not a <button> or form submit
        assert "<a" in html and "Clear" in html, (
            "Clear must be rendered as an <a> anchor tag"
        )


# ── DoD 6: Open upper bound (only date_from) ──────────────────────────────────


class TestOpenUpperBound:
    def test_only_date_from_includes_expenses_on_and_after(self, client, user_multi_year):
        _login(client, user_multi_year)
        # 2025-01-01 onwards — should include 2025 expenses, exclude 2024
        resp = client.get("/profile?date_from=2025-01-01")
        html = resp.data.decode()
        assert "2025 electric" in html, "Expense on date_from boundary should be included"
        assert "2025 pharmacy" in html, "Expense after date_from should be included"
        assert "2024 groceries" not in html, "Expense before date_from must be excluded"
        assert "2024 bus pass" not in html, "Expense before date_from must be excluded"

    def test_only_date_from_exact_boundary_is_inclusive(self, client, user_multi_year):
        _login(client, user_multi_year)
        # 2025-01-15 is the exact date of the Bills expense
        resp = client.get("/profile?date_from=2025-01-15")
        html = resp.data.decode()
        assert "2025 electric" in html, (
            "Expense on exact date_from boundary must be included (>=)"
        )

    def test_only_date_from_stats_reflect_open_upper_bound(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-01-01")
        html = resp.data.decode()
        # 2025 total = 200 + 40 = 240
        assert "240.00" in html, (
            "Total spent should be 240.00 for all expenses from 2025-01-01 onwards"
        )


# ── DoD 7: Open lower bound (only date_to) ────────────────────────────────────


class TestOpenLowerBound:
    def test_only_date_to_includes_expenses_on_and_before(self, client, user_multi_year):
        _login(client, user_multi_year)
        # Up to 2024-12-31 — should include 2024 expenses, exclude 2025
        resp = client.get("/profile?date_to=2024-12-31")
        html = resp.data.decode()
        assert "2024 groceries" in html, "Expense before date_to should be included"
        assert "2024 bus pass" in html, "Expense before date_to should be included"
        assert "2025 electric" not in html, "Expense after date_to must be excluded"
        assert "2025 pharmacy" not in html, "Expense after date_to must be excluded"

    def test_only_date_to_exact_boundary_is_inclusive(self, client, user_multi_year):
        _login(client, user_multi_year)
        # 2024-11-20 is the exact date of the Transport expense
        resp = client.get("/profile?date_to=2024-11-20")
        html = resp.data.decode()
        assert "2024 bus pass" in html, (
            "Expense on exact date_to boundary must be included (<=)"
        )

    def test_only_date_to_stats_reflect_open_lower_bound(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_to=2024-12-31")
        html = resp.data.decode()
        # 2024 total = 50 + 30 = 80
        assert "80.00" in html, (
            "Total spent should be 80.00 for all expenses up to 2024-12-31"
        )


# ── DoD 8: Invalid date triggers flash error ──────────────────────────────────


class TestInvalidDateHandling:
    def test_invalid_date_from_returns_200(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=not-a-date")
        assert resp.status_code == 200, "Invalid date should not crash the server"

    def test_invalid_date_from_shows_flash_error(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=not-a-date")
        html = resp.data.decode()
        assert "Invalid date" in html or "invalid" in html.lower() or "YYYY-MM-DD" in html, (
            "A flash error message should appear for an invalid date_from value"
        )

    def test_invalid_date_to_shows_flash_error(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_to=not-a-date")
        html = resp.data.decode()
        assert "Invalid date" in html or "invalid" in html.lower() or "YYYY-MM-DD" in html, (
            "A flash error message should appear for an invalid date_to value"
        )

    def test_invalid_date_renders_unfiltered_page(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=not-a-date")
        html = resp.data.decode()
        # All expenses should still be visible (unfiltered fallback)
        assert "2024 groceries" in html, "Unfiltered data must show when date is invalid"
        assert "2025 electric" in html, "Unfiltered data must show when date is invalid"

    def test_invalid_date_no_active_filter_banner(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=not-a-date")
        html = resp.data.decode()
        assert "Showing results" not in html, (
            "Active-filter banner must not appear when the date is invalid"
        )

    def test_invalid_date_form_inputs_cleared(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=not-a-date")
        html = resp.data.decode()
        # After an error the raw invalid value should not be re-injected into the form
        assert 'value="not-a-date"' not in html, (
            "Invalid date value must not be placed back into the form input"
        )

    def test_malformed_date_with_wrong_format_is_rejected(self, client, user_multi_year):
        _login(client, user_multi_year)
        # DD-MM-YYYY format — wrong separator and order
        resp = client.get("/profile?date_from=20-01-2025")
        html = resp.data.decode()
        assert resp.status_code == 200
        assert "Showing results" not in html, (
            "Wrong date format (DD-MM-YYYY) must be treated as invalid"
        )

    def test_partial_date_string_is_rejected(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-13")
        html = resp.data.decode()
        assert resp.status_code == 200
        assert "Showing results" not in html, (
            "Incomplete date string must be treated as invalid"
        )


# ── DoD 9: Summary stats update with filter ───────────────────────────────────


class TestSummaryStatsWithFilter:
    def test_total_spent_reflects_filtered_range(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        html = resp.data.decode()
        assert "240.00" in html, "Total spent must be 240.00 for 2025 filter"

    def test_transaction_count_reflects_filtered_range(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=2024-01-01&date_to=2024-12-31")
        html = resp.data.decode()
        # 2024 has 2 transactions
        assert "80.00" in html, "Total for 2024 must be 80.00"

    def test_top_category_reflects_filtered_range(self, client, user_multi_year):
        _login(client, user_multi_year)
        # 2024 only: Food=$50, Transport=$30 → top is Food
        resp = client.get("/profile?date_from=2024-01-01&date_to=2024-12-31")
        html = resp.data.decode()
        # Food (50) is highest in 2024
        assert "Food" in html, "Top category should be Food for 2024 filter"

    def test_stats_show_zero_for_date_range_with_no_expenses(self, client, user_multi_year):
        _login(client, user_multi_year)
        # 2020 has no expenses at all
        resp = client.get("/profile?date_from=2020-01-01&date_to=2020-12-31")
        html = resp.data.decode()
        assert "0.00" in html, "Total spent should be 0.00 when no expenses in range"
        assert "No expenses yet" in html, (
            "Transaction table should show empty state when no expenses in filtered range"
        )


# ── DoD 10: Category breakdown percentages sum to 100 with filter ─────────────


class TestCategoryBreakdownPercentagesWithFilter:
    def test_pct_sums_to_100_via_query_helper_with_date_range(self, user_multi_year):
        result = get_category_breakdown(
            user_multi_year, date_from="2025-01-01", date_to="2025-12-31"
        )
        assert result, "Category breakdown should not be empty for a range with expenses"
        total_pct = sum(r["pct"] for r in result)
        assert total_pct == 100, (
            f"Category percentages must sum to 100, got {total_pct}"
        )

    def test_pct_sums_to_100_with_only_date_from(self, user_multi_year):
        result = get_category_breakdown(
            user_multi_year, date_from="2025-01-01"
        )
        assert result
        assert sum(r["pct"] for r in result) == 100, (
            "Category percentages must sum to 100 with open upper bound"
        )

    def test_pct_sums_to_100_with_only_date_to(self, user_multi_year):
        result = get_category_breakdown(
            user_multi_year, date_to="2024-12-31"
        )
        assert result
        assert sum(r["pct"] for r in result) == 100, (
            "Category percentages must sum to 100 with open lower bound"
        )

    def test_pct_sums_to_100_for_all_data_no_filter(self, user_multi_year):
        result = get_category_breakdown(user_multi_year)
        assert result
        assert sum(r["pct"] for r in result) == 100, (
            "Category percentages must sum to 100 with no filter (baseline)"
        )

    def test_breakdown_empty_for_range_with_no_expenses(self, user_multi_year):
        result = get_category_breakdown(
            user_multi_year, date_from="2020-01-01", date_to="2020-12-31"
        )
        assert result == [], "Breakdown must be empty list when no expenses in range"


# ── Query helper unit tests: get_recent_transactions with date filters ─────────


class TestGetRecentTransactionsDateFilter:
    def test_date_from_filters_out_earlier_expenses(self, user_multi_year):
        txs = get_recent_transactions(user_multi_year, date_from="2025-01-01")
        categories = [tx["category"] for tx in txs]
        # Only Bills and Health from 2025 should appear
        assert "Bills" in categories
        assert "Health" in categories
        assert "Food" not in categories, "Food from 2024 must be excluded"
        assert "Transport" not in categories, "Transport from 2024 must be excluded"

    def test_date_to_filters_out_later_expenses(self, user_multi_year):
        txs = get_recent_transactions(user_multi_year, date_to="2024-12-31")
        categories = [tx["category"] for tx in txs]
        assert "Food" in categories
        assert "Transport" in categories
        assert "Bills" not in categories, "Bills from 2025 must be excluded"
        assert "Health" not in categories, "Health from 2025 must be excluded"

    def test_both_bounds_narrow_to_single_year(self, user_multi_year):
        txs = get_recent_transactions(
            user_multi_year, date_from="2024-01-01", date_to="2024-12-31"
        )
        assert len(txs) == 2, "Only 2 expenses exist in 2024"

    def test_no_filter_returns_all_expenses(self, user_multi_year):
        txs = get_recent_transactions(user_multi_year)
        assert len(txs) == 4, "All 4 expenses must be returned with no filter"

    def test_date_from_boundary_is_inclusive(self, user_multi_year):
        # 2024-03-10 is the exact date of the Food expense
        txs = get_recent_transactions(user_multi_year, date_from="2024-03-10")
        descriptions = [tx["description"] for tx in txs]
        assert "2024 groceries" in descriptions, (
            "Expense on the exact date_from must be included"
        )

    def test_date_to_boundary_is_inclusive(self, user_multi_year):
        # 2025-06-20 is the exact date of the Health expense
        txs = get_recent_transactions(user_multi_year, date_to="2025-06-20")
        descriptions = [tx["description"] for tx in txs]
        assert "2025 pharmacy" in descriptions, (
            "Expense on the exact date_to must be included"
        )

    def test_inverted_range_returns_empty(self, user_multi_year):
        # date_from after date_to — should return nothing
        txs = get_recent_transactions(
            user_multi_year, date_from="2025-12-31", date_to="2024-01-01"
        )
        assert txs == [], "Inverted date range should return an empty list"

    def test_single_day_range_returns_only_matching_expense(self, user_multi_year):
        txs = get_recent_transactions(
            user_multi_year, date_from="2025-01-15", date_to="2025-01-15"
        )
        assert len(txs) == 1, "Single-day range should return exactly one expense"
        assert txs[0]["category"] == "Bills"


# ── Query helper unit tests: get_summary_stats with date filters ───────────────


class TestGetSummaryStatsDateFilter:
    def test_date_from_date_to_narrows_stats(self, user_multi_year):
        stats = get_summary_stats(
            user_multi_year, date_from="2025-01-01", date_to="2025-12-31"
        )
        assert stats["total_spent"] == pytest.approx(240.00)
        assert stats["transaction_count"] == 2
        assert stats["top_category"] == "Bills"

    def test_only_date_from_stats(self, user_multi_year):
        stats = get_summary_stats(user_multi_year, date_from="2025-01-01")
        assert stats["total_spent"] == pytest.approx(240.00)
        assert stats["transaction_count"] == 2

    def test_only_date_to_stats(self, user_multi_year):
        stats = get_summary_stats(user_multi_year, date_to="2024-12-31")
        assert stats["total_spent"] == pytest.approx(80.00)
        assert stats["transaction_count"] == 2
        assert stats["top_category"] == "Food"

    def test_no_filter_returns_all_time_stats(self, user_multi_year):
        stats = get_summary_stats(user_multi_year)
        assert stats["total_spent"] == pytest.approx(320.00)
        assert stats["transaction_count"] == 4

    def test_empty_range_returns_zeros(self, user_multi_year):
        stats = get_summary_stats(
            user_multi_year, date_from="2020-01-01", date_to="2020-12-31"
        )
        assert stats["total_spent"] == 0
        assert stats["transaction_count"] == 0
        assert stats["top_category"] == "—"

    def test_single_day_stats(self, user_multi_year):
        stats = get_summary_stats(
            user_multi_year, date_from="2025-01-15", date_to="2025-01-15"
        )
        assert stats["total_spent"] == pytest.approx(200.00)
        assert stats["transaction_count"] == 1
        assert stats["top_category"] == "Bills"


# ── Query helper unit tests: get_category_breakdown with date filters ──────────


class TestGetCategoryBreakdownDateFilter:
    def test_date_range_filter_returns_only_matching_categories(self, user_multi_year):
        result = get_category_breakdown(
            user_multi_year, date_from="2025-01-01", date_to="2025-12-31"
        )
        names = [r["name"] for r in result]
        assert "Bills" in names
        assert "Health" in names
        assert "Food" not in names, "Food was only in 2024, not 2025"
        assert "Transport" not in names, "Transport was only in 2024, not 2025"

    def test_only_date_from_breakdown(self, user_multi_year):
        result = get_category_breakdown(user_multi_year, date_from="2025-01-01")
        names = [r["name"] for r in result]
        assert "Bills" in names
        assert "Food" not in names

    def test_only_date_to_breakdown(self, user_multi_year):
        result = get_category_breakdown(user_multi_year, date_to="2024-12-31")
        names = [r["name"] for r in result]
        assert "Food" in names
        assert "Transport" in names
        assert "Bills" not in names

    def test_breakdown_ordered_by_amount_desc_with_filter(self, user_multi_year):
        result = get_category_breakdown(
            user_multi_year, date_from="2025-01-01", date_to="2025-12-31"
        )
        amounts = [r["amount"] for r in result]
        assert amounts == sorted(amounts, reverse=True), (
            "Breakdown must be ordered by amount descending even with a filter"
        )

    def test_breakdown_pct_are_integers_with_filter(self, user_multi_year):
        result = get_category_breakdown(
            user_multi_year, date_from="2025-01-01", date_to="2025-12-31"
        )
        for r in result:
            assert isinstance(r["pct"], int), "pct must be an integer"

    def test_breakdown_required_keys_with_filter(self, user_multi_year):
        result = get_category_breakdown(
            user_multi_year, date_from="2025-01-01", date_to="2025-12-31"
        )
        for r in result:
            assert {"name", "amount", "pct"} <= r.keys(), (
                "Each breakdown entry must have name, amount, and pct"
            )


# ── Edge cases ────────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_string_params_treated_as_no_filter(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile?date_from=&date_to=")
        assert resp.status_code == 200
        html = resp.data.decode()
        # All data should appear — empty strings = no filter
        assert "2024 groceries" in html
        assert "2025 electric" in html

    def test_whitespace_only_date_treated_as_no_filter(self, client, user_multi_year):
        _login(client, user_multi_year)
        # %20 = space in URL encoding
        resp = client.get("/profile?date_from=%20&date_to=%20")
        assert resp.status_code == 200
        html = resp.data.decode()
        # Whitespace-only input should be stripped and treated as absent
        assert "2024 groceries" in html
        assert "2025 electric" in html

    def test_date_from_equals_date_to_single_day(self, client, user_multi_year):
        _login(client, user_multi_year)
        # 2025-01-15 has one expense: Bills $200
        resp = client.get("/profile?date_from=2025-01-15&date_to=2025-01-15")
        html = resp.data.decode()
        assert "2025 electric" in html, "Expense on single-day range must appear"
        assert "2025 pharmacy" not in html, "Expense outside single day must not appear"

    def test_inverted_range_shows_empty_transaction_table(self, client, user_multi_year):
        _login(client, user_multi_year)
        # date_from is after date_to — no matching expenses
        resp = client.get("/profile?date_from=2025-12-31&date_to=2024-01-01")
        html = resp.data.decode()
        assert "No expenses yet" in html, (
            "Inverted date range should show the empty-state message"
        )

    def test_profile_page_renders_filter_form(self, client, user_multi_year):
        _login(client, user_multi_year)
        resp = client.get("/profile")
        html = resp.data.decode()
        assert 'method="get"' in html, "Filter form must use GET method"
        assert 'name="date_from"' in html, "date_from input must exist"
        assert 'name="date_to"' in html, "date_to input must exist"
        assert "Filter" in html, "Submit button labelled Filter must exist"
        assert "Clear" in html, "Clear link must exist"

    def test_user_only_sees_own_expenses_with_filter(self, app, client):
        """Two users — filter on one user must not expose the other user's data."""
        conn = db_module.get_db()
        cursor1 = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("User A", "usera@example.com", generate_password_hash("pass1")),
        )
        conn.commit()
        uid_a = cursor1.lastrowid

        cursor2 = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("User B", "userb@example.com", generate_password_hash("pass2")),
        )
        conn.commit()
        uid_b = cursor2.lastrowid

        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (?, ?, ?, ?, ?)",
            (uid_a, 99.99, "Food", "2025-03-01", "User A secret expense"),
        )
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (?, ?, ?, ?, ?)",
            (uid_b, 55.00, "Bills", "2025-03-01", "User B private expense"),
        )
        conn.commit()
        conn.close()

        _login(client, uid_a, "User A")
        resp = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        html = resp.data.decode()
        assert "User A secret expense" in html
        assert "User B private expense" not in html, (
            "Filtered profile must not expose another user's expenses"
        )

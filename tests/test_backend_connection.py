# tests/test_backend_connection.py
"""
Tests for Step 5: Backend Connection.
Covers all four query helpers and the GET /profile route.
"""

import os
import sqlite3
import tempfile

import pytest
import database.db as db_module
import database.queries as q_module
from database.db import init_db
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def app():
    """Create a fresh Flask app wired to an in-memory temp database."""
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
def user_with_expenses(app):
    """Insert a test user with 3 known expenses; return user_id."""
    from werkzeug.security import generate_password_hash
    conn = db_module.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        ("Test User", "test@example.com",
         generate_password_hash("password123"), "2026-01-15 10:00:00"),
    )
    conn.commit()
    uid = cursor.lastrowid
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (?, ?, ?, ?, ?)",
        [
            (uid, 100.00, "Bills",     "2026-05-20", "Electric"),
            (uid,  50.00, "Food",      "2026-05-15", "Groceries"),
            (uid,  50.00, "Transport", "2026-05-10", "Bus pass"),
        ],
    )
    conn.commit()
    conn.close()
    return uid


@pytest.fixture
def user_no_expenses(app):
    """Insert a test user with zero expenses; return user_id."""
    from werkzeug.security import generate_password_hash
    conn = db_module.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        ("Empty User", "empty@example.com",
         generate_password_hash("password123"), "2026-03-01 08:00:00"),
    )
    conn.commit()
    uid = cursor.lastrowid
    conn.close()
    return uid


# ── S1: get_user_by_id tests ──────────────────────────────────────────────

class TestGetUserById:
    def test_returns_dict_for_valid_id(self, user_with_expenses):
        result = get_user_by_id(user_with_expenses)
        assert result is not None
        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"
        assert result["member_since"] == "January 2026"
        assert result["initials"] == "TU"

    def test_returns_none_for_nonexistent_id(self, app):
        result = get_user_by_id(99999)
        assert result is None


# ── S1: get_recent_transactions tests ─────────────────────────────────────

class TestGetRecentTransactions:
    def test_returns_list_ordered_newest_first(self, user_with_expenses):
        txs = get_recent_transactions(user_with_expenses)
        assert len(txs) == 3
        dates = [tx["date"] for tx in txs]
        assert dates == sorted(dates, reverse=True)

    def test_each_item_has_required_keys(self, user_with_expenses):
        txs = get_recent_transactions(user_with_expenses)
        for tx in txs:
            assert "date" in tx
            assert "description" in tx
            assert "category" in tx
            assert "amount" in tx

    def test_amount_is_float(self, user_with_expenses):
        txs = get_recent_transactions(user_with_expenses)
        for tx in txs:
            assert isinstance(tx["amount"], float)

    def test_returns_empty_list_for_no_expenses(self, user_no_expenses):
        txs = get_recent_transactions(user_no_expenses)
        assert txs == []

    def test_limit_parameter_respected(self, user_with_expenses):
        txs = get_recent_transactions(user_with_expenses, limit=2)
        assert len(txs) == 2


# ── S2 STUB: get_summary_stats tests ─────────────────────────────────────

class TestGetSummaryStats:
    # S2-TEST-STUB-START
    def test_returns_correct_stats_with_expenses(self, user_with_expenses):
        result = get_summary_stats(user_with_expenses)
        assert result["total_spent"] == pytest.approx(200.00)
        assert result["transaction_count"] == 3
        assert result["top_category"] == "Bills"

    def test_returns_zeros_for_no_expenses(self, user_no_expenses):
        result = get_summary_stats(user_no_expenses)
        assert result["total_spent"] == 0
        assert result["transaction_count"] == 0
        assert result["top_category"] == "—"

    def test_total_spent_is_numeric(self, user_with_expenses):
        result = get_summary_stats(user_with_expenses)
        assert isinstance(result["total_spent"], (int, float))
    # S2-TEST-STUB-END


# ── S3 STUB: get_category_breakdown tests ────────────────────────────────

class TestGetCategoryBreakdown:
    # S3-TEST-STUB-START
    def test_ordered_by_amount_desc(self, user_with_expenses):
        result = get_category_breakdown(user_with_expenses)
        amounts = [r["amount"] for r in result]
        assert amounts == sorted(amounts, reverse=True)

    def test_pct_sums_to_100(self, user_with_expenses):
        result = get_category_breakdown(user_with_expenses)
        assert sum(r["pct"] for r in result) == 100

    def test_pct_values_are_integers(self, user_with_expenses):
        for r in get_category_breakdown(user_with_expenses):
            assert isinstance(r["pct"], int)

    def test_required_keys_present(self, user_with_expenses):
        for r in get_category_breakdown(user_with_expenses):
            assert {"name", "amount", "pct"} <= r.keys()

    def test_returns_empty_list_for_no_expenses(self, user_no_expenses):
        assert get_category_breakdown(user_no_expenses) == []

    def test_correct_categories_present(self, user_with_expenses):
        names = [r["name"] for r in get_category_breakdown(user_with_expenses)]
        assert "Bills" in names and "Food" in names and "Transport" in names
    # S3-TEST-STUB-END


# ── Route tests ───────────────────────────────────────────────────────────

class TestProfileRoute:
    def test_unauthenticated_redirects_to_login(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_authenticated_returns_200(self, client, user_with_expenses):
        with client.session_transaction() as sess:
            sess["user_id"] = user_with_expenses
            sess["user_name"] = "Test User"
        resp = client.get("/profile")
        assert resp.status_code == 200

    def test_shows_user_name_and_email(self, client, user_with_expenses):
        with client.session_transaction() as sess:
            sess["user_id"] = user_with_expenses
            sess["user_name"] = "Test User"
        resp = client.get("/profile")
        html = resp.data.decode()
        assert "Test User" in html
        assert "test@example.com" in html

    def test_rupee_symbol_present(self, client, user_with_expenses):
        with client.session_transaction() as sess:
            sess["user_id"] = user_with_expenses
            sess["user_name"] = "Test User"
        resp = client.get("/profile")
        html = resp.data.decode()
        assert "₹" in html

    def test_empty_user_shows_no_expenses_message(self, client, user_no_expenses):
        with client.session_transaction() as sess:
            sess["user_id"] = user_no_expenses
            sess["user_name"] = "Empty User"
        resp = client.get("/profile")
        html = resp.data.decode()
        assert resp.status_code == 200
        assert "No expenses yet" in html

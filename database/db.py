import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash


def get_db():
    """Open spendly.db with row_factory and foreign-key enforcement enabled."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "spendly.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create users and expenses tables if they don't already exist."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def seed_db():
    """Insert demo user and sample expenses — skips silently if already seeded."""
    conn = get_db()

    # Idempotency guard — bail out if demo user already exists
    existing = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    if existing:
        conn.close()
        return

    # Insert demo user with hashed password
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    conn.commit()

    user_id = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()["id"]

    # 8 sample expenses covering all 7 required categories
    expenses = [
        (user_id, 12.50,  "Food",          "2026-05-01", "Lunch at cafe"),
        (user_id, 45.00,  "Transport",     "2026-05-03", "Monthly bus pass"),
        (user_id, 120.00, "Bills",         "2026-05-05", "Electricity bill"),
        (user_id, 30.00,  "Health",        "2026-05-08", "Pharmacy"),
        (user_id, 15.00,  "Entertainment", "2026-05-10", "Streaming subscription"),
        (user_id, 60.00,  "Shopping",      "2026-05-14", "New shoes"),
        (user_id, 8.75,   "Other",         "2026-05-17", "Miscellaneous"),
        (user_id, 22.00,  "Food",          "2026-05-20", "Grocery run"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    conn.close()


def get_user_by_email(email: str):
    """Return the users row for the given email, or None if not found."""
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return user


def create_user(name: str, email: str, password: str) -> int:
    """Hash password, insert a new user row, and return the new user_id."""
    password_hash = generate_password_hash(password)
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def verify_login(email: str, password: str):
    """Return the user row if credentials are valid, otherwise None."""
    user = get_user_by_email(email)
    if user is None:
        return None
    if check_password_hash(user["password_hash"], password):
        return user
    return None

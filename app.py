import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, session, url_for, flash
from database.db import init_db, seed_db, get_user_by_email, create_user, verify_login
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown

app = Flask(__name__)
app.secret_key = os.urandom(24)

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _parse_date(value: str) -> str | None:
    """Return value if valid YYYY-MM-DD; return None if empty; raise ValueError if malformed."""
    if not value:
        return None
    datetime.strptime(value, "%Y-%m-%d")
    return value


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    # POST — process the form
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    error = None

    if not name or not email or not password:
        error = "All fields are required."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif get_user_by_email(email):
        error = "An account with that email already exists."

    if error:
        return render_template("register.html", error=error, name=name, email=email)

    user_id = create_user(name, email, password)
    session["user_id"] = user_id
    session["user_name"] = name
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    # POST — process the form
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    error = None

    if not email or not password:
        error = "All fields are required."
    else:
        user = verify_login(email, password)
        if user is None:
            error = "Invalid email or password."

    if error:
        return render_template("login.html", error=error, email=email)

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    uid = session["user_id"]

    # ── S1: user info ────────────────────────────────────────────────────
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    # ── Date filter extraction and validation ────────────────────────────
    raw_from = request.args.get("date_from", "").strip()
    raw_to = request.args.get("date_to", "").strip()

    date_from = date_to = None
    try:
        date_from = _parse_date(raw_from)
        date_to = _parse_date(raw_to)
    except ValueError:
        flash("Invalid date format. Please use YYYY-MM-DD.", "error")
        date_from = date_to = None
        raw_from = raw_to = ""

    # ── S2: summary stats ────────────────────────────────────────────────
    raw_stats = get_summary_stats(uid, date_from=date_from, date_to=date_to)
    stats = {
        "total_spent":       f"₹{raw_stats['total_spent']:.2f}",
        "transaction_count": raw_stats["transaction_count"],
        "top_category":      raw_stats["top_category"],
    }

    # ── S1: transactions ─────────────────────────────────────────────────
    transactions = [
        {**tx, "amount": f"₹{tx['amount']:.2f}"}
        for tx in get_recent_transactions(uid, date_from=date_from, date_to=date_to)
    ]

    # ── S3: category breakdown ───────────────────────────────────────────
    categories = [
        {**cat, "amount": f"₹{cat['amount']:.2f}"}
        for cat in get_category_breakdown(uid, date_from=date_from, date_to=date_to)
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        date_from=raw_from,
        date_to=raw_to,
        filter_active=(date_from is not None or date_to is not None),
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)

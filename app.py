import os

from flask import Flask, render_template, request, redirect, session, url_for
from database.db import get_db, init_db, seed_db, get_user_by_email, create_user, verify_login

app = Flask(__name__)
app.secret_key = os.urandom(24)

with app.app_context():
    init_db()
    seed_db()


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

    user = {
        "name": "Alex Morgan",
        "email": "alex@example.com",
        "member_since": "May 2025",
        "initials": "AM",
    }

    stats = {
        "total_spent": "₹313.25",
        "transaction_count": 8,
        "top_category": "Bills",
    }

    transactions = [
        {"date": "May 01, 2026", "description": "Lunch at cafe",         "category": "Food",          "amount": "₹12.50"},
        {"date": "May 03, 2026", "description": "Monthly bus pass",       "category": "Transport",     "amount": "₹45.00"},
        {"date": "May 05, 2026", "description": "Electricity bill",       "category": "Bills",         "amount": "₹120.00"},
        {"date": "May 08, 2026", "description": "Pharmacy",               "category": "Health",        "amount": "₹30.00"},
        {"date": "May 10, 2026", "description": "Streaming subscription", "category": "Entertainment", "amount": "₹15.00"},
        {"date": "May 14, 2026", "description": "New shoes",              "category": "Shopping",      "amount": "₹60.00"},
        {"date": "May 17, 2026", "description": "Miscellaneous",          "category": "Other",         "amount": "₹8.75"},
        {"date": "May 20, 2026", "description": "Grocery run",            "category": "Food",          "amount": "₹22.00"},
    ]

    categories = [
        {"name": "Bills",         "amount": "₹120.00", "pct": 38, "bar_class": "bar-w-38"},
        {"name": "Shopping",      "amount": "₹60.00",  "pct": 19, "bar_class": "bar-w-19"},
        {"name": "Transport",     "amount": "₹45.00",  "pct": 14, "bar_class": "bar-w-14"},
        {"name": "Food",          "amount": "₹34.50",  "pct": 11, "bar_class": "bar-w-11"},
        {"name": "Health",        "amount": "₹30.00",  "pct": 10, "bar_class": "bar-w-10"},
        {"name": "Entertainment", "amount": "₹15.00",  "pct": 5,  "bar_class": "bar-w-05"},
        {"name": "Other",         "amount": "₹8.75",   "pct": 3,  "bar_class": "bar-w-03"},
    ]

    return render_template("profile.html", user=user, stats=stats,
                           transactions=transactions, categories=categories)


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

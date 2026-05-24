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
        return redirect(url_for("landing"))

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
    return redirect(url_for("landing"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

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
    return redirect(url_for("landing"))


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
    return "Profile page — coming in Step 4"


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

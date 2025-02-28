from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from passlib.hash import bcrypt
from models import get_db_connection, query_db

auth = Blueprint("auth", __name__, url_prefix="/auth")

# Signup Route
@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        firstName = request.form["firstName"]
        lastName = request.form["lastName"]
        salary = int(request.form["salary"])
        role = request.form["role"]

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("auth.signup"))

        hashed_password = bcrypt.hash(password)
        initial_points = 5000 if salary < 10000 else 4000 if salary < 20000 else 3000 if salary < 30000 else 2000 if salary < 40000 else 1000

        try:
            with get_db_connection() as conn:
                conn.execute("INSERT INTO users (username, password, lastName, firstName, salary, points, role) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (username, hashed_password, lastName, firstName, salary, initial_points, role))
                conn.commit()
            flash("Signup successful! You can now log in.", "success")
            return redirect(url_for("auth.login"))
        except:
            flash("Username already exists. Please choose another one.", "danger")

    return render_template("signup.html")

# Login Route
@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
        if user and bcrypt.verify(password, user["password"]):
            session["userID"] = user["userID"]
            session["username"] = username
            session["role"] = user["role"]
            flash(f"Welcome, {username}!", "success")

            return redirect(url_for("dashboard.user_dashboard" if user["role"] == "client" else "dashboard.admin_dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")

# Logout Route
@auth.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

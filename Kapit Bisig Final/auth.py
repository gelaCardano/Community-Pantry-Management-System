from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from passlib.hash import bcrypt
from models import get_db_connection, query_db

auth = Blueprint("auth", __name__, url_prefix="/auth")

# Signup Route
@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        role = request.form.get("role")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        firstName = request.form.get("firstName")
        lastName = request.form.get("lastName")

        salary_input = request.form.get("salary", "0")  # Default to "0" if empty
        salary = int(salary_input) if salary_input.isdigit() else 0  # Convert only if valid

        # Validate admin code for admin signups
        if role == "admin":
            code = request.form.get("code")
            if code != "123456789":
                flash("Admin code is incorrect, please try again", "danger")
                return redirect(url_for("auth.signup"))

        # Validate password confirmation
        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("auth.signup"))

        hashed_password = bcrypt.hash(password)
        initial_points = max(1000, 5000 - (salary // 10000) * 1000)  # Simplified formula

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
        username = request.form.get("username")
        password = request.form.get("password")

        user = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
        if user and bcrypt.verify(password, user["password"]):
            session.update({"userID": user["userID"], "username": username, "role": user["role"]})
            return redirect(url_for("dashboard.user_dashboard" if user["role"] == "client" else "dashboard.admin_dashboard"))

        flash("Invalid username or password.", "danger")
    
    return render_template("login.html")

# Forgot Password
@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        if 'verify' in request.form:
            username = request.form.get('username', '').lower()
            firstName = request.form.get('firstName', '').lower()
            lastName = request.form.get('lastName', '').lower()

            user = query_db("SELECT * FROM users WHERE username COLLATE NOCASE = ? AND firstName COLLATE NOCASE = ? AND lastName COLLATE NOCASE = ?",
                            (username, firstName, lastName), one=True)

            if user:
                session['username_verified'] = username
                flash('User verified! You may now reset your password.', 'success')
            else:
                flash('User verification failed. Please check your details.', 'danger')

        elif 'reset' in request.form and session.get('username_verified'):
            new_password = request.form.get("new_password")
            confirm_password = request.form.get("confirm_password")

            if new_password != confirm_password:
                flash("New passwords do not match!", "danger")
                return redirect(url_for("auth.forgot_password"))

            hashed_password = bcrypt.hash(new_password)
            query_db("UPDATE users SET password = ? WHERE username = ?", (hashed_password, session.pop('username_verified')), one=True)
            flash("Password changed successfully! Please log in again.", "success")
            return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")

# Change Password
@auth.route("/change-password", methods=["GET", "POST"])
def change_password():
    if "username" not in session:
        flash("You must be logged in to change your password.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        user = query_db("SELECT * FROM users WHERE username = ?", (session["username"],), one=True)
        if not user or not bcrypt.verify(old_password, user["password"]):
            flash("Old password is incorrect.", "danger")
            return redirect(url_for("auth.change_password"))

        if new_password != confirm_password:
            flash("New passwords do not match!", "danger")
            return redirect(url_for("auth.change_password"))

        query_db("UPDATE users SET password = ? WHERE username = ?", (bcrypt.hash(new_password), session["username"]), one=True)
        flash("Password changed successfully! Please log in again.", "success")
        return redirect(url_for("auth.logout"))

    return render_template("change_password.html")

# Logout Route
@auth.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from passlib.hash import bcrypt
from models import get_db_connection, query_db

auth = Blueprint("auth", __name__, url_prefix="/auth")

# Signup Route
@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        role = request.form["role"]
        if role == "admin":
            code = request.form["code"]
            if code == "123456789":
                username = request.form["username"]
                password = request.form["password"]
                confirm_password = request.form["confirm_password"]
                firstName = request.form["firstName"]
                lastName = request.form["lastName"]
                salary = 0
            else:
                flash("Admin code is incorrect, please try again", "danger")
                return redirect(url_for("auth.signup"))
        elif role == "client":
            username = request.form["username"]
            password = request.form["password"]
            confirm_password = request.form["confirm_password"]
            firstName = request.form["firstName"]
            lastName = request.form["lastName"]
            salary = int(request.form["salary"])

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

            return redirect(url_for("dashboard.user_dashboard" if user["role"] == "client" else "dashboard.admin_dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        flash('If the email is registered, a reset link has been sent.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')

@auth.route("/change-password", methods=["GET", "POST"])
def change_password():

    username = session["username"]

    if request.method == "POST":
        old_password = request.form["old_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]
        
        # Fetch user from the database
        user = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
        
        if not user:
            flash("User does not exist.", "danger")
            return redirect(url_for("auth.change_password"))

        # Verify old password
        if not bcrypt.verify(old_password, user["password"]):
            flash("Old password is incorrect.", "danger")
            return redirect(url_for("auth.change_password"))
        
        if new_password == old_password:
            flash("New passwords cannot be same as before!", "danger")
            return redirect(url_for("auth.change_password"))

        # Check if new passwords match
        if new_password != confirm_password:
            flash("New passwords do not match!", "danger")
            return redirect(url_for("auth.change_password"))

        # Hash new password and update database
        hashed_password = bcrypt.hash(new_password)
        try:
            with get_db_connection() as conn:
                conn.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, username))
                conn.commit()
            flash("Password changed successfully! Please log in again.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            flash(f"Error updating password: {str(e)}", "danger")

    return render_template("change_password.html")

# Logout Route
@auth.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

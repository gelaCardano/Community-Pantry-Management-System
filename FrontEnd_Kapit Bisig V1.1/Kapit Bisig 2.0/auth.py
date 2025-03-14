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
        username = request.form.get('username', '').lower()
        firstName = request.form.get('firstName', '').lower()
        lastName = request.form.get('lastName', '').lower()

        with get_db_connection() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username COLLATE NOCASE = ? AND firstName COLLATE NOCASE = ? AND lastName COLLATE NOCASE = ?",
                (username, firstName, lastName)
            ).fetchone()

        if user:
            flash('User verified! You may now reset your password.', 'success')
            session["username"] = username
            return redirect(url_for('auth.reset_password', username=username))  
        else:
            flash('User verification failed. Please check your details.', 'danger')

    return render_template('forgot_password.html')

@auth.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    username = session["username"]

    if request.method == "POST":
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        user = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
        if not user:
            flash("User does not exist.", "danger")
            return redirect(url_for("auth.forgot_password"))

        # Check if new passwords match
        if new_password != confirm_password:
            flash("New passwords do not match!", "danger")
            return redirect(url_for("auth.reset_password"))

        hashed_password = bcrypt.hash(new_password)

        try:
            with get_db_connection() as conn:
                conn.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, username))
                conn.commit()
            flash("Password changed successfully! Please log in again.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            flash(f"Error updating password: {str(e)}", "danger")

    return render_template("reset_password.html")

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

@auth.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    if "userID" not in session:
        flash("Please log in to edit your profile.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["userID"]

    # Fetch user data
    user = query_db("SELECT * FROM users WHERE userID = ?", (user_id,), one=True)

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("dashboard.user_dashboard"))

    if request.method == "POST":
        username = request.form["username"].strip()
        first_name = request.form["firstName"].strip()
        last_name = request.form["lastName"].strip()
        
        try:
            salary = int(request.form["salary"].strip())  # Convert salary to integer
            if salary < 0:
                raise ValueError
        except ValueError:
            flash("Salary must be a valid non-negative number!", "danger")
            return redirect(url_for("auth.edit_profile"))

        # Function to determine points based on salary
        def get_points(salary):
            return 5000 if salary < 10000 else 4000 if salary < 20000 else 3000 if salary < 30000 else 2000 if salary < 40000 else 1000

        # Determine previous supposed points
        previous_salary = user["salary"]
        initial_points = get_points(previous_salary)

        # Determine points used
        points_used = initial_points - user["points"]

        # Determine new assigned points based on the new salary
        new_assigned_points = get_points(salary)

        # Deduct points used from new assigned points
        new_points = max(new_assigned_points - points_used, 0)  # Ensure points don't go negative

        # Update user info
        try:
            with get_db_connection() as conn:
                conn.execute(
                    "UPDATE users SET username = ?, firstName = ?, lastName = ?, salary = ?, points = ? WHERE userID = ?",
                    (username, first_name, last_name, salary, new_points, user_id)
                )
                conn.commit()

            # Update session username
            session["username"] = username

            flash("Profile updated successfully!", "success")
            return redirect(url_for("dashboard.user_dashboard"))

        except Exception as e:
            flash("Username already exists or another error occurred. Please try another one.", "danger")

    return render_template("edit_profile.html", user=user)

# Logout Route
@auth.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from passlib.hash import bcrypt

app = Flask(__name__)
app.secret_key = "your_secret_key"

# ---------- Database Connection ----------
def get_db_connection():
    conn = sqlite3.connect("kapitbisig.db")
    conn.row_factory = sqlite3.Row  # Allows dictionary-like access to rows
    return conn

# ---------- Routes ----------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
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
            return redirect(url_for("signup"))

        hashed_password = bcrypt.hash(password)
        initial_points = 5000 if salary < 10000 else 4000 if salary < 20000 else 3000 if salary < 30000 else 2000 if salary < 40000 else 1000

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password, lastName, firstName, salary, points, role) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (username, hashed_password, lastName, firstName, salary, initial_points, role))
            conn.commit()
            conn.close()
            flash("Signup successful! You can now log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists. Please choose another one.", "danger")
    
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()

        if result and bcrypt.verify(password, result["password"]):
            session["userID"] = result["userID"]
            session["username"] = username
            session["role"] = result["role"]
            flash(f"Welcome, {username}!", "success")

            if session["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("user_dashboard"))
        
        flash("Invalid username or password.", "danger")
    
    return render_template("login.html")


@app.route("/user_dashboard")
def user_dashboard():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch user data based on session username
    cursor.execute("SELECT * FROM users WHERE username = ?", (session["username"],))
    user = cursor.fetchone()

    # Fetch available pantry items
    cursor.execute("SELECT * FROM items WHERE itemQuantity > 0")
    items = cursor.fetchall()

    conn.close()

    return render_template("user_dashboard.html", user=user, items=items)


@app.route("/admin_dashboard")
def admin_dashboard():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch admin data
    cursor.execute("SELECT * FROM users WHERE username = ?", (session["username"],))
    admin = cursor.fetchone()

    # Fetch all transactions
    cursor.execute("SELECT * FROM transactions ORDER BY timestamp DESC")
    transactions = cursor.fetchall()

    # Fetch pending complaints
    cursor.execute("SELECT * FROM complaints WHERE issueStatus = 'Pending'")
    complaints = cursor.fetchall()

    conn.close()

    return render_template("admin_dashboard.html", admin=admin, transactions=transactions, complaints=complaints)


@app.route("/add_item", methods=["POST"])
def add_item():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("login"))

    itemName = request.form["itemName"]
    itemValue = int(request.form["itemValue"])
    itemQuantity = int(request.form["itemQuantity"])

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if item exists
    cursor.execute("SELECT itemID FROM items WHERE itemName = ?", (itemName,))
    itemExists = cursor.fetchone()

    if itemExists:
        cursor.execute("UPDATE items SET itemQuantity = itemQuantity + ? WHERE itemName = ?", (itemQuantity, itemName))
    else:
        cursor.execute("INSERT INTO items (itemName, itemValue, itemQuantity) VALUES (?, ?, ?)",
                       (itemName, itemValue, itemQuantity))
    
    conn.commit()
    conn.close()
    flash(f"{itemQuantity} units of {itemName} added successfully!", "success")

    return redirect(url_for("admin_dashboard"))


@app.route("/resolve_complaint", methods=["POST"])
def resolve_complaint():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("login"))

    issueID = request.form["issueID"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Update complaint status
    cursor.execute("UPDATE complaints SET issueStatus = 'Resolved' WHERE issueID = ?", (issueID,))
    conn.commit()
    conn.close()

    flash(f"Complaint {issueID} has been resolved.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/request_item", methods=["POST"])
def request_item():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("login"))

    userID = session["userID"]
    itemID = request.form["itemID"]
    quantity = int(request.form["quantity"])

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get item details
    cursor.execute("SELECT itemName, itemValue, itemQuantity FROM items WHERE itemID = ?", (itemID,))
    item = cursor.fetchone()

    if not item:
        flash("Item not found.", "danger")
        return redirect(url_for("user_dashboard"))

    itemName, itemValue, itemQuantity = item
    totalCost = itemValue * quantity

    # Check user points
    cursor.execute("SELECT points FROM users WHERE userID = ?", (userID,))
    userPoints = cursor.fetchone()[0]

    if quantity > itemQuantity:
        flash("Not enough stock available.", "danger")
    elif totalCost > userPoints:
        flash("Not enough points to request this item.", "danger")
    else:
        # Create a pending transaction for admin approval
        cursor.execute("INSERT INTO transactions (userID, action, details, status) VALUES (?, 'Request Item', ?, 'Pending Approval')",
                       (userID, f"Requested {quantity} of {itemName}"))

        conn.commit()
        flash("Item request submitted for admin approval.", "success")

    conn.close()
    return redirect(url_for("user_dashboard"))

@app.route("/approve_request", methods=["POST"])
def approve_request():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("login"))

    transactionID = request.form["transactionID"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Retrieve transaction details
    cursor.execute("SELECT userID, details FROM transactions WHERE transactionID = ?", (transactionID,))
    transaction = cursor.fetchone()

    if transaction:
        userID, details = transaction
        itemName = details.split(" ")[2]
        quantity = int(details.split(" ")[1])

        # Get item details
        cursor.execute("SELECT itemID, itemValue, itemQuantity FROM items WHERE itemName = ?", (itemName,))
        item = cursor.fetchone()

        if not item:
            flash("Item not found.", "danger")
            return redirect(url_for("admin_dashboard"))

        itemID, itemValue, itemQuantity = item
        totalCost = itemValue * quantity

        # Check user points and item stock
        cursor.execute("SELECT points FROM users WHERE userID = ?", (userID,))
        userPoints = cursor.fetchone()[0]

        if quantity > itemQuantity:
            flash("Not enough stock to approve request.", "danger")
        elif totalCost > userPoints:
            flash("User does not have enough points to complete request.", "danger")
        else:
            # Deduct points and update stock
            cursor.execute("UPDATE users SET points = points - ? WHERE userID = ?", (totalCost, userID))
            cursor.execute("UPDATE items SET itemQuantity = itemQuantity - ? WHERE itemID = ?", (quantity, itemID))
            cursor.execute("UPDATE transactions SET status = 'Approved' WHERE transactionID = ?", (transactionID,))

            conn.commit()
            flash(f"Request ID {transactionID} has been approved.", "success")

    conn.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/reject_request", methods=["POST"])
def reject_request():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("login"))

    transactionID = request.form["transactionID"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE transactions SET status = 'Rejected' WHERE transactionID = ?", (transactionID,))
    conn.commit()
    conn.close()

    flash(f"Request ID {transactionID} has been rejected.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# ---------- Run Flask ----------
if __name__ == "__main__":
    app.run(debug=True)

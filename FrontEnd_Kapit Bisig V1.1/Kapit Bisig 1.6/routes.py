from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import get_db_connection, query_db

dashboard = Blueprint("dashboard", __name__)

# Home Page Route
@dashboard.route("/")
def home():
    return render_template("index.html")

# User Dashboard Route
@dashboard.route("/user_dashboard")
def user_dashboard():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("auth.login"))

    user = query_db("SELECT * FROM users WHERE username = ?", (session["username"],), one=True)
    items = query_db("SELECT * FROM items WHERE itemQuantity > 0")

    return render_template("user_dashboard.html", user=user, items=items)

# Admin Dashboard Route
@dashboard.route("/admin_dashboard")
def admin_dashboard():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("auth.login"))

    admin = query_db("SELECT * FROM users WHERE username = ?", (session["username"],), one=True)
    transactions = query_db("SELECT * FROM transactions ORDER BY timestamp DESC")
    pending_requests = query_db("SELECT * FROM transactions WHERE status = 'Pending Approval'")
    complaints = query_db("SELECT * FROM complaints WHERE issueStatus = 'Pending'")

    return render_template("admin_dashboard.html", admin=admin, transactions=transactions, pending_requests=pending_requests, complaints=complaints)

# Approve Item Request Route (Fixed)
@dashboard.route("/approve_request", methods=["POST"])
def approve_request():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    transactionID = request.form.get("transactionID")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE transactions SET status = 'Approved' WHERE transactionID = ?", (transactionID,))
    conn.commit()
    conn.close()

    flash(f"Transaction {transactionID} has been approved.", "success")
    return redirect(url_for("dashboard.admin_dashboard"))

# Reject Item Request Route (Fixed)
@dashboard.route("/reject_request", methods=["POST"])
def reject_request():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    transactionID = request.form.get("transactionID")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE transactions SET status = 'Rejected' WHERE transactionID = ?", (transactionID,))
    conn.commit()
    conn.close()

    flash(f"Request ID {transactionID} has been rejected.", "success")
    return redirect(url_for("dashboard.admin_dashboard"))

# Add Item Route (Fixed)
@dashboard.route("/add_item", methods=["POST"])
def add_item():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    itemName = request.form["itemName"]
    itemValue = int(request.form["itemValue"])
    itemQuantity = int(request.form["itemQuantity"])

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT itemID FROM items WHERE itemName = ?", (itemName,))
    itemExists = cursor.fetchone()

    if itemExists:
        cursor.execute("UPDATE items SET itemQuantity = itemQuantity + ? WHERE itemName = ?", (itemQuantity, itemName))
    else:
        cursor.execute("INSERT INTO items (itemName, itemValue, itemQuantity) VALUES (?, ?, ?)", (itemName, itemValue, itemQuantity))

    conn.commit()
    conn.close()

    flash(f"{itemQuantity} units of {itemName} added successfully!", "success")
    return redirect(url_for("dashboard.admin_dashboard"))

# File Complaint Route (Fixed)
@dashboard.route("/file_complaint", methods=["POST"])
def file_complaint():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("auth.login"))

    userID = session["userID"]
    issueDesc = request.form["issueDesc"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO complaints (userID, issueDesc, issueStatus) VALUES (?, ?, 'Pending')", (userID, issueDesc))
    conn.commit()
    conn.close()

    flash("Your complaint has been submitted successfully!", "success")
    return redirect(url_for("dashboard.user_dashboard"))

# Resolve Complaint Route
@dashboard.route("/resolve_complaint", methods=["POST"])
def resolve_complaint():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    issueID = request.form["issueID"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE complaints SET issueStatus = 'Resolved' WHERE issueID = ?", (issueID,))
    conn.commit()
    conn.close()

    flash(f"Complaint {issueID} has been resolved.", "success")
    return redirect(url_for("dashboard.admin_dashboard"))

# Bulk Request Items Route (Fixed)
@dashboard.route("/request_items_bulk", methods=["POST"])
def request_items_bulk():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("auth.login"))

    userID = session["userID"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT points FROM users WHERE userID = ?", (userID,))
    userPoints = cursor.fetchone()["points"]

    cursor.execute("SELECT * FROM items WHERE itemQuantity > 0")
    items = cursor.fetchall()

    requested_items = []
    total_cost = 0

    for item in items:
        itemID = item["itemID"]
        quantity_requested = int(request.form.get(f"quantity_{itemID}", 0))

        if quantity_requested > 0:
            itemValue = item["itemValue"]
            itemQuantity = item["itemQuantity"]
            cost = quantity_requested * itemValue

            if quantity_requested > itemQuantity:
                flash(f"Not enough stock for {item['itemName']}.", "danger")
                conn.close()
                return redirect(url_for("dashboard.user_dashboard"))

            requested_items.append((itemID, quantity_requested, item["itemName"], cost))
            total_cost += cost

    if total_cost > userPoints:
        flash("Not enough points for this request.", "danger")
        conn.close()
        return redirect(url_for("dashboard.user_dashboard"))

    if not requested_items:
        flash("No items selected.", "danger")
        conn.close()
        return redirect(url_for("dashboard.user_dashboard"))

    details = "; ".join([f"Requested {q} of {name}" for _, q, name, _ in requested_items])
    cursor.execute("INSERT INTO transactions (userID, action, details, status) VALUES (?, 'Request Item', ?, 'Pending Approval')", (userID, details))

    conn.commit()
    flash("Bulk item request submitted for admin approval.", "success")
    conn.close()
    return redirect(url_for("dashboard.user_dashboard"))
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import get_db_connection, query_db

dashboard = Blueprint("dashboard", __name__)

# Home Page Route
@dashboard.route("/")
def home():
    return render_template("index.html")

# User Dashboard Route with Scrollable Inventory
@dashboard.route("/user_dashboard")
def user_dashboard():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("auth.login"))

    user = query_db("SELECT * FROM users WHERE username = ?", (session["username"],), one=True)
    items = query_db("SELECT * FROM items WHERE itemQuantity > 0")

    return render_template("user_dashboard.html", user=user, items=items)

# Admin Dashboard Route
@dashboard.route("/admin_dashboard")
def admin_dashboard():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("auth.login"))

    admin = query_db("SELECT * FROM users WHERE username = ?", (session["username"],), one=True)
    transactions = query_db("SELECT * FROM transactions ORDER BY timestamp DESC")
    pending_requests = query_db("SELECT * FROM transactions WHERE status = 'Pending Approval'")
    complaints = query_db("SELECT * FROM complaints WHERE issueStatus = 'Pending'")

    return render_template("admin_dashboard.html", admin=admin, transactions=transactions, pending_requests=pending_requests, complaints=complaints)

# Approve Item Request Route (Fixed)
@dashboard.route("/approve_request", methods=["POST"])
def approve_request():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    transactionID = request.form.get("transactionID")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE transactions SET status = 'Approved' WHERE transactionID = ?", (transactionID,))
    conn.commit()
    conn.close()

    flash(f"Transaction {transactionID} has been approved.", "success")
    return redirect(url_for("dashboard.admin_dashboard"))

# Reject Item Request Route (Fixed)
@dashboard.route("/reject_request", methods=["POST"])
def reject_request():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    transactionID = request.form.get("transactionID")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE transactions SET status = 'Rejected' WHERE transactionID = ?", (transactionID,))
    conn.commit()
    conn.close()

    flash(f"Request ID {transactionID} has been rejected.", "success")
    return redirect(url_for("dashboard.admin_dashboard"))

# Add Item Route (Fixed)
@dashboard.route("/add_item", methods=["POST"])
def add_item():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    itemName = request.form["itemName"]
    itemValue = int(request.form["itemValue"])
    itemQuantity = int(request.form["itemQuantity"])

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT itemID FROM items WHERE itemName = ?", (itemName,))
    itemExists = cursor.fetchone()

    if itemExists:
        cursor.execute("UPDATE items SET itemQuantity = itemQuantity + ? WHERE itemName = ?", (itemQuantity, itemName))
    else:
        cursor.execute("INSERT INTO items (itemName, itemValue, itemQuantity) VALUES (?, ?, ?)", (itemName, itemValue, itemQuantity))

    conn.commit()
    conn.close()

    flash(f"{itemQuantity} units of {itemName} added successfully!", "success")
    return redirect(url_for("dashboard.admin_dashboard"))

# File Complaint Route (Fixed)
@dashboard.route("/file_complaint", methods=["POST"])
def file_complaint():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("auth.login"))

    userID = session["userID"]
    issueDesc = request.form["issueDesc"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO complaints (userID, issueDesc, issueStatus) VALUES (?, ?, 'Pending')", (userID, issueDesc))
    conn.commit()
    conn.close()

    flash("Your complaint has been submitted successfully!", "success")
    return redirect(url_for("dashboard.user_dashboard"))

# Resolve Complaint Route
@dashboard.route("/resolve_complaint", methods=["POST"])
def resolve_complaint():
    if "username" not in session or session["role"] != "admin":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    issueID = request.form["issueID"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE complaints SET issueStatus = 'Resolved' WHERE issueID = ?", (issueID,))
    conn.commit()
    conn.close()

    flash(f"Complaint {issueID} has been resolved.", "success")
    return redirect(url_for("dashboard.admin_dashboard"))

# Bulk Request Items Route (Fixed)
@dashboard.route("/request_items_bulk", methods=["POST"])
def request_items_bulk():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("auth.login"))

    userID = session["userID"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT points FROM users WHERE userID = ?", (userID,))
    userPoints = cursor.fetchone()["points"]

    cursor.execute("SELECT * FROM items WHERE itemQuantity > 0")
    items = cursor.fetchall()

    requested_items = []
    total_cost = 0

    for item in items:
        itemID = item["itemID"]
        quantity_requested = int(request.form.get(f"quantity_{itemID}", 0))

        if quantity_requested > 0:
            itemValue = item["itemValue"]
            itemQuantity = item["itemQuantity"]
            cost = quantity_requested * itemValue

            if quantity_requested > itemQuantity:
                flash(f"Not enough stock for {item['itemName']}.", "danger")
                conn.close()
                return redirect(url_for("dashboard.user_dashboard"))

            requested_items.append((itemID, quantity_requested, item["itemName"], cost))
            total_cost += cost

    if total_cost > userPoints:
        flash("Not enough points for this request.", "danger")
        conn.close()
        return redirect(url_for("dashboard.user_dashboard"))

    if not requested_items:
        flash("No items selected.", "danger")
        conn.close()
        return redirect(url_for("dashboard.user_dashboard"))

    details = "; ".join([f"Requested {q} of {name}" for _, q, name, _ in requested_items])
    cursor.execute("INSERT INTO transactions (userID, action, details, status) VALUES (?, 'Request Item', ?, 'Pending Approval')", (userID, details))

    conn.commit()
    flash("Bulk item request submitted for admin approval.", "success")
    conn.close()
    return redirect(url_for("dashboard.user_dashboard"))

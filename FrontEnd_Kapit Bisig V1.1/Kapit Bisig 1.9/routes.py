from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from backend import execute_query, Item, Admin

dashboard = Blueprint("dashboard", __name__)


# ---------- Helper Functions ---------- #
def is_admin():
    """Checks if the user is an admin."""
    return "username" in session and session.get("role") == "admin"


# ---------- Home Page Route ---------- #
@dashboard.route("/")
def home():
    return render_template("index.html")


# ---------- User Dashboard Route ---------- #
@dashboard.route("/user_dashboard")
def user_dashboard():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("auth.login"))

    user = execute_query("SELECT * FROM users WHERE username = ?", (session["username"],), fetchone=True)
    items = execute_query("SELECT * FROM items WHERE itemQuantity > 0")

    return render_template("user_dashboard.html", user=user, items=items)


# ---------- Admin Dashboard Route ---------- #
@dashboard.route("/admin_dashboard")
def admin_dashboard():
    if not is_admin():
        flash("Unauthorized access.", "danger")
        return redirect(url_for("auth.login"))

    admin = execute_query("SELECT * FROM users WHERE username = ?", (session["username"],), fetchone=True)
    transactions = execute_query("SELECT * FROM transactions ORDER BY timestamp DESC")
    pending_requests = execute_query("SELECT * FROM transactions WHERE status = 'Pending Approval'")
    complaints = execute_query("SELECT * FROM complaints WHERE issueStatus = 'Pending'")

    return render_template("admin_dashboard.html", admin=admin, transactions=transactions, pending_requests=pending_requests, complaints=complaints)


# ---------- Approve & Reject Item Requests ---------- #
@dashboard.route("/approve_request", methods=["POST"])
def approve_request():
    if not is_admin():
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    transactionID = request.form.get("transactionID")
    execute_query("UPDATE transactions SET status = 'Approved' WHERE transactionID = ?", (transactionID,), commit=True)

    flash(f"Transaction {transactionID} has been approved.", "success")
    return redirect(url_for("dashboard.admin_dashboard"))


@dashboard.route("/reject_request", methods=["POST"])
def reject_request():
    if not is_admin():
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    transactionID = request.form.get("transactionID")
    execute_query("UPDATE transactions SET status = 'Rejected' WHERE transactionID = ?", (transactionID,), commit=True)

    flash(f"Request ID {transactionID} has been rejected.", "success")
    return redirect(url_for("dashboard.admin_dashboard"))


# ---------- Add Item Route (Admin Only) ---------- #
@dashboard.route("/add_item", methods=["POST"])
def add_item():
    if not is_admin():
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    itemName = request.form["itemName"]
    itemValue = int(request.form["itemValue"])
    itemQuantity = int(request.form["itemQuantity"])

    # Add item using the backend function
    Item.add_item(session["userID"], itemName, itemValue, itemQuantity)

    flash(f"{itemQuantity} units of {itemName} added successfully!", "success")
    return redirect(url_for("dashboard.admin_dashboard"))


# ---------- File Complaint Route ---------- #
@dashboard.route("/file_complaint", methods=["POST"])
def file_complaint():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("auth.login"))

    userID = session["userID"]
    issueDesc = request.form["issueDesc"]

    execute_query("INSERT INTO complaints (userID, issueDesc, issueStatus) VALUES (?, ?, 'Pending')",
                  (userID, issueDesc), commit=True)

    flash("Your complaint has been submitted successfully!", "success")
    return redirect(url_for("dashboard.user_dashboard"))


# ---------- Resolve Complaint (Admin Only) ---------- #
@dashboard.route("/resolve_complaint", methods=["POST"])
def resolve_complaint():
    if not is_admin():
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    issueID = request.form["issueID"]
    execute_query("UPDATE complaints SET issueStatus = 'Resolved' WHERE issueID = ?", (issueID,), commit=True)

    flash(f"Complaint {issueID} has been resolved.", "success")
    return redirect(url_for("dashboard.admin_dashboard"))


# ---------- Bulk Request Items Route ---------- #
@dashboard.route("/request_items_bulk", methods=["POST"])
def request_items_bulk():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("auth.login"))

    userID = session["userID"]
    userPoints = execute_query("SELECT points FROM users WHERE userID = ?", (userID,), fetchone=True)["points"]
    items = execute_query("SELECT * FROM items WHERE itemQuantity > 0")

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
                return redirect(url_for("dashboard.user_dashboard"))

            requested_items.append((itemID, quantity_requested, item["itemName"], cost))
            total_cost += cost

    if total_cost > userPoints:
        flash("Not enough points for this request.", "danger")
        return redirect(url_for("dashboard.user_dashboard"))

    if not requested_items:
        flash("No items selected.", "danger")
        return redirect(url_for("dashboard.user_dashboard"))

    details = "; ".join([f"Requested {q} of {name}" for _, q, name, _ in requested_items])
    execute_query("INSERT INTO transactions (userID, action, details, status) VALUES (?, 'Request Item', ?, 'Pending Approval')",
                  (userID, details), commit=True)

    flash("Bulk item request submitted for admin approval.", "success")
    return redirect(url_for("dashboard.user_dashboard"))


# ---------- User Donation Request Route ---------- #
@dashboard.route("/request_donation", methods=["POST"])
def request_donation():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("auth.login"))

    userID = session["userID"]
    itemName = request.form["itemName"]
    itemValue = int(request.form["itemValue"])
    itemQuantity = int(request.form["itemQuantity"])

    Item.donate_item(session["userID"], itemName, itemValue, itemQuantity)

    flash("Your donation request is pending admin approval.", "success")
    return redirect(url_for("dashboard.user_dashboard"))


# ---------- Admin Approves Donations ---------- #
@dashboard.route("/approve_donation", methods=["POST"])
def approve_donation():
    if not is_admin():
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    transactionID = request.form["transactionID"]
    admin = Admin(session["userID"], session["username"], "", "", 0, 0, "admin")

    admin.approve_donation(transactionID)

    flash(f"Donation request {transactionID} has been approved.", "success")
    return redirect(url_for("dashboard.admin_dashboard"))

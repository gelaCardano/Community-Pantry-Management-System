from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from backend import execute_query, Item, Admin
import os
from PIL import Image

dashboard = Blueprint("dashboard", __name__)

# Define the upload folder
UPLOAD_FOLDER = 'static/images/items'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the folder exists

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

@dashboard.route("/add_item", methods=["POST"])
def add_item():
    if not is_admin():
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    itemName = request.form["itemName"]
    itemValue = int(request.form["itemValue"])
    itemQuantity = int(request.form["itemQuantity"])

    if 'image' not in request.files:
        flash('No image uploaded', 'error')
        return redirect(url_for('dashboard.admin_dashboard'))

    file = request.files['image']
    
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('dashboard.admin_dashboard'))

    if file and allowed_file(file.filename):
        # Format filename (lowercase, replace spaces with dashes)
        formatted_filename = f"{itemName.replace(' ', '-').lower()}.png"
        filepath = os.path.join(UPLOAD_FOLDER, formatted_filename)

        # Convert image to PNG
        image = Image.open(file)
        image = image.convert("RGB")
        image.save(filepath, "PNG")

    # Add item using execute_query #
    try:
        execute_query(
            "INSERT INTO items (itemName, itemValue, itemQuantity) VALUES (?, ?, ?)",
            (itemName, itemValue, itemQuantity),
            commit=True
        )
        flash(f"{itemQuantity} units of {itemName} added successfully!", "success")
    except:
        flash("Item could not be added. It may already exist.", "danger")

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

    userID = session.get("userID")
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

# ---------- User Request Donation ---------- #
@dashboard.route("/request_donation", methods=["POST"])
def request_donation():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("auth.login"))

    username = session["username"]
    itemName = request.form["itemName"]
    itemValue = int(request.form["itemValue"])
    itemQuantity = int(request.form["itemQuantity"])

    if 'image' not in request.files:
        flash('No image uploaded', 'error')
        return redirect(url_for('dashboard.user_dashboard'))

    file = request.files['image']
    
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('dashboard.user_dashboard'))

    if file and allowed_file(file.filename):
        formatted_filename = f"{itemName.replace(' ', '-').lower()}.png"
        filepath = os.path.join(UPLOAD_FOLDER, formatted_filename)

        image = Image.open(file)
        image = image.convert("RGB")
        image.save(filepath, "PNG")

    else:
        flash("Invalid file type.", "danger")
        return redirect(url_for("dashboard.user_dashboard"))

    try:
        execute_query(
            "INSERT INTO donations (username, itemName, itemValue, itemQuantity, status) VALUES (?, ?, ?, ?, 'Pending')",
        (username, itemName, itemValue, itemQuantity),
        commit=True
    )
        flash("Your donation request has been submitted for admin approval.", "success")
    except Exception as e:
        flash(f"Donation request failed: {str(e)}", "danger")  # Show error
        print(f"Database Error: {e}")  # Print error for debugging

    return redirect(url_for("dashboard.user_dashboard"))

# ---------- Admin Approves Donation ---------- #
@dashboard.route("/approve_donation", methods=["POST"])
def approve_donation():
    if not is_admin():
        flash("Unauthorized action.", "danger")
        return redirect(url_for("auth.login"))

    donationID = request.form["donationID"]

    donation = execute_query("SELECT * FROM donations WHERE donationID = ?", (donationID,), fetchone=True)
    if not donation:
        flash("Donation request not found.", "danger")
        return redirect(url_for("dashboard.admin_dashboard"))

    itemName = donation["itemName"]
    itemValue = donation["itemValue"]
    itemQuantity = donation["itemQuantity"]
    imagePath = donation["imagePath"]

    try:
        execute_query(
            "INSERT INTO items (itemName, itemValue, itemQuantity) VALUES (?, ?, ?)",
            (itemName, itemValue, itemQuantity),
            commit=True
        )

        execute_query(
            "UPDATE donations SET status = 'Approved' WHERE donationID = ?",
            (donationID,),
            commit=True
        )

        flash(f"Donation {donationID} approved. {itemQuantity} units of {itemName} added to inventory.", "success")
    except:
        flash("Failed to approve donation.", "danger")

    return redirect(url_for("dashboard.admin_dashboard"))
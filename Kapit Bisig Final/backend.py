import sqlite3
import os
from passlib.hash import bcrypt
from werkzeug.utils import secure_filename

DB_NAME = "kapitbisig.db"
UPLOAD_FOLDER = "static/images/items"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# ---------- Database Connection ---------- #
def get_db_connection():
    """Establishes and returns a database connection."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Enables dict-like row access
    return conn


def execute_query(query, params=(), commit=False, fetchone=False):
    """Executes a query and optionally commits or fetches results."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
            return cursor.fetchone() if fetchone else cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database Error: {e}")
        return None


# ---------- Helper Functions ---------- #
def allowed_file(filename):
    """Checks if the uploaded file type is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def assign_missing_item_images():
    """Automatically assigns image filenames to pre-existing items without an image."""
    items = execute_query("SELECT itemID, itemName FROM items WHERE itemImage IS NULL OR itemImage = ''")

    for item in items:
        itemID, itemName = item
        image_filename = itemName.lower().replace(" ", "-") + ".png"

        execute_query(
            "UPDATE items SET itemImage = ? WHERE itemID = ?",
            (image_filename, itemID),
            commit=True
        )

    if items:
        print("Missing item images assigned successfully!")


# ---------- User Management ---------- #
class User:
    """Represents a user fetched from the database."""

    def __init__(self, userID, username, lastName, firstName, salary, points, role):
        self.userID = userID
        self.username = username
        self.lastName = lastName
        self.firstName = firstName
        self.salary = salary
        self.points = points
        self.role = role  # Either "client" or "admin"

    def __str__(self):
        return f"{self.firstName} {self.lastName} (Username: {self.username}) - Role: {self.role}, Points: {self.points}"


# ---------- Item Management ---------- #
class Item:
    """Handles pantry items, including requests and donations."""

    @staticmethod
    def view_items():
        """Displays available items."""
        items = execute_query("SELECT * FROM items")
        return items if items else []

    @staticmethod
    def request_item(user, itemID, quantity):
        """Logs an item request for admin approval."""
        item = execute_query(
            "SELECT itemName, itemValue, itemQuantity FROM items WHERE itemID = ?",
            (itemID,), fetchone=True
        )

        if not item:
            return "Item not found."

        itemName, itemValue, itemQuantity = item
        totalCost = itemValue * quantity

        if itemQuantity < quantity:
            return "Not enough stock."
        elif user.points < totalCost:
            return "Insufficient points."

        execute_query(
            "INSERT INTO transactions (userID, action, details, status) VALUES (?, 'Request Item', ?, 'Pending Approval')",
            (user.userID, f"Requested {quantity} of {itemName}"), commit=True
        )

        return "Item request submitted for admin approval."

    @staticmethod
    def donate_item(userID, itemName, itemValue, itemQuantity, imageFile):
        """Logs a donation request for admin approval with an uploaded image."""
        if not allowed_file(imageFile.filename):
            print("DEBUG: Invalid file format detected.")
            return "Invalid file format."

        filename = secure_filename(imageFile.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        imageFile.save(file_path)
        print(f"DEBUG: Image saved at {file_path}")

        execute_query(
            "INSERT INTO donation_requests (userID, itemName, itemValue, itemQuantity, itemImage, status) "
            "VALUES (?, ?, ?, ?, ?, 'Pending Approval')",
            (userID, itemName, itemValue, itemQuantity, filename), commit=True
        )

        print("DEBUG: Donation successfully inserted into the database.")
        return "Your donation request is pending admin approval."


# ---------- Admin Management ---------- #
class Admin(User):
    """Admin inherits from User and can resolve complaints and approve donations."""

    def resolve_issue(self, issueID):
        """Resolves a complaint by updating its status."""
        execute_query(
            "UPDATE complaints SET issueStatus = 'Resolved' WHERE issueID = ?",
            (issueID,), commit=True
        )
        print(f"Complaint {issueID} resolved.")

    def approve_donation(self, transactionID):
        """Admin approves donation, adds item to inventory, logs the transaction, and rewards the user."""
        donation = execute_query(
            "SELECT userID, itemName, itemValue, itemQuantity, itemImage FROM donation_requests WHERE id = ? AND status = 'Pending Approval'",
            (transactionID,), fetchone=True
        )

        if not donation:
            return "Invalid donation request or already processed."

        userID, itemName, itemValue, itemQuantity, itemImage = donation

        # Check if the item already exists
        existing_item = execute_query(
            "SELECT itemID FROM items WHERE itemName = ?", (itemName,), fetchone=True
        )

        if existing_item:
            execute_query(
                "UPDATE items SET itemQuantity = itemQuantity + ? WHERE itemName = ?",
                (itemQuantity, itemName), commit=True
            )
        else:
            execute_query(
                "INSERT INTO items (itemName, itemValue, itemQuantity, itemImage) VALUES (?, ?, ?, ?)",
                (itemName, itemValue, itemQuantity, itemImage), commit=True
            )

        # Grant points to user
        earned_points = itemValue * itemQuantity
        execute_query(
            "UPDATE users SET points = points + ? WHERE userID = ?",
            (earned_points, userID), commit=True
        )

        # Log the approved donation as a transaction
        execute_query(
            "INSERT INTO transactions (userID, action, details, status) VALUES (?, 'Donation', ?, 'Approved')",
            (userID, f"Donated {itemQuantity} of {itemName}"), commit=True
        )

        # Mark the donation request as approved
        execute_query(
            "UPDATE donation_requests SET status = 'Approved' WHERE id = ?",
            (transactionID,), commit=True
        )

        return f"Donation approved! {earned_points} points awarded to user {userID}."


# ---------- Complaint System ---------- #
class Complaint:
    """Handles user complaints."""

    def __init__(self, user, issueDesc):
        self.user = user
        self.issueDesc = issueDesc
        self.issueID = self._file_complaint()

    def _file_complaint(self):
        """Files a complaint and logs it."""
        execute_query(
            "INSERT INTO complaints (userID, issueDesc) VALUES (?, ?)",
            (self.user.userID, self.issueDesc), commit=True
        )
        issueID = execute_query("SELECT last_insert_rowid()", fetchone=True)[0]

        execute_query(
            "INSERT INTO transactions (userID, action, details, status) VALUES (?, 'File Complaint', ?, 'Pending')",
            (self.user.userID, f"Complaint ID {issueID}: {self.issueDesc}"), commit=True
        )

        return issueID


# ---------- Authentication System ---------- #
def signup(username, password, firstName, lastName, salary, role):
    """Handles user registration."""
    hashed_password = bcrypt.hash(password)

    execute_query(
        "INSERT INTO users (username, password, lastName, firstName, salary, points, role) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (username, hashed_password, lastName, firstName, salary, 2000, role), commit=True
    )
    return "Signup successful! You can now log in."


# Run image assignment when the backend starts
assign_missing_item_images()

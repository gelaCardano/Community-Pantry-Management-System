import sqlite3
from passlib.hash import bcrypt

DB_NAME = "kapitbisig.db"


# ---------- Database Connection ---------- #
def get_db_connection():
    """Establishes and returns a database connection."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Enables dict-like row access
    return conn


def execute_query(query, params=(), commit=False, fetchone=False):
    """Executes a query and optionally commits or fetches results."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            conn.commit()
        return cursor.fetchone() if fetchone else cursor.fetchall()


# ---------- User Management ---------- #
class UserFromDB:
    """Represents an existing user fetched from the database."""
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


class Admin(UserFromDB):
    """Admin inherits from User and can resolve complaints and approve donations."""
    def resolve_issue(self, issueID):
        """Resolves a complaint by updating its status."""
        execute_query(
            "UPDATE complaints SET issueStatus = 'Resolved' WHERE issueID = ?",
            (issueID,), commit=True
        )
        print(f"Complaint {issueID} resolved.")

    def approve_donation(self, transactionID):
        """Admin approves donation and adds item to inventory while rewarding user."""
        donation = execute_query(
            "SELECT userID, details FROM transactions WHERE transactionID = ? AND action = 'Donate Item' AND status = 'Pending Approval'",
            (transactionID,), fetchone=True
        )

        if not donation:
            print("Invalid donation request or already processed.")
            return

        userID, details = donation
        details_parts = details.split(" ")
        itemQuantity = int(details_parts[3])
        itemName = details_parts[5]
        itemValue = int(details_parts[-3])

        # Check if item exists
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
                "INSERT INTO items (itemName, itemValue, itemQuantity) VALUES (?, ?, ?)",
                (itemName, itemValue, itemQuantity), commit=True
            )

        # Grant points to user
        earned_points = itemValue * itemQuantity
        execute_query(
            "UPDATE users SET points = points + ? WHERE userID = ?",
            (earned_points, userID), commit=True
        )

        # Mark transaction as approved
        execute_query(
            "UPDATE transactions SET status = 'Approved' WHERE transactionID = ?",
            (transactionID,), commit=True
        )

        print(f"Donation approved! {earned_points} points awarded to user {userID}.")


# ---------- Item Management ---------- #
class Item:
    """Handles pantry items, including requests and donations."""

    @staticmethod
    def view_items():
        """Displays available items."""
        items = execute_query("SELECT * FROM items")
        if not items:
            print("No items available.")
        else:
            print("\n=== Available Items ===")
            for item in items:
                print(f"Item ID: {item['itemID']} | Name: {item['itemName']} | "
                      f"Value: {item['itemValue']} points | Quantity: {item['itemQuantity']}")

    @staticmethod
    def request_item(user, itemID, quantity):
        """Processes an item request from users."""
        item = execute_query(
            "SELECT itemName, itemValue, itemQuantity FROM items WHERE itemID = ?",
            (itemID,), fetchone=True
        )

        if not item:
            print("Item not found.")
            return

        itemName, itemValue, itemQuantity = item
        totalCost = itemValue * quantity

        if itemQuantity < quantity:
            print("Not enough stock.")
        elif user.points < totalCost:
            print("Insufficient points.")
        else:
            execute_query("UPDATE users SET points = points - ? WHERE userID = ?", (totalCost, user.userID), commit=True)
            execute_query("UPDATE items SET itemQuantity = itemQuantity - ? WHERE itemID = ?", (quantity, itemID), commit=True)

            execute_query(
                "INSERT INTO transactions (userID, action, details, status) VALUES (?, 'Request Item', ?, 'Pending Approval')",
                (user.userID, f"Requested {quantity} of {itemName}"), commit=True
            )

            print("Item request successful!")

    @staticmethod
    def donate_item(user, itemName, itemValue, itemQuantity):
        """Allows users to request to donate items (pending admin approval)."""

        execute_query(
            "INSERT INTO transactions (userID, action, details, status) VALUES (?, 'Donate Item', ?, 'Pending Approval')",
            (user.userID, f"Requested to donate {itemQuantity} of {itemName} (Value: {itemValue} points each)"),
            commit=True
        )

        print(f"Your donation request for {itemQuantity} units of {itemName} is pending admin approval.")


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

        print("Complaint filed successfully.")
        return issueID


# ---------- Authentication System ---------- #
def signup():
    """Handles user registration."""
    username = input("Enter a username: ")
    password = input("Enter a password: ")
    confirm_password = input("Re-enter your password: ")

    if password != confirm_password:
        print("Passwords do not match!")
        return None

    firstName = input("Enter your first name: ")
    lastName = input("Enter your last name: ")
    salary = int(input("Enter your salary: "))

    role = input("Enter role (client/admin): ").strip().lower()
    if role not in ["client", "admin"]:
        print("Invalid role! Choose 'client' or 'admin'.")
        return None

    hashed_password = bcrypt.hash(password)
    initial_points = 5000 if salary < 10000 else 4000 if salary < 20000 else 3000 if salary < 30000 else 2000 if salary < 40000 else 1000

    try:
        execute_query(
            "INSERT INTO users (username, password, lastName, firstName, salary, points, role) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username, hashed_password, lastName, firstName, salary, initial_points, role), commit=True
        )
        print("Signup successful! You can now log in.")
    except sqlite3.IntegrityError:
        print("Username already exists. Please choose another one.")

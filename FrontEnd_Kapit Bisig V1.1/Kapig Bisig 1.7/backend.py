
import sqlite3
from passlib.hash import bcrypt

# ---------- Database Initialization ----------
conn = sqlite3.connect("kapitbisig.db", check_same_thread=False)
cursor = conn.cursor()

# Users table with password storage and roles
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    userID INTEGER PRIMARY KEY AUTOINCREMENT, 
    username TEXT UNIQUE, 
    password TEXT, 
    lastName TEXT, 
    firstName TEXT, 
    salary INTEGER, 
    points INTEGER,
    role TEXT CHECK(role IN ('client', 'admin')) NOT NULL)''')

# Items table
cursor.execute('''CREATE TABLE IF NOT EXISTS items (
    itemID INTEGER PRIMARY KEY AUTOINCREMENT, 
    itemName TEXT UNIQUE,
    itemValue INTEGER,
    itemQuantity INTEGER)''')

# Complaints table
cursor.execute('''CREATE TABLE IF NOT EXISTS complaints (
    issueID INTEGER PRIMARY KEY AUTOINCREMENT, 
    userID INTEGER, 
    issueDesc TEXT, 
    issueStatus TEXT DEFAULT 'Pending', 
    FOREIGN KEY (userID) REFERENCES users(userID))''')

# Transactions table (NEWLY ADDED)
cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
    transactionID INTEGER PRIMARY KEY AUTOINCREMENT,
    userID INTEGER,
    action TEXT CHECK(action IN ('Add Item', 'Request Item', 'File Complaint', 'Resolve Complaint')),
    details TEXT,
    status TEXT DEFAULT 'Pending',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userID) REFERENCES users(userID))''')

conn.commit()


# ---------- Class Definitions ----------
class UserFromDB:
    """Represents an existing user fetched from the database (does not insert new records)."""
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


class Item:
    """Class to handle pantry items."""
    
    @staticmethod
    def view_items():
        cursor.execute("SELECT * FROM items")
        items = cursor.fetchall()
        if not items:
            print("No items available.")
        else:
            print("\n=== Available Items ===")
            for item in items:
                print(f"Item ID: {item[0]} | Name: {item[1]} | Value: {item[2]} points | Quantity: {item[3]}")

    @staticmethod
    def add_item(user, itemName, itemValue, itemQuantity):
        cursor.execute("SELECT itemID FROM items WHERE itemName = ?", (itemName,))
        itemExists = cursor.fetchone()

        if itemExists:
            cursor.execute("UPDATE items SET itemQuantity = itemQuantity + ? WHERE itemName = ?", (itemQuantity, itemName))
        else:
            cursor.execute("INSERT INTO items (itemName, itemValue, itemQuantity) VALUES (?, ?, ?)",
                        (itemName, itemValue, itemQuantity))
        conn.commit()

        # Log transaction
        cursor.execute("INSERT INTO transactions (userID, action, details, status) VALUES (?, 'Add Item', ?, 'Completed')",
                    (user.userID, f"Added {itemQuantity} of {itemName}"))
        conn.commit()
        print(f"{itemQuantity} units of {itemName} added successfully!")


    @staticmethod
    def request_item(user, itemID, quantity):
        cursor.execute("SELECT itemName, itemValue, itemQuantity FROM items WHERE itemID = ?", (itemID,))
        item = cursor.fetchone()

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
            user.points -= totalCost
            cursor.execute("UPDATE users SET points = ? WHERE userID = ?", (user.points, user.userID))
            cursor.execute("UPDATE items SET itemQuantity = itemQuantity - ? WHERE itemID = ?", (quantity, itemID))
            conn.commit()

            # Log transaction
            cursor.execute("INSERT INTO transactions (userID, action, details) VALUES (?, 'Request Item', ?)",
                        (user.userID, f"Requested {quantity} of {itemName}"))
            conn.commit()

            print("Item request successful!")


class Admin(UserFromDB):
    def resolve_issue(self):
        """Allows only an admin to resolve complaints."""
        cursor.execute("SELECT * FROM complaints WHERE issueStatus = 'Pending'")
        complaints = cursor.fetchall()

        if not complaints:
            print("No pending complaints.")
            return

        print("\nPending Complaints:")
        for complaint in complaints:
            print(f"ID: {complaint[0]}, UserID: {complaint[1]}, Issue: {complaint[2]}, Status: {complaint[3]}")

        issueID = int(input("\nEnter Complaint ID to resolve (or 0 to cancel): "))
        if issueID == 0:
            return

        cursor.execute("UPDATE complaints SET issueStatus = 'Resolved' WHERE issueID = ?", (issueID,))
        conn.commit()
        print(f"Complaint {issueID} has been resolved.")


class Complaint:
    def __init__(self, user, issueDesc):
        self.user = user
        self.issueDesc = issueDesc

        cursor.execute("INSERT INTO complaints (userID, issueDesc) VALUES (?, ?)", (self.user.userID, self.issueDesc))
        conn.commit()
        self.issueID = cursor.lastrowid

        # Log transaction
        cursor.execute("INSERT INTO transactions (userID, action, details) VALUES (?, 'File Complaint', ?)",
                       (user.userID, f"Complaint ID {self.issueID}: {issueDesc}"))
        conn.commit()

        print("Complaint filed successfully.")

    def resolve_issue(self):
        cursor.execute("SELECT * FROM complaints WHERE issueStatus = 'Pending'")
        complaints = cursor.fetchall()

        if not complaints:
            print("No pending complaints.")
            return

        print("\nPending Complaints:")
        for complaint in complaints:
            print(f"ID: {complaint[0]}, UserID: {complaint[1]}, Issue: {complaint[2]}, Status: {complaint[3]}")

        issueID = int(input("\nEnter Complaint ID to resolve (or 0 to cancel): "))
        if issueID == 0:
            return

        cursor.execute("UPDATE complaints SET issueStatus = 'Resolved' WHERE issueID = ?", (issueID,))
        conn.commit()

        # Log transaction
        cursor.execute("INSERT INTO transactions (userID, action, details, status) VALUES (?, 'Resolve Complaint', ?, 'Completed')",
                       (self.userID, f"Resolved Complaint ID {issueID}"))
        conn.commit()

        print(f"Complaint {issueID} has been resolved.")


# ---------- Authentication System ----------
def signup():
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
        cursor.execute("INSERT INTO users (username, password, lastName, firstName, salary, points, role) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (username, hashed_password, lastName, firstName, salary, initial_points, role))
        conn.commit()
        print("Signup successful! You can now log in.")
    except sqlite3.IntegrityError:
        print("Username already exists. Please choose another one.")


def login():
    username = input("Enter username: ")
    password = input("Enter password: ")

    cursor.execute("SELECT userID, password, lastName, firstName, salary, points, role FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()

    if result and bcrypt.verify(password, result[1]):
        userID, _, lastName, firstName, salary, points, role = result
        print(f"\nLogin successful! Welcome, {username} (Role: {role})")

        if role == "admin":
            return Admin(userID, username, lastName, firstName, salary, points, role)
        return UserFromDB(userID, username, lastName, firstName, salary, points, role)
    else:
        print("Invalid username or password.")
        return None


# ---------- Dashboards ----------
def user_dashboard(user):
    while True:
        print("\n=== User Dashboard ===")
        print("1. View Available Items")
        print("2. Request Item")
        print("3. File Complaint")
        print("4. Logout")
        choice = input("Enter choice: ")

        if choice == "1":
            cursor.execute("SELECT * FROM items")
            items = cursor.fetchall()
            print("\n=== Available Items ===")
            for item in items:
                print(f"Item ID: {item[0]} | Name: {item[1]} | Value: {item[2]} points | Quantity: {item[3]}")
        
        elif choice == "2":
            itemID = int(input("Enter Item ID to request: "))
            quantity = int(input("Enter quantity: "))

            cursor.execute("SELECT itemValue, itemQuantity FROM items WHERE itemID = ?", (itemID,))
            item = cursor.fetchone()

            if not item:
                print("Item not found.")
                continue

            itemValue, itemQuantity = item
            totalCost = itemValue * quantity

            if itemQuantity < quantity:
                print("Not enough stock.")
            elif user.points < totalCost:
                print("Insufficient points.")
            else:
                user.points -= totalCost
                cursor.execute("UPDATE users SET points = ? WHERE userID = ?", (user.points, user.userID))
                cursor.execute("UPDATE items SET itemQuantity = itemQuantity - ? WHERE itemID = ?", (quantity, itemID))
                conn.commit()
                print("Item request successful!")

        elif choice == "3":
            issueDesc = input("Enter your complaint: ")
            Complaint(user, issueDesc)
            print("Complaint filed successfully.")

        elif choice == "4":
            print("Logging out...")
            break

        else:
            print("Invalid choice, try again.")


def admin_dashboard(admin):
    while True:
        print("\n=== Admin Dashboard ===")
        print("1. View All Transactions")
        print("2. Add Item to Pantry")
        print("3. View & Resolve Complaints")
        print("4. Logout")
        choice = input("Enter choice: ")

        if choice == "1":
            cursor.execute("SELECT transactionID, userID, action, details, status, timestamp FROM transactions ORDER BY timestamp DESC")
            transactions = cursor.fetchall()

            if not transactions:
                print("No transactions recorded.")
            else:
                print("\n=== Transactions ===")
                for trans in transactions:
                    print(f"Transaction ID: {trans[0]}, User ID: {trans[1]}, Action: {trans[2]}, Details: {trans[3]}, Status: {trans[4]}, Timestamp: {trans[5]}")

        elif choice == "2":
            itemName = input("Enter item name: ")
            itemValue = int(input("Enter item value in points: "))
            itemQuantity = int(input("Enter quantity: "))
            Item.add_item(admin, itemName, itemValue, itemQuantity)

        elif choice == "3":
            admin.resolve_issue()

        elif choice == "4":
            print("Logging out...")
            break

        else:
            print("Invalid choice, try again.")
            

# ---------- Main Program ----------
if __name__ == "__main__":
    print("Welcome to Kapit-Bisig Online Community Pantry!")
    
    while True:
        print("\n1. Sign Up")
        print("2. Log In")
        print("3. Exit")
        choice = input("Enter choice: ")

        if choice == "1":
            signup()
        elif choice == "2":
            user = login()
            if user:
                if user.role == "admin":
                    admin_dashboard(user)
                else:
                    user_dashboard(user)
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid choice, try again.")

import sqlite3

def init_db():
    with sqlite3.connect("kapitbisig.db") as conn:
        cursor = conn.cursor()

        # Users Table
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            userID INTEGER PRIMARY KEY AUTOINCREMENT, 
            username TEXT UNIQUE, 
            password TEXT, 
            lastName TEXT, 
            firstName TEXT, 
            salary INTEGER, 
            points INTEGER,
            role TEXT CHECK(role IN ('client', 'admin')) NOT NULL)''')

        # Items Table (Ensure itemImage column exists)
        cursor.execute('''CREATE TABLE IF NOT EXISTS items (
            itemID INTEGER PRIMARY KEY AUTOINCREMENT, 
            itemName TEXT UNIQUE,
            itemValue INTEGER,
            itemQuantity INTEGER)''')  # Creating without itemImage first

        # Check if `itemImage` column exists, if not, add it
        cursor.execute("PRAGMA table_info(items)")
        columns = [col[1] for col in cursor.fetchall()]
        if "itemImage" not in columns:
            cursor.execute("ALTER TABLE items ADD COLUMN itemImage TEXT")
            print("Added missing column: itemImage")

        # Complaints Table
        cursor.execute('''CREATE TABLE IF NOT EXISTS complaints (
            issueID INTEGER PRIMARY KEY AUTOINCREMENT, 
            userID INTEGER, 
            issueDesc TEXT, 
            issueStatus TEXT DEFAULT 'Pending', 
            FOREIGN KEY (userID) REFERENCES users(userID))''')

        # Transactions Table
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
            transactionID INTEGER PRIMARY KEY AUTOINCREMENT,
            userID INTEGER,
            action TEXT CHECK(action IN ('Add Item', 'Request Item', 'File Complaint', 'Resolve Complaint')),
            details TEXT,
            status TEXT DEFAULT 'Pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (userID) REFERENCES users(userID))''')

        # Ensure `donation_requests` Table Exists
        cursor.execute("PRAGMA table_info(donation_requests)")
        donation_columns = [col[1] for col in cursor.fetchall()]

        if not donation_columns:  # Table does not exist, create it
            print("`donation_requests` table is missing. Creating it now...")
            cursor.execute('''CREATE TABLE donation_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                userID INTEGER, 
                itemName TEXT, 
                itemValue INTEGER, 
                itemQuantity INTEGER, 
                itemImage TEXT,  
                status TEXT DEFAULT 'Pending Approval', 
                FOREIGN KEY (userID) REFERENCES users(userID))''')
            print("Created `donation_requests` table.")

        conn.commit()
        print("✅ Database initialized successfully!")

if __name__ == "__main__":
    init_db()

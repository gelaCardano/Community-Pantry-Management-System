import sqlite3

def init_db():
    with sqlite3.connect("kapitbisig.db") as conn:
        cursor = conn.cursor()

        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            userID INTEGER PRIMARY KEY AUTOINCREMENT, 
            username TEXT UNIQUE, 
            password TEXT, 
            lastName TEXT, 
            firstName TEXT, 
            salary INTEGER, 
            points INTEGER,
            role TEXT CHECK(role IN ('client', 'admin')) NOT NULL)''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS items (
            itemID INTEGER PRIMARY KEY AUTOINCREMENT, 
            itemName TEXT UNIQUE,
            itemValue INTEGER,
            itemQuantity INTEGER)''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS complaints (
            issueID INTEGER PRIMARY KEY AUTOINCREMENT, 
            userID INTEGER, 
            issueDesc TEXT, 
            issueStatus TEXT DEFAULT 'Pending', 
            FOREIGN KEY (userID) REFERENCES users(userID))''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
            transactionID INTEGER PRIMARY KEY AUTOINCREMENT,
            userID INTEGER,
            action TEXT CHECK(action IN ('Add Item', 'Request Item', 'File Complaint', 'Resolve Complaint')),
            details TEXT,
            status TEXT DEFAULT 'Pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (userID) REFERENCES users(userID))''')

        conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")

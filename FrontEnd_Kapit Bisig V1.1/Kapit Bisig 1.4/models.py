import sqlite3
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(query, args=(), one=False):
    with get_db_connection() as conn:
        cursor = conn.execute(query, args)
        result = cursor.fetchall()
        return (result[0] if result else None) if one else result

import sqlite3
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
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

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  # Or your actual DB config

db = SQLAlchemy(app)  # Initialize SQLAlchemy

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    reset_token = db.Column(db.String(64), nullable=True)
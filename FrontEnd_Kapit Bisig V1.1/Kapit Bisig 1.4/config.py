import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your_fallback_secret_key")
    DATABASE = "kapitbisig.db"

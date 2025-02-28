from flask import Flask
from config import Config
from auth import auth
from routes import dashboard

app = Flask(__name__)
app.config.from_object(Config)

# ✅ Register blueprints correctly
app.register_blueprint(auth, url_prefix="/auth")  # All auth routes start with /auth
app.register_blueprint(dashboard)  # Dashboard and homepage routes

if __name__ == "__main__":
    app.run(debug=True)

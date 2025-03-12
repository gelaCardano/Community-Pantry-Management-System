from flask import Flask
from config import Config
from auth import auth
from routes import dashboard
from backend import assign_missing_item_images  # Import image assignment function

app = Flask(__name__)
app.config.from_object(Config)

# Run image assignment for pre-existing items
assign_missing_item_images()

# Register blueprints
app.register_blueprint(auth, url_prefix="/auth")  # All auth routes start with /auth
app.register_blueprint(dashboard)  # Dashboard and homepage routes

if __name__ == "__main__":
    app.run(debug=True)

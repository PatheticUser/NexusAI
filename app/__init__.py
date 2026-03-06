import os
from flask import Flask


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-prod")

    from .routes import bp

    app.register_blueprint(bp)

    return app

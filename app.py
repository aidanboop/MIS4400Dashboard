"""
Flask application entry point.

Run with:
    python app.py
"""

from flask import Flask
from api.routes import bp as api_bp
import config

app = Flask(__name__)
app.register_blueprint(api_bp, url_prefix="/api")


if __name__ == "__main__":
    app.run(debug=config.FLASK_DEBUG, port=config.FLASK_PORT)

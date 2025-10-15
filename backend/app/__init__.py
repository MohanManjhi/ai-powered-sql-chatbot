from flask import Flask
from flask_cors import CORS
import os

def create_app():
    app = Flask(__name__)
    
    # Configure CORS to allow frontend requests (dev + production)
    frontend_origin = os.getenv("FRONTEND_ORIGIN")
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    if frontend_origin:
        allowed_origins.append(frontend_origin)

    CORS(app, resources={
        "/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    from .routes import main
    app.register_blueprint(main)

    return app

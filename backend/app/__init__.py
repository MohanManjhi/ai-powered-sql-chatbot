from flask import Flask, jsonify
from flask_cors import CORS
import os
from app.utils.json_encoder import MongoJSONEncoder

def create_app():
    app = Flask(__name__)
    
    # Configure custom JSON encoder for MongoDB serialization
    app.json_encoder = MongoJSONEncoder
    
    # Configure CORS to allow frontend requests (dev + production)
    frontend_origin = os.getenv("FRONTEND_ORIGIN")
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    if frontend_origin:
        allowed_origins.append(frontend_origin)

    # For development ease, enable CORS globally for the app. In production,
    # restrict origins to the known frontend origins above.
    CORS(app)

    # Register blueprints
    from .routes import main
    app.register_blueprint(main)

    # Test JSON encoder with a dummy route
    @app.route('/test')
    def test():
        from bson import ObjectId
        return jsonify({"id": ObjectId()})

    return app

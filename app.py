from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
from flask_jwt_extended import JWTManager
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from routes.members import members_bp
from routes.auth import auth_bp
from routes.teams import teams_bp

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = "super-secret"
    JWTManager(app)

    CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

    app.register_blueprint(members_bp, url_prefix="/members")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(teams_bp, url_prefix="/teams")

    app.config["DEBUG"] = False

    return app


application = create_app()

# This block will only run when you execute app.py directly
if __name__ == "__main__":
    with application.app_context():
        application.run(
            host=os.getenv("APP_HOST", "0.0.0.0"),
            port=int(os.getenv("APP_PORT", 8000)),
        )

from flask import Flask
from flask_cors import CORS
from routes.views.admin import api
from dotenv import load_dotenv
import os
from flask_jwt_extended import JWTManager

load_dotenv()


def create_app():
    app = Flask(__name__)
    jwt = JWTManager(app)
    cors = CORS(
        app, resources={r"/api/*": {"origins": "http://localhost:3000"}}
    )
    app.register_blueprint(api, url_prefix="/api")
    app.config["DEBUG"] = False
    app.config["JWT_SECRET_KEY"] = "super-secret"

    return app


application = create_app()

# This block will only run when you execute app.py directly
if __name__ == "__main__":
    with application.app_context():
        application.run(
            host=os.getenv("APP_HOST", "0.0.0.0"),
            port=int(os.getenv("APP_PORT", 8000)),
        )

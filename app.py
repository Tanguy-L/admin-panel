from flask import Flask
from routes.views.admin import api
from dotenv import load_dotenv
import os

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.register_blueprint(api, url_prefix="/api")
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

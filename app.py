from flask import Flask, redirect
from routes.views import admin
from dotenv import load_dotenv
import os

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.register_blueprint(admin.views)
    app.config['DEBUG'] = False

    @app.route("/")
    def redirect_to_admin():
        return redirect("/admin")

    return app


# This block will only run when you execute app.py directly
if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        app.run(host=os.getenv('APP_HOST', '0.0.0.0'),
                port=os.getenv('APP_PORT', 5000))

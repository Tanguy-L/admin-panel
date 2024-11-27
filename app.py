from flask import Flask, redirect
from routes.views import admin
from core.settings import get_conf

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
        app_conf = get_conf()["app"]
        app.run(host=app_conf["host"], port=app_conf["port"])
import os
import urllib.parse

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

db = SQLAlchemy()


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

    db_user     = os.environ["DB_USER"]
    db_password = urllib.parse.quote_plus(os.environ["DB_PASSWORD"])
    db_host     = os.environ["DB_HOST"]
    db_port     = os.environ.get("DB_PORT", "5432")
    db_name     = os.environ["DB_NAME"]

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # ------------------------------------------------------------------
    # Flask-Login
    # ------------------------------------------------------------------
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    from models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    # ------------------------------------------------------------------
    # Blueprints
    # ------------------------------------------------------------------
    from auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from search import search as search_blueprint
    app.register_blueprint(search_blueprint)

    # ------------------------------------------------------------------
    # Error handlers
    # ------------------------------------------------------------------
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f"500 error: {e}")
        return render_template("500.html"), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("404.html"), 403  # show 404 to avoid leaking route info

    return app
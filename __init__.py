from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os
import urllib

load_dotenv()  # Load variables from .env file



# init SQLAlchemy so we can use it later in our models
db = SQLAlchemy()
def create_app():
    app = Flask(__name__) # creates the Flask instance, __name__ is the name of the current Python module

    app.config['SECRET_KEY'] =  os.environ['SECRET_KEY'] # it is used by Flask and extensions to keep data safe. Generated using os.urandom(24).hex()
    # MySQL connection via PyMySQL
    db_user = os.environ['DB_USER']
    db_password = urllib.parse.quote_plus(os.environ['DB_PASSWORD'])
    db_host = os.environ['DB_HOST']
    db_port = os.environ.get('DB_PORT', '3306')
    db_name = os.environ['DB_NAME']

    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )  # TODO: make modular function, reuse in apiCall.py

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # deactivate Flask-SQLAlchemy track modifications. Uses memory and not needed unless you use models_committed 
    
    db.init_app(app) # Initialiaze MSSQL database
    # The login manager contains the code that lets your application and Flask-Login work together
    
    login_manager = LoginManager() # Create a Login Manager instance
    login_manager.login_view = 'auth.login' # define the redirection path when login required and we attempt to access without being logged in
    login_manager.init_app(app) # configure it for login
    
    from models import UserAccount
    @login_manager.user_loader
    def load_user(user_id): # reload user object from the user ID stored in the session
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return db.session.get(UserAccount, int(user_id))  # (db.session.get is a simple PK lookup, not an ORM query, so it is fine).
    
    # blueprint for auth routes in our app
    # blueprint allow you to organize your flask app
    from auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    
    # blueprint for non-auth parts of app
    from main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from search import search as search_blueprint
    app.register_blueprint(search_blueprint)

    return app
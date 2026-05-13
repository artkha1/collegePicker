from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import UserAccount, UserResponse
from flask_login import login_user, logout_user, login_required
from __init__ import db
from sqlalchemy import text


auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method=='GET':
        return render_template('login.html')
    else:
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
    # Raw SQL: look up the user by email
    row = db.session.execute(
        text("SELECT id, password FROM user_accounts WHERE email = :email"),
        {"email": email},
    ).mappings().one_or_none()
 
    if not row:
        flash('Please sign up first!')
        return redirect(url_for('auth.signup'))
 
    if not check_password_hash(row['password'], password):
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login'))
 
    # Flask-Login still needs a UserAccount object - fetch it via primary key
    # (db.session.get is a simple PK lookup, not an ORM query, so it is fine).
    user = db.session.get(UserAccount, row['id'])
    login_user(user, remember=remember)
 
    # Keep response_id in the Flask session so anonymous→logged-in code paths
    # can share the same get_user_prefs() helper.
    session['response_id'] = row['id']
 
    return redirect(url_for('main.welcome'))
 

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method=='GET':
        return render_template('signup.html')
    else:
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
    
    # Raw SQL: check whether email is already registered
    existing = db.session.execute(
        text("SELECT id FROM user_accounts WHERE email = :email"),
        {"email": email},
    ).mappings().one_or_none()
 
    if existing:
        flash('Email address already exists')
        return redirect(url_for('auth.signup'))
 
    # Raw SQL: insert a blank user_responses row first (auto-increment gives us the id)
    db.session.execute(
        text(
            "INSERT INTO user_responses "
            "(relImp, sizeImp, allMajors, satMath, satEng, act, "
            " settingImp, regionImp, stateImp, income) "
            "VALUES (NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL)"
        )
    )
    # Retrieve the auto-generated id
    new_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
 
    # Raw SQL: insert the user account row using the same id
    db.session.execute(
        text(
            "INSERT INTO user_accounts (id, email, name, password) "
            "VALUES (:id, :email, :name, :password)"
        ),
        {
            "id": new_id,
            "email": email,
            "name": name,
            "password": generate_password_hash(password),
        },
    )
    db.session.commit()
 
    return redirect(url_for('auth.login'))

@auth.route('/logout')
@login_required
def logout():
    # Clear the response_id we stored at login time
    session.pop('response_id', None)
    logout_user()
    return redirect(url_for('main.index'))

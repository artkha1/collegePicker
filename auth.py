"""
auth.py — Login, signup, and logout routes.
"""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

from __init__ import db
from models import User

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    remember = bool(request.form.get("remember"))

    # Raw SQL: look up the user by email
    row = db.session.execute(
        text("SELECT id, password FROM users WHERE email = :email"),
        {"email": email},
    ).mappings().one_or_none()

    if not row:
        flash("No account found — please sign up first.")
        return redirect(url_for("auth.signup"))

    if not check_password_hash(row["password"], password):
        flash("Incorrect password — please try again.")
        return redirect(url_for("auth.login"))

    user: User = db.session.get(User, row["id"])

    # If the visitor filled out the questionnaire anonymously before
    # logging in, carry those answers over to their account row so they
    # aren't lost.  Anonymous row is deleted afterwards.
    anon_id = session.get("response_id")
    if anon_id and anon_id != user.id:
        anon: User | None = db.session.get(User, anon_id)
        if anon and anon.is_anonymous_visitor:
            _merge_prefs(src=anon, dst=user)
            db.session.delete(anon)
            db.session.commit()

    login_user(user, remember=remember)
    session["response_id"] = user.id
    return redirect(url_for("main.welcome"))


@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    email    = request.form.get("email", "").strip()
    name     = request.form.get("name", "").strip()
    password = request.form.get("password", "")

    # Raw SQL: check for duplicate email before inserting.
    existing = db.session.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email},
    ).mappings().one_or_none()

    if existing:
        flash("An account with that email already exists.")
        return redirect(url_for("auth.signup"))

    # ORM insert
    new_user = User(
        email=email,
        name=name,
        password=generate_password_hash(password),
    )

    # If the visitor already has anonymous questionnaire answers, copy
    # them into the new account so they don't have to re-enter them.
    anon_id = session.get("response_id")
    if anon_id:
        anon: User | None = db.session.get(User, anon_id)
        if anon and anon.is_anonymous_visitor:
            _merge_prefs(src=anon, dst=new_user)
            db.session.delete(anon)

    db.session.add(new_user)
    db.session.commit()

    flash("Account created — please log in.")
    return redirect(url_for("auth.login"))


@auth.route("/logout")
@login_required
def logout():
    session.pop("response_id", None)
    logout_user()
    return redirect(url_for("main.index"))


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _merge_prefs(src: User, dst: User) -> None:
    """
    Copy questionnaire answers from src into dst, but only for fields
    that dst hasn't filled in yet.  This way an existing account's saved
    preferences aren't silently overwritten.
    """
    scalar_fields = (
        "rel_imp", "size_imp", "setting_imp", "region_imp", "state_imp",
        "all_majors", "sat_math", "sat_eng", "act", "income",
    )
    for field in scalar_fields:
        if getattr(dst, field) is None and getattr(src, field) is not None:
            setattr(dst, field, getattr(src, field))

    json_fields = ("rel_affil", "sizes", "sel_majors", "settings", "regions", "states", "spec_prefs")
    for field in json_fields:
        if not getattr(dst, field) and getattr(src, field):
            setattr(dst, field, getattr(src, field))
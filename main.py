"""
main.py — Core application routes.
"""

import os

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from sqlalchemy import text

from __init__ import db, create_app
from form import (
    Questionnaire,
    majorChoices,
    regionChoices,
    religionChoices,
    settingChoices,
    sizeChoices,
    specPrefChoices,
    stateChoices,
)
from models import User, get_user_prefs, purge_anonymous_users
from output import calc

main = Blueprint("main", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_user_id() -> int | None:
    """Return the active users.id for the current request (anon or logged-in)."""
    if current_user.is_authenticated:
        return current_user.id
    return session.get("response_id")


def _get_or_create_anon_user() -> int:
    """
    Return the response_id for an anonymous visitor, creating a new User
    row if this is their first visit.
    """
    uid = session.get("response_id")
    if uid:
        return uid

    anon = User()                    # all preference fields default to NULL / []
    db.session.add(anon)
    db.session.commit()
    session["response_id"] = anon.id
    return anon.id


def _prepopulate_form(form: Questionnaire, user: User) -> None:
    """
    Fill a WTForms Questionnaire with a User's saved preferences so the
    form renders with their previous answers pre-selected on GET.
    """
    # Scalar fields
    if user.rel_imp     is not None: form.relImp.data     = user.rel_imp
    if user.size_imp    is not None: form.sizeImp.data    = user.size_imp
    if user.setting_imp is not None: form.settingImp.data = user.setting_imp
    if user.region_imp  is not None: form.regionImp.data  = user.region_imp
    if user.state_imp   is not None: form.stateImp.data   = user.state_imp
    if user.all_majors  is not None: form.allMajors.data  = user.all_majors
    if user.sat_math    is not None: form.satMath.data    = user.sat_math
    if user.sat_eng     is not None: form.satEng.data     = user.sat_eng
    if user.act         is not None: form.act.data        = user.act
    if user.income      is not None: form.income.data     = user.income

    # Multi-select fields (list of int codes)
    if user.rel_affil:  form.relAffil.data  = user.rel_affil
    if user.sizes:      form.size.data      = user.sizes
    if user.sel_majors: form.major.data     = user.sel_majors
    if user.settings:   form.setting.data   = user.settings
    if user.regions:    form.region.data    = user.regions
    if user.states:     form.state.data     = user.states
    if user.spec_prefs: form.specPref.data  = user.spec_prefs


def _save_prefs_from_form(user: User, form: Questionnaire) -> None:
    """
    Persist submitted form data to the User model.
    Replaces the old SaveUserPreferences stored procedure.
    """
    # Scalar fields
    user.rel_imp     = form.relImp.data
    user.size_imp    = form.sizeImp.data
    user.setting_imp = form.settingImp.data
    user.region_imp  = form.regionImp.data
    user.state_imp   = form.stateImp.data
    user.all_majors  = form.allMajors.data
    user.sat_math    = form.satMath.data
    user.sat_eng     = form.satEng.data
    user.act         = form.act.data
    user.income      = form.income.data

    # Multi-select fields — store just the integer codes; names are
    # static constants in form.py so we don't need to persist them.
    user.rel_affil  = form.relAffil.data  or []
    user.sizes      = form.size.data      or []
    user.sel_majors = form.major.data     or []
    user.settings   = form.setting.data   or []
    user.regions    = form.region.data    or []
    user.states     = form.state.data     or []
    user.spec_prefs = form.specPref.data  or []


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@main.route("/")
def index():
    return render_template("index.html")


@main.route("/welcome")
def welcome():
    if not current_user.is_authenticated:
        return redirect(url_for("main.getStarted"))
    return render_template("welcome.html", name=current_user.name)


@main.route("/getStarted", methods=["GET", "POST"])
def getStarted():
    form = Questionnaire(request.form)

    if request.method == "GET":
        # Lazy cleanup: delete anonymous rows older than 24 h.
        # Runs at most once per page load; the indexed WHERE clause makes
        # it cheap enough to do inline.
        purge_anonymous_users(ttl_hours=24)

        # Prepopulate form for returning users
        if current_user.is_authenticated:
            _prepopulate_form(form, current_user)
        else:
            uid = session.get("response_id")
            if uid:
                anon = db.session.get(User, uid)
                if anon:
                    _prepopulate_form(form, anon)
                else:
                    session.pop("response_id", None)  # stale ID, clear it

        return render_template("getStarted.html", form=form)

    # --- POST: validate ---
    if not form.validate():
        flash("Please check your answers: " + str(form.errors), "danger")
        return render_template("getStarted.html", form=form)

    # Retrieve or create the user row for this visitor.
    if current_user.is_authenticated:
        user: User = current_user
    else:
        uid  = _get_or_create_anon_user()
        user = db.session.get(User, uid)

    _save_prefs_from_form(user, form)
    db.session.commit()

    return redirect(url_for("main.output"))


# ---------------------------------------------------------------------------
# Output / college detail
# ---------------------------------------------------------------------------

def _top_colleges():
    """Run the scoring algorithm for the current visitor (anon or logged-in)."""
    uid = _current_user_id()
    if uid is None:
        return None

    prefs = get_user_prefs(uid)
    if prefs is None:
        return None

    return calc(**prefs, user_id=uid).nlargest(20, "Score").reset_index()


@main.route("/output")
def output():
    top_colleges = _top_colleges()
    if top_colleges is None:
        flash("Please fill out the questionnaire first.")
        return redirect(url_for("main.getStarted"))
    return render_template("output.html", df=top_colleges)


@main.route("/college/<int:college_id>/")
def college(college_id):
    top_colleges = _top_colleges()
    if top_colleges is None:
        flash("Please fill out the questionnaire first.")
        return redirect(url_for("main.getStarted"))

    college = top_colleges.iloc[college_id]

    fieldsDict = {
        "name":                   "Name",
        "city":                   "City",
        "state":                  "State",
        "type":                   "Type",
        "religious_affiliation":  "Religious affiliation",
        "locale":                 "Setting",
        "num_students":           "Number of students",
        "hbcu":                   "Historically Black or Predominantly Black",
        "annh":                   "Alaska Native / Native Hawaiian-serving",
        "aanipi":                 "Asian American / Native American / Pacific Islander-serving",
        "tribal":                 "Tribal college or university",
        "hispanic":               "Hispanic-serving",
        "men_only":               "Men-only",
        "women_only":             "Women-only",
        "online_only":            "Online-only",
        "admission_rate":         "Admission rate",
        "sat_rw_mid":             "SAT Reading & Writing midpoint",
        "sat_math_mid":           "SAT Math midpoint",
        "sat_avg":                "SAT average (cumulative)",
        "act_avg":                "ACT average (cumulative)",
        "graduation_rate":        "Graduation rate",
        "median_earnings_6yr":    "Median earnings 6 years after entry",
        "median_earnings_10yr":   "Median earnings 10 years after entry",
        "avg_cost_of_attendance": "Average cost of attendance",
        "in_state_tuition_fees":  "In-state tuition and fees",
        "out_state_tuition_fees": "Out-of-state tuition and fees",
        "net_price_0_30k":        "Net price — $0–$30,000 family income",
        "net_price_30_48k":       "Net price — $30,001–$48,000 family income",
        "net_price_48_75k":       "Net price — $48,001–$75,000 family income",
        "net_price_75_110k":      "Net price — $75,001–$110,000 family income",
        "net_price_110k_plus":    "Net price — $110,000+ family income",
        "median_starting_debt":   "Median starting debt",
    }

    overview  = ["type", "religious_affiliation", "locale", "num_students",
                 "hbcu", "annh", "aanipi", "tribal", "hispanic",
                 "men_only", "women_only", "online_only"]
    academics = ["admission_rate", "sat_rw_mid", "sat_math_mid", "sat_avg",
                 "act_avg", "graduation_rate",
                 "median_earnings_6yr", "median_earnings_10yr"]
    finance   = ["avg_cost_of_attendance", "in_state_tuition_fees", "out_state_tuition_fees",
                 "net_price_0_30k", "net_price_30_48k", "net_price_48_75k",
                 "net_price_75_110k", "net_price_110k_plus", "median_starting_debt"]
    spec_pref = ["hbcu", "annh", "aanipi", "tribal", "hispanic",
                 "men_only", "women_only", "online_only"]

    return render_template(
        "college.html",
        college=college,
        fieldsDict=fieldsDict,
        overview=overview,
        finance=finance,
        academics=academics,
        specPref=spec_pref,
    )


app = create_app()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
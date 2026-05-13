from flask import Blueprint, render_template, flash, request, redirect,url_for, session
from flask_login import current_user
from __init__ import create_app, db
from form import Questionnaire, religionChoices, sizeChoices, majorChoices, settingChoices, regionChoices, stateChoices, specPrefChoices
from models import get_user_prefs
from sqlalchemy import text
from output import calc
import os

# our main blueprint
main = Blueprint('main', __name__)

def _response_id():
    """Return the active response_id for the current request (logged-in or anonymous)."""
    if current_user.is_authenticated:
        return current_user.id
    return session.get('response_id')
 
 
# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@main.route('/')  # home page that return 'index'
def index():
    return render_template('index.html')

@main.route('/welcome')
def welcome():
    # Only logged-in users have a name to show; redirect others to getStarted.
    if not current_user.is_authenticated:
        return redirect(url_for('main.getStarted'))
    return render_template('welcome.html', name=current_user.name)

@main.route('/getStarted',methods=['GET', 'POST'])
def getStarted():
    form = Questionnaire(request.form)  # initialize the form

    if request.method == 'GET':  # if we are landing on this page, show the page
        return render_template('getStarted.html', form=form)
    
    # --- POST: validate then persist with raw SQL ---
    if not form.validate():
        flash('Error: ' + str(form.errors), 'danger')
        return render_template('getStarted.html', form=form)
 
    rid = _response_id()
 
    if rid is None:
        # Anonymous visitor - create a fresh user_responses row
        result = db.session.execute(
            text(
                "INSERT INTO user_responses "
                "(relImp, sizeImp, allMajors, satMath, satEng, act, "
                " settingImp, regionImp, stateImp, income) "
                "VALUES (NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL)"
            )
        )
        db.session.commit()
        # rid = db.session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        rid = result.lastrowid
        session['response_id'] = rid  # remember for this browser session
 
    # Call SaveUserPreferences stored procedure - handles DELETEs of old rows,
    # UPDATE of scalar fields, and audit log INSERT in a SERIALIZABLE transaction

    raw_conn = db.engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        cursor.callproc('SaveUserPreferences', [
            rid,
            form.relImp.data, form.sizeImp.data, form.allMajors.data,
            form.satMath.data, form.satEng.data, form.act.data,
            form.settingImp.data, form.regionImp.data, form.stateImp.data,
            form.income.data
        ])
        # Consume all result sets
        while cursor.nextset():
            pass
        raw_conn.commit()
        cursor.close() 
    except Exception as e:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()
 
    # --- Insert new multi-select preferences (raw SQL) ---
    rel_map     = dict(religionChoices)
    size_map    = dict(sizeChoices)
    major_map   = dict(majorChoices)
    setting_map = dict(settingChoices)
    region_map  = dict(regionChoices)
    state_map   = dict(stateChoices)
    spec_map    = dict(specPrefChoices)
 
    for code in form.relAffil.data:
        db.session.execute(
            text("INSERT INTO religions (user_id, code, name) VALUES (:uid, :code, :name)"),
            {"uid": rid, "code": code, "name": rel_map.get(code)},
        )
    for code in form.size.data:
        db.session.execute(
            text("INSERT INTO sizes (user_id, code, name) VALUES (:uid, :code, :name)"),
            {"uid": rid, "code": code, "name": size_map.get(code)},
        )
    for code in form.major.data:
        db.session.execute(
            text("INSERT INTO user_majors (user_id, code, name) VALUES (:uid, :code, :name)"),
            {"uid": rid, "code": code, "name": major_map.get(code)},
        )
    for code in form.setting.data:
        db.session.execute(
            text("INSERT INTO settings (user_id, code, name) VALUES (:uid, :code, :name)"),
            {"uid": rid, "code": code, "name": setting_map.get(code)},
        )
    for code in form.region.data:
        db.session.execute(
            text("INSERT INTO regions (user_id, code, name) VALUES (:uid, :code, :name)"),
            {"uid": rid, "code": code, "name": region_map.get(code)},
        )
    for code in form.state.data:
        db.session.execute(
            text("INSERT INTO states (user_id, code, name) VALUES (:uid, :code, :name)"),
            {"uid": rid, "code": code, "name": state_map.get(code)},
        )
    for code in form.specPref.data:
        db.session.execute(
            text("INSERT INTO specPrefs (user_id, code, name) VALUES (:uid, :code, :name)"),
            {"uid": rid, "code": code, "name": spec_map.get(code)},
        )
 
    db.session.commit()
    return redirect(url_for('main.output'))

def topCols():
    """Run the scoring algorithm for the current visitor (anon or logged-in)."""
    rid = _response_id()
    if rid is None:
        return None
 
    prefs = get_user_prefs(rid)
    if prefs is None:
        return None
 
    out  = calc(**prefs, response_id=rid)
    top5 = out.nlargest(5, 'Score').reset_index()
    return top5


@main.route('/output')  # make a directory for the output where top 5 colleges will be shown with links for more information
def output():
    top5 = topCols()
    if top5 is None:
        # Visitor hasn't submitted the form yet - send them there
        flash('Please fill out the questionnaire first.')
        return redirect(url_for('main.getStarted'))
    return render_template('output.html', df=top5)

@main.route('/college/<int:college_id>/')  # the directory with more information on each college. Different depending on the index of the college passed
def college(college_id):
    top5 = topCols()
    if top5 is None:
        flash('Please fill out the questionnaire first.')
        return redirect(url_for('main.getStarted'))
    
    college = top5.iloc[college_id]  # the particular college we are looking at

    # every column and their corresponding label (generated using code in Jupyter but slightly changed manually)
    fieldsDict = {
        'name':                   'Name',
        'city':                   'City',
        'state':                  'State',
        'type':                   'Type',
        'religious_affiliation':  'Religious affiliation',
        'locale':                 'Setting',
        'num_students':           'Number of students',
        'hbcu':                   'Historically Black or Predominantly Black',
        'annh':                   'Alaska Native / Native Hawaiian-serving',
        'aanipi':                 'Asian American / Native American / Pacific Islander-serving',
        'tribal':                 'Tribal college or university',
        'hispanic':               'Hispanic-serving',
        'men_only':               'Men-only',
        'women_only':             'Women-only',
        'online_only':            'Online-only',
        'admission_rate':         'Admission rate',
        'sat_rw_mid':             'SAT Reading & Writing midpoint',
        'sat_math_mid':           'SAT Math midpoint',
        'sat_avg':                'SAT average (cumulative)',
        'act_avg':                'ACT average (cumulative)',
        'graduation_rate':        'Graduation rate',
        'median_earnings_6yr':    'Median earnings 6 years after entry',
        'median_earnings_10yr':   'Median earnings 10 years after entry',
        'avg_cost_of_attendance': 'Average cost of attendance',
        'in_state_tuition_fees':  'In-state tuition and fees',
        'out_state_tuition_fees': 'Out-of-state tuition and fees',
        'net_price_0_30k':        'Net price — $0–$30,000 family income',
        'net_price_30_48k':       'Net price — $30,001–$48,000 family income',
        'net_price_48_75k':       'Net price — $48,001–$75,000 family income',
        'net_price_75_110k':      'Net price — $75,001–$110,000 family income',
        'net_price_110k_plus':    'Net price — $110,000+ family income',
        'median_starting_debt':   'Median starting debt',
    }
 
    overview  = ['type', 'religious_affiliation', 'locale', 'num_students',
                 'hbcu', 'annh', 'aanipi', 'tribal', 'hispanic',
                 'men_only', 'women_only', 'online_only']
    academics = ['admission_rate', 'sat_rw_mid', 'sat_math_mid', 'sat_avg',
                 'act_avg', 'graduation_rate',
                 'median_earnings_6yr', 'median_earnings_10yr']
    finance   = ['avg_cost_of_attendance', 'in_state_tuition_fees', 'out_state_tuition_fees',
                 'net_price_0_30k', 'net_price_30_48k', 'net_price_48_75k',
                 'net_price_75_110k', 'net_price_110k_plus', 'median_starting_debt']
    spec_pref = ['hbcu', 'annh', 'aanipi', 'tribal', 'hispanic',
                 'men_only', 'women_only', 'online_only']
    
    return render_template('college.html',
                           college=college,
                           fieldsDict=fieldsDict,
                           overview=overview,
                           finance=finance,
                           academics=academics,
                           specPref=spec_pref)


app = create_app()  # initialize Flask app using the __init__.py function
if __name__ == '__main__':
    # with app.app_context():
    #     db.create_all()
    #app.run(debug=True)  # run the Flask app on debug mode
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

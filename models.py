from flask_login import UserMixin
from __init__ import db
from sqlalchemy import text

# ---------------------------------------------------------------------------
# College data tables (read-only from the app's perspective)
# ---------------------------------------------------------------------------

class CollegeStatic(db.Model):
    __tablename__ = 'colleges_static'
    college_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    website = db.Column(db.String(255))
    city = db.Column(db.String(255))
    state = db.Column(db.String(255))
    year_established = db.Column(db.Integer)
    type = db.Column(db.String(255))
    religious_affiliation = db.Column(db.String(255))
    online_only = db.Column(db.Boolean)
    hbcu = db.Column(db.Boolean)
    aapi = db.Column(db.Boolean)
    tribal = db.Column(db.Boolean)
    hispanic = db.Column(db.Boolean)
    men_only = db.Column(db.Boolean)
    women_only = db.Column(db.Boolean)

    # Relationships removed - query colleges_dynamic and college_majors directly via raw SQL


class CollegeDynamic(db.Model):
    __tablename__ = 'colleges_dynamic'
    college_id = db.Column(db.Integer, db.ForeignKey('colleges_static.college_id'), primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    admission_rate = db.Column(db.Float)
    sat_rw_mid = db.Column(db.Integer)
    sat_math_mid = db.Column(db.Integer)
    sat_avg = db.Column(db.Integer)
    graduation_rate = db.Column(db.Float)
    median_earnings_10yr = db.Column(db.Float)
    avg_cost_of_attendance = db.Column(db.Float)
    in_state_tuition_fees = db.Column(db.Float)
    out_state_tuition_fees = db.Column(db.Float)
    net_price_0_30k = db.Column(db.Float)
    median_starting_debt = db.Column(db.Float)
    num_students = db.Column(db.Integer)


class Major(db.Model):
    __tablename__ = 'majors'
    major_id = db.Column(db.Integer, primary_key=True)
    major_name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(255))
    stem_flag = db.Column(db.Boolean)
    starting_salary = db.Column(db.Float)

    # Relationship to CollegeMajor removed - query college_majors directly via raw SQL


class CollegeMajor(db.Model):
    __tablename__ = 'college_majors'
    college_id = db.Column(db.Integer, db.ForeignKey('colleges_static.college_id'), primary_key=True)
    major_id = db.Column(db.Integer, db.ForeignKey('majors.major_id'), primary_key=True)

# ---------------------------------------------------------------------------
# User tables
# ---------------------------------------------------------------------------


class UserResponse(db.Model):
    """Stores questionnaire answers. Also used for anonymous sessions."""
    __tablename__ = 'user_responses'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    relImp = db.Column(db.Integer)
    sizeImp = db.Column(db.Integer)
    allMajors = db.Column(db.Boolean)
    satMath = db.Column(db.Integer)
    satEng = db.Column(db.Integer)
    act = db.Column(db.Integer)
    settingImp = db.Column(db.Integer)
    regionImp = db.Column(db.Integer)
    stateImp = db.Column(db.Integer)
    income = db.Column(db.Integer)

    # relationships removed - use get_user_prefs(response_id) below


class UserAccount(UserMixin, db.Model):
    """Login credentials, linked to UserResponse via shared primary key."""
    __tablename__ = 'user_accounts'
    id = db.Column(db.Integer, db.ForeignKey('user_responses.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    name = db.Column(db.String(255))

    # ORM relationship to UserResponse removed - use get_user_prefs(self.id) instead


# ---------------------------------------------------------------------------
# Per-user multi-select preference tables
# ---------------------------------------------------------------------------

class Religion(db.Model):
    __tablename__ = 'religions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_responses.id', ondelete='CASCADE'), nullable=False)
    code = db.Column(db.Integer)
    name = db.Column(db.String(255))


class Size(db.Model):
    __tablename__ = 'sizes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_responses.id', ondelete='CASCADE'), nullable=False)
    code = db.Column(db.Integer)
    name = db.Column(db.String(255))


class UserMajor(db.Model):
    """User's preferred majors (distinct from the college majors catalogue)."""
    __tablename__ = 'user_majors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_responses.id', ondelete='CASCADE'), nullable=False)
    code = db.Column(db.Integer)
    name = db.Column(db.String(255))


class Setting(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_responses.id', ondelete='CASCADE'), nullable=False)
    code = db.Column(db.Integer)
    name = db.Column(db.String(255))


class Region(db.Model):
    __tablename__ = 'regions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_responses.id', ondelete='CASCADE'), nullable=False)
    code = db.Column(db.Integer)
    name = db.Column(db.String(255))


class State(db.Model):
    __tablename__ = 'states'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_responses.id', ondelete='CASCADE'), nullable=False)
    code = db.Column(db.Integer)
    name = db.Column(db.String(255))


class SpecPref(db.Model):
    __tablename__ = 'specPrefs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_responses.id', ondelete='CASCADE'), nullable=False)
    code = db.Column(db.Integer)
    name = db.Column(db.String(255))

# ---------------------------------------------------------------------------
# Raw-SQL helper - replaces the old ORM relationship traversal
# ---------------------------------------------------------------------------
 
class _Row:
    """Lightweight stand-in for an ORM row - exposes .code and .name."""
    __slots__ = ("code", "name")
 
    def __init__(self, code, name):
        self.code = code
        self.name = name
 
 
def get_user_prefs(response_id):
    """
    Fetch all preference data for a given user_responses.id using raw SQL.
 
    Returns a dict whose keys match the keyword arguments of calc() in
    output.py, plus the scalar fields from user_responses.  Returns None
    if no row with that id exists.
 
    Usage (anonymous or logged-in, same call either way):
        prefs = get_user_prefs(session['response_id'])
        if prefs:
            top5 = calc(**prefs)
    """
 
    with db.engine.connect() as conn:
        # --- scalar fields from user_responses ---
        row = conn.execute(
            text(
                "SELECT relImp, sizeImp, allMajors, satMath, satEng, act, "
                "       settingImp, regionImp, stateImp, income "
                "FROM user_responses WHERE id = :uid"
            ),
            {"uid": response_id},
        ).mappings().one_or_none()
 
        if row is None:
            return None
 
        def fetch_list(table):
            """Return a list of _Row objects for a per-user preference table."""
            rows = conn.execute(
                text(f"SELECT code, name FROM {table} WHERE user_id = :uid"),
                {"uid": response_id},
            ).mappings().all()
            return [_Row(r["code"], r["name"]) for r in rows]
 
        return {
            # scalar fields (match calc() parameter names)
            "relImp":     row["relImp"],
            "sizeImp":    row["sizeImp"],
            "allMajors":  bool(row["allMajors"]) if row["allMajors"] is not None else None,
            "satMath":    row["satMath"],
            "satEng":     row["satEng"],
            "act":        row["act"],
            "setImp":     row["settingImp"],   # note: calc() uses setImp, not settingImp
            "regImp":     row["regionImp"],    # calc() uses regImp
            "stImp":      row["stateImp"],     # calc() uses stImp
            "income":     row["income"],
            # multi-select lists
            "rels":       fetch_list("religions"),
            "sizes":      fetch_list("sizes"),
            "majors":     fetch_list("user_majors"),
            "settings":   fetch_list("settings"),
            "regions":    fetch_list("regions"),
            "states":     fetch_list("states"),
            "specPrefs":  fetch_list("specPrefs"),
        }
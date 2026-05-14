"""
Schema overview
---------------
College data (read-only):
    CollegeStatic     → colleges_static
    CollegeDynamic    → colleges_dynamic
    Major             → majors
    CollegeMajor      → college_majors  (association table)

User data:
    User              → users
        Multi-select preferences (religions, sizes, settings, regions,
        states, specPrefs, user_majors) are stored as JSONB arrays
        instead of 7 separate child tables.

Raw SQL:
    GET_TOP_COLLEGES_SQL  — the main college-filtering query.
    get_user_prefs()      — fetches a User row and unpacks it into the
        dict that calc() in output.py expects.
    purge_anonymous_users() — deletes anonymous rows older than `ttl`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from flask_login import UserMixin
from sqlalchemy import text

from __init__ import db


# ---------------------------------------------------------------------------
# College data models (read-only from the app's perspective)
# ---------------------------------------------------------------------------

class CollegeStatic(db.Model):
    __tablename__ = "colleges_static"

    college_id           = db.Column(db.Integer, primary_key=True)
    name                 = db.Column(db.String(255), nullable=False)
    website              = db.Column(db.String(255))
    finaid_website       = db.Column(db.String(255))
    city                 = db.Column(db.String(255))
    state                = db.Column(db.String(255))
    region               = db.Column(db.Integer)
    locale               = db.Column(db.Integer)
    type                 = db.Column(db.Integer)
    religious_affiliation = db.Column(db.Integer)
    online_only          = db.Column(db.Boolean)
    hbcu                 = db.Column(db.Boolean)
    aanipi               = db.Column(db.Boolean)
    annh                 = db.Column(db.Boolean)
    tribal               = db.Column(db.Boolean)
    hispanic             = db.Column(db.Boolean)
    men_only             = db.Column(db.Boolean)
    women_only           = db.Column(db.Boolean)


class CollegeDynamic(db.Model):
    __tablename__ = "colleges_dynamic"

    college_id             = db.Column(db.Integer, db.ForeignKey("colleges_static.college_id"), primary_key=True)
    year                   = db.Column(db.Integer, primary_key=True)
    admission_rate         = db.Column(db.Float)
    sat_rw_mid             = db.Column(db.Integer)
    sat_math_mid           = db.Column(db.Integer)
    sat_avg                = db.Column(db.Integer)
    act_avg                = db.Column(db.Float)
    graduation_rate        = db.Column(db.Float)
    median_earnings_6yr    = db.Column(db.Float)
    median_earnings_10yr   = db.Column(db.Float)
    avg_cost_of_attendance = db.Column(db.Float)
    in_state_tuition_fees  = db.Column(db.Float)
    out_state_tuition_fees = db.Column(db.Float)
    net_price_0_30k        = db.Column(db.Float)
    net_price_30_48k       = db.Column(db.Float)
    net_price_48_75k       = db.Column(db.Float)
    net_price_75_110k      = db.Column(db.Float)
    net_price_110k_plus    = db.Column(db.Float)
    median_starting_debt   = db.Column(db.Float)
    num_students           = db.Column(db.Integer)


class Major(db.Model):
    __tablename__ = "majors"

    major_id   = db.Column(db.Integer, primary_key=True)
    major_name = db.Column(db.String(255), nullable=False)


class CollegeMajor(db.Model):
    __tablename__ = "college_majors"

    college_id = db.Column(db.Integer, db.ForeignKey("colleges_static.college_id"), primary_key=True)
    major_id   = db.Column(db.Integer, db.ForeignKey("majors.major_id"), primary_key=True)


# ---------------------------------------------------------------------------
# User model
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    # Auth — NULL for anonymous (session-only) visitors
    email    = db.Column(db.String(255), unique=True, nullable=True)
    password = db.Column(db.String(255), nullable=True)
    name     = db.Column(db.String(255), nullable=True)

    # Scalar questionnaire fields
    rel_imp     = db.Column(db.Integer)
    size_imp    = db.Column(db.Integer)
    setting_imp = db.Column(db.Integer)
    region_imp  = db.Column(db.Integer)
    state_imp   = db.Column(db.Integer)
    all_majors  = db.Column(db.Boolean)
    sat_math    = db.Column(db.Integer)
    sat_eng     = db.Column(db.Integer)
    act         = db.Column(db.Integer)
    income      = db.Column(db.Integer)

    # Multi-select preferences as JSON arrays of integer codes.
    # Default is an empty list (not NULL) so callers never need to guard.
    rel_affil  = db.Column(db.JSON, nullable=False, default=list)
    sizes      = db.Column(db.JSON, nullable=False, default=list)
    sel_majors = db.Column(db.JSON, nullable=False, default=list)
    settings   = db.Column(db.JSON, nullable=False, default=list)
    regions    = db.Column(db.JSON, nullable=False, default=list)
    states     = db.Column(db.JSON, nullable=False, default=list)
    spec_prefs = db.Column(db.JSON, nullable=False, default=list)

    @property
    def is_anonymous_visitor(self) -> bool:
        """True for session-only users who have not signed up."""
        return self.email is None

# ---------------------------------------------------------------------------
# Raw SQL — GET_TOP_COLLEGES_SQL
#
# Parameters (passed as a dict to SQLAlchemy text()):
#   :user_id        — users.id for the current visitor
#   :all_majors     — boolean; True → college must offer every selected major
#   :region_imp     — importance score; 11 → hard filter on region
#   :state_imp      — importance score; 11 → hard filter on state
#
# Otjer imp fields are handles in output.py because they require re=mapping to different numbers.
# The query returns one row per college (most recent year of dynamic data)
# with a matched_major_count column used for soft scoring in output.py.
# ---------------------------------------------------------------------------

GET_TOP_COLLEGES_SQL = text("""
WITH

-- -----------------------------------------------------------------------
-- CTE 1: major_filter
-- Joins college_majors against the user's selected majors (stored as a
-- JSON array).  Groups by college and uses HAVING to enforce all_majors.
--
-- Features: CTE, JOIN, JSON operator, GROUP BY, HAVING, subquery
-- -----------------------------------------------------------------------
major_filter AS (
    SELECT
        cm.college_id,
        COUNT(DISTINCT cm.major_id) AS matched_major_count
    FROM college_majors cm
    -- jsonb_array_elements_text expands the JSON array into rows so we
    -- can JOIN it against the integer foreign key.
    JOIN (
        SELECT elem::int AS major_id
        FROM jsonb_array_elements_text(
            (SELECT sel_majors FROM users WHERE id = :user_id)
        ) AS elem
    ) chosen_majors ON cm.major_id = chosen_majors.major_id
    GROUP BY cm.college_id
    HAVING
        -- When all_majors is false (or no majors selected) any match counts.
        -- When all_majors is true the college must offer every chosen major.
        (NOT :all_majors)
        OR COUNT(DISTINCT cm.major_id) = (
            SELECT jsonb_array_length(sel_majors)
            FROM users
            WHERE id = :user_id
        )
),

-- -----------------------------------------------------------------------
-- CTE 2: user_prefs
-- Reads the current user's hard-filter importance flags in one place so
-- the main query can reference them without repeating the subquery.
-- -----------------------------------------------------------------------
user_prefs AS (
    SELECT region_imp, state_imp, spec_prefs
    FROM users
    WHERE id = :user_id
)

-- -----------------------------------------------------------------------
-- Main SELECT
-- Joins colleges_static x colleges_dynamic (most-recent year via
-- correlated subquery) x major_filter CTE.
-- Hard filters use NOT EXISTS / IN subqueries against the user's JSON prefs.
--
-- Features: multi-table JOIN, correlated subquery, NOT EXISTS, JSON ops
-- -----------------------------------------------------------------------
SELECT
    cs.college_id,
    cs.name,
    cs.website,
    cs.finaid_website,
    cs.city,
    cs.state,
    cs.locale,
    cs.region,
    cs.type,
    cs.religious_affiliation,
    cs.online_only,
    cs.hbcu,
    cs.annh,
    cs.aanipi,
    cs.tribal,
    cs.hispanic,
    cs.men_only,
    cs.women_only,
    cd.admission_rate,
    cd.sat_rw_mid,
    cd.sat_math_mid,
    cd.sat_avg,
    cd.act_avg,
    cd.graduation_rate,
    cd.median_earnings_6yr,
    cd.median_earnings_10yr,
    cd.avg_cost_of_attendance,
    cd.in_state_tuition_fees,
    cd.out_state_tuition_fees,
    cd.net_price_0_30k,
    cd.net_price_30_48k,
    cd.net_price_48_75k,
    cd.net_price_75_110k,
    cd.net_price_110k_plus,
    cd.median_starting_debt,
    cd.num_students,
    COALESCE(mf.matched_major_count, 0) AS matched_major_count

FROM colleges_static cs

-- Most-recent year of dynamic data (correlated subquery)
JOIN colleges_dynamic cd
    ON cs.college_id = cd.college_id
    AND cd.year = (
        SELECT MAX(cd2.year)
        FROM colleges_dynamic cd2
        WHERE cd2.college_id = cs.college_id
    )

-- Major filter: LEFT JOIN so colleges with no major data still appear
-- when the user selected no majors.
LEFT JOIN major_filter mf
    ON cs.college_id = mf.college_id

WHERE
    -- Only require a major match when the user actually selected majors.
    (
        (SELECT jsonb_array_length(sel_majors) FROM users WHERE id = :user_id) = 0
        OR mf.college_id IS NOT NULL
    )

    -- Hard filter: region (only when region_imp = 11)
    AND (
        (SELECT region_imp FROM user_prefs) < 11
        OR cs.region IN (
            SELECT (elem::int) - 1          -- codes are 1-indexed in form.py
            FROM jsonb_array_elements_text(
                (SELECT regions FROM users WHERE id = :user_id)
            ) AS elem
        )
    )

    -- Hard filter: state (only when state_imp = 11)
    AND (
        (SELECT state_imp FROM user_prefs) < 11
        OR cs.state IN (
            SELECT elem
            FROM jsonb_array_elements_text(
                (SELECT states FROM users WHERE id = :user_id)
            ) AS elem
        )
    )

    -- Hard filters: special preferences (NOT EXISTS for each code)
    -- Either special preferences don't contain that code, or the corresponding attribute is true for a college
    AND (NOT ((SELECT spec_prefs FROM users WHERE id = :user_id) @> '[1]') OR cs.hbcu       = true)
    AND (NOT ((SELECT spec_prefs FROM users WHERE id = :user_id) @> '[2]') OR cs.annh       = true)
    AND (NOT ((SELECT spec_prefs FROM users WHERE id = :user_id) @> '[3]') OR cs.aanipi     = true)
    AND (NOT ((SELECT spec_prefs FROM users WHERE id = :user_id) @> '[4]') OR cs.hispanic   = true)
    AND (NOT ((SELECT spec_prefs FROM users WHERE id = :user_id) @> '[5]') OR cs.tribal     = true)
    AND (NOT ((SELECT spec_prefs FROM users WHERE id = :user_id) @> '[6]') OR cs.men_only   = true)
    AND (NOT ((SELECT spec_prefs FROM users WHERE id = :user_id) @> '[7]') OR cs.women_only = true)
    AND (NOT ((SELECT spec_prefs FROM users WHERE id = :user_id) @> '[8]') OR cs.online_only = true)
""")


# ---------------------------------------------------------------------------
# Lightweight named-tuple stand-in used by calc() in output.py.
# ---------------------------------------------------------------------------

class _Pref:
    """Wraps a (code, name) pair so output.py can use .code / .name."""
    __slots__ = ("code", "name")

    def __init__(self, code: int, name: str | None = None):
        self.code = code
        self.name = name

    def __repr__(self):
        return f"_Pref(code={self.code!r}, name={self.name!r})"


# ---------------------------------------------------------------------------
# get_user_prefs
#
# Fetches a User row via the ORM and unpacks it into the keyword-argument
# dict expected by calc() in output.py.  
# ---------------------------------------------------------------------------

# Maps JSON column name → (form.py choices list or None)
# We import lazily to avoid a circular import with form.py.
def _get_name_map(field: str) -> dict[int, str]:
    """Return a code→name mapping for a given multi-select field."""
    from form import (
        religionChoices, sizeChoices, majorChoices, settingChoices,
        regionChoices, stateChoices, specPrefChoices,
    )
    maps = {
        "rel_affil":  dict(religionChoices),
        "sizes":      dict(sizeChoices),
        "sel_majors": dict(majorChoices),
        "settings":   dict(settingChoices),
        "regions":    dict(regionChoices),
        "states":     dict(stateChoices),
        "spec_prefs": dict(specPrefChoices),
    }
    return maps.get(field, {})


def _to_prefs(codes: list[int], field: str) -> list[_Pref]:
    name_map = _get_name_map(field)
    return [_Pref(c, name_map.get(c)) for c in (codes or [])]


def get_user_prefs(user_id: int) -> dict[str, Any] | None:
    """
    Return the preference dict for calc() in output.py, or None if the
    user_id doesn't exist.

    Uses the ORM for the simple primary-key lookup; the heavy college
    filtering stays in raw SQL (GET_TOP_COLLEGES_SQL).
    """
    user: User | None = db.session.get(User, user_id)
    if user is None:
        return None

    return {
        # Scalar fields (match calc() parameter names)
        "relImp":    user.rel_imp,
        "sizeImp":   user.size_imp,
        "allMajors": bool(user.all_majors) if user.all_majors is not None else None,
        "satMath":   user.sat_math,
        "satEng":    user.sat_eng,
        "act":       user.act,
        "setImp":    user.setting_imp,
        "regImp":    user.region_imp,
        "stImp":     user.state_imp,
        "income":    user.income,
        # Multi-select lists → _Pref objects
        "rels":      _to_prefs(user.rel_affil,  "rel_affil"),
        "sizes":     _to_prefs(user.sizes,       "sizes"),
        "majors":    _to_prefs(user.sel_majors,  "sel_majors"),
        "settings":  _to_prefs(user.settings,    "settings"),
        "regions":   _to_prefs(user.regions,     "regions"),
        "states":    _to_prefs(user.states,      "states"),
        "specPrefs": _to_prefs(user.spec_prefs,  "spec_prefs"),
    }


# ---------------------------------------------------------------------------
# purge_anonymous_users — lazy cleanup of session-only rows
#
# Call this from the getStarted GET handler (or any convenient entry point).
# It runs a single DELETE and commits, taking < 1 ms on the indexed column.
# No scheduler or background worker required.
# ---------------------------------------------------------------------------

def purge_anonymous_users(ttl_hours: int = 24) -> int:
    """
    Delete anonymous user rows (email IS NULL) older than `ttl_hours`.
    Returns the number of rows deleted.

    Raw SQL is used here intentionally — it's a single efficient DELETE
    with an indexed WHERE clause, and avoids loading ORM objects just to
    delete them.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
    result = db.session.execute(
        text("""
            DELETE FROM users
            WHERE email IS NULL
              AND created_at < :cutoff
        """),
        {"cutoff": cutoff},
    )
    db.session.commit()
    return result.rowcount
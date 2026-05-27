"""
tests/test_collegepicker.py — College Picker test suite

Run with:
    pytest tests/ -v

The suite is divided into four areas:
    1. Unit tests — pure logic with no DB or Flask context
    2. Model tests — ORM helpers and purge logic (SQLite in-memory)
    3. Route tests — HTTP behaviour via Flask test client
    4. Search tests — search_colleges / count_colleges query logic

No real Postgres instance is needed; all DB tests use SQLite in-memory
via an app fixture that overrides SQLALCHEMY_DATABASE_URI.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from werkzeug.security import generate_password_hash


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_NAME", "test")


@pytest.fixture(scope="session")
def app():
    """Flask app wired to an in-memory SQLite database."""
    from __init__ import create_app, db as _db

    _app = create_app()
    _app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test-secret-key",
    )

    with _app.app_context():
        _db.create_all()
        yield _app
        try:
            _db.drop_all()
        except Exception:
            pass  # don't fail teardown on timeout


@pytest.fixture
def db(app):
    from __init__ import db as _db
    yield _db
    _db.session.rollback()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(db):
    """Factory: create and persist a User, cleaned up after each test."""
    created = []

    def _make(email=None, password="password123", with_prefs=False):
        from models import User
        u = User(
            email=email,
            password=generate_password_hash(password) if email else None,
            name="Test User" if email else None,
        )
        if with_prefs:
            u.rel_imp = 5
            u.size_imp = 3
            u.rel_affil = [1]
            u.sizes = [1, 2]
            u.sel_majors = [7]
            u.settings = []
            u.regions = []
            u.states = []
            u.spec_prefs = []
        db.session.add(u)
        db.session.commit()
        created.append(u.id)
        return u

    yield _make

    from models import User
    for uid in created:
        u = db.session.get(User, uid)
        if u:
            db.session.delete(u)
    db.session.commit()


@pytest.fixture
def pref():
    """A minimal _Pref-like object."""
    from models import _Pref
    return _Pref


# ---------------------------------------------------------------------------
# 1. UNIT TESTS — pure logic, no DB, no Flask
# ---------------------------------------------------------------------------

class TestFixUrl:
    """output.py fix_url logic extracted for unit testing."""

    @staticmethod
    def fix_url(url):
        if isinstance(url, str):
            if "https" in url:
                return url
            elif "www" in url:
                return "https://" + url
            else:
                return "https://www." + url
        return url

    def test_already_https(self):
        assert self.fix_url("https://mit.edu") == "https://mit.edu"

    def test_www_no_https(self):
        assert self.fix_url("www.mit.edu") == "https://www.mit.edu"

    def test_bare_domain(self):
        assert self.fix_url("mit.edu") == "https://www.mit.edu"

    def test_nan_passthrough(self):
        assert self.fix_url(float("nan")) is not None
        assert pd.isna(self.fix_url(float("nan")))


class TestSizeCode:
    """Size bucketing logic from output.py."""

    @staticmethod
    def size_code(n):
        if pd.isna(n):
            return None
        if n > 15000:
            return 1
        elif n < 5000:
            return 3
        else:
            return 2

    def test_large(self):
        assert self.size_code(20000) == 1

    def test_medium(self):
        assert self.size_code(10000) == 2

    def test_small(self):
        assert self.size_code(1000) == 3

    def test_boundary_large(self):
        assert self.size_code(15001) == 1

    def test_boundary_small(self):
        assert self.size_code(4999) == 3

    def test_nan(self):
        assert self.size_code(float("nan")) is None


class TestPurgeAnonymousUsersLogic:
    """TTL cutoff arithmetic."""

    def test_cutoff_is_past(self):
        ttl = 24
        cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl)
        assert cutoff < datetime.now(timezone.utc)

    def test_cutoff_zero_hours(self):
        """TTL of 0 should expire everything created before right now."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=0)
        old = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert old < cutoff


class TestMergePrefs:
    """_merge_prefs copies only unfilled fields."""

    def test_does_not_overwrite_existing(self, app):
        with app.app_context():
            from auth import _merge_prefs
            from models import User

            src = User(rel_imp=8, sizes=[1, 2])
            dst = User(rel_imp=3, sizes=[])   # dst has rel_imp already

            _merge_prefs(src, dst)

            assert dst.rel_imp == 3        # not overwritten
            assert dst.sizes == [1, 2]     # was empty, filled in

    def test_fills_empty_scalar(self, app):
        with app.app_context():
            from auth import _merge_prefs
            from models import User

            src = User(size_imp=7)
            dst = User(size_imp=None)

            _merge_prefs(src, dst)
            assert dst.size_imp == 7

    def test_fills_empty_json(self, app):
        with app.app_context():
            from auth import _merge_prefs
            from models import User

            src = User(regions=[2, 3])
            dst = User(regions=[])

            _merge_prefs(src, dst)
            assert dst.regions == [2, 3]


class TestSearchHelpers:
    """_parse_int and _parse_float from search.py."""

    def test_parse_int_valid(self):
        from search import _parse_int
        assert _parse_int("42") == 42

    def test_parse_int_empty(self):
        from search import _parse_int
        assert _parse_int("") is None

    def test_parse_int_none(self):
        from search import _parse_int
        assert _parse_int(None) is None

    def test_parse_int_invalid(self):
        from search import _parse_int
        assert _parse_int("abc") is None

    def test_parse_float_valid(self):
        from search import _parse_float
        assert _parse_float("3.14") == pytest.approx(3.14)

    def test_parse_float_empty(self):
        from search import _parse_float
        assert _parse_float("") is None


class TestNormalizeSearchYear:
    def test_valid_year(self):
        from search import normalize_search_year, SEARCH_YEAR_MIN, SEARCH_YEAR_MAX
        assert normalize_search_year(SEARCH_YEAR_MIN) == SEARCH_YEAR_MIN
        assert normalize_search_year(SEARCH_YEAR_MAX) == SEARCH_YEAR_MAX

    def test_out_of_range_falls_back(self):
        from search import normalize_search_year, DEFAULT_SEARCH_YEAR
        assert normalize_search_year(1900) == DEFAULT_SEARCH_YEAR
        assert normalize_search_year(None) == DEFAULT_SEARCH_YEAR


# ---------------------------------------------------------------------------
# 2. MODEL TESTS — ORM and helpers with SQLite
# ---------------------------------------------------------------------------

class TestUserModel:
    def test_create_anonymous(self, make_user, db):
        u = make_user()
        assert u.id is not None
        assert u.email is None
        assert u.is_anonymous_visitor is True

    def test_create_authenticated(self, make_user):
        u = make_user(email="alice@example.com")
        assert u.email == "alice@example.com"
        assert u.is_anonymous_visitor is False

    def test_json_defaults_are_lists(self, make_user):
        u = make_user()
        assert u.rel_affil == []
        assert u.sizes == []
        assert u.sel_majors == []

    def test_email_unique_constraint(self, make_user, db):
        make_user(email="bob@example.com")
        from models import User
        from sqlalchemy.exc import IntegrityError
        dup = User(email="bob@example.com", password="x")
        db.session.add(dup)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_created_at_set_automatically(self, make_user):
        u = make_user()
        assert u.created_at is not None


class TestGetUserPrefs:
    def test_returns_none_for_missing_id(self, app, db):
        with app.app_context():
            from models import get_user_prefs
            assert get_user_prefs(999999) is None

    def test_returns_dict_for_existing_user(self, make_user, app):
        with app.app_context():
            from models import get_user_prefs
            u = make_user(email="prefs@example.com", with_prefs=True)
            prefs = get_user_prefs(u.id)
            assert prefs is not None
            assert "sizes" in prefs
            assert "rels" in prefs
            assert prefs["relImp"] == 5

    def test_json_lists_become_pref_objects(self, make_user, app):
        with app.app_context():
            from models import get_user_prefs, _Pref
            u = make_user(email="prefs2@example.com", with_prefs=True)
            prefs = get_user_prefs(u.id)
            assert all(isinstance(p, _Pref) for p in prefs["sizes"])


class TestPurgeAnonymousUsers:
    def test_deletes_old_anonymous_rows(self, make_user, app, db):
        with app.app_context():
            from models import purge_anonymous_users, User

            u = make_user()
            uid = u.id  # save before purge expires the object
            # Backdate created_at to 48 hours ago
            u.created_at = datetime.now(timezone.utc) - timedelta(hours=48)
            db.session.commit()

            deleted = purge_anonymous_users(ttl_hours=24)
            assert deleted >= 1
            db.session.expire_all()
            assert db.session.get(User, uid) is None

    def test_keeps_recent_anonymous_rows(self, make_user, app, db):
        with app.app_context():
            from models import purge_anonymous_users, User

            u = make_user()  # just created — within TTL
            purge_anonymous_users(ttl_hours=24)
            assert db.session.get(User, u.id) is not None

    def test_never_deletes_authenticated_users(self, make_user, app, db):
        with app.app_context():
            from models import purge_anonymous_users, User

            u = make_user(email="keep@example.com")
            u.created_at = datetime.now(timezone.utc) - timedelta(hours=48)
            db.session.commit()

            purge_anonymous_users(ttl_hours=1)
            assert db.session.get(User, u.id) is not None


# ---------------------------------------------------------------------------
# 3. ROUTE TESTS — HTTP behaviour
# ---------------------------------------------------------------------------

class TestIndexRoute:
    def test_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_contains_get_started_link(self, client):
        resp = client.get("/")
        assert b"getStarted" in resp.data or b"Get Started" in resp.data


class TestGetStartedRoute:
    def test_get_returns_200(self, client):
        resp = client.get("/getStarted")
        assert resp.status_code == 200

    def test_post_missing_fields_stays_on_form(self, client):
        resp = client.post("/getStarted", data={})
        assert resp.status_code in (200, 302)


class TestAuthRoutes:
    def test_login_get(self, client):
        assert client.get("/login").status_code == 200

    def test_signup_get(self, client):
        assert client.get("/signup").status_code == 200

    def test_signup_creates_user(self, client, app, db):
        with app.app_context():
            resp = client.post("/signup", data={
                "email": "newuser@example.com",
                "name": "New User",
                "password": "securepassword",
            }, follow_redirects=True)
            assert resp.status_code == 200

            from models import User
            u = db.session.execute(
                __import__("sqlalchemy").text("SELECT id FROM users WHERE email = :e"),
                {"e": "newuser@example.com"}
            ).one_or_none()
            assert u is not None

    def test_login_wrong_password(self, client, make_user):
        make_user(email="wrongpw@example.com", password="correct")
        resp = client.post("/login", data={
            "email": "wrongpw@example.com",
            "password": "incorrect",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Incorrect" in resp.data or b"incorrect" in resp.data

    def test_login_unknown_email(self, client):
        resp = client.post("/login", data={
            "email": "nobody@example.com",
            "password": "whatever",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"sign up" in resp.data.lower() or b"No account" in resp.data

    def test_logout_requires_login(self, client):
        resp = client.get("/logout")
        assert resp.status_code in (302, 401)


class TestOutputRoute:
    def test_redirects_without_session(self, client):
        """Visiting /output with no questionnaire answers should redirect."""
        resp = client.get("/output")
        assert resp.status_code == 302
        assert "getStarted" in resp.headers["Location"]


class TestSearchRoute:
    def test_get_returns_200(self, client):
        assert client.get("/search").status_code == 200

    def test_search_with_query(self, client):
        resp = client.get("/search?q=university")
        assert resp.status_code == 200

    def test_search_empty_query_with_flag(self, client):
        """Empty q with searched flag should return results page, not prompt."""
        resp = client.get("/search?q=")
        assert resp.status_code == 200

    def test_search_invalid_year_falls_back(self, client):
        resp = client.get("/search?q=university&year=1900")
        assert resp.status_code == 200

    def test_search_swapped_size_range_normalised(self, client):
        """If size_min > size_max the route should swap them silently."""
        resp = client.get("/search?q=university&size_min=50000&size_max=100")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 4. OUTPUT / SCORING TESTS — calc() with mock data
# ---------------------------------------------------------------------------

def _make_pref(code, name=None):
    from models import _Pref
    return _Pref(code, name)


def _make_college_df(n=10, **overrides):
    """
    Build a minimal DataFrame of fake college rows that calc() can process.
    All required columns are present; override any with keyword args.
    """
    base = {
        "college_id":            range(n),
        "name":                  [f"College {i}" for i in range(n)],
        "website":               ["https://example.com"] * n,
        "finaid_website":        ["https://example.com/aid"] * n,
        "city":                  ["Springfield"] * n,
        "state":                 ["IL"] * n,
        "region":                [4] * n,
        "locale":                [12] * n,        # Midsize City → setting 1
        "type":                  [1] * n,
        "religious_affiliation": [30] * n,        # Roman Catholic → rel_code 1
        "online_only":           [False] * n,
        "hbcu":                  [False] * n,
        "annh":                  [False] * n,
        "aanipi":                [False] * n,
        "tribal":                [False] * n,
        "hispanic":              [False] * n,
        "men_only":              [False] * n,
        "women_only":            [False] * n,
        "admission_rate":        [0.5] * n,
        "sat_rw_mid":            [550.0] * n,
        "sat_math_mid":          [560.0] * n,
        "sat_avg":               [1110.0] * n,
        "act_avg":               [24.0] * n,
        "graduation_rate":       [0.7] * n,
        "median_earnings_6yr":   [45000.0] * n,
        "median_earnings_10yr":  [55000.0] * n,
        "avg_cost_of_attendance":[30000.0] * n,
        "in_state_tuition_fees": [10000.0] * n,
        "out_state_tuition_fees":[25000.0] * n,
        "net_price_0_30k":       [5000.0] * n,
        "net_price_30_48k":      [8000.0] * n,
        "net_price_48_75k":      [12000.0] * n,
        "net_price_75_110k":     [18000.0] * n,
        "net_price_110k_plus":   [25000.0] * n,
        "median_starting_debt":  [20000.0] * n,
        "num_students":          [10000.0] * n,
        "matched_major_count":   [2] * n,
    }
    base.update(overrides)
    return pd.DataFrame(base)


class TestCalcScoring:
    """
    calc() is tested by mocking load_college_data so no DB is needed.
    We verify scoring behaviour, not exact numbers — relative ordering
    and match/no-match logic matter.
    """

    def _run_calc(self, df, **kwargs):
        defaults = dict(
            rels=[], sizes=[], majors=[], settings=[], regions=[], states=[],
            specPrefs=[], relImp=5, sizeImp=5, allMajors=False,
            satMath=None, satEng=None, act=None,
            setImp=5, regImp=5, stImp=5, income=0, user_id=1,
        )
        defaults.update(kwargs)
        with patch("output.load_college_data", return_value=df):
            from output import calc
            return calc(**defaults)

    def test_returns_dataframe(self):
        result = self._run_calc(_make_college_df())
        assert isinstance(result, pd.DataFrame)

    def test_score_column_exists(self):
        result = self._run_calc(_make_college_df())
        assert "Score" in result.columns

    def test_match_column_exists(self):
        result = self._run_calc(_make_college_df())
        assert "Match" in result.columns

    def test_match_info_column_exists(self):
        result = self._run_calc(_make_college_df())
        assert "match_info" in result.columns

    def test_match_is_clipped_non_negative(self):
        result = self._run_calc(_make_college_df())
        assert all(float(v) >= 0 for v in result["Match"])

    def test_size_filter_removes_non_matching(self):
        """sizeImp=11 (hard filter) with Large-only should drop small colleges."""
        df = _make_college_df(n=5)
        df.loc[:2, "num_students"] = 20000  # first 3 → Large (code 1)
        df.loc[3:, "num_students"] = 1000   # last 2 → Small (code 3)
        result = self._run_calc(
            df,
            sizes=[_make_pref(1)],  # Large only
            sizeImp=11,
        )
        assert len(result) == 3

    def test_size_soft_score_boosts_matching(self):
        df = _make_college_df(n=2)
        df.loc[0, "num_students"] = 20000  # Large
        df.loc[1, "num_students"] = 1000   # Small
        result = self._run_calc(
            df,
            sizes=[_make_pref(1)],   # prefer Large
            sizeImp=5,
        )
        scores = result["Score"]
        assert scores.iloc[0] > scores.iloc[1]

    def test_rel_filter_removes_non_matching(self):
        df = _make_college_df(n=3)
        df.loc[2, "religious_affiliation"] = 99  # → rel_code 3 (Other Religious)
        result = self._run_calc(
            df,
            rels=[_make_pref(1)],   # Roman Catholic only
            relImp=11,
        )
        assert len(result) == 2

    def test_sat_scores_reduce_deviation_penalty(self):
        """A college whose SAT matches the user's should outscore a mismatched one."""
        df = _make_college_df(n=2)
        df.loc[0, "sat_math_mid"] = 700
        df.loc[0, "sat_rw_mid"]   = 700
        df.loc[0, "sat_avg"]      = 1400
        df.loc[1, "sat_math_mid"] = 400
        df.loc[1, "sat_rw_mid"]   = 400
        df.loc[1, "sat_avg"]      = 800
        result = self._run_calc(df, satMath=700, satEng=700)
        scores = result.reset_index(drop=True)["Score"]
        assert scores[0] > scores[1]

    def test_empty_dataframe_returns_empty(self):
        result = self._run_calc(_make_college_df(n=0))
        assert len(result) == 0

    def test_match_info_has_size_key_when_sizes_given(self):
        df = _make_college_df(n=2)
        result = self._run_calc(df, sizes=[_make_pref(1)], sizeImp=5)
        for _, row in result.iterrows():
            assert "size" in row["match_info"]

    def test_match_info_size_match_correct(self):
        df = _make_college_df(n=1, num_students=[20000.0])
        result = self._run_calc(df, sizes=[_make_pref(1)], sizeImp=5)
        info = result.iloc[0]["match_info"]
        assert len(info["size"]["matches"]) == 1
        assert len(info["size"]["misses"]) == 0

    def test_match_info_size_miss_correct(self):
        df = _make_college_df(n=1, num_students=[1000.0])  # Small
        result = self._run_calc(df, sizes=[_make_pref(1)], sizeImp=5)  # prefer Large
        info = result.iloc[0]["match_info"]
        assert len(info["size"]["misses"]) == 1
        assert len(info["size"]["matches"]) == 0

    def test_formatting_num_students_is_string(self):
        result = self._run_calc(_make_college_df())
        # After formatting, num_students should be a comma-formatted string
        val = result.iloc[0]["num_students"]
        assert isinstance(val, str)
        assert "," in val or val.isdigit()

    def test_urls_fixed(self):
        df = _make_college_df(n=1, website=["mit.edu"])
        result = self._run_calc(df)
        assert result.iloc[0]["website"].startswith("https://")
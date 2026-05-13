from flask import Blueprint, render_template, request, jsonify
from sqlalchemy import text
from __init__ import db

search = Blueprint("search", __name__)

SEARCH_YEAR_MIN = 2020
SEARCH_YEAR_MAX = 2023
DEFAULT_SEARCH_YEAR = SEARCH_YEAR_MAX
SEARCH_YEAR_OPTIONS = list(range(SEARCH_YEAR_MAX, SEARCH_YEAR_MIN - 1, -1))

TYPE_LABELS = {
    1: "Public",
    2: "Private Non-Profit",
    3: "Private For-Profit",
}

STATE_FULL_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
    "AS": "American Samoa",
    "FM": "Micronesia",
    "GU": "Guam",
    "MH": "Marshall Islands",
    "MP": "Marianas Islands",
    "PR": "Puerto Rico",
    "VI": "Virgin Islands",
}


def state_full_name(code: str | None) -> str | None:
    if not code:
        return None
    code = str(code).strip()
    if code == "":
        return None

    return STATE_FULL_NAMES.get(code.upper(), code)


def get_search_filter_options():
    """
    Fetch dropdown options for search filters from the database.
    Returns (states, types) where:
    - states is a list of strings
    - types is a list of dicts: {"value": "<code>", "label": "<mapped label>"}
    """
    states = db.session.execute(
        text(
            "SELECT DISTINCT state "
            "FROM colleges_static "
            "WHERE state IS NOT NULL AND state <> '' "
            "ORDER BY state"
        )
    ).scalars().all()

    type_codes = db.session.execute(
        text(
            "SELECT DISTINCT type "
            "FROM colleges_static "
            "WHERE type IS NOT NULL "
            "ORDER BY type"
        )
    ).scalars().all()

    # Normalize DB values like 1.0 -> 1
    codes = []
    for v in type_codes:
        try:
            codes.append(int(v))
        except (TypeError, ValueError):
            continue

    types = [{"value": str(c), "label": TYPE_LABELS.get(c, str(c))} for c in sorted(set(codes))]

    states_out = [{"value": s, "label": state_full_name(s) or s} for s in states]
    return states_out, types


def get_year_options():
    """Years available in the search year filter (newest first)."""
    return list(SEARCH_YEAR_OPTIONS)


def normalize_search_year(year: int | None) -> int:
    """Coerce to a supported search year; invalid or missing → default."""
    if year is not None and SEARCH_YEAR_MIN <= year <= SEARCH_YEAR_MAX:
        return year
    return DEFAULT_SEARCH_YEAR


def search_colleges(
    name_substring: str,
    *,
    state: str | None = None,
    college_type: int | None = None,
    year: int = DEFAULT_SEARCH_YEAR,
    size_min: int | None = None,
    size_max: int | None = None,
    adm_min_pct: float | None = None,
    adm_max_pct: float | None = None,
    sort_key: str | None = None,
    sort_dir: str | None = None,
    limit: int = 10,
    offset: int = 0,
):
    """
    Search colleges by name and optional filters.
    """
    term = (name_substring or "").strip()
    if not term:
        return []

    # Convert percent inputs to 0..1 scale used by the DB.
    adm_min = None if adm_min_pct is None else adm_min_pct / 100.0
    adm_max = None if adm_max_pct is None else adm_max_pct / 100.0

    sort_key = (sort_key or "").strip().lower()
    sort_dir = (sort_dir or "").strip().lower()
    if sort_dir not in {"asc", "desc"}:
        sort_dir = "asc"

    sort_expr_map = {
        "name": "cs.name",
        "state": "cs.state",
        "type": "cs.type",
        "size": "ld.num_students",
        "sat_avg": "ld.sat_avg",
        "admission_rate": "ld.admission_rate",
    }
    sort_expr = sort_expr_map.get(sort_key, "cs.name")

    # NULLS LAST emulation for MySQL: order by (expr IS NULL), then expr
    order_by = f"({sort_expr} IS NULL) ASC, {sort_expr} {sort_dir.upper()}, cs.name ASC"

    year = normalize_search_year(year)
    ld_join = """
        SELECT cd.college_id, cd.year, cd.num_students, cd.admission_rate, cd.sat_avg
        FROM colleges_dynamic cd
        WHERE cd.year = :year
    """

    sql = f"""
        SELECT
            cs.college_id,
            cs.name,
            cs.state,
            cs.type AS type_code,
            CAST(ld.num_students AS SIGNED) AS num_students,
            CAST(ld.sat_avg AS SIGNED) AS sat_avg,
            adm_avg.avg_admission_rate AS admission_rate_avg,
            ld.admission_rate,
            ld.year AS data_year
        FROM colleges_static cs
        LEFT JOIN (
            SELECT college_id, AVG(admission_rate) AS avg_admission_rate
            FROM colleges_dynamic
            WHERE admission_rate IS NOT NULL
              AND year BETWEEN {SEARCH_YEAR_MIN} AND {SEARCH_YEAR_MAX}
            GROUP BY college_id
        ) adm_avg
          ON adm_avg.college_id = cs.college_id
        LEFT JOIN (
            {ld_join}
        ) ld
          ON ld.college_id = cs.college_id
        WHERE LOWER(cs.name) LIKE LOWER(:pat)
          AND (:state IS NULL OR cs.state = :state)
          AND (:ctype IS NULL OR cs.type = :ctype)
          AND (:size_min IS NULL OR ld.num_students >= :size_min)
          AND (:size_max IS NULL OR ld.num_students <= :size_max)
          AND (:adm_min IS NULL OR ld.admission_rate >= :adm_min)
          AND (:adm_max IS NULL OR ld.admission_rate <= :adm_max)
        ORDER BY {order_by}
        LIMIT :lim OFFSET :off
    """

    params = {
        "pat": f"%{term}%",
        "state": state or None,
        "ctype": college_type or None,
        "size_min": size_min,
        "size_max": size_max,
        "adm_min": adm_min,
        "adm_max": adm_max,
        "lim": limit,
        "off": offset,
        "year": year,
    }

    rows = db.session.execute(text(sql), params).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        try:
            code = int(d.get("type_code")) if d.get("type_code") is not None else None
        except (TypeError, ValueError):
            code = None
        d["type_label"] = TYPE_LABELS.get(code, None)

        # Defensive: sometimes drivers return numeric as float/Decimal.
        ns = d.get("num_students")
        if ns is not None:
            try:
                d["num_students"] = int(ns)
            except (TypeError, ValueError):
                pass

        sa = d.get("sat_avg")
        if sa is not None:
            try:
                d["sat_avg"] = int(sa)
            except (TypeError, ValueError):
                pass

        d["state_full"] = state_full_name(d.get("state"))

        dy = d.get("data_year")
        if dy is not None:
            try:
                d["data_year"] = int(dy)
            except (TypeError, ValueError):
                pass

        ar_avg = d.get("admission_rate_avg")
        if ar_avg is not None:
            try:
                d["admission_rate_avg"] = float(ar_avg)
            except (TypeError, ValueError):
                pass

        out.append(d)
    return out


def count_colleges(
    name_substring: str,
    *,
    state: str | None = None,
    college_type: int | None = None,
    year: int = DEFAULT_SEARCH_YEAR,
    size_min: int | None = None,
    size_max: int | None = None,
    adm_min_pct: float | None = None,
    adm_max_pct: float | None = None,
) -> int:
    term = (name_substring or "").strip()
    if not term:
        return 0

    adm_min = None if adm_min_pct is None else adm_min_pct / 100.0
    adm_max = None if adm_max_pct is None else adm_max_pct / 100.0

    year = normalize_search_year(year)
    ld_join = """
        SELECT cd.college_id, cd.year, cd.num_students, cd.admission_rate, cd.sat_avg
        FROM colleges_dynamic cd
        WHERE cd.year = :year
    """

    sql = f"""
        SELECT COUNT(DISTINCT cs.college_id) AS cnt
        FROM colleges_static cs
        LEFT JOIN (
            {ld_join}
        ) ld
          ON ld.college_id = cs.college_id
        WHERE LOWER(cs.name) LIKE LOWER(:pat)
          AND (:state IS NULL OR cs.state = :state)
          AND (:ctype IS NULL OR cs.type = :ctype)
          AND (:size_min IS NULL OR ld.num_students >= :size_min)
          AND (:size_max IS NULL OR ld.num_students <= :size_max)
          AND (:adm_min IS NULL OR ld.admission_rate >= :adm_min)
          AND (:adm_max IS NULL OR ld.admission_rate <= :adm_max)
    """

    params = {
        "pat": f"%{term}%",
        "state": state or None,
        "ctype": college_type or None,
        "size_min": size_min,
        "size_max": size_max,
        "adm_min": adm_min,
        "adm_max": adm_max,
        "year": year,
    }

    return int(db.session.execute(text(sql), params).scalar() or 0)


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


@search.route("/search", methods=["GET"])
def index():
    q = request.args.get("q", "").strip()
    state = (request.args.get("state") or "").strip() or None
    college_type = _parse_int(request.args.get("type"))

    year = normalize_search_year(_parse_int((request.args.get("year") or "").strip()))

    size_min = _parse_int(request.args.get("size_min"))
    size_max = _parse_int(request.args.get("size_max"))
    adm_min_pct = _parse_float(request.args.get("adm_min"))
    adm_max_pct = _parse_float(request.args.get("adm_max"))

    # Normalize swapped ranges if user enters them backwards.
    if size_min is not None and size_max is not None and size_min > size_max:
        size_min, size_max = size_max, size_min
    if adm_min_pct is not None and adm_max_pct is not None and adm_min_pct > adm_max_pct:
        adm_min_pct, adm_max_pct = adm_max_pct, adm_min_pct

    page = _parse_int(request.args.get("page")) or 1
    if page < 1:
        page = 1
    page_size = 10
    offset = (page - 1) * page_size

    sort = (request.args.get("sort") or "").strip()
    direction = (request.args.get("dir") or "").strip()
    arrow = (request.args.get("arrow") or "").strip()

    total = (
        count_colleges(
            q,
            state=state,
            college_type=college_type,
            year=year,
            size_min=size_min,
            size_max=size_max,
            adm_min_pct=adm_min_pct,
            adm_max_pct=adm_max_pct,
        )
        if q
        else 0
    )

    results = (
        search_colleges(
            q,
            state=state,
            college_type=college_type,
            year=year,
            size_min=size_min,
            size_max=size_max,
            adm_min_pct=adm_min_pct,
            adm_max_pct=adm_max_pct,
            sort_key=sort,
            sort_dir=direction,
            limit=page_size,
            offset=offset,
        )
        if q
        else []
    )

    total_pages = max(1, (total + page_size - 1) // page_size) if q else 0
    if total_pages and page > total_pages:
        page = total_pages

    states, types = get_search_filter_options()
    years = get_year_options()

    return render_template(
        "search.html",
        q=q,
        results=results,
        total=total,
        page=page,
        total_pages=total_pages,
        states=states,
        types=types,
        years=years,
        selected_year=str(year),
        default_search_year=str(DEFAULT_SEARCH_YEAR),
        selected_state=state or "",
        selected_type=str(college_type) if college_type is not None else "",
        size_min=size_min if size_min is not None else "",
        size_max=size_max if size_max is not None else "",
        adm_min=adm_min_pct if adm_min_pct is not None else "",
        adm_max=adm_max_pct if adm_max_pct is not None else "",
        sort=sort,
        dir=direction,
        arrow=arrow,
    )


@search.get("/search/college/<int:college_id>/metrics")
def college_metrics(college_id: int):
    """Time series from colleges_dynamic for chart (all years for one college)."""
    rows = db.session.execute(
        text(
            "SELECT year, avg_cost_of_attendance, admission_rate, sat_avg, graduation_rate "
            "FROM colleges_dynamic "
            "WHERE college_id = :cid "
            "AND year BETWEEN :ymin AND :ymax "
            "ORDER BY year ASC"
        ),
        {"cid": college_id, "ymin": SEARCH_YEAR_MIN, "ymax": SEARCH_YEAR_MAX},
    ).mappings().all()

    years = []
    costs = []
    admissions_pct = []
    sat_avgs = []
    graduation_rate_pct = []
    for r in rows:
        y = r.get("year")
        try:
            y = int(y)
        except (TypeError, ValueError):
            continue
        years.append(y)
        costs.append(r.get("avg_cost_of_attendance"))
        ar = r.get("admission_rate")
        admissions_pct.append(None if ar is None else float(ar) * 100.0)
        sa = r.get("sat_avg")
        sat_avgs.append(None if sa is None else int(sa))
        gr = r.get("graduation_rate")
        graduation_rate_pct.append(None if gr is None else float(gr) * 100.0)

    return jsonify(
        {
            "college_id": college_id,
            "years": years,
            "avg_cost_of_attendance": costs,
            "admission_rate_pct": admissions_pct,
            "sat_avg": sat_avgs,
            "graduation_rate_pct": graduation_rate_pct,
        }
    )

import requests
import os
import pandas as pd
import math
import numpy as np
import psycopg2
import psycopg2.extras
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

# This script fetches data from the College Scorecard API and saves it to the database.
# There's a limit of 1000 requests per hour (one run is about 60 requests per year),
# so it shouldn't be run all the time.
# Run quarterly or when CollegeScorecard is updated:
# https://collegescorecard.ed.gov/data/changelog/

key = os.environ['SCORECARD_API_KEY']
url_base = "https://api.data.gov/ed/collegescorecard/v1/schools/"
LATEST_YEAR = 2023  # year of latest available data

# Fields that never change year-over-year, only fetched for LATEST_YEAR.
STATIC_FIELDS = [
    'id',
    'school.name',
    'school.city',
    'school.school_url',
    'school.price_calculator_url',
    'school.state',
    'school.locale',
    'school.region_id',
    'school.ownership_peps',
    'school.religious_affiliation',
    'school.online_only',
    'school.men_only',
    'school.women_only',
    'school.minority_serving.historically_black',
    'school.minority_serving.predominantly_black',
    'school.minority_serving.annh',
    'school.minority_serving.aanipi',
    'school.minority_serving.tribal',
    'school.minority_serving.hispanic',
    'school.institutional_characteristics.level',
    # Program percentages are also static (major offerings don't change often)
    'latest.academics.program_percentage.agriculture',
    'latest.academics.program_percentage.resources',
    'latest.academics.program_percentage.architecture',
    'latest.academics.program_percentage.ethnic_cultural_gender',
    'latest.academics.program_percentage.communication',
    'latest.academics.program_percentage.communications_technology',
    'latest.academics.program_percentage.computer',
    'latest.academics.program_percentage.personal_culinary',
    'latest.academics.program_percentage.education',
    'latest.academics.program_percentage.engineering',
    'latest.academics.program_percentage.engineering_technology',
    'latest.academics.program_percentage.language',
    'latest.academics.program_percentage.family_consumer_science',
    'latest.academics.program_percentage.legal',
    'latest.academics.program_percentage.english',
    'latest.academics.program_percentage.humanities',
    'latest.academics.program_percentage.library',
    'latest.academics.program_percentage.biological',
    'latest.academics.program_percentage.mathematics',
    'latest.academics.program_percentage.military',
    'latest.academics.program_percentage.multidiscipline',
    'latest.academics.program_percentage.parks_recreation_fitness',
    'latest.academics.program_percentage.philosophy_religious',
    'latest.academics.program_percentage.theology_religious_vocation',
    'latest.academics.program_percentage.physical_science',
    'latest.academics.program_percentage.science_technology',
    'latest.academics.program_percentage.psychology',
    'latest.academics.program_percentage.security_law_enforcement',
    'latest.academics.program_percentage.public_administration_social_service',
    'latest.academics.program_percentage.social_science',
    'latest.academics.program_percentage.construction',
    'latest.academics.program_percentage.mechanic_repair_technology',
    'latest.academics.program_percentage.precision_production',
    'latest.academics.program_percentage.transportation',
    'latest.academics.program_percentage.visual_performing',
    'latest.academics.program_percentage.health',
    'latest.academics.program_percentage.business_marketing',
    'latest.academics.program_percentage.history',
]

# Fields that vary year-over-year, fetched for every year.
# Uses "latest." prefix which gets rewritten to the target year by fields_for_year().
DYNAMIC_FIELDS = [
    'id',
    'school.institutional_characteristics.level',  # needed for filtering
    'latest.student.size',
    'latest.admissions.admission_rate.by_ope_id',
    'latest.admissions.sat_scores.midpoint.critical_reading',
    'latest.admissions.sat_scores.midpoint.math',
    'latest.admissions.sat_scores.average.by_ope_id',
    'latest.admissions.act_scores.midpoint.cumulative',
    'latest.completion.completion_rate_4yr_100nt',
    'latest.earnings.6_yrs_after_entry.median',
    'latest.earnings.10_yrs_after_entry.median',
    'latest.cost.attendance.academic_year',
    'latest.cost.tuition.in_state',
    'latest.cost.tuition.out_of_state',
    'latest.cost.net_price.public.by_income_level.0-30000',
    'latest.cost.net_price.public.by_income_level.30001-48000',
    'latest.cost.net_price.public.by_income_level.48001-75000',
    'latest.cost.net_price.public.by_income_level.75001-110000',
    'latest.cost.net_price.public.by_income_level.110001-plus',
    'latest.cost.net_price.private.by_income_level.0-30000',
    'latest.cost.net_price.private.by_income_level.30001-48000',
    'latest.cost.net_price.private.by_income_level.48001-75000',
    'latest.cost.net_price.private.by_income_level.75001-110000',
    'latest.cost.net_price.private.by_income_level.110001-plus',
    'latest.aid.median_debt.completers.overall',
]

# Maps API program_percentage field suffix -> canonical major name
# Must match form.py major choices exactly
MAJOR_MAP = {
    'agriculture':                          'Agriculture, Agriculture Operations, And Related Sciences',
    'resources':                            'Natural Resources And Conservation',
    'architecture':                         'Architecture And Related Services',
    'ethnic_cultural_gender':               'Area, Ethnic, Cultural, Gender, And Group Studies',
    'communication':                        'Communication, Journalism, And Related Programs',
    'communications_technology':            'Communications Technologies/Technicians And Support Services',
    'computer':                             'Computer And Information Sciences And Support Services',
    'personal_culinary':                    'Personal And Culinary Services',
    'education':                            'Education',
    'engineering':                          'Engineering',
    'engineering_technology':               'Engineering Technologies And Engineering-Related Fields',
    'language':                             'Foreign Languages, Literatures, And Linguistics',
    'family_consumer_science':              'Family And Consumer Sciences/Human Sciences',
    'legal':                                'Legal Professions And Studies',
    'english':                              'English Language And Literature/Letters',
    'humanities':                           'Liberal Arts And Sciences, General Studies And Humanities',
    'library':                              'Library Science',
    'biological':                           'Biological And Biomedical Sciences',
    'mathematics':                          'Mathematics And Statistics',
    'military':                             'Military Technologies And Applied Sciences',
    'multidiscipline':                      'Multi/Interdisciplinary Studies',
    'parks_recreation_fitness':             'Parks, Recreation, Leisure, And Fitness Studies',
    'philosophy_religious':                 'Philosophy And Religious Studies',
    'theology_religious_vocation':          'Theology And Religious Vocations',
    'physical_science':                     'Physical Sciences',
    'science_technology':                   'Science Technologies/Technicians',
    'psychology':                           'Psychology',
    'security_law_enforcement':             'Homeland Security, Law Enforcement, Firefighting And Related Protective Services',
    'public_administration_social_service': 'Public Administration And Social Service Professions',
    'social_science':                       'Social Sciences',
    'construction':                         'Construction Trades',
    'mechanic_repair_technology':           'Mechanic And Repair Technologies/Technicians',
    'precision_production':                 'Precision Production',
    'transportation':                       'Transportation And Materials Moving',
    'visual_performing':                    'Visual And Performing Arts',
    'health':                               'Health Professions And Related Programs',
    'business_marketing':                   'Business, Management, Marketing, And Related Support Services',
    'history':                              'History',
}


def fields_for_year(field_list, year):
    """
    Join a field list into a comma-separated string, rewriting "latest."
    to the target year prefix for historical years.
    """
    joined = ','.join(field_list)
    if year == LATEST_YEAR:
        return joined
    return joined.replace("latest.", f"{year}.")


def get_col_data(page, year, field_list):
    p = {
        "school.operating": "1",
        "fields": fields_for_year(field_list, year),
        "page": page,
        "per_page": 100,  # maximum value
        "api_key": key,
    }
    resp = requests.get(url=url_base, params=p)
    return resp.json()


def fetch_page(page, year, field_list, total_pages):
    """Fetch a single page; returns (page_index, results_list) or (page_index, None) on error."""
    try:
        data = get_col_data(page, year, field_list)
        print(f"  [{year}] page {page + 1}/{total_pages}")
        return page, data['results']
    except Exception as e:
        print(f"  [{year}] error on page {page}: {e}")
        return page, None


def callAPI(year, field_list, max_workers=10):
    """
    Fetch all pages for a given year concurrently using a thread pool.
    """
    first_response = get_col_data(0, year, field_list)

    if "metadata" not in first_response:
        print(f"API error for year {year}:")
        print(first_response)
        raise Exception("API response missing metadata")

    metadata = first_response["metadata"]
    total_pages = math.ceil(metadata['total'] / metadata['per_page'])
    print(f"[{year}] fetching {total_pages} pages with {max_workers} workers...")

    # results_map preserves page order regardless of thread completion order
    results_map = {0: first_response['results']}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_page, page, year, field_list, total_pages): page
            for page in range(1, total_pages)  # page 0 already fetched above
        }
        for future in as_completed(futures):
            page, results = future.result()
            if results is not None:
                results_map[page] = results

    # Reassemble in order
    all_rows = []
    for page in sorted(results_map):
        all_rows.extend(results_map[page])

    college_info = pd.DataFrame(all_rows).fillna(value=np.nan)
    college_info = college_info[
        (college_info['school.institutional_characteristics.level'] == 1)
    ].dropna(thresh=max(10, len(field_list) // 2))  # remove colleges that have more than half of the fields missing
    college_info = college_info.replace("", np.nan)
    return college_info


def build_static(df):
    static = pd.DataFrame()
    static["college_id"] = df["id"]
    static["name"] = df["school.name"]
    static["website"] = df["school.school_url"]
    static["finaid_website"] = df["school.price_calculator_url"]
    static["city"] = df["school.city"]
    static["state"] = df["school.state"]
    static["locale"] = df["school.locale"]
    static["region"] = df["school.region_id"]
    static["type"] = df["school.ownership_peps"]
    static["religious_affiliation"] = df["school.religious_affiliation"]
    static["online_only"] = df["school.online_only"].astype(bool)
    static["hbcu"] = (df["school.minority_serving.historically_black"].astype(bool) |
                      df["school.minority_serving.predominantly_black"].astype(bool))
    static["annh"] = df["school.minority_serving.annh"].astype(bool)
    static["aanipi"] = df["school.minority_serving.aanipi"].astype(bool)
    static["tribal"] = df["school.minority_serving.tribal"].astype(bool)
    static["hispanic"] = df["school.minority_serving.hispanic"].astype(bool)
    static["men_only"] = df["school.men_only"].astype(bool)
    static["women_only"] = df["school.women_only"].astype(bool)
    return static[static["name"].notna()]


def build_dynamic(df, year):
    prefix = "latest" if year == LATEST_YEAR else str(year)

    def net_price(bracket):
        pub = f"{prefix}.cost.net_price.public.by_income_level.{bracket}"
        prv = f"{prefix}.cost.net_price.private.by_income_level.{bracket}"
        return df[prv].where(df[prv].notna(), df[pub])  # keep either private or public depending on what's missing

    dynamic = pd.DataFrame()
    dynamic["college_id"] = df["id"]
    dynamic["year"] = year
    dynamic["admission_rate"] = df[f"{prefix}.admissions.admission_rate.by_ope_id"]
    dynamic["sat_rw_mid"] = df[f"{prefix}.admissions.sat_scores.midpoint.critical_reading"]
    dynamic["sat_math_mid"] = df[f"{prefix}.admissions.sat_scores.midpoint.math"]
    dynamic["sat_avg"] = df[f"{prefix}.admissions.sat_scores.average.by_ope_id"]
    dynamic["act_avg"] = df[f"{prefix}.admissions.act_scores.midpoint.cumulative"]
    dynamic["num_students"] = df[f"{prefix}.student.size"]
    dynamic["graduation_rate"] = df[f"{prefix}.completion.completion_rate_4yr_100nt"]
    dynamic["median_earnings_6yr"] = df[f"{prefix}.earnings.6_yrs_after_entry.median"]
    dynamic["median_earnings_10yr"] = df[f"{prefix}.earnings.10_yrs_after_entry.median"]
    dynamic["avg_cost_of_attendance"] = df[f"{prefix}.cost.attendance.academic_year"]
    dynamic["in_state_tuition_fees"] = df[f"{prefix}.cost.tuition.in_state"]
    dynamic["out_state_tuition_fees"] = df[f"{prefix}.cost.tuition.out_of_state"]
    dynamic["net_price_0_30k"] = net_price("0-30000")
    dynamic["net_price_30_48k"] = net_price("30001-48000")
    dynamic["net_price_48_75k"] = net_price("48001-75000")
    dynamic["net_price_75_110k"] = net_price("75001-110000")
    dynamic["net_price_110k_plus"] = net_price("110001-plus")
    dynamic["median_starting_debt"] = df[f"{prefix}.aid.median_debt.completers.overall"]
    return dynamic[dynamic["college_id"].notna()]


def build_majors_and_college_majors(df):
    majors = pd.DataFrame([
        {"major_id": i + 1, "major_name": name}
        for i, name in enumerate(sorted(MAJOR_MAP.values()))
    ])

    name_to_id = dict(zip(majors["major_name"], majors["major_id"]))
    suffix_to_id = {suffix: name_to_id[name] for suffix, name in MAJOR_MAP.items()}

    major_cols = [col for col in df.columns if "program_percentage" in col]
    # melt - turn columns into values
    long = df[["id"] + major_cols].melt(id_vars="id", var_name="major_col", value_name="percentage")
    long = long[long["percentage"] > 0]  # only keep colleges that offer that major
    long["suffix"] = long["major_col"].str.split("program_percentage.").str[-1]
    long["major_id"] = long["suffix"].map(suffix_to_id)
    long = long.dropna(subset=["major_id"])

    college_majors = (long[["id", "major_id"]]
                      .rename(columns={"id": "college_id"})
                      .drop_duplicates())
    college_majors["major_id"] = college_majors["major_id"].astype(int)

    return majors, college_majors


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db_connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", 5432)),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        dbname=os.environ["DB_NAME"],
    )  # IPv4


def clean_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


def insert_dataframe(df, table_name):
    """
    Bulk-insert a DataFrame into table_name using psycopg2's execute_values.
    Uses ON CONFLICT DO NOTHING so re-running after a partial failure is safe.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    columns = list(df.columns)
    column_names = ", ".join(columns)

    # execute_values uses a single %s placeholder representing the whole row tuple
    sql = f"""
        INSERT INTO {table_name} ({column_names})
        VALUES %s
        ON CONFLICT DO NOTHING
    """

    rows = [
        tuple(clean_value(v) for v in row)
        for row in df.to_numpy()
    ]

    psycopg2.extras.execute_values(cursor, sql, rows)
    conn.commit()

    print(f"Inserted rows into {table_name} (duplicates skipped)")

    cursor.close()
    conn.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_year(year):
    """Fetch, build, and insert data for one year. Called from a thread pool."""
    if year == LATEST_YEAR:
        # For the latest year, fetch everything in one API pass and
        # build all four tables from it.
        print(f"Fetching static + dynamic data for {year}...")
        all_fields = STATIC_FIELDS + [f for f in DYNAMIC_FIELDS if f not in STATIC_FIELDS]
        df = callAPI(year, all_fields)

        static = build_static(df)
        print(f"Inserting {len(static)} rows into colleges_static...")
        insert_dataframe(static, "colleges_static")

        majors, college_majors = build_majors_and_college_majors(df)
        print(f"Inserting {len(majors)} rows into majors...")
        insert_dataframe(majors, "majors")
        print(f"Inserting {len(college_majors)} rows into college_majors...")
        insert_dataframe(college_majors, "college_majors")

    else:
        # For historical years, only fetch the dynamic fields.
        print(f"Fetching dynamic data for {year}...")
        df = callAPI(year, DYNAMIC_FIELDS)

    dynamic = build_dynamic(df, year)  # build dynamic for all
    print(f"Inserting {len(dynamic)} rows for {year} into colleges_dynamic...")
    insert_dataframe(dynamic, "colleges_dynamic")
    print(f"[{year}] done.")


if __name__ == '__main__':
    YEARS = [2020, 2021, 2022, 2023]

    # Fetch and insert all years in parallel.
    # Each year gets its own thread; within each year, pages are also
    # fetched in parallel (see callAPI). DB inserts use separate
    # connections per call so there's no shared state to worry about.
    # Cap at 4 workers, one per year, so we don't blow the rate limit.
    with ThreadPoolExecutor(max_workers=len(YEARS)) as executor:
        futures = {executor.submit(process_year, year): year for year in YEARS}
        for future in as_completed(futures):
            year = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"[{year}] failed: {e}")

    print("Done.")
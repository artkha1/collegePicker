-- =====================================================================
-- COLLEGE Picker — DATABASE SCHEMA
-- PostgreSQL
-- =====================================================================


-- =====================================================================
-- COLLEGE DATA TABLES (read-only from the app's perspective)
-- =====================================================================

CREATE TABLE colleges_static (
    college_id              INT PRIMARY KEY,
    name                    VARCHAR(255) NOT NULL,
    website                 VARCHAR(255),
    finaid_website          VARCHAR(255),
    city                    VARCHAR(255),
    state                   VARCHAR(255),
    region                  INT,
    locale                  INT,
    type                    INT,
    religious_affiliation   INT,
    online_only             BOOLEAN,
    hbcu                    BOOLEAN,
    aanipi                  BOOLEAN,
    annh                    BOOLEAN,
    tribal                  BOOLEAN,
    hispanic                BOOLEAN,
    men_only                BOOLEAN,
    women_only              BOOLEAN
);

CREATE TABLE colleges_dynamic (
    college_id              INT REFERENCES colleges_static(college_id),
    year                    INT NOT NULL,
    admission_rate          FLOAT   CHECK (admission_rate  IS NULL OR admission_rate  BETWEEN 0 AND 1),
    sat_rw_mid              INT,
    sat_math_mid            INT,
    sat_avg                 INT,
    act_avg                 FLOAT,
    graduation_rate         FLOAT   CHECK (graduation_rate IS NULL OR graduation_rate BETWEEN 0 AND 1),
    median_earnings_6yr     FLOAT,
    median_earnings_10yr    FLOAT,
    avg_cost_of_attendance  FLOAT,
    in_state_tuition_fees   FLOAT,
    out_state_tuition_fees  FLOAT,
    net_price_0_30k         FLOAT,
    net_price_30_48k        FLOAT,
    net_price_48_75k        FLOAT,
    net_price_75_110k       FLOAT,
    net_price_110k_plus     FLOAT,
    median_starting_debt    FLOAT,
    num_students            INT,
    PRIMARY KEY (college_id, year)
);

CREATE TABLE majors (
    major_id    INT PRIMARY KEY,
    major_name  VARCHAR(255) NOT NULL
);

CREATE TABLE college_majors (
    college_id  INT REFERENCES colleges_static(college_id),
    major_id    INT REFERENCES majors(major_id),
    PRIMARY KEY (college_id, major_id)
);


-- =====================================================================
-- USER TABLE
--
-- Multi-select preferences are stored as JSON arrays of integer codes,
-- matching the choice codes defined in form.py.  This eliminates 7
-- child tables and their associated foreign keys without losing any
-- information — the codes and their meanings are static app-level
-- constants, not data that needs to be queried relationally.
--
-- Rows with email IS NULL are anonymous (session-only) visitors.
-- They are cleaned up by the purge_anonymous_users() function in
-- models.py after a configurable TTL (default 24 hours).
-- =====================================================================

CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Auth (NULL for anonymous visitors)
    email       VARCHAR(255) UNIQUE,
    password    VARCHAR(255),
    name        VARCHAR(255),

    -- Scalar questionnaire answers
    rel_imp     INT  CHECK (rel_imp     IS NULL OR rel_imp     BETWEEN 1 AND 11),
    size_imp    INT  CHECK (size_imp    IS NULL OR size_imp    BETWEEN 1 AND 11),
    setting_imp INT  CHECK (setting_imp IS NULL OR setting_imp BETWEEN 1 AND 11),
    region_imp  INT  CHECK (region_imp  IS NULL OR region_imp  BETWEEN 1 AND 11),
    state_imp   INT  CHECK (state_imp   IS NULL OR state_imp   BETWEEN 1 AND 11),
    all_majors  BOOLEAN,
    sat_math    INT  CHECK (sat_math    IS NULL OR sat_math    BETWEEN 200 AND 800),
    sat_eng     INT  CHECK (sat_eng     IS NULL OR sat_eng     BETWEEN 200 AND 800),
    act         INT  CHECK (act         IS NULL OR act         BETWEEN 1   AND 36),
    income      INT  CHECK (income      IS NULL OR income      BETWEEN 0   AND 5),

    -- Multi-select preferences stored as JSON integer arrays.
    -- e.g. rel_affil = [1, 3]  (codes from form.py religionChoices)
    rel_affil   JSONB NOT NULL DEFAULT '[]',
    sizes       JSONB NOT NULL DEFAULT '[]',
    sel_majors  JSONB NOT NULL DEFAULT '[]',  -- user's chosen majors
    settings    JSONB NOT NULL DEFAULT '[]',
    regions     JSONB NOT NULL DEFAULT '[]',
    states      JSONB NOT NULL DEFAULT '[]',
    spec_prefs  JSONB NOT NULL DEFAULT '[]'
);

-- Index to make the anonymous-cleanup query fast
CREATE INDEX idx_users_anon_cleanup ON users (created_at) WHERE email IS NULL;
import pandas as pd
import numpy as np
from sqlalchemy import text

from __init__ import db
from models import GET_TOP_COLLEGES_SQL


def load_college_data(user_id: int) -> pd.DataFrame:
    """
    Run the GET_TOP_COLLEGES_SQL raw-SQL query for this user and return
    the results as a DataFrame.  Replaces the old stored-procedure callproc.
    """
    with db.engine.connect() as conn:
        result = conn.execute(
            GET_TOP_COLLEGES_SQL,
            {
                "user_id":    int(user_id),
                "all_majors": bool(
                    conn.execute(
                        text("SELECT all_majors FROM users WHERE id = :uid"),
                        {"uid": user_id},
                    ).scalar()
                ),
            },
        )
        rows = result.mappings().all()

    return pd.DataFrame(rows)



def calc(rels, sizes, majors, settings, regions, states, specPrefs,
         relImp, sizeImp, allMajors, satMath, satEng, act,
         setImp, regImp, stImp, income, user_id):

    collegeInfo = load_college_data(user_id)

    collegeInfo['Score'] = 0
    maxScore = 0

    # Fix website URLs
    def fix_url(url):
        if isinstance(url, str):  # avoid NaNs
            if 'https' in url:
                return url
            elif 'www' in url:
                return 'https://' + url
            else:
                return 'https://www.' + url
        return url
    collegeInfo['website'] = collegeInfo['website'].apply(fix_url)
    collegeInfo['finaid_website'] = collegeInfo['finaid_website'].apply(fix_url)

    # Religious affiliation scoring - map numeric codes to simplified groups
    relsDict = {-1:4,-2:4,22:2,24:2,27:2,28:2,30:1,33:2,34:2,35:2,36:2,37:2,38:2,39:2,40:2,41:2,42:2,43:2,44:2,45:2,47:2,48:2,49:2,50:2,51:2,52:2,53:2,54:2,55:2,57:2,58:2,59:2,60:2,61:2,64:2,65:2,66:2,
    67:2,68:2,69:2,71:2,73:2,74:2,75:2,76:2,77:2,78:2,79:2,80:3,81:2,84:2,87:2,88:2,89:2,91:2,92:2,93:2,94:2,95:2,97:2,99:3,100:2,101:2,102:2,103:2,105:2,106:3,107:2}
    collegeInfo['rel_code'] = collegeInfo['religious_affiliation'].map(relsDict).fillna(4)

    if len(rels) > 0:
        user_rel_codes = [r.code for r in rels]
        if relImp == 11:  # filter out those that don't match the preference
            collegeInfo = collegeInfo[collegeInfo['rel_code'].isin(user_rel_codes)]
        else:
            collegeInfo.loc[collegeInfo['rel_code'].isin(user_rel_codes), 'Score'] += relImp * 10
            maxScore += relImp * 10

    # Size scoring
    def size_code(row):
        n = row['num_students']
        if pd.isna(n):
            return None
        if n > 15000:
            return 1
        elif n < 5000:
            return 3
        else:
            return 2
    collegeInfo['sizeCode'] = collegeInfo.apply(size_code, axis=1)

    if len(sizes) > 0:
        user_size_codes = [s.code for s in sizes]
        if sizeImp == 11:
            collegeInfo = collegeInfo[collegeInfo['sizeCode'].isin(user_size_codes)]
        else:
            collegeInfo.loc[collegeInfo['sizeCode'].isin(user_size_codes), 'Score'] += sizeImp * 10
            maxScore += sizeImp * 10

    # Majors - soft scoring (hard filtering already done by stored procedure)
    if len(majors) > 0:
        user_major_ids = set(m.code for m in majors)
        matched = collegeInfo['matched_major_count'].fillna(0)
        total = len(user_major_ids) if user_major_ids else 1
        collegeInfo['Score'] += (matched / total) * 50
        maxScore += 50

    # Setting scoring
    setDict = {11:1,12:1,13:1,21:2,22:2,23:2,31:2,32:2,33:2,41:3,42:3,43:3}
    collegeInfo['settingCode'] = collegeInfo['locale'].map(setDict)

    if len(settings) > 0:
        user_setting_codes = [s.code for s in settings]
        if setImp == 11:
            collegeInfo = collegeInfo[collegeInfo['settingCode'].isin(user_setting_codes)]
        else:
            collegeInfo.loc[collegeInfo['settingCode'].isin(user_setting_codes), 'Score'] += setImp * 10
            maxScore += setImp * 10

    # Region scoring (hard filter already applied in stored procedure when regImp=11)
    if len(regions) > 0 and regImp != 11:
        user_region_codes = [r.code - 1 for r in regions]
        collegeInfo.loc[collegeInfo['region'].isin(user_region_codes), 'Score'] += regImp * 10
        maxScore += regImp * 10

    # State scoring (hard filter already applied in SP when stImp=11)
    if len(states) > 0 and stImp != 11:
        user_state_names = [s.name for s in states]
        collegeInfo.loc[collegeInfo['state'].isin(user_state_names), 'Score'] += stImp * 10
        maxScore += stImp * 10

    # Special preferences were already handled in SP

    # Test scores
    if satMath is None:
        satMath = np.nan
    if satEng is None:
        satEng = np.nan
    if act is None:
        act = np.nan

    collegeInfo['SAT Math deviation'] = abs(collegeInfo['sat_math_mid'] - satMath)
    collegeInfo['SAT English deviation'] = abs(collegeInfo['sat_rw_mid'] - satEng)
    collegeInfo['SAT total deviation'] = abs(collegeInfo['sat_avg'] - (satMath + satEng))
    collegeInfo['ACT deviation'] = abs(collegeInfo['act_avg']-act) 

    # Normalise continuous columns
    cols_to_norm = [
        'SAT Math deviation', 'SAT English deviation', 'SAT total deviation', 'ACT deviation',
        'net_price_0_30k', 'net_price_30_48k', 'net_price_48_75k', 'net_price_75_110k', 'net_price_110k_plus',
        'avg_cost_of_attendance',
        'median_earnings_6yr',
        'graduation_rate',
    ]
    for col in cols_to_norm:
        mn, mx = collegeInfo[col].min(), collegeInfo[col].max()
        collegeInfo[col + ' normalized'] = ((collegeInfo[col] - mn) / (mx - mn)) * 100

    def update_score_tests(row):
        row = row.copy()
        candidates = []

        if pd.notna(satMath) and pd.notna(satEng):
            candidates.append(row.get('SAT Math deviation normalized', np.nan) * 0.5 + 
                            row.get('SAT English deviation normalized', np.nan) * 0.5)
            candidates.append(row.get('SAT total deviation normalized', np.nan))

        if pd.notna(act):
            candidates.append(row.get('ACT deviation normalized', np.nan))

        valid = [c for c in candidates if pd.notna(c)]
        if candidates:  # user provided something
            row['Score'] -= min(valid) if valid else 100

        return row
    collegeInfo = collegeInfo.apply(update_score_tests, axis=1)

    # Cost scoring
    income_col_map = {
        1: 'net_price_0_30k',
        2: 'net_price_30_48k',
        3: 'net_price_48_75k',
        4: 'net_price_75_110k',
        5: 'net_price_110k_plus',
    }
    def update_score_cost(row):
        row = row.copy()
        cost_col = income_col_map.get(income)
        cost_norm = row.get(cost_col + ' normalized', np.nan) if cost_col else np.nan

        # fall back to avg cost of attendance if income-specific price is missing
        if pd.isna(cost_norm):
            cost_norm = row.get('avg_cost_of_attendance normalized', np.nan)

        row['Score'] -= cost_norm if pd.notna(cost_norm) else 100
        return row
    collegeInfo = collegeInfo.apply(update_score_cost, axis=1)

    # Earnings and graduation rate (higher = better)
    collegeInfo['Score'] += collegeInfo.get('median_earnings_6yr normalized',
                             pd.Series(0, index=collegeInfo.index)).fillna(0)
    collegeInfo['Score'] += collegeInfo.get('graduation_rate normalized',
                             pd.Series(0, index=collegeInfo.index)).fillna(0)
    maxScore += 200

    # Match percentage
    collegeInfo['Match'] = (collegeInfo['Score'] / maxScore * 100).round(1).clip(lower=0)

    
    # --- Formatting (display only, after all scoring) ---
    # Format columns
    colsToInt = [
        'num_students',
        'sat_rw_mid',
        'sat_math_mid',
        'sat_avg',
        'avg_cost_of_attendance',
        'in_state_tuition_fees',
        'out_state_tuition_fees',
        'median_starting_debt',
        'median_earnings_6yr',
        'median_earnings_10yr',
    ]  # convert to int
    rateCols = [
        'admission_rate',
        'graduation_rate',
    ]

    collegeInfo[rateCols] = (collegeInfo[rateCols].fillna(0) * 100).round(2).astype(str).apply(lambda x: x + '%')

    for col in colsToInt:
        collegeInfo[col] = collegeInfo[col].fillna(0).astype(int).apply('{:,}'.format)
    
    # Decode numeric codes to human-readable strings
    relstrDict = {22:'American Evangelical Lutheran Church',24:'African Methodist Episcopal Zion Church',
    27:'Assemblies of God Church',28:'Brethren Church',30:'Roman Catholic',33:'Wisconsin Evangelical Lutheran Synod',
    34:'Christ and Missionary Alliance Church',35:'Christian Reformed Church',36:'Evangelical Congregational Church',
    37:'Evangelical Covenant Church of America',38:'Evangelical Free Church of America',39:'Evangelical Lutheran Church',
    40:'International United Pentecostal Church',41:'Free Will Baptist Church',42:'Interdenominational',
    43:'Mennonite Brethren Church',44:'Moravian Church',45:'North American Baptist',47:'Pentecostal Holiness Church',
    48:'Christian Churches and Churches of Christ',49:'Reformed Church in America',50:'Episcopal Church, Reformed',
    51:'African Methodist Episcopal',52:'American Baptist',53:'American Lutheran',54:'Baptist',
    55:'Christian Methodist Episcopal',57:'Church of God',58:'Church of Brethren',59:'Church of the Nazarene',
    60:'Cumberland Presbyterian',61:'Christian Church (Disciples of Christ)',64:'Free Methodist',65:'Friends',
    66:'Presbyterian Church (USA)',67:'Lutheran Church in America',68:'Lutheran Church - Missouri Synod',
    69:'Mennonite Church',71:'United Methodist',73:'Protestant Episcopal',74:'Churches of Christ',
    75:'Southern Baptist',76:'United Church of Christ',77:'Protestant, not specified',
    78:'Multiple Protestant Denomination',79:'Other Protestant',80:'Jewish',81:'Reformed Presbyterian Church',
    84:'United Brethren Church',87:'Missionary Church Inc',88:'Undenominational',89:'Wesleyan',
    91:'Greek Orthodox',92:'Russian Orthodox',93:'Unitarian Universalist',94:'Latter Day Saints (Mormon Church)',
    95:'Seventh Day Adventists',97:'The Presbyterian Church in America',99:'Other',100:'Original Free Will Baptist',
    101:'Ecumenical Christian',102:'Evangelical Christian',103:'Presbyterian',105:'General Baptist',
    106:'Muslim',107:'Plymouth Brethren'}
    collegeInfo['religious_affiliation'] = collegeInfo['religious_affiliation'].map(relstrDict)

    localestrDict = {11:'Large City',12:'Midsize City',13:'Small City',21:'Large Suburb',22:'Midsize Suburb',
    23:'Small Suburb',31:'Fringe Town',32:'Distant Town',33:'Remote Town',
    41:'Fringe Rural',42:'Distant Rural',43:'Remote Rural'}
    collegeInfo['locale'] = collegeInfo['locale'].map(localestrDict)

    ownDict = {1:'Public', 2:'Private Non-Profit', 3:'Private For-Profit'}
    collegeInfo['type'] = collegeInfo['type'].map(ownDict)

    # Convert remaining numeric columns to formatted strings
    if len(collegeInfo) > 0:
        for numCol in list(collegeInfo.select_dtypes('number')):
            if numCol != 'Score':
                collegeInfo[numCol] = collegeInfo[numCol].apply(
                    lambda x: '{:,}'.format(x) if pd.notna(x) else np.nan
                )

    collegeInfo = collegeInfo.where(pd.notnull(collegeInfo), None)
    return collegeInfo
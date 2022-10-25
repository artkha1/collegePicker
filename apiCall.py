import requests
import os
import pandas as pd
import math
import numpy as np
from flask import url_for

#the below code accesses data from the collegeScorecard API. However, it takes a pretty long time to run and there's a limit of 1000 requests per hour (one run of the below code 
#is about 250 requests), so it shouldn't be run all the time. Instead, it should be run once in a while and the data should be saved as a csv file.
#Since the data is pretty much always the same and is infrequently updated, it should be run quarterly, or even more rarely, when CollegeScorecard is updated (https://collegescorecard.ed.gov/data/changelog/)

key = "secret" #TODO: Remove when uploading
url_base = "https://api.data.gov/ed/collegescorecard/v1/schools/"
fields = ','.join(['id','school.religious_affiliation','latest.student.size',
	'latest.academics.program_percentage.agriculture','latest.academics.program_percentage.resources','latest.academics.program_percentage.architecture','latest.academics.program_percentage.ethnic_cultural_gender',
	'latest.academics.program_percentage.communication','latest.academics.program_percentage.communications_technology','latest.academics.program_percentage.computer','latest.academics.program_percentage.personal_culinary',
	'latest.academics.program_percentage.education','latest.academics.program_percentage.engineering','latest.academics.program_percentage.engineering_technology','latest.academics.program_percentage.language',
	'latest.academics.program_percentage.family_consumer_science','latest.academics.program_percentage.legal','latest.academics.program_percentage.english','latest.academics.program_percentage.humanities',
	'latest.academics.program_percentage.library','latest.academics.program_percentage.biological','latest.academics.program_percentage.mathematics','latest.academics.program_percentage.military',
	'latest.academics.program_percentage.multidiscipline','latest.academics.program_percentage.parks_recreation_fitness','latest.academics.program_percentage.philosophy_religious',
	'latest.academics.program_percentage.theology_religious_vocation','latest.academics.program_percentage.physical_science','latest.academics.program_percentage.science_technology',
	'latest.academics.program_percentage.psychology','latest.academics.program_percentage.security_law_enforcement','latest.academics.program_percentage.public_administration_social_service',
	'latest.academics.program_percentage.social_science','latest.academics.program_percentage.construction','latest.academics.program_percentage.mechanic_repair_technology','latest.academics.program_percentage.precision_production',
	'latest.academics.program_percentage.transportation','latest.academics.program_percentage.visual_performing','latest.academics.program_percentage.health','latest.academics.program_percentage.business_marketing','latest.academics.program_percentage.history',
	'latest.admissions.sat_scores.midpoint.critical_reading','latest.admissions.sat_scores.midpoint.math', 'latest.admissions.sat_scores.average.by_ope_id','latest.admissions.act_scores.midpoint.cumulative'
	'school.locale','school.region_id','school.state',
	'school.minority_serving.historically_black','school.minority_serving.predominantly_black','school.minority_serving.annh',
	'school.minority_serving.aanipi','school.minority_serving.tribal','school.minority_serving.hispanic','school.men_only',
	'school.women_only','school.online_only',
	'latest.cost.net_price.public.by_income_level.0-30000','latest.cost.net_price.public.by_income_level.30001-48000',
	'latest.cost.net_price.public.by_income_level.48001-75000','latest.cost.net_price.public.by_income_level.75001-110000',
	'latest.cost.net_price.public.by_income_level.110001-plus','latest.cost.net_price.private.by_income_level.0-30000',
	'latest.cost.net_price.private.by_income_level.30001-48000','latest.cost.net_price.private.by_income_level.48001-75000',
	'latest.cost.net_price.private.by_income_level.75001-110000','latest.cost.net_price.private.by_income_level.110001-plus',
	'latest.cost.attendance.academic_year','latest.cost.tuition.in_state','latest.cost.tuition.out_of_state',
	'latest.aid.median_debt.income.0_30000','latest.aid.median_debt.income.30001_75000','latest.aid.median_debt.income.greater_than_75000',
	'latest.aid.median_debt.completers.overall',
	'school.name','school.city','school.school_url','school.price_calculator_url','latest.admissions.admission_rate.by_ope_id',
	'latest.earnings.10_yrs_after_entry.median','latest.earnings.6_yrs_after_entry.median','latest.completion.completion_rate_4yr_100nt',
	'school.ownership_peps',"school.institutional_characteristics.level"]) #all the needed fields, generated in Jupyter

def get_col_data(page): #return the json output of each api page
	p = {"school.operating":"1","fields":fields,"page":page, "api_key": key}
	resp = requests.get(url=url_base, params=p)
	return resp.json()

def callAPI():
	metadata = get_col_data(0)['metadata']
	all_pages = []
	for i in range(math.ceil(metadata['total']/metadata['per_page'])): #iterate through all the pages
		try:
			all_pages.extend(get_col_data(i)['results']) #add data from each page
		except:
			with open("out.txt", "w") as out: #print the error if it's there
				print(get_col_data(i),file=out)


	collegeInfo = pd.DataFrame(all_pages).fillna(value=np.nan) #load data into dataframe
	collegeInfo = collegeInfo[(collegeInfo['school.institutional_characteristics.level']==1)].dropna(thresh=50) #remove non-4-year colleges and those with 50 or more missing values (out of 86 columns total)
	#os.makedirs(r'C:\Users\timkh\OneDrive\Desktop\Programming\Projects\Python\CollegePickerWebsite\static',exist_ok=True)
	#collegeInfo.to_csv(r'C:\Users\timkh\OneDrive\Desktop\Programming\Projects\Python\CollegePickerWebsite\static\APIoutput.csv')
	collegeInfo.to_csv(os.path.join('static','APIoutput.csv'))

if __name__ == '__main__':
	callAPI()
	#df = pd.util.testing.makeDataFrame()
	#os.makedirs(r'\static',exist_ok=True)
	#df.to_csv(r'\static\test.csv')
	#df.to_csv(url_for('static',filename='test.csv'))
	#df.to_csv(os.path.join('static','test.csv'))
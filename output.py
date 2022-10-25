import pandas as pd
import numpy as np
import math
import os


#create function to output top 5 colleges
def calc(rels,sizes,majors,settings,regions,states,specPrefs,relImp,sizeImp,allMajors,satMath,satEng,act,setImp,regImp,stImp,income):
	#rels is a list of Religion objects. Similar for other arguments

	#collegeInfo = pd.read_csv(r'C:\Users\timkh\OneDrive\Desktop\Programming\Projects\Python\CollegePickerWebsite\static\APIoutput.csv')
	collegeInfo = pd.read_csv(os.path.join('static','APIoutput.csv'))

	majorsDict = {1: 'latest.academics.program_percentage.agriculture',26: 'latest.academics.program_percentage.resources',2: 'latest.academics.program_percentage.architecture',3: 'latest.academics.program_percentage.ethnic_cultural_gender',
	 6: 'latest.academics.program_percentage.communication',7: 'latest.academics.program_percentage.communications_technology',8: 'latest.academics.program_percentage.computer',28: 'latest.academics.program_percentage.personal_culinary',
	 10: 'latest.academics.program_percentage.education',11: 'latest.academics.program_percentage.engineering',12: 'latest.academics.program_percentage.engineering_technology',15: 'latest.academics.program_percentage.language',
	 14: 'latest.academics.program_percentage.family_consumer_science',19: 'latest.academics.program_percentage.legal',13: 'latest.academics.program_percentage.english',20: 'latest.academics.program_percentage.humanities',
	 21: 'latest.academics.program_percentage.library',4: 'latest.academics.program_percentage.biological',22: 'latest.academics.program_percentage.mathematics',24: 'latest.academics.program_percentage.military',
	 25: 'latest.academics.program_percentage.multidiscipline',27: 'latest.academics.program_percentage.parks_recreation_fitness',29: 'latest.academics.program_percentage.philosophy_religious',
	 36: 'latest.academics.program_percentage.theology_religious_vocation',30: 'latest.academics.program_percentage.physical_science',34: 'latest.academics.program_percentage.science_technology',
	 32: 'latest.academics.program_percentage.psychology',18: 'latest.academics.program_percentage.security_law_enforcement',33: 'latest.academics.program_percentage.public_administration_social_service',
	 35: 'latest.academics.program_percentage.social_science',9: 'latest.academics.program_percentage.construction',23: 'latest.academics.program_percentage.mechanic_repair_technology',31: 'latest.academics.program_percentage.precision_production',
	 37: 'latest.academics.program_percentage.transportation',38: 'latest.academics.program_percentage.visual_performing',16: 'latest.academics.program_percentage.health',5: 'latest.academics.program_percentage.business_marketing',
	 17: 'latest.academics.program_percentage.history'} #not manual - generated in the notebook. Each major's code's correponding column

	collegeInfo['Score'] = 0 #create the score column, set all scores to 0 for now
	maxScore = 0 #this will be the max score for this user to calculate % match

	collegeInfo['ColsUsed'] = "" #create a new empty column where we will store the columns that will be shown for each college
	def initColsUsed(row): #initialize the columns that will be shown in the output as long as they are not NaN and that need a label
		row = row.copy() #shouldn't change the object being iterated, so creating copy
		row['ColsUsed'] = ['school.locale'] #start the list, add locale to it since every college has it and it'll always be shown
		
		#add the below if the college has this information
		if not math.isnan(row['school.religious_affiliation']):
			row['ColsUsed'].append('school.religious_affiliation')
		if not math.isnan(row['latest.student.size']):
			row['ColsUsed'].append('latest.student.size')
		if type(row['school.price_calculator_url']) == str:
			row['ColsUsed'].append('school.price_calculator_url')
		if not math.isnan(row['school.ownership_peps']):
			row['ColsUsed'].append('school.ownership_peps')
		if not math.isnan(row['latest.earnings.6_yrs_after_entry.median']):
			row['ColsUsed'].append('latest.earnings.6_yrs_after_entry.median')
		if not math.isnan(row['latest.earnings.10_yrs_after_entry.median']):
			row['ColsUsed'].append('latest.earnings.10_yrs_after_entry.median')
		if not math.isnan(row['latest.completion.completion_rate_4yr_100nt']):
			row['ColsUsed'].append('latest.completion.completion_rate_4yr_100nt')
		if not math.isnan(row['latest.admissions.admission_rate.by_ope_id']):
			row['ColsUsed'].append('latest.admissions.admission_rate.by_ope_id')
		if not math.isnan(row['latest.admissions.sat_scores.average.by_ope_id']):
			row['ColsUsed'].append('latest.admissions.sat_scores.average.by_ope_id')
		if not math.isnan(row['latest.admissions.sat_scores.midpoint.math']):
			row['ColsUsed'].extend(['latest.admissions.sat_scores.midpoint.math','latest.admissions.sat_scores.midpoint.critical_reading'])
		if not math.isnan(row['latest.admissions.act_scores.midpoint.cumulative']):
			row['ColsUsed'].append('latest.admissions.act_scores.midpoint.cumulative')

		#add the special preferences if the college matches them
		if row['school.online_only']==1:  
			row['ColsUsed'].append('school.online_only')  
		if row['school.women_only']==1:  
			row['ColsUsed'].append('school.women_only')   
		if row['school.men_only']==1:  
			row['ColsUsed'].append('school.men_only')
		if row['school.minority_serving.hispanic']==1:  
			row['ColsUsed'].append('school.minority_serving.hispanic')
		if row['school.minority_serving.tribal']==1:  
			row['ColsUsed'].append('school.minority_serving.tribal')
		if row['school.minority_serving.aanipi']==1:  
			row['ColsUsed'].append('school.minority_serving.aanipi')
		if row['school.minority_serving.annh']==1:  
			row['ColsUsed'].append('school.minority_serving.annh')
		if row['school.minority_serving.predominantly_black']==1:  
			row['ColsUsed'].append('school.minority_serving.predominantly_black')
		if row['school.minority_serving.historically_black']==1:  
			row['ColsUsed'].append('school.minority_serving.historically_black')

		#add the needed % in major, depending on what majors a user has selected
		if len(majors)>0:
			for major in majors:
				row['ColsUsed'].append(majorsDict[major.code])

		#cost will be in an another function - only show what's relevant based on income and what's not NaN. Eventually implement in/out-state tuition once I add a question what state you are from
		return row
	collegeInfo = collegeInfo.apply(initColsUsed,axis=1)

	#URLs are messed up, each with a different format
	def fixURL(url):
		if type(url)==str: #avoid NaNs
			if 'https' in url:
				return url
			elif 'www' in url:
				return 'https://'+url
			else:
				return 'https://www.'+url
		else:
			return url

	collegeInfo['school.school_url'] = collegeInfo['school.school_url'].apply(fixURL)
	collegeInfo['school.price_calculator_url'] = collegeInfo['school.price_calculator_url'].apply(fixURL)


	#filter the dataframe and change scores based on categorical/discrete variables. Updating scores based on continuous variables like salary and graduation rate will be done later
	relsDict = {-1:4,-2:4,22:2,24:2,27:2,28:2,30:1,33:2,34:2,35:2,36:2,37:2,38:2,39:2,40:2,41:2,42:2,43:2,44:2,45:2,47:2,48:2,49:2,50:2,51:2,52:2,53:2,54:2,55:2,57:2,58:2,59:2,60:2,61:2,64:2,65:2,66:2,
	67:2,68:2,69:2,71:2,73:2,74:2,75:2,76:2,77:2,78:2,79:2,80:3,81:2,84:2,87:2,88:2,89:2,91:2,92:2,93:2,94:2,95:2,97:2,99:3,100:2,101:2,102:2,103:2,105:2,106:3,107:2,np.nan:4} #map all of the religious codes to my less specific ones
	collegeInfo['school.religious_affiliation.new'] = collegeInfo['school.religious_affiliation'].map(relsDict)
	
	if len(rels)>0: #if user has religious preferences
		if relImp == 11: #remove all colleges that don't match user's selection if user wishes
			collegeInfo = collegeInfo[collegeInfo['school.religious_affiliation.new'].isin([rel.code for rel in rels])] #only leave religions that are in the user's list
		else:
			collegeInfo.loc[collegeInfo['school.religious_affiliation.new'].isin([rel.code for rel in rels]),'Score'] += relImp*10
			maxScore += relImp*10 #increase max score
	
	
	#create a categorical sizeCode based on size
	def sizeCode(colSeries): #college Series
		if colSeries['latest.student.size']>15000:
			return 1
		elif colSeries['latest.student.size']<5000:
			return 3
		else:
			return 2
	collegeInfo['sizeCode'] = collegeInfo.apply(sizeCode,axis=1)

	if len(sizes) > 0: #same as religion but for size
		if sizeImp == 11:
			collegeInfo = collegeInfo[collegeInfo['sizeCode'].isin([size.code for size in sizes])]
		else:
			collegeInfo.loc[collegeInfo['sizeCode'].isin([size.code for size in sizes]),'Score'] += sizeImp*10
			maxScore += sizeImp*10




	def hasMajor(colSeries): #return true if a college has at least one of the selected majors
		for major in majors:
			if colSeries[majorsDict[major.code]]>0:
				return True
		return False

	if len(majors)>0: #if user has preferences for majors
		if allMajors: #if user only wants colleges that have all selected majors
			for major in majors:
				collegeInfo = collegeInfo[collegeInfo[majorsDict[major.code]]>0] #iterate through user's every major and remove colleges that have 0% of their students in that major
		else: #if user wants colleges that offer at least one of his majors
			collegeInfo = collegeInfo[collegeInfo.apply(hasMajor,axis=1)]


	#same as religions but for setting
	setDict = {11:1,12:1,13:1,21:2,22:2,23:2,31:2,32:2,33:2,41:3,42:3,43:3}
	collegeInfo['school.locale.new'] = collegeInfo['school.locale'].map(setDict)
	if len(settings)>0:
		if setImp == 11:
			collegeInfo = collegeInfo[collegeInfo['school.locale.new'].isin([setting.code for setting in settings])]
		else:
			collegeInfo.loc[collegeInfo['school.locale.new'].isin([setting.code for setting in settings]),'Score'] += setImp*10
			maxScore += setImp*10

	#regions
	if len(regions)>0:
		if regImp == 11:
			collegeInfo = collegeInfo[collegeInfo['school.region_id'].isin([reg.code-1 for reg in regions])] #-1 because the region IDs in the API start with 0 but my codes start with 1
		else:
			collegeInfo.loc[collegeInfo['school.region_id'].isin([reg.code-1 for reg in regions]),'Score'] += regImp*10
			maxScore += regImp*10

	#states
	if len(states)>0:
		if stImp == 11:
			collegeInfo = collegeInfo[collegeInfo['school.state'].isin([st.name for st in states])]
		else:
			collegeInfo.loc[collegeInfo['school.state'].isin([st.name for st in states]),'Score'] += stImp*10
			maxScore += stImp*10


	#special preference codes and ther corresponding columns
	specPrefsDict = {1:'Black',2:'school.minority_serving.annh',3:'school.minority_serving.aanipi',5:'school.minority_serving.tribal',4:'school.minority_serving.hispanic',6:'school.men_only',
	 7:'school.women_only',8:'school.online_only'}

	def black(colSeries): #return 1 if a college is either HBCU or predominantly black, 0 otherwise
		if colSeries['school.minority_serving.historically_black']==1 or colSeries['school.minority_serving.predominantly_black']==1:
			return 1
		else:
			return 0

	collegeInfo['Black'] = collegeInfo.apply(black, axis=1)

	if len(specPrefs)>0:
		for pref in specPrefs:
			collegeInfo = collegeInfo[collegeInfo[specPrefsDict[pref.code]]==1] #only leave colleges that match all special preferences


	#now deal with continuous variables. Test scores first. If a test score is left blank, it comes back as None - in that case change it to NaN so that mathematical operations can be done with them
	if satMath is None:
		satMath = np.nan
	if satEng is None:
		satEng = np.nan
	if act is None:
		act = np.nan

	#find the absolute deviations
	collegeInfo['SAT Math deviation'] = abs(collegeInfo['latest.admissions.sat_scores.midpoint.math']-satMath)
	collegeInfo['SAT English deviation'] = abs(collegeInfo['latest.admissions.sat_scores.midpoint.critical_reading']-satEng)
	collegeInfo['SAT total deviation'] = abs(collegeInfo['latest.admissions.sat_scores.average.by_ope_id']-(satMath+satEng))
	collegeInfo['ACT deviation'] = abs(collegeInfo['latest.admissions.act_scores.midpoint.cumulative']-act)

	#columns to normalize
	colstoNorm = ['SAT Math deviation','SAT English deviation','SAT total deviation','ACT deviation','latest.cost.net_price.public.by_income_level.0-30000','latest.cost.net_price.public.by_income_level.30001-48000',
	'latest.cost.net_price.public.by_income_level.48001-75000','latest.cost.net_price.public.by_income_level.75001-110000','latest.cost.net_price.public.by_income_level.110001-plus','latest.cost.net_price.private.by_income_level.0-30000',
	'latest.cost.net_price.private.by_income_level.30001-48000','latest.cost.net_price.private.by_income_level.48001-75000','latest.cost.net_price.private.by_income_level.75001-110000','latest.cost.net_price.private.by_income_level.110001-plus',
	'latest.cost.attendance.academic_year','latest.cost.tuition.in_state','latest.cost.tuition.out_of_state','latest.aid.median_debt.income.0_30000','latest.aid.median_debt.income.30001_75000','latest.aid.median_debt.income.greater_than_75000',
	'latest.aid.median_debt.completers.overall','latest.earnings.10_yrs_after_entry.median','latest.earnings.6_yrs_after_entry.median','latest.completion.completion_rate_4yr_100nt'] #columns that need to be normalized. Add average aid to it from IPEDS

	collegeInfo[[col + ' normalized' for col in colstoNorm]] = collegeInfo[colstoNorm].apply(lambda x: ((x - x.min()) / (x.max() - x.min())) * 100) #normalize it using min-max. Keep in mind, the normalization happens after the filtering, so colleges will only be compared to other colleges that fit the student's "extremely important" criteria


	def updateScoreTests(colSeries): #update college score based on test score deviations
		colSeries = colSeries.copy() #shouldn't change row itself while iterating
		if not math.isnan(satMath):
			if not math.isnan(colSeries['SAT Math deviation']): #deviation could be NaN if college doesn't report SAT Math
				colSeries['Score'] -= (colSeries['SAT Math deviation normalized'] * 0.5 + colSeries['SAT English deviation normalized'] * 0.5)
			else:
				if not math.isnan(colSeries['SAT total deviation']):
					colSeries['Score'] -= colSeries['SAT total deviation normalized']
				else:
					colSeries['Score'] -= 100

		if not math.isnan(act):
			if not math.isnan(colSeries['ACT deviation']):
				colSeries['Score'] -= colSeries['ACT deviation normalized']
			else:
				colSeries['Score'] -= 100

		return colSeries

	collegeInfo = collegeInfo.apply(updateScoreTests, axis=1)

	#list of corresponding columns based on student's stated income level (code)
	incomeDict = {0:['latest.cost.attendance.academic_year','latest.cost.tuition.in_state','latest.cost.tuition.out_of_state','latest.aid.median_debt.completers.overall'],
	1:['latest.cost.net_price.public.by_income_level.0-30000','latest.cost.net_price.private.by_income_level.0-30000','latest.aid.median_debt.income.0_30000'],
	2:['latest.cost.net_price.public.by_income_level.30001-48000','latest.cost.net_price.private.by_income_level.30001-48000','latest.aid.median_debt.income.30001_75000'],
	3:['latest.cost.net_price.public.by_income_level.48001-75000','latest.cost.net_price.private.by_income_level.48001-75000','latest.aid.median_debt.income.30001_75000'],
	4:['latest.cost.net_price.public.by_income_level.75001-110000','latest.cost.net_price.private.by_income_level.75001-110000','latest.aid.median_debt.income.greater_than_75000'],
	5:['latest.cost.net_price.public.by_income_level.110001-plus','latest.cost.net_price.private.by_income_level.110001-plus','latest.aid.median_debt.income.greater_than_75000']}
	
	def updateScoreCost(colSeries):
		colSeries = colSeries.copy()
		colsToCheck = incomeDict[income]
		for col in colsToCheck: #will check columns in order
			if not math.isnan(colSeries[col]):
				colSeries['ColsUsed'].append(col)
				colSeries['Score'] -= colSeries[col + ' normalized']
				return colSeries
		#at this point, if nothing is returned, the college has no information about cost based on income. Instead, try to base it off the general cost
		for col in incomeDict[0]:
			if not math.isnan(colSeries[col]):
				colSeries['ColsUsed'].append(col)
				colSeries['Score'] -= colSeries[col + ' normalized']
				return colSeries
		#at this point, if nothing is returned, there is no information about cost at all. Assume it is maximum
		colSeries['Score'] -= 100
		return colSeries

	collegeInfo = collegeInfo.apply(updateScoreCost, axis=1)

	#add the continuous variables that need to be normalized
	collegeInfo['Score'] += collegeInfo['latest.earnings.10_yrs_after_entry.median normalized'].fillna(0) 
	collegeInfo['Score'] += collegeInfo['latest.earnings.6_yrs_after_entry.median normalized'].fillna(0)
	collegeInfo['Score'] += collegeInfo['latest.completion.completion_rate_4yr_100nt normalized'].fillna(0)
	maxScore += 300
	#collegeInfo['Score'] += collegeInfo['latest.admissions.admission_rate.by_ope_id'].fillna(0)*100 #This should be uncommented to give an advantage to colleges that are easier to 
	#get into. Important - not normalized! Don't forget to change maxScore if used

	#columns that are currently floats but shold be integers for better presentation
	colsToInt = ['latest.student.size','latest.admissions.sat_scores.midpoint.critical_reading','latest.admissions.sat_scores.midpoint.math','latest.admissions.act_scores.midpoint.cumulative',
	'latest.admissions.act_scores.midpoint.english','latest.admissions.act_scores.midpoint.math','latest.admissions.sat_scores.average.by_ope_id','latest.cost.net_price.public.by_income_level.0-30000',
	'latest.cost.net_price.public.by_income_level.30001-48000','latest.cost.net_price.public.by_income_level.48001-75000','latest.cost.net_price.public.by_income_level.75001-110000',
	'latest.cost.net_price.public.by_income_level.110001-plus','latest.cost.net_price.private.by_income_level.0-30000','latest.cost.net_price.private.by_income_level.30001-48000',
	'latest.cost.net_price.private.by_income_level.48001-75000','latest.cost.net_price.private.by_income_level.75001-110000','latest.cost.net_price.private.by_income_level.110001-plus',
	'latest.cost.attendance.academic_year','latest.cost.tuition.in_state','latest.cost.tuition.out_of_state','latest.aid.median_debt.income.0_30000','latest.aid.median_debt.income.30001_75000',
	'latest.aid.median_debt.income.greater_than_75000','latest.aid.median_debt.completers.overall','latest.earnings.10_yrs_after_entry.median','latest.earnings.6_yrs_after_entry.median']

	#numeric codes to words
	relstrDict = {22:'American Evangelical Lutheran Church',24:'African Methodist Episcopal Zion Church',27:'Assemblies of God Church',28:'Brethren Church',30:'Roman Catholic',33:'Wisconsin Evangelical Lutheran Synod',
34:'Christ and Missionary Alliance Church',35:'Christian Reformed Church',36:'Evangelical Congregational Church',37:'Evangelical Covenant Church of America',38:'Evangelical Free Church of America',
39:'Evangelical Lutheran Church',40:'International United Pentecostal Church',41:'Free Will Baptist Church',42:'Interdenominational',43:'Mennonite Brethren Church',44:'Moravian Church',
45:'North American Baptist',47:'Pentecostal Holiness Church',48:'Christian Churches and Churches of Christ',49:'Reformed Church in America',50:'Episcopal Church, Reformed',51:'African Methodist Episcopal',
52:'American Baptist',53:'American Lutheran',54:'Baptist',55:'Christian Methodist Episcopal',57:'Church of God',58:'Church of Brethren',59:'Church of the Nazarene',60:'Cumberland Presbyterian',
61:'Christian Church (Disciples of Christ)',64:'Free Methodist',65:'Friends',66:'Presbyterian Church (USA)',67:'Lutheran Church in America',68:'Lutheran Church - Missouri Synod',
69:'Mennonite Church',71:'United Methodist',73:'Protestant Episcopal',74:'Churches of Christ',75:'Southern Baptist',76:'United Church of Christ',77:'Protestant, not specified',
78:'Multiple Protestant Denomination',79:'Other Protestant',80:'Jewish',81:'Reformed Presbyterian Church',84:'United Brethren Church',87:'Missionary Church Inc',88:'Undenominational',
89:'Wesleyan',91:'Greek Orthodox',92:'Russian Orthodox',93:'Unitarian Universalist',94:'Latter Day Saints (Mormon Church)',95:'Seventh Day Adventists',97:'The Presbyterian Church in America',
99:'Other',100:'Original Free Will Baptist',101:'Ecumenical Christian',102:'Evangelical Christian',103:'Presbyterian',105:'General Baptist',106:'Muslim',107:'Plymouth Brethren'}

	localestrDict = {11:'Large City',12:'Midsize City',13:'Small City',21:'Large Suburb',22:'Midsize Suburb',23:'Small Suburb',31:'Fringe Town',32:'Distant Town',33:'Remote Town',
	41:'Fringe Rural',42:'Distant Rural',43:'Remote Rural'}

	ownDict = {1:'Public',2:'Private Non-Profit',3:'Private For-Profit'}

	rateCols = [col for col in collegeInfo.columns if 'rate' in col or 'percentage' in col] #all of the columns that are rates/percentages and that should be multiplied by 100

	
	collegeInfo['Match'] = (collegeInfo['Score']/maxScore*100).round(1).clip(lower=0) #find % match, round, and replace negative numbers with 0
	collegeInfo[colsToInt] = collegeInfo[colsToInt].fillna(0).astype(int) #convert the floats to ints
	collegeInfo[rateCols] = (collegeInfo[rateCols].fillna(0)*100).round(2).astype(str) + '%' #multiply percentages by 100, round, add the percentage sign
	collegeInfo['school.religious_affiliation'] = collegeInfo['school.religious_affiliation'].map(relstrDict) #convert codes to words
	collegeInfo['school.locale'] = collegeInfo['school.locale'].map(localestrDict)
	collegeInfo['school.ownership_peps'] = collegeInfo['school.ownership_peps'].map(ownDict)
	
	if len(collegeInfo)>0: #check if the output is empty, if not checked returns an error
		for numCol in list(collegeInfo.select_dtypes('number')): #look at every numeric column
			if numCol != 'Score': #have to exclude score because this function turns all of the columns into strings, so if score is also converted, we can't use nlargest on it
				collegeInfo[numCol] = collegeInfo[numCol].apply('{:,}'.format) #separate thousands with commas
	return collegeInfo

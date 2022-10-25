from wtforms import Form, validators, SelectField, SelectMultipleField, IntegerField, BooleanField

#create all the needed lists for the select fields
ratings = [(i,str(i)) for i in range(1,11)] #choices 1-10 for importance. [(1,1),(2,2), etc.]
ratings.append((11,"Extremely Important - only show me colleges that match my selection"))

religionChoices = [(1,'Roman Catholic'), (2,'Other Christian'), (3,'Other Religious'), (4,'Non-secular')]

sizeChoices = [(1,'Large (>15,000 students)'), (2,'Medium (between 5,000 and 15,000 students)'), (3,'Small (<5,000)')]

majorChoices = list(zip(range(1,39),sorted(["Agriculture, Agriculture Operations, And Related Sciences", "Natural Resources And Conservation", "Architecture And Related Services",
        "Area, Ethnic, Cultural, Gender, And Group Studies","Communication, Journalism, And Related Programs","Communications Technologies/Technicians And Support Services",
        "Computer And Information Sciences And Support Services","Personal And Culinary Services","Education","Engineering","Engineering Technologies And Engineering-Related Fields",
        "Foreign Languages, Literatures, And Linguistics","Family And Consumer Sciences/Human Sciences","Legal Professions And Studies","English Language And Literature/Letters",
        "Liberal Arts And Sciences, General Studies And Humanities","Library Science","Biological And Biomedical Sciences","Mathematics And Statistics","Military Technologies And Applied Sciences",
        "Multi/Interdisciplinary Studies","Parks, Recreation, Leisure, And Fitness Studies","Philosophy And Religious Studies","Theology And Religious Vocations","Physical Sciences",
        "Science Technologies/Technicians","Psychology","Homeland Security, Law Enforcement, Firefighting And Related Protective Services","Public Administration And Social Service Professions",
        "Social Sciences","Construction Trades","Mechanic And Repair Technologies/Technicians","Precision Production","Transportation And Materials Moving","Visual And Performing Arts",
        "Health Professions And Related Programs","Business, Management, Marketing, And Related Support Services","History"])))

settingChoices = [(1,'Urban'),(2,'Suburban or Small Town'),(3,'Rural')]

regionChoices = [(1,'U.S. Service Schools'),(2,'New England (CT, ME, MA, NH, RI, VT)'),(3,'Mid East (DE, DC, MD, NJ, NY, PA)'),(4,'Great Lakes (IL, IN, MI, OH, WI)'),
        (5,'Plains (IA, KS, MN, MO, NE, ND, SD)'),(6,'Southeast (AL, AR, FL, GA, KY, LA, MS, NC, SC, TN, VA, WV)'),(7,'Southwest (AZ, NM, OK, TX)'),(8,'Rocky Mountains (CO, ID, MT, UT, WY)'),
        (9,'Far West (AK, CA, HI, NV, OR, WA)'),(10,'Outlying Areas (AS, FM, GU, MH, MP, PR, PW, VI)')]

stateChoices = list(zip(range(1,60),["AK","AL","AR","AS","AZ","CA","CO","CT","DC","DE","FL","FM","GA","GU","HI","IA","ID","IL","IN","KS","KY","LA","MA","MD","ME","MH","MI","MN","MO","MP","MS","MT",
        "NC","ND","NE","NH","NJ","NM","NV","NY","OH","OK","OR","PA","PR","PW","RI","SC","SD","TN","TX","UT","VA","VI","VT","WA","WI","WV","WY"]))

specPrefChoices = [(1,'Historically Black and/or predominantly Black'),(2,'Alaska Native or Hawaii Native-serving'),(3,'Asian American, Native American, or Pacific Islander-serving'),(4,'Hispanic serving'),
                (5,'Tribal'),(6,'Male-only'),(7,'Female-only'),(8,'Online-only')]

class Questionnaire(Form):
    #all question fields. coerce=int makes it so that the output is an integer, not a string
    relAffil = SelectMultipleField("What do you want your college's religious affiliation to be?",choices=religionChoices,coerce=int)
    relImp = SelectField("On a scale of 1-10, how important is the college's religious affiliation to you?",choices = ratings,coerce=int)
    size = SelectMultipleField("What do you want your college's size to be?",choices=sizeChoices,coerce=int)
    sizeImp = SelectField("On a scale of 1-10, how important is the college's size to you?",choices = ratings,coerce=int)
    major = SelectMultipleField("What field(s) do you plan to major in?",choices=majorChoices,coerce=int)
    allMajors = BooleanField("Only show me colleges that offer all of the selected majors.")
    satMath = IntegerField("What is your SAT Math score? Leave this question blank if you did not take the test.",[validators.NumberRange(min=200,max=800),validators.Optional()])
    satEng = IntegerField("What is your SAT Reading and Writing score? Leave this question blank if you did not take the test.",[validators.NumberRange(min=200,max=800),validators.Optional()])
    act = IntegerField("What is your ACT score? Leave this question blank if you did not take the test.",[validators.NumberRange(min=1,max=36),validators.Optional()])
    setting = SelectMultipleField("What do you want your college's setting to be?",choices=settingChoices,coerce=int)
    settingImp = SelectField("On a scale of 1-10, how important is the college's setting to you?",choices = ratings,coerce=int)
    region = SelectMultipleField("What region do you want to attend college in?",choices=regionChoices,coerce=int)
    regionImp = SelectField("On a scale of 1-10, how important is the college's region to you?",choices = ratings,coerce=int)
    state = SelectMultipleField("What state do you want to attend college in?",choices=stateChoices,coerce=int)
    stateImp = SelectField("On a scale of 1-10, how important is the college's state to you?",choices = ratings,coerce=int)
    specPref = SelectMultipleField("What other special preferences do you want your college to match?",choices=specPrefChoices,coerce=int,validators = [validators.Optional()])
    income = SelectField("What is your household income? This will be used for determining cost.",
        choices=[(0,"Don't know/prefer not to answer"),(1,'$0-30,000'),(2,'$30,001-48,000'),(3,'$48,001-75,000'),(4,'$75,001-110,000'),(5,'>$110,000')], coerce=int)

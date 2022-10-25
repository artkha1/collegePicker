from flask import Blueprint, render_template, flash,request,redirect,url_for
from flask_login import login_required, current_user
from __init__ import create_app, db
from form import Questionnaire, religionChoices, sizeChoices, majorChoices, settingChoices, regionChoices, stateChoices, specPrefChoices
from models import User, Religion, Size, Major, Setting, Region, State, SpecPref
from output import calc

# our main blueprint
main = Blueprint('main', __name__)

@main.route('/') #home page that return 'index'
def index():
    return render_template('index.html')

@main.route('/welcome')
@login_required
def welcome():
    return render_template('welcome.html',name=current_user.name)

@main.route('/getStarted',methods=['GET', 'POST']) #get started page that returns 'getStarted'
@login_required
def getStarted():
    form = Questionnaire(request.form)  #initialize the form

    if request.method == 'GET': #if we are landing on this page, show the page
    	return render_template('getStarted.html', form=form)
    else: #if the form is submitted
        if form.validate(): #if there are no validation errors
            #delete the current info of the user so that it can be updated (new stuff is entered)
            Religion.query.filter(Religion.user_id == current_user.id).delete()
            Size.query.filter(Size.user_id == current_user.id).delete()
            Major.query.filter(Major.user_id == current_user.id).delete()
            Setting.query.filter(Setting.user_id == current_user.id).delete()
            Region.query.filter(Region.user_id == current_user.id).delete()
            State.query.filter(State.user_id == current_user.id).delete()
            SpecPref.query.filter(SpecPref.user_id == current_user.id).delete()

            #now add all of the new data
           
            db.session.add_all([Religion(code=rel,name=dict(religionChoices).get(rel),user_id = current_user.id) for rel in form.relAffil.data])
            db.session.add_all([Size(code=size,name=dict(sizeChoices).get(size),user_id = current_user.id) for size in form.size.data])
            db.session.add_all([Major(code=major,name=dict(majorChoices).get(major),user_id = current_user.id) for major in form.major.data])
            db.session.add_all([Setting(code=setting,name=dict(settingChoices).get(setting),user_id = current_user.id) for setting in form.setting.data])
            db.session.add_all([Region(code=reg,name=dict(regionChoices).get(reg),user_id = current_user.id) for reg in form.region.data])
            db.session.add_all([State(code=state,name=dict(stateChoices).get(state),user_id = current_user.id) for state in form.state.data])
            db.session.add_all([SpecPref(code=spec,name=dict(specPrefChoices).get(spec),user_id = current_user.id) for spec in form.specPref.data])

            #update the user database with new data
            updatedUser = User(id=current_user.id, relImp = form.relImp.data, sizeImp = form.sizeImp.data, allMajors = form.allMajors.data, 
                satMath = form.satMath.data, satEng = form.satEng.data, act = form.act.data, settingImp = form.settingImp.data,
                regionImp = form.regionImp.data, stateImp = form.stateImp.data, income = form.income.data)
            db.session.merge(updatedUser) #merge finds the row of the current user and adds/updates all of the data from the form to it
            
            #tried this to reincrement after deleting:
            #db.session.execute("DBCC CHECKIDENT (religions, RESEED, 0)") #doesn't work, does each user separately

            db.session.commit()


            #before I found the current implementation (deleting then re-adding), I used this to add data:
            # db.session.add(Religion(code=None,name=None,user_id = current_user.id)) if any religions were selected

            #and this to query:
            # q = db.session.query(User, Religion, Size, Major, Setting, Region, State, SpecPref).filter(User.id == Religion.user_id).filter(User.id == Size.user_id).filter(
            #     User.id == Major.user_id).filter(User.id == Setting.user_id).filter(User.id == Region.user_id).filter(User.id == State.user_id).filter(User.id == SpecPref.user_id).filter(
            #     User.id == current_user.id).all() #outputs list of classes in that order. (<User 1>, <Religion 71>, <Size 81>, <Major 87>, <Setting 77>, <Region 90>, <State 80>, <SpecPref 51>)
            
            return redirect(url_for('main.output'))
        else:
            flash('Error:'+str(form.errors),'danger') #if there are validation errors, show them

def topCols(): #run the algorithm to find top 5 colleges
    out = calc(
        rels=current_user.religions,sizes=current_user.sizes,majors=current_user.majors,settings=current_user.settings,regions= current_user.regions,states=current_user.states,
        specPrefs=current_user.specPrefs,relImp=current_user.relImp,sizeImp=current_user.sizeImp,allMajors=current_user.allMajors,satMath=current_user.satMath,satEng=current_user.satEng,act=current_user.act,
        setImp=current_user.settingImp,regImp=current_user.regionImp,stImp=current_user.stateImp,income=current_user.income)
    top5 = out.nlargest(5,'Score').reset_index()
    return top5


@main.route('/output') #make a directory for the output where top 5 colleges will be shown with links for more information
@login_required
def output():
    top5 = topCols()
    return render_template('output.html', df=top5)

@main.route('/college/<int:college_id>/') #the directory with more information on each college. Different depending on the index of the college passed
@login_required
def college(college_id):
    top5 = topCols()

    #every column and their corresponding label (generated using code in Jupyter but slightly changed manually:
    fieldsDict = {'school.religious_affiliation': 'Religious affiliation',
 'latest.student.size': 'Number of students',
 'latest.academics.program_percentage.agriculture': 'Percentage of students in Agriculture, Agriculture Operations, And Related Sciences',
 'latest.academics.program_percentage.resources': 'Percentage of students in Natural Resources And Conservation',
 'latest.academics.program_percentage.architecture': 'Percentage of students in Architecture And Related Services',
 'latest.academics.program_percentage.ethnic_cultural_gender': 'Percentage of students in Area, Ethnic, Cultural, Gender, And Group Studies',
 'latest.academics.program_percentage.communication': 'Percentage of students in Communication, Journalism, And Related Programs',
 'latest.academics.program_percentage.communications_technology': 'Percentage of students in Communications Technologies/Technicians And Support Services',
 'latest.academics.program_percentage.computer': 'Percentage of students in Computer And Information Sciences And Support Services',
 'latest.academics.program_percentage.personal_culinary': 'Percentage of students in Personal And Culinary Services',
 'latest.academics.program_percentage.education': 'Percentage of students in Education',
 'latest.academics.program_percentage.engineering': 'Percentage of students in Engineering',
 'latest.academics.program_percentage.engineering_technology': 'Percentage of students in Engineering Technologies And Engineering-Related Fields',
 'latest.academics.program_percentage.language': 'Percentage of students in Foreign Languages, Literatures, And Linguistics',
 'latest.academics.program_percentage.family_consumer_science': 'Percentage of students in Family And Consumer Sciences/Human Sciences',
 'latest.academics.program_percentage.legal': 'Percentage of students in Legal Professions And Studies',
 'latest.academics.program_percentage.english': 'Percentage of students in English Language And Literature/Letters',
 'latest.academics.program_percentage.humanities': 'Percentage of students in Liberal Arts And Sciences, General Studies And Humanities',
 'latest.academics.program_percentage.library': 'Percentage of students in Library Science',
 'latest.academics.program_percentage.biological': 'Percentage of students in Biological And Biomedical Sciences',
 'latest.academics.program_percentage.mathematics': 'Percentage of students in Mathematics And Statistics',
 'latest.academics.program_percentage.military': 'Percentage of students in Military Technologies And Applied Sciences',
 'latest.academics.program_percentage.multidiscipline': 'Percentage of students in Multi/Interdisciplinary Studies',
 'latest.academics.program_percentage.parks_recreation_fitness': 'Percentage of students in Parks, Recreation, Leisure, And Fitness Studies',
 'latest.academics.program_percentage.philosophy_religious': 'Percentage of students in Philosophy And Religious Studies',
 'latest.academics.program_percentage.theology_religious_vocation': 'Percentage of students in Theology And Religious Vocations',
 'latest.academics.program_percentage.physical_science': 'Percentage of students in Physical Sciences',
 'latest.academics.program_percentage.science_technology': 'Percentage of students in Science Technologies/Technicians',
 'latest.academics.program_percentage.psychology': 'Percentage of students in Psychology',
 'latest.academics.program_percentage.security_law_enforcement': 'Percentage of students in Homeland Security, Law Enforcement, Firefighting And Related Protective Services',
 'latest.academics.program_percentage.public_administration_social_service': 'Percentage of students in Public Administration And Social Service Professions',
 'latest.academics.program_percentage.social_science': 'Percentage of students in Social Sciences',
 'latest.academics.program_percentage.construction': 'Percentage of students in Construction Trades',
 'latest.academics.program_percentage.mechanic_repair_technology': 'Percentage of students in Mechanic And Repair Technologies/Technicians',
 'latest.academics.program_percentage.precision_production': 'Percentage of students in Precision Production',
 'latest.academics.program_percentage.transportation': 'Percentage of students in Transportation And Materials Moving',
 'latest.academics.program_percentage.visual_performing': 'Percentage of students in Visual And Performing Arts',
 'latest.academics.program_percentage.health': 'Percentage of students in Health Professions And Related Programs',
 'latest.academics.program_percentage.business_marketing': 'Percentage of students in Business, Management, Marketing, And Related Support Services',
 'latest.academics.program_percentage.history': 'Percentage of students in History',
 'latest.admissions.sat_scores.midpoint.critical_reading': 'Midpoint of the SAT Reading and Writing score',
 'latest.admissions.sat_scores.midpoint.math': 'Midpoint of the SAT Math score',
 'latest.admissions.act_scores.midpoint.cumulative': 'Midpoint of the ACT cumulative score',
 'latest.admissions.sat_scores.average.by_ope_id': 'Average SAT cumulative score',
 'school.locale': 'Locale',
 'school.minority_serving.historically_black': 'Historically Black College or University',
 'school.minority_serving.predominantly_black': 'Predominantly Black',
 'school.minority_serving.annh': 'Alaska Native Native Hawaiian-serving',
 'school.minority_serving.aanipi': 'Asian American Native American Pacific Islander-serving',
 'school.minority_serving.tribal': 'Tribal college or university',
 'school.minority_serving.hispanic': 'Hispanic-serving',
 'school.men_only': 'Men-only',
 'school.women_only': 'Women-only',
 'school.online_only': 'Online-only',
 'latest.cost.net_price.public.by_income_level.0-30000': 'Average net price for $0-$30,000 family income',
 'latest.cost.net_price.public.by_income_level.30001-48000': 'Average net price for $30,001-$48,000 family income',
 'latest.cost.net_price.public.by_income_level.48001-75000': 'Average net price for $48,001-$75,000 family income',
 'latest.cost.net_price.public.by_income_level.75001-110000': 'Average net price for $75,001-$110,000 family income',
 'latest.cost.net_price.public.by_income_level.110001-plus': 'Average net price for $110,000+ family income',
 'latest.cost.net_price.private.by_income_level.0-30000': 'Average net price for $0-$30,000 family income',
 'latest.cost.net_price.private.by_income_level.30001-48000': 'Average net price for $30,001-$48,000 family income',
 'latest.cost.net_price.private.by_income_level.48001-75000': 'Average net price for $48,001-$75,000 family income',
 'latest.cost.net_price.private.by_income_level.75001-110000': 'Average net price for $75,001-$110,000 family income',
 'latest.cost.net_price.private.by_income_level.110001-plus': 'Average net price for $110,000+ family income',
 'latest.cost.attendance.academic_year': 'Average cost of attendance',
 'latest.cost.tuition.in_state': 'In-state tuition and fees',
 'latest.cost.tuition.out_of_state': 'Out-of-state tuition and fees',
 'latest.aid.median_debt.income.0_30000': 'The median starting debt for students with family income between $0-$30,000',
 'latest.aid.median_debt.income.30001_75000': 'The median starting debt for students with family income between $30,001-$75,000',
 'latest.aid.median_debt.income.greater_than_75000': 'The median starting debt for students with family income $75,001+',
 'latest.aid.median_debt.completers.overall': 'The median starting debt for students',
 'latest.admissions.admission_rate.by_ope_id': 'Admission rate',
 'latest.earnings.10_yrs_after_entry.median': 'Median earnings of students working 10 years after entry',
 'latest.earnings.6_yrs_after_entry.median': 'Median earnings of students working 6 years after entry',
 'latest.completion.completion_rate_4yr_100nt': 'Graduation rate',
 'school.ownership_peps': 'Type'}

    college = top5.iloc[college_id] #the particular college we are looking at

    #the below are the columns divided into categories
    overview = ['school.religious_affiliation','latest.student.size','school.locale','school.minority_serving.historically_black','school.minority_serving.predominantly_black','school.minority_serving.annh',
 'school.minority_serving.aanipi','school.minority_serving.tribal','school.minority_serving.hispanic','school.men_only','school.women_only','school.online_only','school.ownership_peps']
    academics = [ 'latest.academics.program_percentage.agriculture','latest.academics.program_percentage.resources','latest.academics.program_percentage.architecture','latest.academics.program_percentage.ethnic_cultural_gender',
 'latest.academics.program_percentage.communication','latest.academics.program_percentage.communications_technology','latest.academics.program_percentage.computer','latest.academics.program_percentage.personal_culinary',
 'latest.academics.program_percentage.education','latest.academics.program_percentage.engineering','latest.academics.program_percentage.engineering_technology','latest.academics.program_percentage.language',
 'latest.academics.program_percentage.family_consumer_science','latest.academics.program_percentage.legal','latest.academics.program_percentage.english','latest.academics.program_percentage.humanities',
 'latest.academics.program_percentage.library','latest.academics.program_percentage.biological','latest.academics.program_percentage.mathematics','latest.academics.program_percentage.military',
 'latest.academics.program_percentage.multidiscipline','latest.academics.program_percentage.parks_recreation_fitness','latest.academics.program_percentage.philosophy_religious','latest.academics.program_percentage.theology_religious_vocation',
 'latest.academics.program_percentage.physical_science','latest.academics.program_percentage.science_technology','latest.academics.program_percentage.psychology','latest.academics.program_percentage.security_law_enforcement',
 'latest.academics.program_percentage.public_administration_social_service','latest.academics.program_percentage.social_science','latest.academics.program_percentage.construction','latest.academics.program_percentage.mechanic_repair_technology',
 'latest.academics.program_percentage.precision_production','latest.academics.program_percentage.transportation','latest.academics.program_percentage.visual_performing','latest.academics.program_percentage.health',
 'latest.academics.program_percentage.business_marketing','latest.academics.program_percentage.history','latest.admissions.sat_scores.midpoint.critical_reading','latest.admissions.sat_scores.midpoint.math',
 'latest.admissions.act_scores.midpoint.cumulative','latest.admissions.act_scores.midpoint.english','latest.admissions.act_scores.midpoint.math','latest.admissions.sat_scores.average.by_ope_id',
 'latest.admissions.admission_rate.by_ope_id','latest.completion.completion_rate_4yr_100nt']
    finance = ['latest.cost.net_price.public.by_income_level.0-30000','latest.cost.net_price.public.by_income_level.30001-48000','latest.cost.net_price.public.by_income_level.48001-75000',
 'latest.cost.net_price.public.by_income_level.75001-110000','latest.cost.net_price.public.by_income_level.110001-plus','latest.cost.net_price.private.by_income_level.0-30000','latest.cost.net_price.private.by_income_level.30001-48000',
 'latest.cost.net_price.private.by_income_level.48001-75000','latest.cost.net_price.private.by_income_level.75001-110000','latest.cost.net_price.private.by_income_level.110001-plus','latest.cost.attendance.academic_year',
 'latest.cost.tuition.in_state','latest.cost.tuition.out_of_state','latest.aid.median_debt.income.0_30000','latest.aid.median_debt.income.30001_75000','latest.aid.median_debt.income.greater_than_75000',
 'latest.aid.median_debt.completers.overall', 'latest.earnings.6_yrs_after_entry.median', 'latest.earnings.10_yrs_after_entry.median']
    specPref = ['school.minority_serving.historically_black','school.minority_serving.predominantly_black','school.minority_serving.annh',
 'school.minority_serving.aanipi','school.minority_serving.tribal','school.minority_serving.hispanic','school.men_only','school.women_only','school.online_only']
    return render_template('college.html',college=college,fieldsDict=fieldsDict,overview=overview,finance=finance,academics=academics,specPref=specPref)



app = create_app() # we initialize our flask app using the __init__.py function
if __name__ == '__main__': #run the code only if the file is run directly, not imported
    db.create_all(app=create_app()) # create the Azure database
    app.run(debug=True) # run the flask app on debug mode

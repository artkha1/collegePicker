from flask_login import UserMixin
from __init__ import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy. Automatically incremented when a new user is entered
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    religions = db.relationship('Religion', backref='users')
    relImp = db.Column(db.Integer)
    sizes = db.relationship('Size', backref='users')
    sizeImp = db.Column(db.Integer)
    majors = db.relationship('Major', backref='users')
    allMajors = db.Column(db.Boolean)
    satMath = db.Column(db.Integer)
    satEng = db.Column(db.Integer)
    #actMath = db.Column(db.Integer)
    #actEng = db.Column(db.Integer)
    act = db.Column(db.Integer)
    settings = db.relationship('Setting', backref='users')
    settingImp = db.Column(db.Integer)
    regions = db.relationship('Region', backref='users')
    regionImp = db.Column(db.Integer)
    states = db.relationship('State', backref='users')
    stateImp = db.Column(db.Integer)
    specPrefs = db.relationship('SpecPref', backref='users')
    income = db.Column(db.Integer)

class Religion(db.Model):
    __tablename__ = 'religions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.Integer)
    name = db.Column(db.String(100))

class Size(db.Model):
    __tablename__ = 'sizes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.Integer)
    name = db.Column(db.String(100))

class Major(db.Model):
    __tablename__ = 'majors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.Integer)
    name = db.Column(db.String(100))

class Setting(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.Integer)
    name = db.Column(db.String(100))

class Region(db.Model):
    __tablename__ = 'regions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.Integer)
    name = db.Column(db.String(100))

class State(db.Model):
    __tablename__ = 'states'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.Integer)
    name = db.Column(db.String(100))

class SpecPref(db.Model):
    __tablename__ = 'specPrefs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.Integer)
    name = db.Column(db.String(100))

    

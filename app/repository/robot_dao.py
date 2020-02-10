from flask_login import login_required, current_user
from ..models.models import *
from sqlalchemy.sql import exists

def robot_exists(name):
	''' check if exists '''
	db.session.query(exists().where(Robot.username == name)).scalar()

def add(name, projectid):
	''' add a new robot '''
	robot = Robot(username=name, project_id=projectid)
	db.session.add(robot)
	db.session.commit()
	return robot

def find_by_name_and_projectid(name, projectid):
	''' find a robot by its name and associated projectid '''
	robot = Robot.query.filter_by(username=name, project_id=projectid).first()
	return robot

def find_by_projectid(projectid):
	''' find by project id and return the list '''
	return Robot.query.filter_by(project_id=projectid).all()

def find_by_id(id):
	return Robot.query.filter_by(id=id).first()
from flask_login import login_required, current_user
from ..models.models import *

def get_access(project_id, user_id):
    """ get the project access level, can be false if there is not project   """
    return ProjectAccess.query.filter_by(projectid=project_id, userid=user_id).first()

def get_admins(project_id):
    """ get the project admins """
    return ProjectAccess.query.filter_by(projectid=project_id, accesslevel=2).all()

def get_guests(project_id):
    """ get the project guests """
    return ProjectAccess.query.filter_by(projectid=project_id, accesslevel=1).all()

def find_by_name(project_name):
    """ find the projects by project_name and get the first one """
    return Project.query.filter_by(projectname=project_name).first()

def get_roles(project_id, user_id):
    """ returns the sorted set of roles from roles for each sample."""
    return sorted(set(SampleRole.query.filter_by(projectid=project_id, userid=user_id).all()))

def get_possible_roles():
    """ returns the overall possible roles """
    return SampleRole.ROLES

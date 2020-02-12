from flask_login import login_required, current_user
from ..models.models import *

def add_project(project):
    """ add a project into db """
    db.session.add(project)
    db.session.commit()

def get_access(project_id, user_id):
    """ get the project access level, can be false if there is not project   """
    return ProjectAccess.query.filter_by(projectid=project_id, userid=user_id).first()

def add_access(project_access):
    """ add a project access object """
    db.session.add(project_access)
    db.session.commit()

def delete_project_access(project_access):
    """ delete a project access """
    db.session.delete(project_access)
    db.session.commit()

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
    return set(SampleRole.query.filter_by(projectid=project_id, userid=user_id).all())

def get_possible_roles():
    """ returns the overall possible roles """
    return SampleRole.ROLES

def delete(project):
    """ delete a project and its related accesses and roles """
    db.session.delete(project)
    related_accesses = ProjectAccess.query.filter_by(projectid=project.id).delete()
    related_sample_roles = SampleRole.query.filter_by(projectid=project.id).delete()
    db.session.commit()

def find_all():
    """ return all the projects """
    return Project.query.all()

def add_sample_role(sample_role):
    """ save a sample role """
    db.session.add(sample_role)
    db.session.commit()

def delete_sample_role(sample_role):
    """ delete a sample role """
    # rows_deleted = db.session.delete(sample_role)
    rows_deleted = SampleRole.query.filter_by(id=sample_role.id, samplename=sample_role.samplename).delete()
    # db.session.flush()
    db.session.commit()
    # db.session.expire_all()
    return rows_deleted

def delete_sample_role_by_project(project_id):
    """ delete a sample role given a project id """
    sr = SampleRole.query.filter_by(projectid=project_id).delete()
    db.session.commit()
    return sr

def get_user_role(project_id, sample_name, user_id):
    """ retrieve a user role """
    return SampleRole.query.filter_by(projectid=project_id, samplename=sample_name, userid=user_id).first()

def add_cat(project_name, cat):
    """ add a category to the project cats list """
    project = Project.query.filter_by(projectname=project_name).first()
    catLabel = CatLabel(value=cat, project_id=project.id)
    project.cats.append( catLabel )
    db.session.commit()
    return CatLabel.query.filter_by(project_id=project.id).all()

def set_cats(project, cats):
    """ set multiple categories to the project cats """
    project.cats = []
    for cat in cats:
        catLabel = CatLabel(value=cat, project_id=project.id)
        project.cats.append( catLabel )
    db.session.commit()
    return CatLabel.query.filter_by(project_id=project.id).all()

def delete_cat(project_name, cat):
    """ delete a category from a project cats list """
    project = Project.query.filter_by(projectname=project_name).first()
    catLabel = CatLabel.query.filter_by(value=cat, project_id=project.id).delete()
    db.session.commit()
    return CatLabel.query.filter_by(project_id=project.id).all()

def add_stock( project_name ):
    """ add an empty stock to a project and returns the list of its stocks """
    project = Project.query.filter_by(projectname=project_name).first()
    stock = LabelStock()
    project.relations.append( stock )
    db.session.commit()
    return LabelStock.query.filter_by(project_id=project.id).all()

def delete_stock( project_name, stockid ):
    """ delete a stock and returns the project stock list """
    project = Project.query.filter_by(projectname=project_name).first()
    stock = LabelStock.query.filter_by( project_id=project.id, id=stockid ).delete()
    Label.query.filter_by(stock_id=stockid).delete()
    db.session.commit()
    return LabelStock.query.filter_by(project_id=project.id).all()

def add_label( project_name, stock_id, label):
    """ add a label to a project stock """
    project = Project.query.filter_by(projectname=project_name).first()
    stock = LabelStock.query.get(stock_id)
    newlabel = Label(value=label, stock_id=stock_id)
    stock.labels.append( newlabel )
    db.session.commit()
    return LabelStock.query.filter_by(project_id=project.id).all()

def delete_label( project_name, stock_id, label ):
    """ delete a label from a project stock """
    project = Project.query.filter_by(projectname=project_name).first()
    label = Label.query.filter_by(value=label, stock_id=stock_id).delete()
    db.session.commit()
    return LabelStock.query.filter_by(project_id=project.id).all()

def set_stock_and_labels(project, stocks):
    """ set multiple stocks and their labels at once to the project labels and labelstocks """
    project.relations = []
    for stock in stocks:
        ls = LabelStock()
        for label in stock: ls.labels.append( Label(value=label) )
        project.relations.append(ls)
    db.session.commit()
    return LabelStock.query.filter_by(project_id=project.id).all()
    

def delete_label_by_id( label_id):
    """ delete label by id """
    Label.query.filter_by(id=label_id).delete()
    db.session.commit()

def add_defaultusertree(project, user_id, username):
    """ add a defaultusertree to a project """
    dut = DefaultUserTrees(project_id=project.id, project=project, user_id=user_id, username=username)
    project.default_user_trees.append( dut )
    db.session.commit()

def add_defaultusertree_robot(project, username, robot):
    """ add a defaultusertree to a project """
    dut = DefaultUserTrees(project_id=project.id, project=project, username=username, robot=robot)
    project.default_user_trees.append( dut )
    db.session.commit()

def delete_defaultusertree_by_id( dut_id ):
    """ delete a defaultusertree given its id """
    DefaultUserTrees.query.filter_by(id=dut_id).delete()
    db.session.commit()

def find_project_cats(project_id):
    """ get the list of cats for project config """
    return CatLabel.query.filter_by(project_id=project_id).all()

def find_project_stocks(project_id):
    """ find all the stocks for a given project """
    return LabelStock.query.filter_by(project_id=project_id).all()

def find_stock_labels(stock_id):
    """ find all the labels for a given stock """
    return Label.query.filter_by(stock_id=stock_id).all()

def set_show_all_trees(project_name, value):
    """ change the value of showAllTrees """
    project = Project.query.filter_by(projectname=project_name).first()
    project.show_all_trees = value
    db.session.commit()
    return project

def set_is_open(project_name, value):
    """ change the value of is_open """
    project = Project.query.filter_by(projectname=project_name).first()
    project.is_open = value
    db.session.commit()
    return project

def find_default_user_trees(project_id):
    """ find userids for this project default user trees """
    # userids = [ dut.user_id for dut in DefaultUserTrees.query.filter_by(project_id=project_id).all() ]
    userids = DefaultUserTrees.query.filter_by(project_id=project_id).all()
    return userids
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField, BooleanField, MultipleFileField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField
from ..models import *
from flask_login import current_user, login_required



ACCESS = [
    (0, 'guest'),
    (1, 'user'), 
    (2, 'admin'),
    ]

ROLES =  [(0, 'annotator'), (1, 'validator'), (2, 'supervalidator')]


class UploadForm(FlaskForm):
    files = FileField()  

#Project forms
class ProjectForm(FlaskForm):
    """
    Form for admin to add or edit a project
    """
    name = StringField('Name', validators=[DataRequired()])
    description = StringField('Description')
    importUser = QuerySelectField(query_factory=lambda: User.query.all(), get_label="id")
    files = FileField('Select conll files', render_kw={'multiple': True})
    is_private = BooleanField('Is private')
    submit = SubmitField('Submit')


##User Forms
class UserAssignForm(FlaskForm):
    """
    Form for admin to assign projects and roles to users
    """
    user = QuerySelectField(query_factory=lambda: User.query.all(),
                                  get_label="id")
    
    # projects are filtered so you can only assign users for projects where you are at least admin
    project = QuerySelectField(query_factory=lambda: [x for x in Project.query.all() if ProjectAccess.query.filter_by(projectid=x.id, userid=current_user.id).filter(ProjectAccess.accesslevel>=2).all()],
                                  get_label="projectname")
    access_level = SelectField('Level', choices=ACCESS, coerce=int)
    submit = SubmitField('Submit')

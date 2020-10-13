from flask_login import UserMixin
# from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy_utils import ChoiceType
from datetime import datetime
# from sqlalchemy.ext.declarative import declarative_base, as_declarative
# from sqlathanor import declarative_base, as_declarative
from sqlalchemy.schema import UniqueConstraint
import base64
import json

# from ...app import db, login_manager #prod
try:
    from ...app import db, login_manager #type: ignore # dev 
except:
    from app import db, login_manager  # prod

from sqlalchemy.ext.declarative import DeclarativeMeta


class BaseM(object):

    def as_json(self, exclude=[], include={}):
        json_rep = dict()
        for k in vars(self):
            # print(getattr(self, k))
            if k in exclude:
                # print(k)
                continue
            elif k[0] == "_":
                continue
            elif type(getattr(self, k)) is bytes:
                # print('yay')
                # print(getattr(self, k))
                json_rep[k] = str(base64.b64encode(getattr(self, k)))
                # json_rep[k] = str(getattr(self, k))
            else:
                json_rep[k] = getattr(self, k)
        for k in include:
            json_rep[k] = include[k]
        return json_rep


class AlchemyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    # this will fail on non-encodable values, like other classes
                    json.dumps(data)
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)


class User(UserMixin, db.Model, BaseM):

    __tablename__ = 'users'

    id = db.Column(db.String(256), primary_key=True)
    auth_provider = db.Column(db.String(256))
    username = db.Column(db.String(60), index=True, unique=True)
    first_name = db.Column(db.String(60), index=True)
    family_name = db.Column(db.String(60), index=True)
    picture_url = db.Column(db.String(128), index=True)
    super_admin = db.Column(db.Boolean, default=False)
    #role = db.Column(db.Integer)
    #projectid = db.Column(db.Integer, db.ForeignKey('projects.id'))
    #todos = db.relationship('Todo', backref='txt_todos')
    created_date = db.Column(db.DateTime)
    last_seen = db.Column(db.DateTime)

    @staticmethod
    def make_valid_nickname(nickname):
        # return re.sub('[^a-zA-Z0-9_\.]', '', nickname)
        return nickname.replace(' ', '')

    @staticmethod
    def make_unique_nickname(nickname):
        if User.query.filter_by(username=nickname).first() is None:
            return nickname
        version = 2
        while True:
            new_nickname = nickname + str(version)
            if User.query.filter_by(nickname=new_nickname).first() is None:
                break
            version += 1
        return new_nickname

    @staticmethod
    def get_or_create(session, **kwargs):
        instance = session.query(User).filter_by(
            username=kwargs['username']).first()
        if instance:
            instance.last_seen = datetime.utcnow()
            session.commit()
            return instance, False
        else:
            instance = User(**kwargs)
            session.add(instance)
            session.commit()
            return instance, True

    @staticmethod
    def setPictureUrl(session, username, pictureUrl):
        '''
        Modify the user url. Need the session and the username to find it. 
        This method is static void.
        Note: should be interfaced by a service.
        '''
        instance = session.query(User).filter_by(username=username).first()
        if instance:
            instance.picture_url = pictureUrl
            session.commit()

    # def allowed(self, level):
        # return self.access >= level

    def __repr__(self):
        return '<user: {}>'.format(self.username)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# TODO: ManytoMany reltnshp btwn user/proj


class Project(db.Model, BaseM):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    projectname = db.Column(db.String(256), nullable=False, unique=True)
    description = db.Column(db.String(256))
    image = db.Column(db.BLOB)
    # users = db.relationship('User', backref='project_user',lazy='dynamic')
    #texts = db.relationship('Text', backref='project_text',lazy='dynamic')
    # is_private = db.Column(db.Boolean, default=False)
    visibility = db.Column(db.Integer)
    # relations = db.relationship('LabelStock')
    # cats = db.relationship('CatLabel')
    show_all_trees = db.Column(db.Boolean, default=True)
    exercise_mode = db.Column(db.Boolean, default=False)
    # is_open = db.Column(db.Boolean, default=False)
    default_user_trees = db.relationship('DefaultUserTrees')


class Feature(db.Model):
    __tablename__ = 'feature'
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(256), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))


class MetaFeature(db.Model):
    __tablename__ = 'metafeature'
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(256), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))


# class LabelStock(db.Model):
# 	__tablename__ = 'labelstocks'
# 	id = db.Column(db.Integer, primary_key=True)
# 	project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
# 	project = db.relationship('Project')
# 	labels = db.relationship('Label')


# class Label(db.Model):
# 	__tablename__ = 'labels'
# 	id = db.Column(db.Integer, primary_key=True)
# 	stock_id = db.Column(db.Integer, db.ForeignKey('labelstocks.id'))
# 	stock = db.relationship('LabelStock')
# 	value = db.Column(db.String(256), nullable=False)


# class CatLabel(db.Model):
# 	__tablename__ = 'catlabels'
# 	id = db.Column(db.Integer, primary_key=True)
# 	project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
# 	project = db.relationship('Project')
# 	value = db.Column(db.String(256), nullable=False)


class ProjectAccess(db.Model):
    __tablename__ = 'projectaccess'
    ACCESS = [(1, 'guest'), (2, 'admin')]

    id = db.Column(db.Integer, primary_key=True)
    projectid = db.Column(db.Integer, db.ForeignKey('projects.id'))
    userid = db.Column(db.String(256), db.ForeignKey('users.id'))
    accesslevel = db.Column(ChoiceType(ACCESS, impl=db.Integer()))


class DefaultUserTrees(db.Model, BaseM):
    __tablename__ = 'defaultusertrees'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    project = db.relationship('Project')
    user_id = db.Column(db.String(256), db.ForeignKey('users.id'))
    # db.ForeignKey('users.username'))
    username = db.Column(db.String(256), nullable=False)
    robot = db.Column(db.Boolean, default=False)


class Robot(db.Model, BaseM):
    __tablename__ = 'robots'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    project = db.relationship('Project')
    username = db.Column(db.String(256), nullable=False)


# class and annotation project settings


# class Exo(db.Model):
#     __tablename__ = 'exo'

#     id = db.Column(db.Integer, primary_key=True)
#     textid = db.Column(db.Integer, db.ForeignKey('texts.id'))
#     type = db.Column(db.Integer)
#     #exotoknum = db.Column(db.Integer)
#     status = db.Column(db.Text)
#     #comment = db.Column(db.Text)

class SampleRole(db.Model):
    __tablename__ = 'samplerole'
    ROLES = [(1, 'annotator'), (2, 'validator'), (3, 'prof')]
    id = db.Column(db.Integer, primary_key=True)
    samplename = db.Column(db.String(256), nullable=False)
    projectid = db.Column(db.Integer, db.ForeignKey('projects.id'))
    userid = db.Column(db.String(256), db.ForeignKey('users.id'))
    role = db.Column(ChoiceType(ROLES, impl=db.Integer()))
    # __table_args__ = (UniqueConstraint('samplename', 'projectid', name='_samplename_projectid_uc'),)


class SampleExerciseLevel(db.Model):
    __tablename__ = 'exerciselevel'
    EXERCISE_LEVEL = [(1, 'teacher_visible'), (2, 'graphical_feedback'),
                      (3, 'numerical_feedback'), (4, 'no_feedback')]
    id = db.Column(db.Integer, primary_key=True)
    sample_name = db.Column(db.String(256), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    exercise_level = db.Column(ChoiceType(EXERCISE_LEVEL, impl=db.Integer()))

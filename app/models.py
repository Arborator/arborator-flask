from flask_login import UserMixin
# from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy_utils import ChoiceType
from datetime import datetime
# from sqlalchemy.ext.declarative import declarative_base, as_declarative
# from sqlathanor import declarative_base, as_declarative
from sqlalchemy.schema import UniqueConstraint
import re
from ..app import db, login_manager


class BaseM(object):

	def as_json(self, exclude=[]):
		json_rep = dict()
		for k in vars(self):
			if k in exclude:
				# print(k)
				continue
			elif k[0] == "_":
				continue
			else:
				json_rep[k] = getattr(self, k)
		return json_rep



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
		#return re.sub('[^a-zA-Z0-9_\.]', '', nickname)
		return nickname.replace(' ','')

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
		instance = session.query(User).filter_by(username=kwargs['username']).first()
		if instance:
			instance.last_seen=datetime.utcnow()
			session.commit()
			return instance, False
		else:
			instance = User(**kwargs)
			session.add(instance)
			session.commit()
			return instance, True

	
	#def allowed(self, level):
		#return self.access >= level

	def __repr__(self):
		return '<user: {}>'.format(self.username)

	
@login_manager.user_loader
def load_user(user_id):
	return User.query.get(user_id)


## TODO: ManytoMany reltnshp btwn user/proj


class Project(db.Model, BaseM):
	__tablename__ = 'projects'

	id = db.Column(db.Integer, primary_key=True)
	projectname = db.Column(db.String(256), nullable=False, unique=True)
	description = db.Column(db.String(256))
	image = db.Column(db.BLOB)
	# users = db.relationship('User', backref='project_user',lazy='dynamic')
	#texts = db.relationship('Text', backref='project_text',lazy='dynamic')
	is_private = db.Column(db.Boolean, default=False)

class ProjectAccess(db.Model):
	__tablename__ = 'projectaccess'
	ACCESS =  [(1, 'guest'), (2, 'admin')]

	id = db.Column(db.Integer, primary_key=True)
	projectid = db.Column(db.Integer, db.ForeignKey('projects.id'))
	userid = db.Column(db.String(256), db.ForeignKey('users.id'))
	# accesslevel = db.Column(db.Integer)
	accesslevel = db.Column(ChoiceType(ACCESS, impl=db.Integer()))



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
	ROLES =  [(1, 'annotator'), (2, 'validator'), (3, 'supervalidator'), (4, 'prof')]
	id = db.Column(db.Integer, primary_key=True)
	samplename = db.Column(db.String(256), nullable=False)
	projectid = db.Column(db.Integer, db.ForeignKey('projects.id'))
	userid = db.Column(db.String(256), db.ForeignKey('users.id'))
	role = db.Column(ChoiceType(ROLES, impl=db.Integer()))
	# __table_args__ = (UniqueConstraint('samplename', 'projectid', name='_samplename_projectid_uc'),)





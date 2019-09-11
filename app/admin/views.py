from flask import render_template, jsonify, abort, flash, redirect, render_template, url_for, request, Response
from flask_login import current_user, login_required
from werkzeug import secure_filename
import os, re, json
from functools import wraps
import requests


from . import admin
from .forms import ProjectForm, UploadForm, UserAssignForm, ACCESS
from .. import db
from ..models import *
from ...config import Config
from ...grew_server.test.test_server import send_request as grew_request
from ..project.views import requires_access_level, get_access_for_project




def superadmin_required(func):
	'''
	Decorator requiring to be a super_admin to see the view
	'''
	@wraps(func)
	def decorated_view(*args, **kwargs):
		if not current_user.super_admin:
			# flash("You do not have access to that page. Sorry!") # problem is with json you don't see the message :/
			resp = Response("", status=403, mimetype='application/json')
			return resp
			# return redirect(url_for('home.home_page'))
		# print("Congrats you're a super admin!")
		return func(*args, **kwargs)
	return decorated_view



## Dashboard View : list of projects and users
@admin.route('/', methods=["GET"])
# @login_required
@superadmin_required
def superadmin_dashboard():
	"""
	Returns a list of users and a list of projects
	"""
	users = list_users().json
	projects = list_projects().json
	return jsonify({"Users":users, "Projects":projects})


# ### Projects Views
# @admin.route('/projects', methods=['GET'])
# # @login_required
# @superadmin_required
# def list_projects():
# 	"""
# 	List all projects
# 	"""
# 	projects = Project.query.all()

# 	for p in projects:

		
# 		if ProjectAccess.query.filter_by(projectid=p.id, userid=current_user.id).first() is None:
# 			access = 0
# 		if p.is_private and access < 1: # private project and current_user is not a user of the project -> filtered
# 			projects.remove(p)

# 	js = json.dumps([p.as_json() for p in projects])
# 	resp = Response(js, status=200,  mimetype='application/json')
# 	# resp.headers['Access-Control-Allow-Origin'] = '*'
# 	return resp


# status : ok
@admin.route('/addproject', methods=['POST'])
# @login_required
# @superadmin_required
def create_project():
	"""
	Create a project
	"""
	
	if not request.json:
		abort(404)

	project = Project(projectname=request.json["project_name"], description=request.json.get("description", ""), is_private=request.json["is_private"])
	print("project", project)
	# test whether the project already exists in the database
	if Project.query.filter_by(projectname=project.projectname).first() is None:
		db.session.add(project)
		# # create the project on grew
		print ('========== [newProject]')
		reply = grew_request ('newProject', data={'project_id': project.projectname})
		print (reply) # TODO: check if error, if error, remove project from db and send error message


		projects = Project.query.all()

		# return jsonify([p.as_json() for p in projects])
		resp = Response('{"message":"Project created."}', status=200,  mimetype='application/json')
			
		db.session.commit()

	else:
		print("project under the same name exists")
		resp = Response('{"errormessage":"Project under the same name exists."}', status=409,  mimetype='application/json')

	
	return resp

# status : ok
@admin.route('/deleteproject', methods=['DELETE'])
# @login_required
# @superadmin_required
def delete_project():
	"""
	Delete a project
	"""

	# current_user.super_admin = True
	# current_user.id = "rinema56@gmail.com"
	if not request.json:
		abort(400)

	project = Project.query.filter_by(projectname=request.json["project_name"]).first()
	if not project:
		abort(400)

	p_access = get_access_for_project(current_user.id, project.id)
	if p_access >=2 or current_user.super_admin: # p_access and p_access >=2
		print(project)
		db.session.delete(project)
		related_accesses = ProjectAccess.query.filter_by(projectid=project.id).delete()
		related_sample_roles = SampleRole.query.filter_by(projectid=project.id).delete()
		db.session.commit()

		print ('========== [eraseProject]')
		reply = grew_request('eraseProject', data={'project_id': project.projectname})
	else:
		print("p_access to low for project {}".format(project.projectname))
		abort(403)
	
	projects = Project.query.all()
	js = json.dumps([p.as_json() for p in projects])
	resp = Response(js, status=200,  mimetype='application/json')
	
	return resp

@admin.route("/test")
# @login_required
def test():
	# print(current_user)
	# print(current_user.super_admin)
	## Projects management
	# list projects
	# res = requests.get("http://localhost:5000/admin")
	# print(current_user)
	# print(current_user.id)

	# delete a project
	# res = requests.delete("http://localhost:5000/admin/projects", json={"projectname":"aa"})

	# create a project
	filenames = ['/home/marine/Téléchargements/1_a.conllu', '/home/marine/Téléchargements/1_b.conllu']
	json = {'files': filenames, "project_name":"first_project", "is_private":True, "import_user":"rinema56@gmail.com"}
	print("doing as requested")
	res = requests.post("http://localhost:5000/admin/projects/addproject", json=json)

	# filenames = ['/home/marine/Téléchargements/1_b.conll']
	# for filename in filenames:
	# 	res = requests.post("http://localhost:5000/admin/projects", json={"projectname":"testy", "is_private":True}, files={'file':open(filename, 'rb')})
	# res = requests.delete("http://localhost:5000/admin/projects", json={"projectname":"aa"})

	# uploading files
	# filenames = ['/home/marine/Téléchargements/1_b.conll']
	# for filename in filenames:
	# 	res = requests.post("http://localhost:5000/admin/upload", files={'file':open(filename, 'rb')})
	# 	print('response from server:',res.text)
	return jsonify({"data":"ok"})


# @admin.route('/upload', methods=['POST'])
# # @login_required
# def upload():
# 	"""
# 	Upload a file in the data storage folder.
# 	"""
# 	f = request.files["file"]
# 	cwd = os.getcwd()
# 	f.save(Config.UPLOAD_FOLDER +secure_filename(f.filename)) #default is grew_server/data
# 	return jsonify({"status":"OK"})

# todo: remove here, see project views sample_upload
def saveconll(request):
	"""
	save conll files inside a grew Project
	"""
	redoublenl = re.compile(r'\s*\n\s*\n+\s*')
	reextensions = re.compile(r'\.(conllu?|txt|tsv|csv)$')


	files = request.json.get("files", [])
	project_name = request.json["project_name"]
	import_user = request.json.get("import_user", "parser") # TODO : facultatif import_user
	print("project ", project_name)
	print("files to add ", files)

	print('========== [getSamples]')
	reply = grew_request(
			'getSamples',
			data = {'project_id': project_name}
				)
	print(json.loads(reply))
	samples = [sa['name'] for sa in json.loads(reply)['data']]

	for fichier in files:
		print("saving {}".format(fichier))
		content = open(fichier).read()
		sample_name = reextensions.sub("", os.path.basename(fichier))
		with open(Config.UPLOAD_FOLDER +secure_filename(sample_name), "w") as outf:
			outf.write(content)
		if sample_name not in samples:

		# create a new sample in the grew project
			print ('========== [newSample]')
			reply = grew_request ('newSample', data={'project_id': project_name, 'sample_id': sample_name })
			print (reply)


			print(project_name, sample_name, import_user)
			with open(os.path.join(Config.UPLOAD_FOLDER,sample_name), 'rb') as inf:
				print ('========== [saveConll]')
				reply = grew_request (
					'saveConll',
					data = {'project_id': project_name, 'sample_id': sample_name, "user_id": import_user},
					files={'conll_file': inf},
				)

	return jsonify({"status":"ok"})


# Users view
# status : ok
@admin.route('/users', methods=["GET"])
# @login_required
# @superadmin_required
def list_users():
	users = User.query.all()
	#default=str is used to serialize the date
	# https://stackoverflow.com/questions/11875770/how-to-overcome-datetime-datetime-not-json-serializable
	js = json.dumps([u.as_json(exclude=["auth_provider", "created_dated"]) for u in users], default=str)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp


# status : ok
@admin.route('/users', methods=["DELETE"])
# @login_required
# @superadmin_required
def delete_user():
	"""
	Deletes a user and returns the list of remaining users
	"""	
	if not request.json:
		abort(400)

	user = User.query.get_or_404(request.json["user_id"])
	if not user:
		abort(400)
	else:
		related_accesses = ProjectAccess.query.filter_by(userid=user.id).delete()
		related_sample_roles = SampleRole.query.filter_by(userid=user.id).delete()
		db.session.delete(user)
		db.session.commit()
	resp = list_users()
	return resp




@admin.route('/users/manage_access', methods=['GET', 'POST'])
# @login_required
def manage_user_access_to_projects():
	"""
	Give a user an access to a project
	"""
	form = UserAssignForm()
	if request.method == "POST":
		project = form.project.data
		user_id = form.user.data.id
		project_access = ProjectAccess.query.filter_by(userid=user_id, projectid=project.id).first()

		if project_access:
			project_access.accesslevel = form.access_level.data
		else:
			project_access = ProjectAccess(projectid=project.id, userid=user_id, accesslevel=form.access_level.data)
			db.session.add(project_access)
		db.session.commit()
		flash('You have successfully assigned a project and role.')
		return redirect(url_for('admin.list_users'))

	return render_template('admin/users/user.html',
						   form=form,
						   title='Assign User')
	


@admin.route('/initdb/', methods=['GET'])
# @login_required
# @adminviews.superadmin_required
def init_database():
	"""
	initdb
	"""

	# TODO: move into else below...
	# all projects in grew are created in the database
	reply = grew_request ('getProjects')
	reply = json.loads(reply)
	print(reply)

	nb_sent = 0
	if reply.get("status") == "OK":
		projects = reply.get("data", [])
		for p in projects:
			print (p['name'])
			json = {"project_name":"first_project", "is_private":False, "description":"This is nothing but a test project to try out stuff"}
			res = requests.post("http://localhost:5000/admin/projects/addproject", json=json)
			#TODO if error...
			
	
	print(projects)

	# print (6546545/0)
	if os.path.isfile( str(db.engine.url)[len('sqlite:///'):]):
		resp = Response('{"database":"was there already"}', status=401,  mimetype='application/json')	
	else:

		print("current_user:",current_user)
		# , "super_admin:",current_user.super_admin)
		db.create_all()
		print(db, db.engine,db.engine.url )
		print("database created")
		resp = Response('{"database":"created"}', status=200,  mimetype='application/json')	



	return resp




@admin.route('/initdb/addstuff', methods=['GET'])
# @login_required
# @adminviews.superadmin_required
def addstuff():
	"""
	Home Handler
	"""
	print (6546545)

	print("current_user:",current_user)
	# , "super_admin:",current_user.super_admin)
	# db.create_all()
	# db.commit()
	print("database created")
	resp = Response('{"database":"filled with stuff"}', status=200,  mimetype='application/json')	
	return resp


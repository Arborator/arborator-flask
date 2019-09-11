from flask import render_template, flash, redirect, url_for, jsonify, request, Response, abort
from flask_login import login_required, current_user
from werkzeug import secure_filename
import json
from functools import wraps
import os


# local imports
from . import project
from ..models import *
from ...grew_server.test.test_server import send_request as grew_request
from ...config import Config

def get_access_for_project(user_id, project_id):
	"""
	Returns the access rights of a user for a given project

	str int -> int
	"""
	project_access = ProjectAccess.query.filter_by(projectid=project_id, userid=user_id).first()

	# if no access links this project and user, the user is a guest
	if not project_access:
		return 0

	return project_access.accesslevel

def get_role_for_sample(user_id, project_id, sample_id):
	"""
	Returns the role of a user for a sample in a given project

	str int int -> int
	"""
	sample_role = SampleRole.query.filter_by(textid=project_id, userid=user_id, id=sample_id).first()

	return sample_role

def role2string(role):
	"""

	"""
	if role == None:
		return None
	role = current_user.ROLES[role][1]
	return role


def requires_access_level(access_level):
	"""
	except for superadmins
	"""
	def decorator(f):
		@wraps(f)
		def decorated_function(*args, **kwargs):

			# not authenticated -> login
			if not current_user.id:
				return redirect(url_for('auth.login'))

			if kwargs.get("project_name"):
				print("got project_name")
				project_id = Project.query.filter_by(name=kwargs["project_name"]).first().id
			else:
				project_id = kwargs["id"]
				print("got project_id")
			projectaccess = get_access_for_project(current_user.id, project_id)

			print("project_access for current user: {}".format(projectaccess))
			
			if not current_user.super_admin: # super_admin are always admin even if it's not in the table
				if projectaccess is None or projectaccess < access_level:
					flash("You do not have access to that page. Sorry!")
					return redirect(url_for('home.home_page'))

			return f(*args, **kwargs)
		return decorated_function
	return decorator


def get_project(request):
	if not request.json:
		abort(400)
	project_name = request.json.get("project_name")
	if not project_name:
		abort(400)
	project = Project.query.filter_by(projectname=project_name).first()
	if not project:
		abort(404)
	return project

############################ controlers


@project.route('/<project_name>/', methods=['GET'])
# @login_required
# @requires_access_level(2)
def project_info(project_name):
	"""
	get project information
	project/<projectname>/ 
	GET
	list of samples (403 si projet privé et utilisateur pas de rôle)
	pê admin names, nb samples, nb arbres, description	
	"""
	print(465465465,current_user)
	current_user.id ="rinema56@gmail.com"
	project = Project.query.filter_by(projectname=project_name).first()
	print(project)
	roles = sorted(set(SampleRole.query.filter_by(projectid=project.id, userid=current_user.id).all()))

	if not roles and project.is_private:
		abort(403)

	admins = ProjectAccess.query.filter_by(projectid=project.id, accesslevel=2).all()
	admins = [a.userid for a in admins]
	guests = ProjectAccess.query.filter_by(projectid=project.id, accesslevel=1).all()
	guests = [g.userid for g in guests]

	reply = grew_request (
		'getSamples',
		data = {'project_id': project.projectname}
		)
	js = json.loads(reply)
	data = js.get("data")

	if data:
		nb_samples = len(data)
		samples = [sa['name'] for sa in data]
		reply = grew_request('getSentIds', data={'project_id': project_name})
		js = json.loads(reply)
		data = js.get("data")
		if data:
			nb_sentences = len(data)

	js = json.dumps({"project_name":project.projectname, "description":project.description,"samples":samples,"admins":admins, "guests":guests, "number_samples":nb_samples, "number_sentences":nb_sentences})
	resp = Response(js, status=200,  mimetype='application/json')

	return resp

@project.route('/<project_name>/', methods=['POST'])
# @login_required
# @requires_access_level(2)
def project_update(project_name):
	"""
	modifie project info

	par exemple
	ajouter admin / guest users:{nom:access, nom:access, nom:"" (pour enlever)}
	changer nom du projet project:{nom:nouveaunom,description:nouvelledescription,isprivate:True}
	
	"""
	print(465465465,"à faire")


@project.route('/<project_name>/delete', methods=['DELETE'])
# @login_required
# @requires_access_level(2)
def delete_project(project_name):
	"""
	Delete a project
	no json
	"""

	current_user.super_admin = True
	current_user.id = "rinema56@gmail.com"
	project = Project.query.filter_by(projectname=project_name).first()

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



@project.route('/<project_name>/upload', methods=["POST"])
def sample_upload(project_name):
	"""
	project/<projectname>/upload
	POST multipart
	multipart (fichier conll), filename, importuser

	TODO: verify either importuser or provided in conll (all the trees must have it)
	more generally: test conll!
	"""
	project = Project.query.filter_by(projectname=project_name).first()

	# is_in_grew = project_is_in_grew(project)

	# redoublenl = re.compile(r'\s*\n\s*\n+\s*')
	reextensions = re.compile(r'\.(conllu?|txt|tsv|csv)$')


	files = request.json.get("files", [])
	import_user = request.json.get("import_user", "")
	samplenames = request.json.get("samplenames", [reextensions.sub("", os.path.basename(f)) for f in files])

	print('========== [getSamples]')
	reply = grew_request (
			'getSamples',
			data = {'project_id': project_name}
				)
	js = json.loads(reply)
	data = js.get("data")

	# checking already existing samples in the project
	if data:
		samples = [sa['name'] for sa in data]
	else:
		samples = []

	for fichier, sample_name in zip(files,samplenames):
		print("saving {}".format(fichier))
		content = open(fichier).read()
		
		with open(Config.UPLOAD_FOLDER +secure_filename(sample_name), "w") as outf:
			outf.write(content)

		if sample_name in samples:
			print("sample déjà là -- à virer")
		else:

			# create a new sample in the grew project
			print ('========== [newSample]')
			reply = grew_request ('newSample', data={'project_id': project_name, 'sample_id': sample_name })
			print (reply)


		print(project_name, sample_name, import_user)
		with open(os.path.join(Config.UPLOAD_FOLDER,sample_name), 'rb') as inf:
			print ('========== [saveConll]')
			if import_user:
				reply = grew_request (
					'saveConll',
					data = {'project_id': project_name, 'sample_id': sample_name, "user_id": import_user},
					files={'conll_file': inf},
				)
			else: # if no import_user has been proviced, it should be in the conll metadata
				reply = grew_request (
					'saveConll',
					data = {'project_id': project_name, 'sample_id': sample_name},
					files={'conll_file': inf},
				)

	print('========== [getSamples]')
	reply = grew_request (
			'getSamples',
			data = {'project_id': project_name}
				)
	samples = {"samples":[sa['name'] for sa in json.loads(reply)['data']]}
	js = json.dumps(samples)
	resp = Response(js, status=200,  mimetype='application/json')

	return resp






# ###################################### Admin Dashboard Views and Functions ######################################
# @project.route('/project/<project_name>/admin')
# # @login_required
# # @requires_access_level(2)
# def admin_dash(project_name): 
# 	"""
# 	Project Dashboard Handler
# 	"""
# 	project = Project.query.filter_by(name=project_name).first()

# 	sample_users_role = dict()peripitiesVoiture

# 	reply = grew_request (
# 		'getSamples',
# 		data = {'project_id': project.projectname}
# 		)
# 	data = json.loads(reply)['data']
# 	for sample in data:
# 		sample_users_role[sample["name"]] = []
# 		for u in sample["users"]:
# 			role = get_role_for_sample(u, project.id, sample["name"])
# 			# str_role = u.ROLES[role][1]
# 			sample_users_role[sample["name"]].append((u,role))

# 	# all users and their role for this project
# 	# for u in users:
# 	# 	access = get_role_in_project(current_user.id, project.id, sampled_id)
# 	# 	users_and_access[u] = u.ROLES[access][1]
# 	return render_template('project/dashboard.html', project=project, sample_users_role=sample_users_role)


# # TODO
# @project.route('/project/<project_name>/admin/add/<int:id>', methods=['GET', 'POST'])
# # @login_required
# # @requires_access_level(2)
# def add_user_with_access(id, project_name, access):
# 	user = User.query.get_or_404(id)
# 	project_id = Project.query.filter_by(project_name=project_name).first()
# 	new_project_access = ProjectAccess(projectid=project_id, accesslevel=access, userid=user.id)
# 	db.session.add(new_project_access)
# 	db.session.commit()
# 	flash('You have successfully added a user to your project.')
# 	return render_template('projects/add_user.html')## testing include function 
# 	##angular style of template inclusion and value inheritance


# # TODO
# @project.route('/project/<project_name>/admin/edit/<int:id>', methods=['GET', 'POST'])
# # @login_required
# # @requires_access_level(2)
# def edit_role(id, role):
# 	check_admin()
# 	user = User.query.get_or_404(id)
# 	user.role = role
# 	db.session.add(user)
# 	db.session.commit()
# 	flash('You have successfully changed a users role')
# 	return render_template('projects/dashboard.html')


# @project.route('/project/<project_name>/admin/remove/<int:id>', methods=['GET', 'POST'])
# # @login_required
# # @requires_access_level(2)
# def remove_user(id):
# 	user = User.query.get_or_404(id)
# 	db.session.delete(user.project_id)
# 	db.session.commit()
# 	flash('You have successfully removed a user.')
# 	return render_template('projects/dashboard.html', )


###################################### Project Page Views and Functions ######################################
# @project.route('/project/projectpage/<project_name>', methods=['GET', 'POST'])
# def projectpage(project_name):
# 	"""
# 	Project Page Handler
# 	"""

# 	print ('========== [getSamples]')
# 	reply = grew_request ('getSamples', data={'project_id': project_name})
# 	reply = json.loads(reply)
# 	# print(reply)

# 	nb_sent = 0
# 	if reply.get("status") == "OK":
# 		samples = reply.get("data", [])
# 		for s in samples:
# 			s["users"] = " ".join(s.get("users", []))
# 			nb_sent += s.get("size", 0)
# 		nsamples = len(samples)

# 	project_id = Project.query.filter_by(name=project_name).first().id
# 	access_level = get_access_for_project(current_user.id, project_id)
		
# 	# private projects can only be viewed by non-guests
# 	is_private = Project.query.filter_by(name=project_name).first().is_private
# 	if access_level == 0 and is_private:
# 		flash("You don't have sufficient rights to view this project")
# 		return redirect(url_for('admin.list_projects'))

# 	return render_template('projects/index.html',project_name=project_name, title=project_name, samples=samples, n=nsamples, nb_sent=nb_sent, access=access_level)


@project.route('/<project_name>/sample/<sample_name>', methods=['GET'])
# @login_required
def samplepage(project_name, sample_name):
	"""
	GET
	nb_sentences, nb_trees, list of annotators, list of validators
	"""
	print ("========[getConll]")
	reply = json.loads(grew_request('getConll', data={'project_id': project_name, 'sample_id':sample_name}))
	# print(json.loads(reply))
	
	if reply.get("status") == "OK":
		samples = reply.get("data", {})
		js = json.dumps(samples)
		resp = Response(js, status=200,  mimetype='application/json')
		return resp
	else:
		abort(409)
	


@project.route('/<project_name>/sample/<sample_name>', methods=['DELETE'])
# @login_required
def delete_sample(project_name, sample_name):
	reply = json.loads(grew_request ('eraseSample', data={'project_id': project_name, 'sample_id': sample_name}))
	return project_info(project_name)
	



# @project.route('/projectpage/<project_name>/testing')
# @requires_access_level(0)
# def test_usersonly(project_id):
# 	return jsonify({"hello":"world"})



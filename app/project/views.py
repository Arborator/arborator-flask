from flask import render_template, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
import json
from functools import wraps


# local imports
from . import project
from ..models import *
from ...grew_server.test.test_server import send_request as grew_request


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

############################ controlers


# TODO: finir cette fonction
@project.route('/project/<project_name>/', methods=['GET'])
# @login_required
# @requires_access_level(2)
def project_info():
	"""
	get project information
	project/<projectname>/ 
	GET
	list of samples (403 si projet privé et utilisateur pas de rôle)
	pê admin names, nb samples, nb arbres, description	
	"""
	project = Project.query.filter_by(name=project_name).first()

	sample_users_role = {}

	reply = grew_request (
		'getSamples',
		data = {'project_id': project.projectname}
		)
	data = json.loads(reply)['data']
	for sample in data:
		sample_users_role[sample["name"]] = []
		for u in sample["users"]:
			role = get_role_for_sample(u, project.id, sample["name"])
			# str_role = u.ROLES[role][1]
			sample_users_role[sample["name"]].append((u,role))


	if not request.json:
		abort(404)

	project = Project(projectname=request.json["project_name"], description=request.json.get("description", ""), is_private=request.json["is_private"])
	print("project", project)

"""

POST
if admin of project or superadmin:  description, is private 
DELETE
if admin of project or superadmin
"""



# TODO: finir cette fonction

@project.route('/project/<project_name>/upload')
def sample_upload():
	"""
	project/<projectname>/upload
	POST multipart
	multipart (fichier conll), filename, importuser
	"""
	project = Project.query.filter_by(name=project_name).first()



	redoublenl = re.compile(r'\s*\n\s*\n+\s*')
	reextensions = re.compile(r'\.(conllu?|txt|tsv|csv)$')


	files = request.json.get("files", [])
	project_name = request.json["project_name"]
	import_user = request.json.get("import_user", "parser") # TODO : facultatif import_user
	print("project ", project_name)
	print("files to add ", files)

	print('========== [getSamples]')
	reply = grew_request (
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





###################################### Admin Dashboard Views and Functions ######################################
@project.route('/project/<project_name>/admin')
# @login_required
# @requires_access_level(2)
def admin_dash(project_name): 
	"""
	Project Dashboard Handler
	"""
	project = Project.query.filter_by(name=project_name).first()

	sample_users_role = dict()

	reply = grew_request (
		'getSamples',
		data = {'project_id': project.projectname}
		)
	data = json.loads(reply)['data']
	for sample in data:
		sample_users_role[sample["name"]] = []
		for u in sample["users"]:
			role = get_role_for_sample(u, project.id, sample["name"])
			# str_role = u.ROLES[role][1]
			sample_users_role[sample["name"]].append((u,role))

	# all users and their role for this project
	# for u in users:
	# 	access = get_role_in_project(current_user.id, project.id, sampled_id)
	# 	users_and_access[u] = u.ROLES[access][1]
	return render_template('project/dashboard.html', project=project, sample_users_role=sample_users_role)


# TODO
@project.route('/project/<project_name>/admin/add/<int:id>', methods=['GET', 'POST'])
# @login_required
# @requires_access_level(2)
def add_user_with_access(id, project_name, access):
	user = User.query.get_or_404(id)
	project_id = Project.query.filter_by(project_name=project_name).first()
	new_project_access = ProjectAccess(projectid=project_id, accesslevel=access, userid=user.id)
	db.session.add(new_project_access)
	db.session.commit()
	flash('You have successfully added a user to your project.')
	return render_template('projects/add_user.html')## testing include function 
	##angular style of template inclusion and value inheritance


# TODO
@project.route('/project/<project_name>/admin/edit/<int:id>', methods=['GET', 'POST'])
# @login_required
# @requires_access_level(2)
def edit_role(id, role):
	check_admin()
	user = User.query.get_or_404(id)
	user.role = role
	db.session.add(user)
	db.session.commit()
	flash('You have successfully changed a users role')
	return render_template('projects/dashboard.html')


@project.route('/project/<project_name>/admin/remove/<int:id>', methods=['GET', 'POST'])
# @login_required
# @requires_access_level(2)
def remove_user(id):
	user = User.query.get_or_404(id)
	db.session.delete(user.project_id)
	db.session.commit()
	flash('You have successfully removed a user.')
	return render_template('projects/dashboard.html', )


###################################### Project Page Views and Functions ######################################
@project.route('/project/projectpage/<project_name>', methods=['GET', 'POST'])
def projectpage(project_name):
	"""
	Project Page Handler
	"""

	print ('========== [getSamples]')
	reply = grew_request ('getSamples', data={'project_id': project_name})
	reply = json.loads(reply)
	# print(reply)

	nb_sent = 0
	if reply.get("status") == "OK":
		samples = reply.get("data", [])
		for s in samples:
			s["users"] = " ".join(s.get("users", []))
			nb_sent += s.get("size", 0)
		nsamples = len(samples)

	project_id = Project.query.filter_by(name=project_name).first().id
	access_level = get_access_for_project(current_user.id, project_id)
		
	# private projects can only be viewed by non-guests
	is_private = Project.query.filter_by(name=project_name).first().is_private
	if access_level == 0 and is_private:
		flash("You don't have sufficient rights to view this project")
		return redirect(url_for('admin.list_projects'))

	return render_template('projects/index.html',project_name=project_name, title=project_name, samples=samples, n=nsamples, nb_sent=nb_sent, access=access_level)


@project.route('/project/<project_name>/<sample_name>')
# @login_required
def samplepage(project_name, sample_name):
	
	print ("========[getConll]")
	reply = grew_request('getConll', data={'project_id': project_name, 'sample_id':sample_name})
	# print(json.loads(reply))
	sent_ids = json.loads(reply).get("data", {})

	return render_template('projects/sample.html',project_name=project_name, dico=sent_ids, sample_name=sample_name)





# @project.route('/projects/projectpage/<project_name>/testing')
# @requires_access_level(0)
# def test_usersonly(project_id):
# 	return jsonify({"hello":"world"})



from flask import render_template, flash, redirect, url_for, jsonify, request, Response, abort, current_app, make_response
from flask_login import login_required, current_user
from werkzeug import secure_filename
import json, logging
from functools import wraps
import os
import re, base64
from ...utils.conll3 import conll3
from collections import OrderedDict
# from flask_cors import cross_origin
import io, zipfile, time

# local imports
from . import project
from ...models.models import *
from ...utils.grew_utils import grew_request

from ...services import project_service, user_service, robot_service, github_service


logging.getLogger('flask_cors').level = logging.DEBUG


def requires_access_level(access_level):
	"""	decorator for access control. except for superadmins """
	def decorator(f):
		@wraps(f)
		def decorated_function(*args, **kwargs):

			# not authenticated -> login
			if not current_user.id: return redirect(url_for('auth.login'))

			if kwargs.get("project_name"): project_id = project_service.get_by_name(kwargs["project_name"]).id
			elif kwargs.get("id"): project_id = kwargs["id"]
			else: abort(400)

			project_access = project_service.get_project_access(project_id, current_user.id)

			print("project_access for current user: {}".format(project_access))
			
			if not current_user.super_admin: # super_admin are always admin even if it's not in the table
				if isinstance(project_access, int): abort(403) 
				if project_access is None or project_access.accesslevel.code < access_level: abort(403)
					# return redirect(url_for('home.home_page'))

			return f(*args, **kwargs)
		return decorated_function
	return decorator


@project.route('/github_api/allow', methods=['GET'])
def allow_github_api():
	# TODO add flash message saying permissions for the github app have been granted
	js = json.dumps({})
	resp = Response(js, status=200,  mimetype='application/json')
	return redirect('/')


# @cross_origin()
@project.route('/fetch_all/', methods=['GET'])
def fetch_all_projects():
	"""
	Returns list of projects with:
	- visibility level
	- roles (of the current user if logged in)
	"""
	projects_info = project_service.get_hub_summary()
	js = json.dumps(projects_info)
	resp = Response(js, status=200,  mimetype='application/json')
	
	# resp.headers['Access-Control-Allow-Origin'] = '*'
	# resp.headers['Access-Control-Allow-Headers'] = '*'
	# resp.headers['Access-Control-Allow-Methods'] = '*'
	return resp


@project.route('/<project_name>/', methods=['GET'])
# @login_required
# @requires_access_level(2)
def project_info(project_name):
	"""
	GET project information

	list of samples (403 si projet privé et utilisateur pas de rôle)
	pê admin names, nb samples, nb arbres, description	

	infos: {
				name: projectname,
				admins : [],
				samples: [
					{ samplename: 'P_ABJ_GWA_10_Steven.lifestory_PRO', sentences: 80, tokens: 20, averageSentenceLength: 12.6, roles :{validators: [], annotators: []}, treesFrom: ['parser', 'tella', 'j.D'], exo: 'percentage'}, 
	"""
	# id ="rinema56@gmail.com"
	# current_user = user_service.get_by_id(id)
	project_infos = project_service.get_infos(project_name, current_user) # FIX : handles anonymous user
	# if project_infos == 403: abort(403)  # removed for now -> the check is done in view and for each actions
	js = json.dumps(project_infos, default=str)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp



@project.route('/<project_name>/treesfrom')
def project_treesfrom(project_name):
	''' get users treesfrom from a project '''
	users = project_service.get_project_treesfrom(project_name)
	js = json.dumps(users, default=str)
	resp = Response(js, status=200, mimetype='application/json')
	return resp


@project.route('/<project_name>/settings/fetch')
def get_project_settings(project_name):
	''' get project infos for settings view. Without bottleneck infos on samples '''
	project_infos = project_service.get_settings_infos(project_name, current_user)
	# if project_infos == 403: abort(403) # removed for now -> the check is done in view and for each actions
	js = json.dumps(project_infos, default=str)
	resp = Response(js, status=200, mimetype='application/json')
	return resp

# new from kim:
@project.route('/<project_name>/settings/update', methods=['POST'])
@requires_access_level(2)
def update_project_settings(project_name):
	""" add an admin/guest to the project {'user_id':id}"""
	print("___project_settings_update")
	if not request.json: abort(400)
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	user = user_service.get_by_id(request.json.get("user_id"))
	# if user: 
	# 	pa = project_service.get_project_access(project.id, user.id)
	# 	accesslevel_dict = {v: k for k, v in dict(ProjectAccess.ACCESS).items()}
	# 	if pa: pa.accesslevel = accesslevel_dict[target_role]
	# 	else: project_service.create_add_project_access(user.id, project.id, accesslevel_dict[target_role])
	# print("000000", request.json) # todo: handle this correctly, depending on whether it has to go to grew or to local storage
	
	for a,v in request.json.items():
		if a == "shownfeatures":
			project_service.update_features(project, v)
		elif a == "shownmeta":
			project_service.update_metafeatures(project, v)
		elif a == "annotationFeatures":
			# update the part of the config that is on grew (valid features, relations, upos...)
			reply = json.loads(grew_request("updateProjectConfig", current_app, data={"project_id":project_name, "config":json.dumps(v)}))
			if reply["status"] != "OK":
				abort(400)
			print("reply", reply)
		elif a == "showAllTrees":
			project_service.change_show_all_trees(project, v)
		elif a == "exerciseMode":
			project_service.change_exercise_mode(project, v)

			
	project_infos = project_service.get_settings_infos(project_name, current_user)
	if project_infos == 403: abort(403) 
	resp = Response( json.dumps(project_infos, default=str), status=200, mimetype='application/json' )
	return resp


@project.route('/<project_name>/conllu-schema/fetch', methods=['GET'])
def get_project_conllu_schema(project_name):
	''' get project config (annotation features json) for settings view.
		these data are stocked in grew server
	'''
	project_config_dict = project_service.get_project_config(project_name)
	# if project_infos == 403: abort(403) # removed for now -> the check is done in view and for each actions
	js = json.dumps(project_config_dict, default=str)
	resp = Response(js, status=200, mimetype='application/json')
	return resp

@project.route('/<project_name>/conllu-schema/update', methods=['POST'])
def update_project_conllu_schema(project_name):
	''' update project config (annotation features json) for settings view.
		these data are stocked in grew server.
	'''
	if not request.json: abort(400)
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	# user = user_service.get_by_id(request.json.get("user_id"))

	project_config_dict = request.json['config']
	project_service.update_project_config(project_name, project_config_dict)
	# if project_infos == 403: abort(403) # removed for now -> the check is done in view and for each actions
	js = json.dumps(project_config_dict, default=str)
	resp = Response(js, status=200, mimetype='application/json')
	return resp

# Kirian : this function is not use at the moment, instead, we use `project_userrole_add_many`
@project.route('/<project_name>/<target_role>/add', methods=['POST'])
@requires_access_level(2)
def project_userrole_add(project_name, target_role):
	""" add an admin/guest to the project {'user_id':id}"""
	if not request.json: abort(400)
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	user = user_service.get_by_id(request.json.get("user_id"))
	if user: 
		pa = project_service.get_project_access(project.id, user.id)
		accesslevel_dict = {v: k for k, v in dict(ProjectAccess.ACCESS).items()}
		if pa: pa.accesslevel = accesslevel_dict[target_role]
		else: project_service.create_add_project_access(user.id, project.id, accesslevel_dict[target_role])
	project_infos = project_service.get_settings_infos(project_name, current_user)
	if project_infos == 403: abort(403) 

	js = json.dumps(project_infos, default=str)
	resp = Response(js , status=200, mimetype='application/json' )
	return resp

# equivalent of project_userrole_add but can handle multiple users in one call
# TODO : delete one of these two 
@project.route('/<project_name>/<target_role>/add_many', methods=['POST'])
@requires_access_level(2)
def project_userrole_add_many(project_name, target_role):
	""" add an admin/guest to the project {'user_id':id}"""
	if not request.json: abort(400)
	project = project_service.get_by_name(project_name)
	if not project: abort(400)

	user_ids = request.json.get("user_id")
	for user_id in user_ids:
		user = user_service.get_by_id(user_id)
		if user:
			pa = project_service.get_project_access(project.id, user.id)
			accesslevel_dict = {v: k for k, v in dict(ProjectAccess.ACCESS).items()}
			if pa: 
				if pa.accesslevel.code < accesslevel_dict[target_role]:
					print("\naccess level is lower than new, replace !")
					project_service.delete_project_access(pa)
					project_service.create_add_project_access(user.id, project.id, accesslevel_dict[target_role])
				# pa.accesslevel = accesslevel_dict[target_role]
			else: project_service.create_add_project_access(user.id, project.id, accesslevel_dict[target_role])
	project_infos = project_service.get_settings_infos(project_name, current_user)
	if project_infos == 403: abort(403) 
	resp = Response( json.dumps(project_infos, default=str), status=200, mimetype='application/json' )
	return resp


@project.route('/<project_name>/<target_role>/remove', methods=['POST'])
@requires_access_level(2)
def project_userrole_remove(project_name, target_role):
	""" remove an admin/guest to the project {'user_id':id}"""
	if not request.json: abort(400)
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	user = user_service.get_by_id(request.json.get("user_id"))
	if user: 
		accesslevel_dict = {v: k for k, v in dict(ProjectAccess.ACCESS).items()}
		pa = project_service.get_project_access(project.id, user.id)
		if pa: project_service.delete_project_access(pa)
	project_infos = project_service.get_settings_infos(project_name, current_user)
	if project_infos == 403: abort(403) 
	resp = Response( json.dumps(project_infos, default=str), status=200, mimetype='application/json' )
	return resp


@project.route('/<project_name>/defaultusertrees/add', methods=['POST'])
@requires_access_level(2)
def project_defaultusertrees_add(project_name):
	""" add a defaultusertree to the project {'user':user}"""
	if not request.json: abort(400)
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	
	selected = json.loads(request.json.get("user"))
	print('selected', selected)
	if 'robot' in selected:
		r = robot_service.get_by_id(selected['id'])
		project_service.add_default_user_tree(project, r.id, r.username, robot=True)
	else:
		# user = user_service.get_by_id(request.json.get("user_id"))
		user = user_service.get_by_id(selected['id'])
		if user: project_service.add_default_user_tree(project, user.id, user.username)
	project_infos = project_service.get_settings_infos(project_name, current_user)
	if project_infos == 403: abort(403) 
	resp = Response( json.dumps(project_infos, default=str), status=200, mimetype='application/json' )
	return resp

@project.route('/<project_name>/defaultusertrees/remove', methods=['POST'])
@requires_access_level(2)
def project_defaultusertrees_remove(project_name):
	""" add a defaultusertree to the project {'dut_id':id}"""
	if not request.json: abort(400)
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	project_service.remove_default_user_tree(request.json.get("dut_id"))
	project_infos = project_service.get_settings_infos(project_name, current_user)
	if project_infos == 403: abort(403) 
	resp = Response( json.dumps(project_infos, default=str), status=200, mimetype='application/json' )
	return resp


@project.route('/<project_name>/showalltrees', methods=['POST'])
@requires_access_level(2)
def project_show_all_trees(project_name):
	if not request.json: abort(400)
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	value = request.json.get("value")
	project_service.change_show_all_trees(project_name, value)
	project_infos = project_service.get_settings_infos(project_name, current_user)
	resp = Response( json.dumps(project_infos, default=str), status=200, mimetype='application/json' )
	return resp

# @project.route('/<project_name>/openproject', methods=['POST'])
# @requires_access_level(2)
# def project_open_project(project_name):
# 	if not request.json: abort(400)
# 	project = project_service.get_by_name(project_name)
# 	if not project: abort(400)
# 	value = request.json.get("value")
# 	project_service.change_is_open(project_name, value)
# 	project_infos = project_service.get_settings_infos(project_name, current_user)
# 	resp = Response( json.dumps(project_infos, default=str), status=200, mimetype='application/json' )
# 	return resp

@project.route('/<project_name>/private', methods=['POST'])
@requires_access_level(2)
def project_private_project(project_name):
	if not request.json: abort(400)
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	value = request.json.get("value")
	project_service.change_visibility(project_name, value)
	project_infos = project_service.get_settings_infos(project_name, current_user)
	resp = Response( json.dumps(project_infos, default=str), status=200, mimetype='application/json' )
	return resp

@project.route('/<project_name>/description', methods=['POST'])
@requires_access_level(2)
def project_description(project_name):
	if not request.json: abort(400)
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	value = request.json.get("value")
	project_service.change_description(project_name, value)
	project_infos = project_service.get_settings_infos(project_name, current_user)
	resp = Response( json.dumps(project_infos, default=str), status=200, mimetype='application/json' )
	return resp

@project.route('/<project_name>/image', methods=['POST'])
@requires_access_level(2)
def project_image(project_name):
	if not request.files: abort(400)
	print('hey', request.files.to_dict(flat=False))
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	files = request.files.to_dict(flat=False).get("files")
	content = request.files['files'].read()
	project_service.change_image(project_name, content)
	project_infos = project_service.get_settings_infos(project_name, current_user)
	resp = Response( json.dumps(project_infos, default=str), status=200, mimetype='application/json' )
	return resp

# status : not currently used
# @project.route('/<project_name>/', methods=['POST'])
# @login_required
# @requires_access_level(2)
# def project_update(project_name):
# 	"""
# 	modifie project info

# 	par exemple
# 	ajouter admin / guest users:{nom:access, nom:access, nom:"" (pour enlever)}
# 	changer nom du projet project:{projectname:nouveaunom,description:nouvelledescription,isprivate:True, image:blob}
# 	"""
# 	if not request.json: abort(400)
# 	project = project_service.get_by_name(project_name)
# 	if not project: abort(400)
# 	if request.json.get("users"):
# 		for k,v in request.json.get("users").items():
# 			user = user_service.get_by_id(k)
# 			if user:
# 				pa = project_service.get_project_access(project.id, user.id)
# 				if pa:
# 					if v: # update
# 						pa.accesslevel = v
# 					else: # delete an existing project access
# 						project_service.delete_project_access(pa)
# 				else:
# 					if v: # create
# 						project_service.create_add_project_access(user.id, project.id, v)
# 					else:
# 						pass

# 			else: abort(400)
# 	if request.json.get("project"):
# 		print("**here**")
# 		for k,v in request.json.get("project").items():
# 			if k == "projectname":
# 				reply = json.loads(grew_request("renameProject", current_app, data={"project_id":project_name, "new_project_id":v}))
# 				if reply["status"] != "OK": abort(400)
# 				# update project_name if it went well
# 			setattr(project,k,v)
# 	db.session.commit()
# 	return project_info(project.projectname)






@project.route('/<project_name>/delete', methods=['DELETE'])
# @login_required
# @requires_access_level(2)
def delete_project(project_name):
	"""
	Delete a project
	no json
	"""
	project = project_service.get_by_name(project_name)
	if not project:	abort(400)
	pa = project_service.get_project_access(project.id, current_user.id)
	p_access=0
	if pa == 0: print('unauthorized, pa 0, error on crreation no access set'); project_service.delete(project)
	else: p_access = project_service.get_project_access(project.id, current_user.id).accesslevel.code
	if p_access >=2 or current_user.super_admin:
		project_service.delete(project)
	else:
		print("p_access to low for project {}".format(project.projectname))
		abort(403)
	projects = project_service.get_all()

	print("hub", project_service.get_hub_summary())
	print("projects", project_service.get_all())
	js = json.dumps(projects)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp


@project.route('/<project_name>/search', methods=["GET","POST"])
def search_project(project_name):
	"""
	expects json with grew pattern such as
	{
	"pattern":"pattern { N [upos=\"NUM\"] }"
	}
	important: simple and double quotes must be escaped!


	returns:
	{'sample_id': 'P_WAZP_07_Imonirhuas.Life.Story_PRO', 'sent_id': 'P_WAZP_07_Imonirhuas-Life-Story_PRO_97', 'nodes': {'N': 'Bernard_11'}, 'edges': {}}, {'sample_id':...
	"""

	project = project_service.get_by_name(project_name)
	if not project: abort(404)
	if not request.json: abort(400)

	pattern = request.json.get("pattern")
	reply = json.loads(grew_request("searchPatternInGraphs", current_app, data={"project_id":project.projectname, "pattern":pattern}))
	if reply["status"] != "OK": abort(400)
	trees={}

	# print(121212,reply["data"])
	# matches={}
	# reendswithnumbers = re.compile(r"_(\d+)$")

	for m in reply["data"]:
		if m['user_id'] == '': abort(409)
		conll = json.loads(grew_request("getConll", current_app, data={"sample_id":m["sample_id"], "project_id":project.projectname, "sent_id":m["sent_id"], "user_id":m['user_id']}))
		if conll["status"] != "OK": abort(404)
		conll = conll["data"]
		# trees=project_service.formatTrees(m, trees, conll, m['user_id'])
		trees=project_service.formatTrees_new(m, trees, conll)
	# print(56565,trees)
	js = json.dumps(trees)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp
	

@project.route('/<project_name>/tryRule', methods=["GET","POST"])
def tryRule_project(project_name):
	"""
	expects json with grew pattern such as
	{
	"pattern":"pattern { N [upos=\"NUM\"] }"
	"rewriteCommands":"commands { N [upos=\"NUM\"] }"
	}
	important: simple and double quotes must be escaped!


	returns:
	{'sample_id': 'P_WAZP_07_Imonirhuas.Life.Story_PRO', 'sent_id': 'P_WAZP_07_Imonirhuas-Life-Story_PRO_97', 'nodes': {'N': 'Bernard_11'}, 'edges': {}}, {'sample_id':...
	"""
	
	project = project_service.get_by_name(project_name)
	if not project: abort(404)
	if not request.json: abort(400)
	
	pattern = request.json.get("pattern")
	rewriteCommands = request.json.get("rewriteCommands")
	# tryRule(<string> project_id, [<string> sample_id], [<string> user_id], <string> pattern, <string> commands)
	
	print( pattern, rewriteCommands)
	reply = json.loads(grew_request("tryRule", current_app, data={"project_id":project.projectname, "pattern":pattern, "commands":rewriteCommands}))
	print(8989,reply)
	if reply["status"] != "OK": 
		if 'message' in reply:
			resp =  jsonify({'status': reply["status"], 'message': reply["message"]  })
			resp.status_code = 444
			return resp
		abort(400)
	trees={}
	print(78787)
	print(121212,reply["data"])
	# matches={}
	# reendswithnumbers = re.compile(r"_(\d+)$")
	# {'WAZL_15_MC-Abi_MG': {'WAZL_15_MC-Abi_MG__8': {'sentence': '# kalapotedly < you see < # ehn ...', 'conlls': {'kimgerdes': ..
	for m in reply["data"]:
		if m['user_id'] == '': abort(409)
		print('___')
		# for x in m:
		# 	print('mmmm',x)
		trees['sample_id']=trees.get('sample_id',{})
		trees['sample_id']['sent_id']=trees['sample_id'].get('sent_id',{'conlls':{},'nodes': {}, 'edges': {}})
		trees['sample_id']['sent_id']['conlls'][m['user_id']]=m['conll']
		# trees['sample_id']['sent_id']['matches'][m['user_id']]=[{"edges":{},"nodes":{}}] # TODO: get the nodes and edges from the grew server!
		if 'sentence' not in trees['sample_id']['sent_id']:
			trees['sample_id']['sent_id']['sentence'] = conll3.conll2tree(m['conll']).sentence()
		# print('mmmm',trees['sample_id']['sent_id'])
		
	

	js = json.dumps(trees)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp
	


@project.route('/<project_name>/upload', methods=["POST", "OPTIONS"])
# @cross_origin()
# @cross_origin(origin='*', headers=['Content-Type', 'Authorization', 'Access-Control-Allow-Credentials'])
@requires_access_level(2)
def sample_upload(project_name):
	"""
	project/<projectname>/upload
	POST multipart
	multipart (fichier conll), import_user (if not contained in the file's metadata)

	TODO: verify either importuser or provided in conll (all the trees must have it)
	more generally: test conll!
	"""
	project = project_service.get_by_name(project_name)
	if not project: abort(404)

	fichiers = request.files.to_dict(flat=False).get("files")
	robot_active = request.form.get("robot", "false")
	robot_name = request.form.get("robotname", "")
	if robot_active == 'true': 
		import_user = robot_name
		robot_service.create_or_get_robot_for_project(robot_name, project.id)

	else : import_user = request.form.get("import_user", "") # TODO : change import_user
	print("IMPORT USER: {}".format(import_user))
	if fichiers:
		reextensions = re.compile(r'\.(conll(u|\d+)?|txt|tsv|csv)$')
		samples  = project_service.get_samples(project_name)
		for f in fichiers: 
			status, message = project_service.upload_sample(f, project_name, import_user, reextensions=reextensions, existing_samples=samples)
			if status!=200:
				print(message)	
				resp =  jsonify({'status': status, 'message': message  })
				resp.status_code = status
				return resp
	samples = {"samples":project_service.get_samples(project_name)}
	js = json.dumps(samples)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp

@project.route('/create', methods=["POST"])
@login_required
# @cross_origin()
def create_project():
	''' create an emty project'''
	project = request.get_json()['project']
	creator = current_user.id
	project_service.create_empty_project(project, creator)
	js = json.dumps({})
	resp = Response(js, status=200, mimetype='application/json')
	return resp

@project.route('/<project_name>/create/upload', methods=["POST", "OPTIONS"])
# @cross_origin()
# @cross_origin(origin='*', headers=['Content-Type', 'Authorization', 'Access-Control-Allow-Credentials'])
def project_create_upload(project_name):
	"""
	projects/<projectname>/create
	POST multipart
	create a project with a starter sample
	"""

	fichiers = request.files.to_dict(flat=False).get("files")
	import_user = request.form.get("import_user", "") 
	print("IMPORT USER: {}\t create project: {}".format(import_user, project_name))
	if fichiers:
		reextensions = re.compile(r'\.(conll(u|\d+)?|txt|tsv|csv)$')
		# samples  = project_service.get_samples(project_name)
		for f in fichiers:
			project_service.upload_project(f, project_name, import_user, reextensions=reextensions)

	# samples = {"samples":project_service.get_samples(project_name)}
	# print(samples)
	# js = json.dumps(samples)
	js = json.dumps({})
	resp = Response(js, status=200,  mimetype='application/json')
	return resp

@project.route('/<project_name>/update_config', methods=["POST"])
# @cross_origin()
# @cross_origin(origin='*', headers=['Content-Type', 'Authorization', 'Access-Control-Allow-Credentials'])
@requires_access_level(2)
def project_update_config(project_name):
	"""
	Update the project configuration

	relations : [["comp", "subj"], [":obj"], ["@x"]] # relations available in the dropdown menu
	cat : ["NOUN", "ADV"] # pos available in the dropdown menu
	sentencefeatures : ["text", "sent_id"] # sentence features shown in order
	features : ["lemma", "gloss"] # node features shown in order
	"""
	project = project_service.get_by_name(project_name)
	if not project: abort(404)
	pa = project_service.get_project_access(project.id, current_user.id)
	if pa < 2: abort(403)
	if not request.json: abort(400)

	data = request.get_json(force=True)

	# defaults
	if not data.get("relations"):
		data["relations"] = [["subj", "comp", "vocative", "det", "dep", "mod", "conj", "cc", "parataxis", "fixed", "flat", "compound", "discourse", "dislocated", "goeswith", "orphan", "punct", "root"],[":aux",":caus",":cleft",":pred",":appos"],["@comp","@mod","@subj","@dep","@det"]]
	if not data.get("cat"):
		data["cat"] = ["ADJ", "ADP", "ADV", "AUX", "CCONJ", "DET", "INTJ", "NOUN", "NUM", "PART", "PRON", "PROPN", "PUNCT", "SCONJ", "VERB", "X"]
	js = json.dumps(data)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp


# @project.route('/<project_name>/config/cat/<action>', methods=["POST"])
# # @cross_origin()
# @requires_access_level(2)
# def project_cat_add(project_name, action):
# 	project = project_service.get_by_name(project_name)
# 	if not project: abort(404)
# 	if not request.json: abort(400)
# 	data = request.get_json(force=True)

# 	if not data.get("cat"): abort(400)
# 	cats = list()
# 	if action == 'add':	cats = project_service.add_cat_label(project_name, current_user, data.get("cat") )
# 	elif action == 'delete': cats = project_service.remove_cat_label(project_name, current_user, data.get("cat") )
# 	else: abort(400)
# 	js = json.dumps(cats, default=str)
# 	resp = Response(js, status=200, mimetype='application/json')
# 	return resp

# @project.route('/<project_name>/config/txtcats', methods=["POST"])
# # @cross_origin()
# @requires_access_level(2)
# def project_txtcats(project_name):
# 	project = project_service.get_by_name(project_name)
# 	if not project: abort(404)
# 	if not request.json: abort(400)
# 	data = request.get_json(force=True)

# 	if not data.get("cats"): abort(400)
# 	cats = list()
# 	cats = project_service.parse_txtcats(project, data.get("cats"))
# 	js = json.dumps(cats, default=str)
# 	resp = Response(js, status=200, mimetype='application/json')
# 	return resp

# @project.route('/<project_name>/config/txtlabels', methods=["POST"])
# # @cross_origin()
# @requires_access_level(2)
# def project_txtlabels(project_name):
# 	project = project_service.get_by_name(project_name)
# 	if not project: abort(404)
# 	if not request.json: abort(400)
# 	data = request.get_json(force=True)

# 	if not data.get("labels"): abort(400)
# 	labels = list()
# 	labels = project_service.parse_txtlabels(project, data.get("labels"))
# 	js = json.dumps(labels, default=str)
# 	resp = Response(js, status=200, mimetype='application/json')
# 	return resp

# @project.route('/<project_name>/config/stock/<action>', methods=["POST"])
# # @cross_origin()
# @requires_access_level(2)
# def project_stock_add(project_name, action):
# 	project = project_service.get_by_name(project_name)
# 	if not project: abort(404)
# 	if not request.json: abort(400)
# 	data = request.get_json(force=True)

# 	if not data.get("stockid"): abort(400)
# 	labels = list()
# 	if action == 'add': labels = project_service.add_stock(project_name)
# 	elif action == 'delete': labels = project_service.remove_stock(project_name, data.get("stockid"))
# 	else: abort(400)
# 	js = json.dumps(labels, default=str)
# 	resp = Response(js, status=200, mimetype='application/json')
# 	return resp

# @project.route('/<project_name>/config/label/<action>', methods=["POST"])
# # @cross_origin()
# @requires_access_level(2)
# def project_label_add(project_name, action):
# 	project = project_service.get_by_name(project_name)
# 	print(1)
# 	if not project: abort(404)
# 	if not request.json: abort(400)
# 	data = request.get_json(force=True)

# 	print(2, data)
# 	if not data.get("stockid"): abort(400)
# 	labels = list()
# 	if action == 'add': labels = project_service.add_label(project_name, data.get("stockid"), data.get("label"))
# 	elif action == 'delete': labels = project_service.remove_label(project_name, data.get("labelid"), data.get("stockid"), data.get("label"))
# 	else: abort(400)
# 	js = json.dumps(labels, default=str)
# 	resp = Response(js, status=200, mimetype='application/json')
# 	return resp


# @project.route('/<project_name>/export/zip', methods=["POST", "GET"])
@project.route('/<project_name>/export/zip', methods=["POST"])
# @cross_origin()
# @requires_access_level(1) # not for open projects
def sample_export(project_name):
	project = project_service.get_by_name(project_name)
	if not project: abort(404)
	if not request.json: abort(400)
	
	data = request.get_json(force=True)
	samplenames = data['samples']
	print("requested zip", samplenames, project_name)
	sampletrees = list()
	samplecontentfiles = list()
	for samplename in samplenames: 
		reply = json.loads(grew_request('getConll', current_app, data={'project_id': project_name, 'sample_id':samplename}))
		if reply.get("status") == "OK":

			# {"sent_id_1":{"conlls":{"user_1":"conllstring"}}}
			sample_tree = json.loads(project_service.servSampleTrees(reply.get("data", {})  ))
			sample_content = project_service.sampletree2contentfile(sample_tree)

			for sent_id in sample_tree:
				
				last = project_service.get_last_user(sample_tree[sent_id]["conlls"])
				sample_content["last"] = sample_content.get("last", []) + [sample_tree[sent_id]["conlls"][last]]
			
			# gluing back the trees
			sample_content["last"] = "\n\n".join(sample_content["last"])
			samplecontentfiles.append(sample_content)

		else:
			print("Error: {}".format(reply.get("message")))

	memory_file = project_service.contentfiles2zip(samplenames, samplecontentfiles)

	resp = Response(memory_file, status=200,  mimetype='application/zip', headers={'Content-Disposition':'attachment;filename=dump.{}.zip'.format(project_name)})
	return resp


@project.route('/<project_name>/sample/<sample_name>', methods=['GET'])
def samplepage(project_name, sample_name):
	"""
	GET
	nb_sentences, nb_trees, list of annotators, list of validators

	TODO: tester si le projet est privé
	pour l'arbre : annotateur ne peut pas voir d'autres arbres sauf la base

	returns:
	{
	"P_ABJ_GWA_10_Steven-lifestory_PRO_1": {
		"sentence": "fdfdfsf",
		"conlls":{
		"yuchen": "# elan_id = ABJ_GWA_10_M_001 ABJ_GWA_10_M_002 ABJ_GWA_10_M_003\n# sent_id = P_ABJ_GWA_10_Steven-lifestory_PRO_1\n# sent_translation = I stay with my mother in the village. #\n# text = I dey stay with my moder //+ # for village //\n1\tI\t_\tINTJ\t_\tCase=Nom|endali=2610|Number=Sing|Person=1|PronType=Prs|
		....
	"""
	print ("========[getConll]")
	reply = json.loads(grew_request('getConll', current_app, data={'project_id': project_name, 'sample_id':sample_name}))
	reendswithnumbers = re.compile(r"_(\d+)$")
	
	if reply.get("status") == "OK":
		samples = reply.get("data", {})	
		project = project_service.get_by_name(project_name)
		if not project: abort(404)
		if project.show_all_trees or project.visibility == 2:
			js = json.dumps( project_service.samples2trees(samples, sample_name) )
		else:
			validator = project_service.is_validator(project.id, sample_name, current_user.id)
			if validator:  js = json.dumps( project_service.samples2trees(samples, sample_name) )
			else:  js = json.dumps( project_service.samples2trees_with_restrictions(samples, sample_name, current_user, project_name) )
		# print(js)
		resp = Response(js, status=200,  mimetype='application/json')
		return resp
	else: abort(409)
 

@project.route('/<project_name>/sample/<sample_name>/search', methods=['GET', 'POST'])
def search_sample(project_name, sample_name):
	"""
	Aplly a grew search inside a project and sample
	"""
	project = project_service.get_by_name(project_name)
	if not project: abort(404)
	if not request.json: abort(400)

	samples = {"samples":project_service.get_samples(project_name)}
	if not sample_name in samples["samples"]: abort(404)

	pattern = request.json.get("pattern")
	reply = json.loads(grew_request("searchPatternInGraphs", current_app, data={"project_id":project.projectname, "pattern":pattern}))
	if reply["status"] != "OK": abort(400)

	trees={}
	# matches={}
	# reendswithnumbers = re.compile(r"_(\d+)$")

	for m in reply["data"]:
		if m["sample_id"] != sample_name: continue
		if m['user_id'] == '': abort(409)

		conll = json.loads(grew_request("getConll", current_app, data={"sample_id":m["sample_id"], "project_id":project.projectname, "sent_id":m["sent_id"], "user_id":m['user_id']}))
		if conll["status"] != "OK": abort(404)
		conll = conll["data"]
		# trees=project_service.formatTrees(m, trees, conll, m['user_id'])
		trees=project_service.formatTrees_new(m, trees, conll)
		# # adding trees
		# # {trees:{sent_id:{user:conll, user:conll}}, matches:{(sent_id, user_id):[{nodes: [], edges:[]}]}}
		# if m["sent_id"] not in trees:
		# 	t = conll3.conll2tree(conll)
		# 	s = t.sentence()
		# 	trees[m["sent_id"]] = {"sentence":s, "conlls":{user_id:conll}}
		# else:
		# 	trees[m["sent_id"]]["conlls"].update(user_id=conll)
		# nodes = []
		# for k in m['nodes'].values():
		# 	nodes +=[k.split("_")[-1]]

		# edges = []
		# for k in m['edges'].values():
		# 	edges +=[k.split("_")[-1]]

		# matches[m["sent_id"]+'____'+user_id] = {"edges":edges,"nodes":nodes}

	js = json.dumps(trees)
	resp = Response(js, status=200,  mimetype='application/json')

	return resp


@project.route('/<project_name>/sample/<sample_name>/users', methods=['GET'])
# @login_required
def sampleusers(project_name, sample_name):
	"""
	project/<projectname>/<samplename>/users
	POST
	json {username:status} statut: annotator, validator
	DELETE
	enlever tout statut
	
	"""
	print ("========[sampleusers]")

	project = project_service.get_by_name(project_name) 
	if not project: abort(404)
	sampleusers = project_service.get_samples_roles(project.id, sample_name, json=True)
	js = json.dumps(sampleusers)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp


@project.route('/<project_name>/sample/<role>/add', methods=['POST'])
@requires_access_level(2)
def addRole2Sample(project_name, role):
	''' add or displace (toggle fashion) a role to a user for a specific in-project sample '''
	print('1')
	if not request.json: abort(400)
	req = request.json
	samples = {"samples":project_service.get_samples(req['projectname'])}
	res = {}
	print(2, req)
	if 'samplename' in req:
		if not req['samplename'] in samples["samples"]: abort(404)
		possible_roles = [x[0] for x in project_service.get_possible_roles()]
		roleInt = [r[0] for r in project_service.get_possible_roles() if r[1] == role][0]
		user = user_service.get_by_username(req['username'])
		if not user: abort(400)
		project_service.add_or_delete_sample_role(user, req['samplename'], req['projectname'], roleInt, False)
		sample = project_service.get_sample(req['samplename'], req['projectname'])
		res = sample
	js = json.dumps(res)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp

@project.route('/<project_name>/sample/<role>/remove', methods=['POST'])
@requires_access_level(2)
def removeRole2Sample(project_name, role):
	''' remove a role to a user for a specific in-project sample '''
	if not request.json: abort(400)
	req = request.json
	samples = {"samples":project_service.get_samples(req['projectname'])}
	res = {}
	if 'samplename' in req:
		if not req['samplename'] in samples["samples"]: abort(404)
		possible_roles = [x[0] for x in project_service.get_possible_roles()]
		roleInt = [r[0] for r in project_service.get_possible_roles() if r[1] == role][0]
		user = user_service.get_by_username(req['username'])
		if not user: abort(400)
		project_service.add_or_delete_sample_role(user, req['samplename'], req['projectname'], roleInt, True)
		sample = project_service.get_sample(req['samplename'], req['projectname'])
		res = sample
	js = json.dumps(res)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp



@project.route('/<project_name>/sample/<sample_name>/users', methods=['POST'])
# @login_required
@requires_access_level(2)
def userrole(project_name, sample_name):
	"""
	project/<projectname>/<samplename>/users
	POST
	json {username:status} statut: annotator, validator
	if status is empty: DELETE user
	enlever tout statut
	
	"""
	project = project_service.get_by_name(project_name)
	if not project: abort(404)
	if not request.json: abort(400)

	

	# # TODO : check that sample exists
	samples = {"samples":project_service.get_samples(project_name)}
	if not sample_name in samples["samples"]: abort(404)
	possible_roles = [x[0] for x in project_service.get_possible_roles()]

	for u,r in request.json.items():
		user = user_service.get_by_id(u)
		if not user: abort(400)
		if r:
			if r not in possible_roles: abort(400)
			project_service.create_add_sample_role(u, sample_name, project.id, r)
		else:
			sr = SampleRole.query.filter_by(projectid=project.id, samplename=sample_name, userid=u).first()
			if sr: project_service.delete_sample_role(sr)
	return sampleusers(project_name, sample_name)



@project.route('/<project_name>/sample/<sample_name>', methods=['DELETE'])
@login_required
@requires_access_level(2)
def delete_sample(project_name, sample_name):
	"""
	Delete a sample and everything in the db related to this sample
	"""
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	project_service.delete_sample(project_name, project.id, sample_name)
	return project_info(project_name)


@project.route('/<project_name>/sample/<sample_name>', methods=['POST'])
# @login_required
@requires_access_level(2)
def update_sample(project_name, sample_name):
	"""
	TODO 
	"""
	pass


@project.route("/<project_name>/saveTrees", methods=["POST"])
@login_required
# @requires_access_level(1)
def save_trees(project_name):
	project = project_service.get_by_name(project_name)
	print("save_trees",project_name, project)
	if not project:
		print("problem with proj")
		abort(404)
	if not request.json: 
		print("problem with request.json")
		abort(400)


	# samples = {"samples":project_service.get_samples(project_name)}
	# if not sample_name in samples["samples"]:
	# 	print("problem with sample")
	# 	abort(404)

	data = request.json
	if data:
		print(data)
		trees = data.get("trees")
		# no user_id was sent : save to current_user, else save to provided user
		# user_id = data.get("user_id", current_user.id)
		user_id = data.get("user_id", current_user.id)
		
		# if not user_id: abort(400)
		for tree in trees:
			sample_name = tree.get("sample_name")
			sent_id = tree.get("sent_id")
			conll = tree.get("conll")

			print("saving", sample_name, sent_id)
			
			# print(464564,conll)
			# if not sent_id: abort(400)
			if not conll: abort(400)
			if project.visibility != 2:
				if not project_service.is_annotator(project.id, sample_name, current_user.id) or not project_service.is_validator(project.id, sample_name, current_user.id):
					abort(403)
	
			print(">>>>", project_name)
			reply = grew_request (
				'saveGraph', current_app,
				data = {'project_id': project_name, 'sample_id': sample_name, 'user_id':user_id, 'sent_id':sent_id, "conll_graph":conll}
				)
			resp = json.loads(reply)
			if resp["status"] != "OK":
				print(resp)
				if "data" in resp:
					response = jsonify({'status': 400, 'message': str(resp["data"])  })
				else: 
					response = jsonify({'status': 400, 'message': 'You idiots!...'  })
				response.status_code = 400
				abort(response)
			
	resp = Response(dict(), status=200,  mimetype='application/json')
	return resp



# TODO : if user is not currently authenticated, they should only have access to recent mode
@project.route("/<project_name>/relation_table", methods=["POST"])
# @login_required
def get_relation_table(project_name):
	project = project_service.get_by_name(project_name)
	print('project', project)
	if not project:
		print("problem with proj")
		abort(404)

	if not request.json: abort(400)
	table_type = request.json.get("table_type")
	if not table_type : abort(400)

	reply = grew_request (
				'searchPatternInGraphs', current_app,
				data = {'project_id': project_name, "pattern":'pattern { e: GOV -> DEP}', "clusters":["e; GOV.upos; DEP.upos"]}
				)
	response = json.loads(reply)
	if response["status"] != "OK": abort(400)
	# current_user.id = "gael.guibon"
	data = response.get("data")
	for e, v in data.items():
		for gov, vv in v.items():
			for dep, vvv in vv.items():
				trees = dict()
				for elt in vvv:
					if table_type == 'user':
						if elt["user_id"] != current_user.username:
							continue
						else:
							conll = elt.get("conll")
							trees = project_service.formatTrees_new(elt, trees, conll)
					else:
						conll = elt.get("conll")
						trees = project_service.formatTrees_new(elt, trees, conll)

				# filtering out
				if table_type == "recent":
					for samp in trees:
						for sent in trees[samp]:
							last = project_service.get_last_user(trees[samp][sent]["conlls"])
							trees[samp][sent]["conlls"] = {last:trees[samp][sent]["conlls"][last]}
							trees[samp][sent]["matches"] = {last:trees[samp][sent]["matches"][last]}
				elif table_type == "user_recent":
					for samp in trees:
						for sent in trees[samp]:
							if current_user.username in trees[samp][sent]["conlls"]:
								trees[samp][sent]["conlls"] = {current_user.username:trees[samp][sent]["conlls"][current_user.username]}
								trees[samp][sent]["matches"] = {current_user.username:trees[samp][sent]["matches"][current_user.username]}
							else:
								last = project_service.get_last_user(trees[samp][sent]["conlls"])
								trees[samp][sent]["conlls"] = {last:trees[samp][sent]["conlls"][last]}
								trees[samp][sent]["matches"] = {last:trees[samp][sent]["matches"][last]}
				elif table_type == "all":
					pass
				data[e][gov][dep] = trees
	js = json.dumps(data)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp



def commit_sample(project_name, sample_name, commit_type):
	reply = json.loads(grew_request('getConll', current_app, data={'project_id': project_name, 'sample_id':sample_name}))
	if reply.get("status") == "OK":
		sample = reply.get("data", {})	
		content = {}

		for sent_id in sample:
			
			if commit_type == 'all':
				for user, conll in sample[sent_id].items():
					content[user] = content.get(user, []) + [conll]
			elif commit_type == "user":
				if current_user.username in sample[sent_id]:
					conll = sample[sent_id][current_user.username]
					content[current_user.username] = content.get(current_user.username, []) + [conll]
			elif commit_type == "recent":
				last = project_service.get_last_user(sample[sent_id])
				conll = sample[sent_id][last]
				content[current_user.username] = content.get(current_user.username, []) + [conll]
			elif commit_type == "user_recent":
				if current_user.username in sample[sent_id]:
					conll = sample[sent_id][current_user.username]
				else:
					last = project_service.get_last_user(sample[sent_id])
					conll = sample[sent_id][last]
				content[current_user.username] = content.get(current_user.username, []) + [conll]	

		# no trees for the user
		if commit_type == 'user' and current_user.username not in content :
			return 204

		# user-based mode 
		elif commit_type in ['user', 'user_recent', 'recent']:
			content = "\n\n".join(content[current_user.username])
			content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

			user_repo = github_service.get_user_repository(current_user.username)

			if commit_type == "recent":
				suffix = "_last"
			else:
				suffix = "_"+current_user.username

			resp = github_service.exists_sample(current_user.username, project_name, sample_name+suffix)

			if resp.status_code == 200:
				print("updating sample - commit type : {}".format(commit_type))
				sha = json.loads(resp.content.decode())["sha"]
				data = {'sha':sha, 'content':content, 'message':'updating sample', 'author':{"name":current_user.username, "email":"unknown"}}
			else:
				print(resp.status_code)
				print("new sample - commit type : {}".format(commit_type))
				data = {'content':content, 'message':'uploading a new sample', 'author':{"name":current_user.username, "email":"unknown"}}

			resp = github_service.make_commit(user_repo, data, project_name, sample_name+suffix)
			print(resp.status_code)
			# print(resp.content.decode())
			return resp.status_code

		# admin mode : commit all trees in separate files
		elif commit_type == 'all':
			for username in content:
				conll_content = "\n\n".join(content[username])
				conll_content = base64.b64encode(conll_content.encode("utf-8")).decode("utf-8")

				user_repo = github_service.get_user_repository(current_user.username)
				suffix = "_"+username
				print("sample outfile : ", sample_name+suffix)
				resp = github_service.exists_sample(current_user.username, project_name, sample_name+suffix)

				if resp.status_code == 200:
					print("updating sample - commit type : {}".format(commit_type))
					sha = json.loads(resp.content.decode())["sha"]
					data = {'sha':sha, 'content':conll_content, 'message':'updating sample', 'author':{"name":current_user.username, "email":"unknown"}}
				else:
					print(resp.status_code)
					print("new sample - commit type : {}".format(commit_type))
					data = {'content':conll_content, 'message':'uploading a new sample', 'author':{"name":current_user.username, "email":"unknown"}}

				resp = github_service.make_commit(user_repo, data, project_name, sample_name+suffix)
				print(resp.status_code)
				print(resp.content.decode())
				if resp.status_code not in [200, 201]:
					abort(resp.status_code)
			return resp.status_code

	else:
		return 404


@project.route("/<project_name>/commit", methods=["POST"])
@login_required
# @requires_access_level(1)
def commit(project_name):
	project = project_service.get_by_name(project_name)
	if not project: abort(404)
	if not request.json: abort(400)
	sample_names = request.json.get("samplenames")
	commit_type = request.json.get("commit_type")
	print(sample_names, commit_type)
	# the user has an installation_id /!\ the user can remove their installation at all times so don't store in the db
	installation_id = github_service.get_installation_id()
	if installation_id:
		for sample_name in sample_names:
			exit_code = commit_sample(project_name, sample_name, commit_type)
			if exit_code == 204:
				print("no trees for user")
				resp =  jsonify({'status': exit_code, 'message': 'No trees were found for user {}, please make some trees before comitting the samples.'.format(current_user.username)  })
				resp.status_code = exit_code
				return resp
			# 200 : ok, 201 : created (if the sample is new for the user)
			if exit_code not in [200, 201]:
				abort(exit_code)
	else:
		status = 418
		if current_app.config['ENV'] == 'development':
			message = """It seems like you haven't installed the github arborator-grew-dev application yet.<br>
			Access to this feature is only available to users that have installed the app.<br>
			1. Create a repository on your github account (this will act as your storage base).<br>
			2. Go to https://github.com/apps/arborator-grew-dev/ and click Install<br>
			3. Look over the granted permissions and if you accept select 1 repository (created at step 1.) and click Install & Authorize."""
			
		elif current_app.config['ENV'] == 'production':
			message = """It seems like you haven't installed the github arborator-grew-dev application yet.<br>
			Access to this feature is only available to users that have installed the app.<br>
			1. Create a repository on your github account (this will act as your storage base).<br>
			2. Go to https://github.com/apps/arborator-grew/ and click Install<br>
			3. Look over the granted permissions and if you accept select 1 repository (created at step 1.) and click Install & Authorize."""

		# TODO mettre un petit message pour dire qu'il faut se connecter via github + donner permissions
		resp =  jsonify({'status': status, 'message': message  })
		resp.status_code = status
		return resp

	resp = Response(dict(), status=200,  mimetype='application/json')
	return resp



def pull_sample_and_save_on_grew(github_user, project_name, sample_name, tree_user):
	resp = github_service.get_sample(github_user, project_name, sample_name+"_"+tree_user)
	if resp.status_code == 404:
		resp = Response({"message":"This sample is absent from your github storage which makes pulling impossible."}, status=404,  mimetype='application/json')
		return resp
	elif resp.status_code != 200:
		abort(resp.status_code)
	else:
		content = json.loads(resp.content.decode()).get("content")
		content = base64.b64decode(content).decode("utf-8")
		reply = grew_request (
				'saveConll', current_app,
				data = {'project_id': project_name, 'sample_id': sample_name, 'user_id':tree_user},
				files = {'conll_file':content}
				)
		resp = json.loads(reply)
		if resp["status"] != "OK":
			print(resp)
			abort(404)
		return 200


@project.route("/<project_name>/pull", methods=["POST"])
@login_required
# @requires_access_level(1)
def pull(project_name):
	project = project_service.get_by_name(project_name)
	if not project: abort(404)
	if not request.json: abort(400)
	sample_names = request.json.get("samplenames")
	pull_type = request.json.get("pull_type")
	print(sample_names, pull_type)

	# the user has an installation_id /!\ the user can remove their installation at all times so don't store in the db
	installation_id = github_service.get_installation_id()
	
	if installation_id:
		for sample_name in sample_names:
			print(sample_name, pull_type)
			if pull_type == 'user':
				print("!!")
				status = pull_sample_and_save_on_grew(current_user.username, project_name, sample_name, current_user.username)
				print(current_user.username, status)
			elif pull_type == 'all':
				print("**")
				users = github_service.get_all_users(current_user.username, project_name, sample_name)
				for u in users:
					status = pull_sample_and_save_on_grew(current_user.username, project_name, sample_name, u)
					print(u, status)
		
		resp = Response(dict(), status=200,  mimetype='application/json')
		return resp
	else:
		status = 418
		if current_app.config['ENV'] == 'development':
			message = """It seems like you haven't installed the github arborator-grew-dev application yet.<br>
			Access to this feature is only available to users that have installed the app.<br>
			1. Create a repository on your github account (this will act as your storage base).<br>
			2. Go to https://github.com/apps/arborator-grew-dev/ and click Install<br>
			3. Look over the granted permissions and if you accept select 1 repository (created at step 1.) and click Install & Authorize."""
			
		elif current_app.config['ENV'] == 'production':
			message = """It seems like you haven't installed the github arborator-grew application yet.<br>
			Access to this feature is only available to users that have installed the app.<br>
			1. Create a repository on your github account (this will act as your storage base).<br>
			2. Go to https://github.com/apps/arborator-grew/ and click Install<br>
			3. Look over the granted permissions and if you accept select 1 repository (created at step 1.) and click Install & Authorize."""

		# TODO mettre un petit message pour dire qu'il faut se connecter via github + donner permissions
		resp =  jsonify({'status': status, 'message': message  })
		resp.status_code = status
		return resp


@project.route("/<project_name>/getLexicon", methods=["POST"])
@login_required
# @requires_access_level(1)
def getLexicon(project_name):
	project = project_service.get_by_name(project_name)
	if not project: abort(404)
	if not request.json: abort(400)
	sample_names = request.json.get("samplenames")
	treeSelection = request.json.get("treeSelection")
	print(sample_names, treeSelection)

	temp_d = [ {  "form": "dis",  "lemma": "dis",  "POS": "DET",  "features": "Number=Sing|PronType=Dem",  "gloss": "SG.DEM",  "frequency": 12 }, {  "form": "#",  "lemma": "#",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 211 }, {  "form": "story",  "lemma": "story",  "POS": "NOUN",  "features": "_",  "gloss": "story",  "frequency": 2 }, {  "form": "wen",  "lemma": "wey",  "POS": "SCONJ",  "features": "gloss=REL",  "gloss": "when",  "frequency": 5 }, {  "form": "I",  "lemma": "I",  "POS": "PRON",  "features": "Case=Nom|Number=Sing|Person=1|PronType=Prs",  "gloss": "NOM.SG.1",  "frequency": 51 }, {  "form": "wan",  "lemma": "want",  "POS": "VERB",  "features": "_",  "gloss": "want",  "frequency": 2 }, {  "form": "give",  "lemma": "give",  "POS": "VERB",  "features": "_",  "gloss": "give",  "frequency": 10 }, {  "form": "now",  "lemma": "now",  "POS": "ADV",  "features": "_",  "gloss": "now",  "frequency": 3 }, {  "form": "<",  "lemma": "<",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 47 }, {  "form": "na",  "lemma": "na",  "POS": "PART",  "features": "PartType=Cop",  "gloss": "be.COP",  "frequency": 15 }, {  "form": "about",  "lemma": "about",  "POS": "ADP",  "features": "_",  "gloss": "about",  "frequency": 2 }, {  "form": "my",  "lemma": "my",  "POS": "PRON",  "features": "Number=Sing|Person=1|Poss=Yes",  "gloss": "SG.1.POSS",  "frequency": 33 }, {  "form": "own",  "lemma": "own",  "POS": "ADJ",  "features": "_",  "gloss": "own",  "frequency": 2 }, {  "form": "life",  "lemma": "life",  "POS": "NOUN",  "features": "_",  "gloss": "life",  "frequency": 5 }, {  "form": "experience",  "lemma": "experience",  "POS": "NOUN",  "features": "_",  "gloss": "experience",  "frequency": 1 }, {  "form": "//",  "lemma": "//",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 87 }, {  "form": "{",  "lemma": "{",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 32 }, {  "form": "papa",  "lemma": "papa",  "POS": "NOUN",  "features": "_",  "gloss": "papa",  "frequency": 4 }, {  "form": "|c",  "lemma": "|c",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 24 }, {  "form": "and",  "lemma": "and",  "POS": "CCONJ",  "features": "_",  "gloss": "and",  "frequency": 11 }, {  "form": "mama",  "lemma": "mama",  "POS": "NOUN",  "features": "_",  "gloss": "mama",  "frequency": 2 }, {  "form": "}",  "lemma": "}",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 32 }, {  "form": "dey",  "lemma": "dey",  "POS": "AUX",  "features": "Aspect=Imp",  "gloss": "IPFV",  "frequency": 15 }, {  "form": "&//",  "lemma": "&//",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 3 }, {  "form": "dem",  "lemma": "dem",  "POS": "PRON",  "features": "Case=Nom|Number=Plur|Person=3|PronType=Prs",  "gloss": "NOM.PL.3",  "frequency": 6 }, {  "form": "from",  "lemma": "from",  "POS": "ADP",  "features": "_",  "gloss": "from",  "frequency": 5 }, {  "form": "Etsako",  "lemma": "Etsako",  "POS": "PROPN",  "features": "_",  "gloss": "Etsako",  "frequency": 1 }, {  "form": "in",  "lemma": "in",  "POS": "ADP",  "features": "_",  "gloss": "in",  "frequency": 3 }, {  "form": "Edo",  "lemma": "Edo",  "POS": "PROPN",  "features": "_",  "gloss": "Edo",  "frequency": 1 }, {  "form": "State",  "lemma": "state",  "POS": "NOUN",  "features": "_",  "gloss": "state",  "frequency": 2 }, {  "form": "for",  "lemma": "for",  "POS": "ADP",  "features": "_",  "gloss": "for",  "frequency": 14 }, {  "form": "inside",  "lemma": "inside",  "POS": "ADP",  "features": "_",  "gloss": "inside",  "frequency": 7 }, {  "form": "Nigeria",  "lemma": "Nigeria",  "POS": "PROPN",  "features": "_",  "gloss": "Nigeria",  "frequency": 1 }, {  "form": "wey",  "lemma": "wey",  "POS": "SCONJ",  "features": "gloss=REL",  "gloss": "when",  "frequency": 3 }, {  "form": "birth",  "lemma": "birth",  "POS": "NOUN",  "features": "_",  "gloss": "birth",  "frequency": 4 }, {  "form": "to",  "lemma": "to",  "POS": "ADP",  "features": "_",  "gloss": "to",  "frequency": 19 }, {  "form": "me",  "lemma": "me",  "POS": "PRON",  "features": "Case=Acc|Number=Sing|Person=1|PronType=Prs",  "gloss": "ACC.SG.1",  "frequency": 18 }, {  "form": "as",  "lemma": "as",  "POS": "ADP",  "features": "_",  "gloss": "as",  "frequency": 7 }, {  "form": "no",  "lemma": "no",  "POS": "PART",  "features": "Polarity=Neg",  "gloss": "NEG",  "frequency": 16 }, {  "form": "be",  "lemma": "be",  "POS": "VERB",  "features": "PartType=Cop",  "gloss": "be.COP",  "frequency": 10 }, {  "form": "alone",  "lemma": "alone",  "POS": "ADJ",  "features": "_",  "gloss": "alone",  "frequency": 1 }, {  "form": ">+",  "lemma": ">+",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 10 }, {  "form": "o",  "lemma": "o",  "POS": "PART",  "features": "PartType=Disc",  "gloss": "EMPH",  "frequency": 10 }, {  "form": "we",  "lemma": "we",  "POS": "PRON",  "features": "Case=Nom|Number=Plur|Person=1|PronType=Prs",  "gloss": "NOM.PL.1",  "frequency": 11 }, {  "form": "eight",  "lemma": "eight",  "POS": "NUM",  "features": "NumType=Card",  "gloss": "eight.CARD",  "frequency": 1 }, {  "form": "number",  "lemma": "number",  "POS": "NOUN",  "features": "_",  "gloss": "number",  "frequency": 1 }, {  "form": "con",  "lemma": "con",  "POS": "AUX",  "features": "Aspect=Cons",  "gloss": "CONS",  "frequency": 45 }, {  "form": "six",  "lemma": "six",  "POS": "NUM",  "features": "NumType=Card",  "gloss": "six.CARD",  "frequency": 1 }, {  "form": "boys",  "lemma": "boy",  "POS": "NOUN",  "features": "Number=Plur",  "gloss": "boy.PL",  "frequency": 1 }, {  "form": "two",  "lemma": "two",  "POS": "NUM",  "features": "NumType=Card",  "gloss": "two.CARD",  "frequency": 2 }, {  "form": "girls",  "lemma": "girl",  "POS": "NOUN",  "features": "Number=Plur",  "gloss": "girl.PL",  "frequency": 1 }, {  "form": "process",  "lemma": "process",  "POS": "NOUN",  "features": "_",  "gloss": "process",  "frequency": 1 }, {  "form": "person",  "lemma": "person",  "POS": "NOUN",  "features": "_",  "gloss": "person",  "frequency": 2 }, {  "form": "grow",  "lemma": "grow",  "POS": "VERB",  "features": "_",  "gloss": "grow",  "frequency": 3 }, {  "form": "di",  "lemma": "di",  "POS": "DET",  "features": "Definite=Def|PronType=Art",  "gloss": "DEF.ART",  "frequency": 38 }, {  "form": "e",  "lemma": "im",  "POS": "PRON",  "features": "Case=Nom|Number=Sing|Person=3|PronType=Prs",  "gloss": "NOM.SG.3",  "frequency": 19 }, {  "form": "full",  "lemma": "full",  "POS": "ADJ",  "features": "_",  "gloss": "full",  "frequency": 1 }, {  "form": "of",  "lemma": "of",  "POS": "ADP",  "features": "_",  "gloss": "of",  "frequency": 9 }, {  "form": "different",  "lemma": "different",  "POS": "ADJ",  "features": "_",  "gloss": "different",  "frequency": 4 }, {  "form": "challenges",  "lemma": "challenge",  "POS": "NOUN",  "features": "Number=Plur",  "gloss": "challenge.PL",  "frequency": 1 }, {  "form": "sha",  "lemma": "sha",  "POS": "PART",  "features": "PartType=Disc",  "gloss": "really",  "frequency": 2 }, {  "form": "though",  "lemma": "though",  "POS": "SCONJ",  "features": "_",  "gloss": "though",  "frequency": 2 }, {  "form": "God",  "lemma": "God",  "POS": "PROPN",  "features": "_",  "gloss": "God",  "frequency": 2 }, {  "form": "im",  "lemma": "im",  "POS": "PRON",  "features": "Case=Nom|Number=Sing|Person=3|PronType=Prs",  "gloss": "NOM.SG.3",  "frequency": 4 }, {  "form": "see",  "lemma": "see",  "POS": "VERB",  "features": "_",  "gloss": "see",  "frequency": 4 }, {  "form": "us",  "lemma": "us",  "POS": "PRON",  "features": "Case=Acc|Number=Plur|Person=1|PronType=Prs",  "gloss": "ACC.PL.1",  "frequency": 4 }, {  "form": "through",  "lemma": "trough",  "POS": "ADP",  "features": "_",  "gloss": "trough",  "frequency": 2 }, {  "form": "when",  "lemma": "when",  "POS": "ADV",  "features": "PronType=Int",  "gloss": "when.Q",  "frequency": 6 }, {  "form": "up",  "lemma": "up",  "POS": "ADP",  "features": "_",  "gloss": "up",  "frequency": 2 }, {  "form": "young",  "lemma": "young",  "POS": "ADJ",  "features": "_",  "gloss": "young",  "frequency": 1 }, {  "form": "children",  "lemma": "child",  "POS": "NOUN",  "features": "Number=Plur",  "gloss": "child.PL",  "frequency": 1 }, {  "form": "our",  "lemma": "our",  "POS": "PRON",  "features": "Number=Plur|Person=1|Poss=Yes",  "gloss": "PL.1.POSS",  "frequency": 2 }, {  "form": "parents",  "lemma": "parent",  "POS": "NOUN",  "features": "Number=Plur",  "gloss": "parent.PL",  "frequency": 3 }, {  "form": "||",  "lemma": "||",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 15 }, {  "form": "strong",  "lemma": "strong",  "POS": "ADJ",  "features": "_",  "gloss": "strong",  "frequency": 1 }, {  "form": "healthy",  "lemma": "healthy",  "POS": "ADJ",  "features": "_",  "gloss": "healthy",  "frequency": 1 }, {  "form": "well",  "lemma": "well",  "POS": "ADV",  "features": "_",  "gloss": "well",  "frequency": 7 }, {  "form": "play",  "lemma": "play",  "POS": "VERB",  "features": "_",  "gloss": "play",  "frequency": 2 }, {  "form": "go",  "lemma": "go",  "POS": "VERB",  "features": "_",  "gloss": "go",  "frequency": 10 }, {  "form": "outside",  "lemma": "outside",  "POS": "ADP",  "features": "_",  "gloss": "outside",  "frequency": 1 }, {  "form": "//=",  "lemma": "//=",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 4 }, {  "form": "come",  "lemma": "come",  "POS": "VERB",  "features": "_",  "gloss": "come",  "frequency": 12 }, {  "form": "house",  "lemma": "house",  "POS": "NOUN",  "features": "_",  "gloss": "house",  "frequency": 4 }, {  "form": "school",  "lemma": "school",  "POS": "NOUN",  "features": "_",  "gloss": "school",  "frequency": 3 }, {  "form": "back",  "lemma": "back",  "POS": "ADV",  "features": "_",  "gloss": "back",  "frequency": 8 }, {  "form": "one",  "lemma": "one",  "POS": "DET",  "features": "Definite=Spec|PronType=Art",  "gloss": "SPEC.ART",  "frequency": 3 }, {  "form": "fateful",  "lemma": "fateful",  "POS": "ADJ",  "features": "_",  "gloss": "fateful",  "frequency": 1 }, {  "form": "day",  "lemma": "day",  "POS": "NOUN",  "features": "_",  "gloss": "day",  "frequency": 3 }, {  "form": "den",  "lemma": "den",  "POS": "ADV",  "features": "_",  "gloss": "den",  "frequency": 12 }, {  "form": "don",  "lemma": "don",  "POS": "AUX",  "features": "Aspect=Perf",  "gloss": "PRF",  "frequency": 12 }, {  "form": "reach",  "lemma": "reach",  "POS": "VERB",  "features": "_",  "gloss": "reach",  "frequency": 2 }, {  "form": "seven",  "lemma": "seven",  "POS": "NUM",  "features": "NumType=Card",  "gloss": "seven.CARD",  "frequency": 3 }, {  "form": "years",  "lemma": "year",  "POS": "NOUN",  "features": "Number=Plur",  "gloss": "year.PL",  "frequency": 3 }, {  "form": "take",  "lemma": "take",  "POS": "VERB",  "features": "_",  "gloss": "take",  "frequency": 10 }, {  "form": "write",  "lemma": "write",  "POS": "VERB",  "features": "_",  "gloss": "write",  "frequency": 1 }, {  "form": "final",  "lemma": "final",  "POS": "ADJ",  "features": "_",  "gloss": "final",  "frequency": 1 }, {  "form": "exam",  "lemma": "exam",  "POS": "NOUN",  "features": "_",  "gloss": "exam",  "frequency": 2 }, {  "form": "next",  "lemma": "next",  "POS": "ADJ",  "features": "_",  "gloss": "next",  "frequency": 1 }, {  "form": "class",  "lemma": "class",  "POS": "NOUN",  "features": "_",  "gloss": "class",  "frequency": 1 }, {  "form": "dey",  "lemma": "dey",  "POS": "VERB",  "features": "VerbType=Cop",  "gloss": "dey.COP",  "frequency": 5 }, {  "form": "primary",  "lemma": "primary",  "POS": "ADJ",  "features": "_",  "gloss": "primary",  "frequency": 2 }, {  "form": "then",  "lemma": "den",  "POS": "ADV",  "features": "_",  "gloss": "den",  "frequency": 1 }, {  "form": "three",  "lemma": "three",  "POS": "NUM",  "features": "NumType=Card",  "gloss": "three.CARD",  "frequency": 1 }, {  "form": "finish",  "lemma": "finish",  "POS": "VERB",  "features": "_",  "gloss": "finish",  "frequency": 1 }, {  "form": "dere",  "lemma": "dere",  "POS": "ADV",  "features": "_",  "gloss": "there",  "frequency": 3 }, {  "form": "for",  "lemma": "for",  "POS": "AUX",  "features": "Mood=Cond",  "gloss": "COND",  "frequency": 1 }, {  "form": "sick",  "lemma": "sick",  "POS": "ADJ",  "features": "_",  "gloss": "sick",  "frequency": 3 }, {  "form": "de",  "lemma": "dem",  "POS": "PRON",  "features": "Case=Nom|Number=Plur|Person=3|PronType=Prs",  "gloss": "NOM.PL.3",  "frequency": 10 }, {  "form": "rush",  "lemma": "rush",  "POS": "VERB",  "features": "_",  "gloss": "rush",  "frequency": 1 }, {  "form": "me",  "lemma": "me",  "POS": "PRON",  "features": "Case=Nom|Number=Sing|Person=1|PronType=Prs",  "gloss": "NOM.SG.1",  "frequency": 7 }, {  "form": "ah",  "lemma": "ah",  "POS": "INTJ",  "features": "_",  "gloss": "ah",  "frequency": 4 }, {  "form": "!//",  "lemma": "!//",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 2 }, {  "form": "how",  "lemma": "how",  "POS": "ADV",  "features": "PronType=Int",  "gloss": "how.Q",  "frequency": 2 }, {  "form": "body",  "lemma": "body",  "POS": "NOUN",  "features": "_",  "gloss": "body",  "frequency": 3 }, {  "form": "say",  "lemma": "say",  "POS": "VERB",  "features": "_",  "gloss": "say",  "frequency": 9 }, {  "form": "[",  "lemma": "[",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 12 }, {  "form": "one",  "lemma": "one",  "POS": "NOUN",  "features": "_",  "gloss": "one",  "frequency": 12 }, {  "form": "(",  "lemma": "(",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 5 }, {  "form": "travel",  "lemma": "travel",  "POS": "VERB",  "features": "_",  "gloss": "travel",  "frequency": 1 }, {  "form": "dey",  "lemma": "dey",  "POS": "VERB",  "features": "VerbType=Cop",  "gloss": "be.COP",  "frequency": 1 }, {  "form": "around",  "lemma": "around",  "POS": "ADP",  "features": "_",  "gloss": "around",  "frequency": 1 }, {  "form": "//)",  "lemma": "//)",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 2 }, {  "form": "sey",  "lemma": "sey",  "POS": "SCONJ",  "features": "_",  "gloss": "COMP",  "frequency": 7 }, {  "form": "wen",  "lemma": "wey",  "POS": "SCONJ",  "features": "gloss=REL",  "gloss": "REL",  "frequency": 1 }, {  "form": "go",  "lemma": "go",  "POS": "AUX",  "features": "Aspect=Prosp",  "gloss": "CONT",  "frequency": 7 }, {  "form": "put",  "lemma": "put",  "POS": "VERB",  "features": "_",  "gloss": "put",  "frequency": 4 }, {  "form": "do",  "lemma": "do",  "POS": "VERB",  "features": "_",  "gloss": "do",  "frequency": 8 }, {  "form": "self",  "lemma": "sef",  "POS": "PART",  "features": "PartType=Disc",  "gloss": "FOC",  "frequency": 1 }, {  "form": "medication",  "lemma": "medication",  "POS": "NOUN",  "features": "_",  "gloss": "medication",  "frequency": 1 }, {  "form": "//]",  "lemma": "//]",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 7 }, {  "form": "she",  "lemma": "she",  "POS": "PRON",  "features": "Case=Nom|Gender=Fem|Number=Sing|Person=3|PronType=Prs",  "gloss": "NOM.F.SG.3",  "frequency": 1 }, {  "form": "swing",  "lemma": "swing",  "POS": "VERB",  "features": "_",  "gloss": "swing",  "frequency": 1 }, {  "form": "into",  "lemma": "into",  "POS": "ADP",  "features": "_",  "gloss": "into",  "frequency": 1 }, {  "form": "action",  "lemma": "action",  "POS": "NOUN",  "features": "_",  "gloss": "action",  "frequency": 1 }, {  "form": "with",  "lemma": "wit",  "POS": "ADP",  "features": "_",  "gloss": "with",  "frequency": 3 }, {  "form": "her",  "lemma": "her",  "POS": "ADJ",  "features": "Gender=Fem|Number=Sing|Person=3|Poss=Yes",  "gloss": "F.SG.3.POSS",  "frequency": 1 }, {  "form": "oder",  "lemma": "oder",  "POS": "ADJ",  "features": "_",  "gloss": "other",  "frequency": 2 }, {  "form": "neighbour",  "lemma": "neighbour",  "POS": "NOUN",  "features": "_",  "gloss": "neighbour",  "frequency": 1 }, {  "form": "carry",  "lemma": "carry",  "POS": "VERB",  "features": "_",  "gloss": "carry",  "frequency": 4 }, {  "form": "specialist",  "lemma": "specialist",  "POS": "NOUN",  "features": "_",  "gloss": "specialist",  "frequency": 2 }, {  "form": "hospital",  "lemma": "hospital",  "POS": "NOUN",  "features": "_",  "gloss": "hospital",  "frequency": 3 }, {  "form": "admission",  "lemma": "admission",  "POS": "NOUN",  "features": "_",  "gloss": "admission",  "frequency": 4 }, {  "form": "straight",  "lemma": "straight",  "POS": "ADJ",  "features": "_",  "gloss": "straight",  "frequency": 1 }, {  "form": "series",  "lemma": "series",  "POS": "NOUN",  "features": "_",  "gloss": "series",  "frequency": 2 }, {  "form": "operation",  "lemma": "operation",  "POS": "NOUN",  "features": "_",  "gloss": "operation",  "frequency": 2 }, {  "form": "even",  "lemma": "even",  "POS": "ADV",  "features": "_",  "gloss": "even",  "frequency": 6 }, {  "form": "before",  "lemma": "before",  "POS": "ADP",  "features": "_",  "gloss": "before",  "frequency": 1 }, {  "form": "journey",  "lemma": "journey",  "POS": "NOUN",  "features": "_",  "gloss": "journey",  "frequency": 2 }, {  "form": "say",  "lemma": "_",  "POS": "_",  "features": "MotNouveau=Yes",  "gloss": "_",  "frequency": 1 }, {  "form": "am",  "lemma": "am",  "POS": "PRON",  "features": "Case=Acc|Number=Sing|Person=3|PronType=Prs",  "gloss": "ACC.SG.3",  "frequency": 13 }, {  "form": "sign",  "lemma": "sign",  "POS": "NOUN",  "features": "_",  "gloss": "sign",  "frequency": 1 }, {  "form": "]",  "lemma": "]",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 5 }, {  "form": "naim",  "lemma": "naim",  "POS": "ADV",  "features": "_",  "gloss": "then",  "frequency": 2 }, {  "form": "really",  "lemma": "really",  "POS": "ADV",  "features": "_",  "gloss": "really",  "frequency": 1 }, {  "form": "on",  "lemma": "on",  "POS": "ADP",  "features": "_",  "gloss": "on",  "frequency": 5 }, {  "form": "try",  "lemma": "try",  "POS": "VERB",  "features": "_",  "gloss": "try",  "frequency": 6 }, {  "form": "|a",  "lemma": "||",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 3 }, {  "form": "battle",  "lemma": "battle",  "POS": "VERB",  "features": "_",  "gloss": "battle",  "frequency": 1 }, {  "form": "almost",  "lemma": "almost",  "POS": "ADV",  "features": "_",  "gloss": "almost",  "frequency": 1 }, {  "form": "a",  "lemma": "a",  "POS": "DET",  "features": "Definite=Ind|PronType=Art",  "gloss": "INDF.ART",  "frequency": 1 }, {  "form": "year",  "lemma": "year",  "POS": "NOUN",  "features": "_",  "gloss": "year",  "frequency": 2 }, {  "form": "dat",  "lemma": "dat",  "POS": "DET",  "features": "Number=Sing|PronType=Dem",  "gloss": "SG.DEM",  "frequency": 4 }, {  "form": "renovation",  "lemma": "renovation",  "POS": "NOUN",  "features": "_",  "gloss": "renovation",  "frequency": 1 }, {  "form": "refer",  "lemma": "refer",  "POS": "VERB",  "features": "_",  "gloss": "refer",  "frequency": 1 }, {  "form": "UBTH",  "lemma": "UBTH",  "POS": "PROPN",  "features": "_",  "gloss": "UBTH",  "frequency": 4 }, {  "form": "make",  "lemma": "make",  "POS": "AUX",  "features": "Mood=Opt",  "gloss": "SBJV",  "frequency": 2 }, {  "form": "so",  "lemma": "so",  "POS": "ADV",  "features": "_",  "gloss": "so",  "frequency": 9 }, {  "form": "still",  "lemma": "still",  "POS": "ADV",  "features": "_",  "gloss": "still",  "frequency": 2 }, {  "form": "fit",  "lemma": "fit",  "POS": "AUX",  "features": "Mood=Pot",  "gloss": "ABIL",  "frequency": 6 }, {  "form": "revive",  "lemma": "revive",  "POS": "VERB",  "features": "_",  "gloss": "revive",  "frequency": 1 }, {  "form": "at",  "lemma": "at",  "POS": "ADP",  "features": "_",  "gloss": "at",  "frequency": 2 }, {  "form": "end",  "lemma": "end",  "POS": "NOUN",  "features": "_",  "gloss": "end",  "frequency": 1 }, {  "form": "bed",  "lemma": "bed",  "POS": "NOUN",  "features": "_",  "gloss": "bed",  "frequency": 1 }, {  "form": "pray",  "lemma": "pray",  "POS": "VERB",  "features": "_",  "gloss": "pray",  "frequency": 1 }, {  "form": "live",  "lemma": "live",  "POS": "VERB",  "features": "_",  "gloss": "live",  "frequency": 2 }, {  "form": "because",  "lemma": "because",  "POS": "SCONJ",  "features": "_",  "gloss": "because",  "frequency": 2 }, {  "form": "pain",  "lemma": "pain",  "POS": "NOUN",  "features": "_",  "gloss": "pain",  "frequency": 1 }, {  "form": "wen",  "lemma": "wey",  "POS": "SCONJ",  "features": "gloss=REL",  "gloss": "which",  "frequency": 1 }, {  "form": "pass",  "lemma": "pass",  "POS": "VERB",  "features": "_",  "gloss": "pass",  "frequency": 1 }, {  "form": "time",  "lemma": "time",  "POS": "NOUN",  "features": "_",  "gloss": "time",  "frequency": 3 }, {  "form": "too",  "lemma": "too",  "POS": "ADV",  "features": "_",  "gloss": "too",  "frequency": 1 }, {  "form": "much",  "lemma": "much",  "POS": "ADJ",  "features": "_",  "gloss": "much",  "frequency": 1 }, {  "form": "terribly",  "lemma": "terribly",  "POS": "ADV",  "features": "_",  "gloss": "terribly",  "frequency": 1 }, {  "form": "bad",  "lemma": "bad",  "POS": "ADJ",  "features": "_",  "gloss": "bad",  "frequency": 1 }, {  "form": "|r",  "lemma": "|r",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 5 }, {  "form": "make",  "lemma": "make",  "POS": "VERB",  "features": "_",  "gloss": "make",  "frequency": 2 }, {  "form": "headway",  "lemma": "headway",  "POS": "NOUN",  "features": "_",  "gloss": "headway",  "frequency": 1 }, {  "form": "okay",  "lemma": "OK",  "POS": "INTJ",  "features": "_",  "gloss": "OK",  "frequency": 1 }, {  "form": "native",  "lemma": "native",  "POS": "ADJ",  "features": "_",  "gloss": "native",  "frequency": 1 }, {  "form": "villages",  "lemma": "village",  "POS": "NOUN",  "features": "Number=Plur",  "gloss": "village.PL",  "frequency": 2 }, {  "form": "bring",  "lemma": "bring",  "POS": "VERB",  "features": "_",  "gloss": "bring",  "frequency": 1 }, {  "form": "im",  "lemma": "im",  "POS": "PRON",  "features": "Gender=Masc|Number=Sing|Person=3",  "gloss": "M.SG.3.POSS",  "frequency": 1 }, {  "form": "medicine",  "lemma": "medicine",  "POS": "NOUN",  "features": "_",  "gloss": "medicine",  "frequency": 1 }, {  "form": "cure",  "lemma": "cure",  "POS": "VERB",  "features": "_",  "gloss": "cure",  "frequency": 1 }, {  "form": "types",  "lemma": "type",  "POS": "NOUN",  "features": "Number=Plur",  "gloss": "type.PL",  "frequency": 1 }, {  "form": "things",  "lemma": "ting",  "POS": "NOUN",  "features": "Number=Plur",  "gloss": "thing.PL",  "frequency": 1 }, {  "form": "some",  "lemma": "some",  "POS": "PRON",  "features": "_",  "gloss": "some",  "frequency": 1 }, {  "form": "sacrifice",  "lemma": "sacrifice",  "POS": "NOUN",  "features": "_",  "gloss": "sacrifice",  "frequency": 2 }, {  "form": "all",  "lemma": "all",  "POS": "ADV",  "features": "_",  "gloss": "all",  "frequency": 4 }, {  "form": "tell",  "lemma": "tell",  "POS": "VERB",  "features": "_",  "gloss": "tell",  "frequency": 1 }, {  "form": "you",  "lemma": "you",  "POS": "PRON",  "features": "Case=Nom|Person=2|PronType=Prs",  "gloss": "NOM.2",  "frequency": 11 }, {  "form": "over",  "lemma": "over",  "POS": "ADP",  "features": "_",  "gloss": "over",  "frequency": 1 }, {  "form": "tire",  "lemma": "tire",  "POS": "VERB",  "features": "_",  "gloss": "tire",  "frequency": 2 }, {  "form": "sef",  "lemma": "sef",  "POS": "PART",  "features": "PartType=Disc",  "gloss": "FOC",  "frequency": 2 }, {  "form": "matter",  "lemma": "matter",  "POS": "NOUN",  "features": "_",  "gloss": "matter",  "frequency": 1 }, {  "form": "is",  "lemma": "be",  "POS": "AUX",  "features": "Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin",  "gloss": "be.IND.SG.3.PRS.FIN",  "frequency": 1 }, {  "form": "either",  "lemma": "either",  "POS": "CCONJ",  "features": "_",  "gloss": "either",  "frequency": 1 }, {  "form": "or",  "lemma": "or",  "POS": "CCONJ",  "features": "_",  "gloss": "or",  "frequency": 5 }, {  "form": "side",  "lemma": "side",  "POS": "NOUN",  "features": "_",  "gloss": "side",  "frequency": 1 }, {  "form": "the",  "lemma": "di",  "POS": "DET",  "features": "Definite=Def|PronType=Art",  "gloss": "DEF.ART",  "frequency": 1 }, {  "form": "world",  "lemma": "world",  "POS": "NOUN",  "features": "_",  "gloss": "world",  "frequency": 1 }, {  "form": "anymore",  "lemma": "anymore",  "POS": "ADV",  "features": "_",  "gloss": "anymore",  "frequency": 1 }, {  "form": "move",  "lemma": "move",  "POS": "VERB",  "features": "_",  "gloss": "move",  "frequency": 1 }, {  "form": "village",  "lemma": "village",  "POS": "NOUN",  "features": "_",  "gloss": "village",  "frequency": 1 }, {  "form": "town",  "lemma": "town",  "POS": "NOUN",  "features": "_",  "gloss": "town",  "frequency": 2 }, {  "form": "anything",  "lemma": "anyting",  "POS": "PRON",  "features": "_",  "gloss": "anything",  "frequency": 1 }, {  "form": "happen",  "lemma": "happen",  "POS": "VERB",  "features": "_",  "gloss": "happen",  "frequency": 1 }, {  "form": "like",  "lemma": "like",  "POS": "ADP",  "features": "_",  "gloss": "like",  "frequency": 6 }, {  "form": "dat",  "lemma": "dat",  "POS": "PRON",  "features": "Number=Sing|PronType=Dem",  "gloss": "SG.DEM",  "frequency": 5 }, {  "form": "glory",  "lemma": "glory",  "POS": "NOUN",  "features": "_",  "gloss": "glory",  "frequency": 1 }, {  "form": "October",  "lemma": "October",  "POS": "PROPN",  "features": "_",  "gloss": "October",  "frequency": 3 }, {  "form": "but",  "lemma": "but",  "POS": "CCONJ",  "features": "_",  "gloss": "but",  "frequency": 3 }, {  "form": "remember",  "lemma": "remember",  "POS": "VERB",  "features": "_",  "gloss": "remember",  "frequency": 1 }, {  "form": "exact",  "lemma": "exact",  "POS": "ADJ",  "features": "_",  "gloss": "exact",  "frequency": 1 }, {  "form": "just",  "lemma": "just",  "POS": "ADV",  "features": "_",  "gloss": "just",  "frequency": 2 }, {  "form": ")",  "lemma": ")",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 3 }, {  "form": "second",  "lemma": "second",  "POS": "ADJ",  "features": "NumType=Ord",  "gloss": "second.ORD",  "frequency": 1 }, {  "form": "I",  "lemma": "I",  "POS": "PRON",  "features": "Lang=en|Case=Nom|Number=Sing|Person=1|PronType=Prs",  "gloss": "NOM.SG.1",  "frequency": 1 }, {  "form": "found",  "lemma": "find",  "POS": "VERB",  "features": "Lang=en|Mood=Ind|Tense=Past|VerbForm=Fin",  "gloss": "find.IND.PST.FIN",  "frequency": 1 }, {  "form": "my",  "lemma": "my",  "POS": "PRON",  "features": "Lang=en|Number=Sing|Person=1|Poss=Yes",  "gloss": "SG.1.POSS",  "frequency": 1 }, {  "form": "healing",  "lemma": "healing",  "POS": "NOUN",  "features": "Lang=en",  "gloss": "healing",  "frequency": 1 }, {  "form": "church",  "lemma": "church",  "POS": "NOUN",  "features": "_",  "gloss": "church",  "frequency": 3 }, {  "form": "miracle",  "lemma": "miracle",  "POS": "NOUN",  "features": "_",  "gloss": "miracle",  "frequency": 2 }, {  "form": "know",  "lemma": "know",  "POS": "VERB",  "features": "_",  "gloss": "know",  "frequency": 1 }, {  "form": "find",  "lemma": "find",  "POS": "VERB",  "features": "_",  "gloss": "find",  "frequency": 4 }, {  "form": "healing",  "lemma": "healing",  "POS": "NOUN",  "features": "_",  "gloss": "healing",  "frequency": 2 }, {  "form": "herbalist",  "lemma": "herbalist",  "POS": "NOUN",  "features": "_",  "gloss": "herbalist",  "frequency": 1 }, {  "form": "place",  "lemma": "place",  "POS": "NOUN",  "features": "_",  "gloss": "place",  "frequency": 2 }, {  "form": "healings",  "lemma": "healing",  "POS": "NOUN",  "features": "Number=Plur",  "gloss": "healing",  "frequency": 1 }, {  "form": "born",  "lemma": "born",  "POS": "VERB",  "features": "_",  "gloss": "give_birth",  "frequency": 1 }, {  "form": "which",  "lemma": "which",  "POS": "DET",  "features": "PronType=Int",  "gloss": "which",  "frequency": 1 }, {  "form": "wen",  "lemma": "when",  "POS": "SCONJ",  "features": "_",  "gloss": "when",  "frequency": 2 }, {  "form": "Roman",  "lemma": "Roman",  "POS": "ADJ",  "features": "_",  "gloss": "Roman",  "frequency": 1 }, {  "form": "Catholic",  "lemma": "Catholic",  "POS": "ADJ",  "features": "_",  "gloss": "Catholic",  "frequency": 1 }, {  "form": "Church",  "lemma": "church",  "POS": "NOUN",  "features": "_",  "gloss": "church",  "frequency": 1 }, {  "form": "name",  "lemma": "name",  "POS": "NOUN",  "features": "_",  "gloss": "name",  "frequency": 1 }, {  "form": "na",  "lemma": "na",  "POS": "PART",  "features": "PartType=Cop",  "gloss": "be1",  "frequency": 9 }, {  "form": "Ibrahim",  "lemma": "Ibrahim",  "POS": "PROPN",  "features": "_",  "gloss": "Ibrahim",  "frequency": 1 }, {  "form": "Salomi",  "lemma": "Salomi",  "POS": "PROPN",  "features": "_",  "gloss": "Salomi",  "frequency": 1 }, {  "form": "ting",  "lemma": "ting",  "POS": "NOUN",  "features": "_",  "gloss": "thing",  "frequency": 2 }, {  "form": "wey",  "lemma": "wey",  "POS": "SCONJ",  "features": "_",  "gloss": "REL",  "frequency": 4 }, {  "form": "want",  "lemma": "want",  "POS": "VERB",  "features": "_",  "gloss": "want",  "frequency": 4 }, {  "form": "talk",  "lemma": "talk",  "POS": "VERB",  "features": "_",  "gloss": "talk",  "frequency": 1 }, {  "form": "prepare",  "lemma": "prepare",  "POS": "VERB",  "features": "_",  "gloss": "prepare",  "frequency": 4 }, {  "form": "egusi",  "lemma": "egusi",  "POS": "NOUN",  "features": "_",  "gloss": "melon_seed",  "frequency": 2 }, {  "form": "soup",  "lemma": "soup",  "POS": "NOUN",  "features": "_",  "gloss": "soup",  "frequency": 4 }, {  "form": "first",  "lemma": "first",  "POS": "ADJ",  "features": "NumType=Ord",  "gloss": "first.ORD",  "frequency": 1 }, {  "form": "go",  "lemma": "go",  "POS": "AUX",  "features": "Aspect=Prosp",  "gloss": "PROSP",  "frequency": 10 }, {  "form": "grind",  "lemma": "grind",  "POS": "VERB",  "features": "_",  "gloss": "grind",  "frequency": 3 }, {  "form": "your",  "lemma": "your",  "POS": "PRON",  "features": "Number=Plur|Person=2|Poss=Yes",  "gloss": "PL.2.POSS",  "frequency": 6 }, {  "form": "melon",  "lemma": "melon",  "POS": "NOUN",  "features": "_",  "gloss": "melon",  "frequency": 7 }, {  "form": "//+",  "lemma": "//+",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 1 }, {  "form": "depending",  "lemma": "depend",  "POS": "VERB",  "features": "Tense=Pres|VerbForm=Part",  "gloss": "depend.PRS.PTCP",  "frequency": 1 }, {  "form": "quantity",  "lemma": "quantity",  "POS": "NOUN",  "features": "_",  "gloss": "quantity",  "frequency": 1 }, {  "form": "weh",  "lemma": "wey",  "POS": "SCONJ",  "features": "_",  "gloss": "REL",  "frequency": 1 }, {  "form": "after",  "lemma": "after",  "POS": "ADP",  "features": "_",  "gloss": "after",  "frequency": 8 }, {  "form": "pound",  "lemma": "pound",  "POS": "VERB",  "features": "_",  "gloss": "pound",  "frequency": 1 }, {  "form": "pepper",  "lemma": "pepper",  "POS": "NOUN",  "features": "_",  "gloss": "pepper",  "frequency": 2 }, {  "form": "keep",  "lemma": "keep",  "POS": "VERB",  "features": "_",  "gloss": "keep",  "frequency": 1 }, {  "form": "everyt",  "lemma": "X",  "POS": "X",  "features": "_",  "gloss": "X",  "frequency": 1 }, {  "form": "ingredients",  "lemma": "ingredient",  "POS": "NOUN",  "features": "Number=Plur",  "gloss": "ingredient.PL",  "frequency": 1 }, {  "form": "ready",  "lemma": "ready",  "POS": "ADJ",  "features": "_",  "gloss": "ready",  "frequency": 2 }, {  "form": "so",  "lemma": "so",  "POS": "SCONJ",  "features": "_",  "gloss": "so",  "frequency": 1 }, {  "form": "dey",  "lemma": "dey",  "POS": "VERB",  "features": "VerbType=Cop",  "gloss": "be2",  "frequency": 4 }, {  "form": "easy",  "lemma": "easy",  "POS": "ADJ",  "features": "_",  "gloss": "easy",  "frequency": 1 }, {  "form": "eh",  "lemma": "eh",  "POS": "INTJ",  "features": "_",  "gloss": "eh",  "frequency": 3 }, {  "form": "slice",  "lemma": "slice",  "POS": "VERB",  "features": "_",  "gloss": "slice",  "frequency": 2 }, {  "form": "vegetable",  "lemma": "vegetable",  "POS": "NOUN",  "features": "_",  "gloss": "vegetable",  "frequency": 1 }, {  "form": "maybe",  "lemma": "maybe",  "POS": "ADV",  "features": "_",  "gloss": "maybe",  "frequency": 1 }, {  "form": "if",  "lemma": "if",  "POS": "SCONJ",  "features": "_",  "gloss": "if",  "frequency": 1 }, {  "form": "use",  "lemma": "use",  "POS": "VERB",  "features": "_",  "gloss": "use",  "frequency": 2 }, {  "form": "ugu",  "lemma": "ugwu",  "POS": "NOUN",  "features": "_",  "gloss": "vegetable_sp",  "frequency": 4 }, {  "form": "it's",  "lemma": "it's",  "POS": "PART",  "features": "PartType=Cop",  "gloss": "be1",  "frequency": 1 }, {  "form": "eider",  "lemma": "eider",  "POS": "CCONJ",  "features": "_",  "gloss": "either",  "frequency": 1 }, {  "form": "bitter",  "lemma": "bitter",  "POS": "ADJ",  "features": "_",  "gloss": "bitter",  "frequency": 1 }, {  "form": "leaf",  "lemma": "leaf",  "POS": "NOUN",  "features": "_",  "gloss": "leaf",  "frequency": 4 }, {  "form": "mostly",  "lemma": "mostly",  "POS": "ADV",  "features": "_",  "gloss": "mostly",  "frequency": 1 }, {  "form": "like",  "lemma": "like",  "POS": "VERB",  "features": "_",  "gloss": "like",  "frequency": 2 }, {  "form": "pumpkin",  "lemma": "pumpkin",  "POS": "NOUN",  "features": "_",  "gloss": "pumpkin",  "frequency": 3 }, {  "form": "is",  "lemma": "be",  "POS": "VERB",  "features": "Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin|VerbType=Cop",  "gloss": "be.IND.SG.3.PRS.FIN",  "frequency": 2 }, {  "form": "wash",  "lemma": "wash",  "POS": "VERB",  "features": "_",  "gloss": "wash",  "frequency": 3 }, {  "form": "meat",  "lemma": "meat",  "POS": "NOUN",  "features": "_",  "gloss": "meat",  "frequency": 3 }, {  "form": "okporoko",  "lemma": "okporoko",  "POS": "NOUN",  "features": "_",  "gloss": "dried_fish",  "frequency": 1 }, {  "form": "is",  "lemma": "be",  "POS": "VERB",  "features": "Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin",  "gloss": "be.IND.SG.3.PRS.FIN",  "frequency": 1 }, {  "form": "dry",  "lemma": "dry",  "POS": "ADJ",  "features": "_",  "gloss": "dry",  "frequency": 2 }, {  "form": "f-",  "lemma": "X",  "POS": "X",  "features": "_",  "gloss": "X",  "frequency": 1 }, {  "form": "stockfish",  "lemma": "stockfish",  "POS": "NOUN",  "features": "_",  "gloss": "stockfish",  "frequency": 2 }, {  "form": "fish",  "lemma": "fish",  "POS": "NOUN",  "features": "_",  "gloss": "fish",  "frequency": 2 }, {  "form": "everyting",  "lemma": "everyting",  "POS": "PRON",  "features": "_",  "gloss": "everything",  "frequency": 1 }, {  "form": "togeder",  "lemma": "togeder",  "POS": "ADV",  "features": "_",  "gloss": "together",  "frequency": 1 }, {  "form": "steam",  "lemma": "steam",  "POS": "VERB",  "features": "_",  "gloss": "steam",  "frequency": 3 }, {  "form": "add",  "lemma": "add",  "POS": "VERB",  "features": "_",  "gloss": "add",  "frequency": 1 }, {  "form": "some",  "lemma": "some",  "POS": "DET",  "features": "_",  "gloss": "some",  "frequency": 1 }, {  "form": "seasoning",  "lemma": "seasoning",  "POS": "NOUN",  "features": "_",  "gloss": "seasoning",  "frequency": 1 }, {  "form": "Maggi",  "lemma": "Maggi",  "POS": "PROPN",  "features": "_",  "gloss": "Maggi_cube",  "frequency": 1 }, {  "form": "cube",  "lemma": "cube",  "POS": "NOUN",  "features": "_",  "gloss": "cube",  "frequency": 1 }, {  "form": "salt",  "lemma": "salt",  "POS": "NOUN",  "features": "_",  "gloss": "salt",  "frequency": 1 }, {  "form": "onion",  "lemma": "onion",  "POS": "NOUN",  "features": "_",  "gloss": "onion",  "frequency": 1 }, {  "form": "down",  "lemma": "down",  "POS": "ADP",  "features": "_",  "gloss": "down",  "frequency": 3 }, {  "form": "pour",  "lemma": "pour",  "POS": "VERB",  "features": "_",  "gloss": "pour",  "frequency": 7 }, {  "form": "oil",  "lemma": "oil",  "POS": "NOUN",  "features": "_",  "gloss": "oil",  "frequency": 3 }, {  "form": "pot",  "lemma": "pot",  "POS": "NOUN",  "features": "_",  "gloss": "pot",  "frequency": 3 }, {  "form": "fry",  "lemma": "fry",  "POS": "VERB",  "features": "_",  "gloss": "fry",  "frequency": 3 }, {  "form": "get",  "lemma": "get",  "POS": "VERB",  "features": "_",  "gloss": "get",  "frequency": 1 }, {  "form": "kind",  "lemma": "kind",  "POS": "ADJ",  "features": "_",  "gloss": "kind",  "frequency": 1 }, {  "form": "taste",  "lemma": "taste",  "POS": "NOUN",  "features": "_",  "gloss": "taste",  "frequency": 2 }, {  "form": "already",  "lemma": "already",  "POS": "ADV",  "features": "_",  "gloss": "already",  "frequency": 1 }, {  "form": "season",  "lemma": "season",  "POS": "VERB",  "features": "_",  "gloss": "season",  "frequency": 1 }, {  "form": "leave",  "lemma": "leave",  "POS": "VERB",  "features": "_",  "gloss": "leave",  "frequency": 2 }, {  "form": "top",  "lemma": "top",  "POS": "NOUN",  "features": "_",  "gloss": "top",  "frequency": 1 }, {  "form": "fire",  "lemma": "fire",  "POS": "NOUN",  "features": "_",  "gloss": "fire",  "frequency": 2 }, {  "form": "boil",  "lemma": "boil",  "POS": "VERB",  "features": "_",  "gloss": "boil",  "frequency": 2 }, {  "form": "ten",  "lemma": "ten",  "POS": "NUM",  "features": "_",  "gloss": "ten",  "frequency": 2 }, {  "form": "minutes",  "lemma": "minute",  "POS": "NOUN",  "features": "Number=Plur",  "gloss": "minute.PL",  "frequency": 2 }, {  "form": "meh",  "lemma": "make",  "POS": "AUX",  "features": "Mood=Opt",  "gloss": "SBJV",  "frequency": 2 }, {  "form": "cook",  "lemma": "cook",  "POS": "VERB",  "features": "_",  "gloss": "cook",  "frequency": 1 }, {  "form": "more",  "lemma": "more",  "POS": "ADJ",  "features": "Degree=Cmp",  "gloss": "CMPR",  "frequency": 1 }, {  "form": "decide",  "lemma": "decide",  "POS": "VERB",  "features": "_",  "gloss": "decide",  "frequency": 1 }, {  "form": "wheda",  "lemma": "wheder",  "POS": "SCONJ",  "features": "_",  "gloss": "whether",  "frequency": 1 }, {  "form": "akpu",  "lemma": "akpu",  "POS": "NOUN",  "features": "_",  "gloss": "cassava_flour",  "frequency": 2 }, {  "form": "pounded",  "lemma": "pound",  "POS": "ADJ",  "features": "_",  "gloss": "pound",  "frequency": 2 }, {  "form": "yam",  "lemma": "yam",  "POS": "NOUN",  "features": "_",  "gloss": "yam",  "frequency": 2 }, {  "form": "garri",  "lemma": "garri",  "POS": "NOUN",  "features": "_",  "gloss": "dry_cassava",  "frequency": 2 }, {  "form": "chop",  "lemma": "chop",  "POS": "VERB",  "features": "_",  "gloss": "eat",  "frequency": 1 }, {  "form": "enjoy",  "lemma": "enjoy",  "POS": "VERB",  "features": "_",  "gloss": "enjoy",  "frequency": 1 }, {  "form": "anyone",  "lemma": "anyone",  "POS": "PRON",  "features": "_",  "gloss": "anyone",  "frequency": 1 }, {  "form": "choice",  "lemma": "choice",  "POS": "NOUN",  "features": "_",  "gloss": "choice",  "frequency": 1 }, {  "form": "personally",  "lemma": "personally",  "POS": "ADV",  "features": "_",  "gloss": "personally",  "frequency": 1 }, {  "form": "home",  "lemma": "home",  "POS": "NOUN",  "features": "_",  "gloss": "home",  "frequency": 1 }, {  "form": "Kogi",  "lemma": "Kogi",  "POS": "PROPN",  "features": "_",  "gloss": "Kogi",  "frequency": 1 }, {  "form": "bus",  "lemma": "bus",  "POS": "NOUN",  "features": "_",  "gloss": "bus",  "frequency": 1 }, {  "form": "criminal",  "lemma": "criminal",  "POS": "NOUN",  "features": "_",  "gloss": "criminal",  "frequency": 1 }, {  "form": "pick",  "lemma": "pick",  "POS": "VERB",  "features": "_",  "gloss": "pick",  "frequency": 1 }, {  "form": "pocket",  "lemma": "pocket",  "POS": "NOUN",  "features": "_",  "gloss": "pocket",  "frequency": 1 }, {  "form": "comot",  "lemma": "comot",  "POS": "VERB",  "features": "_",  "gloss": "get_out",  "frequency": 1 }, {  "form": "purse",  "lemma": "purse",  "POS": "NOUN",  "features": "_",  "gloss": "purse",  "frequency": 4 }, {  "form": "tink",  "lemma": "tink",  "POS": "VERB",  "features": "_",  "gloss": "think",  "frequency": 1 }, {  "form": "money",  "lemma": "money",  "POS": "NOUN",  "features": "_",  "gloss": "money",  "frequency": 1 }, {  "form": "meanwhile",  "lemma": "meanwhile",  "POS": "ADV",  "features": "_",  "gloss": "meanwhile",  "frequency": 1 }, {  "form": "ID",  "lemma": "ID",  "POS": "NOUN",  "features": "_",  "gloss": "ID",  "frequency": 1 }, {  "form": "card",  "lemma": "card",  "POS": "NOUN",  "features": "_",  "gloss": "card",  "frequency": 2 }, {  "form": "ATM",  "lemma": "ATM",  "POS": "NOUN",  "features": "_",  "gloss": "ATM",  "frequency": 1 }, {  "form": "when",  "lemma": "when",  "POS": "SCONJ",  "features": "PronType=Int",  "gloss": "when.Q",  "frequency": 1 }, {  "form": "discover",  "lemma": "discover",  "POS": "VERB",  "features": "_",  "gloss": "discover",  "frequency": 1 }, {  "form": "turn",  "lemma": "turn",  "POS": "VERB",  "features": "_",  "gloss": "turn",  "frequency": 1 }, {  "form": "oya",  "lemma": "oya",  "POS": "INTJ",  "features": "_",  "gloss": "come_on",  "frequency": 1 }, {  "form": "immediately",  "lemma": "immediately",  "POS": "ADV",  "features": "_",  "gloss": "immediately",  "frequency": 1 }, {  "form": "fear",  "lemma": "fear",  "POS": "VERB",  "features": "_",  "gloss": "fear",  "frequency": 1 }, {  "form": "waka",  "lemma": "waka",  "POS": "VERB",  "features": "_",  "gloss": "walk",  "frequency": 1 }, {  "form": "thief",  "lemma": "tief",  "POS": "VERB",  "features": "_",  "gloss": "steal",  "frequency": 1 }, {  "form": ">",  "lemma": ">",  "POS": "PUNCT",  "features": "_",  "gloss": "PUNCT",  "frequency": 1 }, {  "form": "be",  "lemma": "be",  "POS": "VERB",  "features": "PartType=Cop",  "gloss": "be1",  "frequency": 1 }, {  "form": "agboro",  "lemma": "agboro",  "POS": "NOUN",  "features": "_",  "gloss": "tout",  "frequency": 1 }, {  "form": "end",  "lemma": "end",  "POS": "VERB",  "features": "_",  "gloss": "end",  "frequency": 1 } ]
	resp =  jsonify({'lexicon': temp_d, 'message': 'hello'  })
	resp.status_code = 200
	return resp








		# for sent_id in sample:
			
		# 	if treeSelection == 'all':
		# 		for user, conll in sample[sent_id].items():
		# 			content[user] = content.get(user, []) + [conll]
		# 	elif treeSelection == "user":
		# 		if current_user.username in sample[sent_id]:
		# 			conll = sample[sent_id][current_user.username]
		# 			content[current_user.username] = content.get(current_user.username, []) + [conll]
		# 	elif treeSelection == "recent":
		# 		last = project_service.get_last_user(sample[sent_id])
		# 		conll = sample[sent_id][last]
		# 		content[current_user.username] = content.get(current_user.username, []) + [conll]
		# 	elif treeSelection == "user_recent":
		# 		if current_user.username in sample[sent_id]:
		# 			conll = sample[sent_id][current_user.username]
		# 		else:
		# 			last = project_service.get_last_user(sample[sent_id])
		# 			conll = sample[sent_id][last]
		# 		content[current_user.username] = content.get(current_user.username, []) + [conll]
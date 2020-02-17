from flask import render_template, flash, redirect, url_for, jsonify, request, Response, abort, current_app
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
from ...utils.grew_utils import grew_request, upload_project
# from ....config import Config #prod

from ...services import project_service, user_service, robot_service


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

@project.route('/<project_name>/settings/infos')
def project_settings_infos(project_name):
	''' get project infos for settings view. Without bottleneck infos on samples '''
	project_infos = project_service.get_settings_infos(project_name, current_user)
	# if project_infos == 403: abort(403) # removed for now -> the check is done in view and for each actions
	js = json.dumps(project_infos, default=str)
	resp = Response(js, status=200, mimetype='application/json')
	return resp

@project.route('/<project_name>/treesfrom')
def project_treesfrom(project_name):
	''' get users treesfrom from a project '''
	users = project_service.get_project_treesfrom(project_name)
	js = json.dumps(users, default=str)
	resp = Response(js, status=200, mimetype='application/json')
	return resp

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

@project.route('/<project_name>/openproject', methods=['POST'])
@requires_access_level(2)
def project_open_project(project_name):
	if not request.json: abort(400)
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	value = request.json.get("value")
	project_service.change_is_open(project_name, value)
	project_infos = project_service.get_settings_infos(project_name, current_user)
	resp = Response( json.dumps(project_infos, default=str), status=200, mimetype='application/json' )
	return resp

@project.route('/<project_name>/private', methods=['POST'])
@requires_access_level(2)
def project_private_project(project_name):
	if not request.json: abort(400)
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	value = request.json.get("value")
	project_service.change_is_private(project_name, value)
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

@project.route('/<project_name>/', methods=['POST'])
# @login_required
@requires_access_level(2)
def project_update(project_name):
	"""
	modifie project info

	par exemple
	ajouter admin / guest users:{nom:access, nom:access, nom:"" (pour enlever)}
	changer nom du projet project:{projectname:nouveaunom,description:nouvelledescription,isprivate:True, image:blob}
	"""
	if not request.json: abort(400)
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	if request.json.get("users"):
		for k,v in request.json.get("users").items():
			user = user_service.get_by_id(k)
			if user:
				pa = project_service.get_project_access(project.id, user.id)
				if pa:
					if v: # update
						pa.accesslevel = v
					else: # delete an existing project access
						project_service.delete_project_access(pa)
				else:
					if v: # create
						project_service.create_add_project_access(user.id, project.id, v)
					else:
						pass

			else: abort(400)
	if request.json.get("project"):
		print("**here**")
		for k,v in request.json.get("project").items():
			if k == "projectname":
				reply = json.loads(grew_request("renameProject",data={"project_id":project_name, "new_project_id":v}))
				if reply["status"] != "OK": abort(400)
				# update project_name if it went well
			setattr(project,k,v)
	db.session.commit()
	return project_info(project.projectname)






@project.route('/<project_name>/delete', methods=['DELETE'])
# @login_required
@requires_access_level(2)
def delete_project(project_name):
	"""
	Delete a project
	no json
	"""
	# current_user.super_admin = True
	# current_user.id = "rinema56@gmail.com"
	project = project_service.get_by_name(project_name)
	if not project:	abort(400)
	# p_access = get_access_for_project(current_user.id, project.id)
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
	reply = json.loads(grew_request("searchPatternInSentences",data={"project_id":project.projectname, "pattern":pattern}))
	if reply["status"] != "OK": abort(400)
	trees={}
	# matches={}
	reendswithnumbers = re.compile(r"_(\d+)$")

	for m in reply["data"]:
		if reendswithnumbers.search(list(m["nodes"].values())[0]):
			user_id = reendswithnumbers.sub("", list(m["nodes"].values())[0])
		elif reendswithnumbers.search(list(m["edges"].values())[0]):
			user_id = reendswithnumbers.sub("",list(m["edges"].values())[0])
		else: abort(409)

		conll = json.loads(grew_request("getConll", data={"sample_id":m["sample_id"], "project_id":project.projectname, "sent_id":m["sent_id"], "user_id":user_id}))
		if conll["status"] != "OK": abort(404)
		conll = conll["data"]
		trees=project_service.formatTrees(m, trees, conll, user_id)

	js = json.dumps(trees)
	resp = Response(js, status=200,  mimetype='application/json')
	# print(11111)
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
		for f in fichiers: project_service.upload_sample(f, project_name, import_user, reextensions=reextensions, existing_samples=samples)

	samples = {"samples":project_service.get_samples(project_name)}
	# print(samples)
	js = json.dumps(samples)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp

@project.route('/create', methods=["POST"])
# @cross_origin()
def create_project():
	''' create an emty project'''
	project_name = request.form.get("project_name", "")
	# creator = request.form.get("import_user", "") 
	creator = current_user.id
	project_description = request.form.get("description", "")
	# project_image = ''
	project_private = request.form.get("private", False)
	project_isopen = request.form.get("is_open", False)
	project_showAllTrees = request.form.get("show_all_trees", True)
	project_service.create_empty_project(project_name, creator, project_description, project_private, project_isopen, project_showAllTrees)
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


@project.route('/<project_name>/config/cat/<action>', methods=["POST"])
# @cross_origin()
@requires_access_level(2)
def project_cat_add(project_name, action):
	project = project_service.get_by_name(project_name)
	if not project: abort(404)
	if not request.json: abort(400)
	data = request.get_json(force=True)

	if not data.get("cat"): abort(400)
	cats = list()
	if action == 'add':	cats = project_service.add_cat_label(project_name, current_user, data.get("cat") )
	elif action == 'delete': cats = project_service.remove_cat_label(project_name, current_user, data.get("cat") )
	else: abort(400)
	js = json.dumps(cats, default=str)
	resp = Response(js, status=200, mimetype='application/json')
	return resp

@project.route('/<project_name>/config/txtcats', methods=["POST"])
# @cross_origin()
@requires_access_level(2)
def project_txtcats(project_name):
	project = project_service.get_by_name(project_name)
	if not project: abort(404)
	if not request.json: abort(400)
	data = request.get_json(force=True)

	if not data.get("cats"): abort(400)
	cats = list()
	cats = project_service.parse_txtcats(project, data.get("cats"))
	js = json.dumps(cats, default=str)
	resp = Response(js, status=200, mimetype='application/json')
	return resp

@project.route('/<project_name>/config/txtlabels', methods=["POST"])
# @cross_origin()
@requires_access_level(2)
def project_txtlabels(project_name):
	project = project_service.get_by_name(project_name)
	if not project: abort(404)
	if not request.json: abort(400)
	data = request.get_json(force=True)

	if not data.get("labels"): abort(400)
	labels = list()
	labels = project_service.parse_txtlabels(project, data.get("labels"))
	js = json.dumps(labels, default=str)
	resp = Response(js, status=200, mimetype='application/json')
	return resp

@project.route('/<project_name>/config/stock/<action>', methods=["POST"])
# @cross_origin()
@requires_access_level(2)
def project_stock_add(project_name, action):
	project = project_service.get_by_name(project_name)
	if not project: abort(404)
	if not request.json: abort(400)
	data = request.get_json(force=True)

	if not data.get("stockid"): abort(400)
	labels = list()
	if action == 'add': labels = project_service.add_stock(project_name)
	elif action == 'delete': labels = project_service.remove_stock(project_name, data.get("stockid"))
	else: abort(400)
	js = json.dumps(labels, default=str)
	resp = Response(js, status=200, mimetype='application/json')
	return resp

@project.route('/<project_name>/config/label/<action>', methods=["POST"])
# @cross_origin()
@requires_access_level(2)
def project_label_add(project_name, action):
	project = project_service.get_by_name(project_name)
	print(1)
	if not project: abort(404)
	if not request.json: abort(400)
	data = request.get_json(force=True)

	print(2, data)
	if not data.get("stockid"): abort(400)
	labels = list()
	if action == 'add': labels = project_service.add_label(project_name, data.get("stockid"), data.get("label"))
	elif action == 'delete': labels = project_service.remove_label(project_name, data.get("labelid"), data.get("stockid"), data.get("label"))
	else: abort(400)
	js = json.dumps(labels, default=str)
	resp = Response(js, status=200, mimetype='application/json')
	return resp


# @project.route('/<project_name>/export/zip', methods=["POST", "GET"])
@project.route('/<project_name>/export/zip', methods=["POST"])
# @cross_origin()
@requires_access_level(1)
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
		reply = json.loads(grew_request('getConll', data={'project_id': project_name, 'sample_id':samplename}))
		if reply.get("status") == "OK":

			# {"sent_id_1":{"conlls":{"user_1":"conllstring"}}}
			sample_tree = project_service.servSampleTrees(reply.get("data", {})  )	
			sample_content = project_service.sampletree2contentfile(sample_tree)

			# finding the last tree
			timestamps = [(user, project_service.get_timestamp(conll)) for (user, conll) in sample_content.items()]
			# print(timestamps)
			last = sorted([u for (u, t) in timestamps], key=lambda x: x[1])[-1] #pb les timestamps sont pas mis à jour
			# print(last)
			sample_content["last"] = sample_content[last]
			samplecontentfiles.append(sample_content)

		else:
			print("Error: {}".format(reply.get("message")))

	memory_file = project_service.contentfiles2zip(samplenames, samplecontentfiles)

	resp = Response(memory_file, status=200,  mimetype='application/zip', headers={'Content-Disposition':'attachment;filename=dump.{}.zip'.format(project_name)})
	return resp


@project.route('/<project_name>/sample/<sample_name>', methods=['GET'])
# @login_required
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
	reply = json.loads(grew_request('getConll', data={'project_id': project_name, 'sample_id':sample_name}))
	reendswithnumbers = re.compile(r"_(\d+)$")
	
	if reply.get("status") == "OK":
		samples = reply.get("data", {})	
		project = project_service.get_by_name(project_name)
		if not project: abort(404)
		if project.show_all_trees or project.is_open: js = json.dumps( project_service.samples2trees(samples, sample_name) )
		else:
			validator = project_service.is_validator(project.id, sample_name, current_user.id)
			if validator:  js = json.dumps( project_service.samples2trees(samples, sample_name) )
			else:  js = json.dumps( project_service.samples2trees_with_restrictions(samples, sample_name, current_user, project_name) )
		# print(js)
		resp = Response(js, status=200,  mimetype='application/json')
		return resp
	else: abort(409)
 

@project.route('/<project_name>/sample/<sample_name>/search', methods=['GET', 'POST'])
# @login_required
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
	reply = json.loads(grew_request("searchPatternInSentences",data={"project_id":project.projectname, "pattern":pattern}))
	if reply["status"] != "OK": abort(400)

	trees={}
	matches={}
	reendswithnumbers = re.compile(r"_(\d+)$")

	for m in reply["data"]:
		if m["sample_id"] != sample_name: continue
		if reendswithnumbers.search(list(m["nodes"].values())[0]):
			user_id = reendswithnumbers.sub("", list(m["nodes"].values())[0])
		elif reendswithnumbers.search(list(m["edges"].values())[0]):
			user_id = reendswithnumbers.sub("",list(m["edges"].values())[0])
		else: abort(409)

		conll = json.loads(grew_request("getConll", data={"sample_id":m["sample_id"], "project_id":project.projectname, "sent_id":m["sent_id"], "user_id":user_id}))
		if conll["status"] != "OK": abort(404)
		conll = conll["data"]
		trees=project_service.formatTrees(m, trees, conll, user_id)
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
		sample = project_service.get_sample(req['samplename'], req['projectname'], current_user)
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
		sample = project_service.get_sample(req['samplename'], req['projectname'], current_user)
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
# @login_required
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


@project.route("/<project_name>/sample/<sample_name>/saveTrees", methods=["POST"])
# @login_required
# @requires_access_level(1)
def save_trees(project_name, sample_name):
	project = project_service.get_by_name(project_name)
	if not project:
		print("problem with proj")
		abort(404)
	if not request.json: abort(400)
	if not project.is_open:
		if not project_service.is_annotator(project.id, sample_name, current_user.id): abort(403)
	

	samples = {"samples":project_service.get_samples(project_name)}
	if not sample_name in samples["samples"]:
		print("problem with sample")
		abort(404)

	data = request.json
	if data:
		trees = data.get("trees")
		# no user_id was sent : save to current_user, else save to provided user
		# user_id = data.get("user_id", current_user.id)
		user_id = data.get("user_id", current_user.id)
		# if not user_id: abort(400)
		for tree in trees:
			# print(tree)
			sent_id = tree.get("sent_id")
			conll = tree.get("conll")
			# if not sent_id: abort(400)
			if not conll: abort(400)

			reply = grew_request (
				'saveGraph',
				data = {'project_id': project_name, 'sample_id': sample_name, 'user_id':user_id, 'sent_id':sent_id, "conll_graph":conll}
				)
			resp = json.loads(reply)
			# print(resp)
			# print(resp.get("status"))
			if resp["status"] != "OK":
				abort(404)
			
	resp = Response(dict(), status=200,  mimetype='application/json')
	return resp




@project.route("/<project_name>/relation_table/current_user", methods=["GET"])
# @login_required
def get_relation_table_current_user(project_name):
	project = project_service.get_by_name(project_name)
	print('project', project)
	if not project:
		print("problem with proj")
		abort(404)

	reply = grew_request (
				'searchPatternInGraphs',
				data = {'project_id': project_name, "pattern":'pattern { e: GOV -> DEP}', "clusters":["e; GOV.upos; DEP.upos"]}
				)
	response = json.loads(reply)
	if response["status"] != "OK": abort(400)
	# current_user.id = "gael.guibon"
	data = response.get("data")
	for e, v in data.items():
		# print("edge", e)
		for gov, vv in v.items():
			for dep, vvv in vv.items():
				trees = dict()
				for elt in vvv:
					if elt.get("user_id") != current_user.id: continue
					conll = json.loads(grew_request("getConll", data={"sample_id":elt["sample_id"], "project_id":project_name, "sent_id":elt["sent_id"], "user_id":current_user.id}))
					# conll = json.loads(grew_request("getConll", data={"sample_id":elt["sample_id"], "project_id":project_name, "sent_id":elt["sent_id"], "user_id":"marine"}))

					if conll["status"] != "OK": abort(404)
					conll = conll["data"]
					trees=project_service.formatTrees_user(elt, trees, conll)
				data[e][gov][dep] = trees

	js = json.dumps(data)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp

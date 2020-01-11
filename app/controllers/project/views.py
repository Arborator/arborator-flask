from flask import render_template, flash, redirect, url_for, jsonify, request, Response, abort
from flask_login import login_required, current_user
from werkzeug import secure_filename
import json, logging
from functools import wraps
import os
import re, base64
from ...utils.conll3 import conll3
from collections import OrderedDict
from flask_cors import cross_origin
import io, zipfile, time

# local imports
from . import project
from ...models.models import *
from ...utils.grew_utils import grew_request, upload_project
from ....config import Config

from ...services import project_service, user_service


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

			project_access = project_service.get_access_for_project(project_id, current_user.id)

			print("project_access for current user: {}".format(project_access))
			
			if not current_user.super_admin: # super_admin are always admin even if it's not in the table
				if project_access is None or project_access < access_level:
					abort(403)
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
	if project_infos == 403: abort(403) 
	js = json.dumps(project_infos, default=str)
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
# @requires_access_level(2)
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
	else: p_access = project_service.get_project_access(project.id, current_user.id).accesslevel
	if p_access >=2 or current_user.super_admin:
		project_service.delete(project)
	else:
		print("p_access to low for project {}".format(project.projectname))
		abort(403)
	projects = project_service.get_all()
	js = json.dumps(projects)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp



# TODO: on est là !
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
@cross_origin()
# @cross_origin(origin='*', headers=['Content-Type', 'Authorization', 'Access-Control-Allow-Credentials'])
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
	import_user = request.form.get("import_user", "") # TODO : change import_user
	print("IMPORT USER: {}".format(import_user))
	if fichiers:
		reextensions = re.compile(r'\.(conll(u|\d+)?|txt|tsv|csv)$')
		samples  = project_service.get_samples(project_name)
		for f in fichiers:
			project_service.upload_project(f, project_name, import_user, reextensions=reextensions, existing_samples=samples)

	samples = {"samples":project_service.get_samples(project_name)}
	# print(samples)
	js = json.dumps(samples)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp

@project.route('/create', methods=["POST"])
@cross_origin()
def create_project():
	''' create an emty project'''
	project_name = request.form.get("project_name", "")
	creator = request.form.get("import_user", "") 
	project_description = request.form.get("description", "")
	# project_image = ''
	project_private = request.form.get("private", False)
	project_service.create_empty_project(project_name, creator, project_description, project_private)
	js = json.dumps({})
	resp = Response(js, status=200, mimetype='application/json')
	return resp

@project.route('/<project_name>/create/upload', methods=["POST", "OPTIONS"])
@cross_origin()
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



# @project.route('/<project_name>/export/zip', methods=["POST", "GET"])
@project.route('/<project_name>/export/zip', methods=["POST"])
def sample_export(project_name):
	project = project_service.get_by_name(project_name)
	if not project: abort(404)
	if not request.json: abort(400)
	
	data = request.get_json(force=True)
	samplenames = data['samples']
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
		js = json.dumps( project_service.samples2trees(samples, sample_name) )
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




@project.route('/<project_name>/sample/<sample_name>/users', methods=['POST'])
# @login_required
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
			if r not in possible_roles:
				abort(400)
			project_service.create_add_sample_role(u, sample_name, project.id, r)
		else:
			sr = SampleRole.query.filter_by(projectid=project.id, samplename=sample_name, userid=u).first()
			if sr:
				project_service.delete_sample_role(sr)
	return sampleusers(project_name, sample_name)



@project.route('/<project_name>/sample/<sample_name>', methods=['DELETE'])
# @login_required
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
def update_sample(project_name, sample_name):
	"""
	TODO 
	"""
	pass


@project.route("/<project_name>/sample/<sample_name>/saveTrees", methods=["POST"])
# @login_required
def save_trees(project_name, sample_name):
	project = project_service.get_by_name(project_name)
	if not project:
		print("problem with proj")
		abort(404)
	if not request.json: abort(400)

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
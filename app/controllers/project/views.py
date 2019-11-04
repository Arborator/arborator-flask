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


# local imports
from . import project
from ...models.models import *
from ....grew_server.test.test_server import send_request as grew_request
from ...utils import grew_utils
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
	current_user.id ="rinema56@gmail.com" # TODO : handle when user is really anonymous
	project_infos = project_service.get_infos(project_name, current_user)
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
	changer nom du projet project:{nom:nouveaunom,description:nouvelledescription,isprivate:True, image:blob}
	# TODO : change the projectname in grew also !
	
	"""
	if not request.json: abort(400)
	project = project_service.get_by_name(project_name)
	if not project: abort(400)
	if request.json.get("users"):
		for k,v in request.json.get("users").items():
			user = user_service.get_by_id(k)
			if user:
				pa = project_service.get_project_access(project.id, user.id)
				if pa: pa.accesslevel=v
				else: project_service.create_add_project_access(user.id, proejct.id, v)
			else: abort(400)
	if request.json.get("project"):
		for k,v in request.json.get("project").items(): setattr(project,k,v)
	db.session.commit()
	return project_info(project_name)




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
	p_access = get_access_for_project(current_user.id, project.id)
	if p_access >=2 or current_user.super_admin: # p_access and p_access >=2
		project_service.delete(project)
	else:
		print("p_access to low for project {}".format(project.projectname))
		abort(403)
	js = json.dumps( project_service.get_all(json=True) )
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
	matches={}
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

		# adding trees
		# {trees:{sent_id:{"sentence":sentence, "conlls":{user:conll, user:conll}}, matches:{(sent_id, user_id):[{nodes: [], edges:[]}]}}
	
		if m["sent_id"] not in trees:
			t = conll3.conll2tree(conll)
			s = t.sentence()
			trees[m["sent_id"]] = {"sentence":s, "conlls":{user_id:conll}}
		else:
			trees[m["sent_id"]]["conlls"].update(user_id=conll)
		nodes = []
		for k in m['nodes'].values():
			nodes +=[k.split("_")[-1]]

		edges = []
		for k in m['edges'].values():
			edges +=[k.split("_")[-1]]

		matches[m["sent_id"]+'____'+user_id] = {"edges":edges,"nodes":nodes}

	js = json.dumps({"trees":trees,"matches":matches})
	resp = Response(js, status=200,  mimetype='application/json')

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
	import_user = request.form.get("import_user", "")
	if fichiers:
		reextensions = re.compile(r'\.(conll(u|\d+)?|txt|tsv|csv)$')
		samples  = project_service.get_samples(project_name)
		for f in fichiers: project_service.upload_project(f, reextensions=reextensions, existing_samples=samples)

	samples = {"samples":project_service.get_samples(project_name)}
	js = json.dumps(samples)
	resp = Response(js, status=200,  mimetype='application/json')

	return resp



@project.route('/<project_name>/export/zip', methods=["POST", "GET"])
def sample_export(project_name):
	data = request.json
	samplenames = data['samples']
	sampletrees = list()
	for samplename in samplenames: 
		reply = json.loads(grew_request('getConll', data={'project_id': project_name, 'sample_id':samplename}))
		if reply.get("status") == "OK":	sampletrees.append( project_service.servSampleTrees(reply.get("data", {})  )	)
	# print(sampletrees[0])
	# print(reply)
	resp = Response({}, status=200,  mimetype='application/zip', headers={'Content-Disposition':'attachment;filename=dump.zip'})
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
		js = json.dumps( project_service.samples2trees(samples) )
		resp = Response(js, status=200,  mimetype='application/json')
		return resp
	else: abort(409)


@project.route('/<project_name>/sample/<sample_name>/search', methods=['GET'])
# @login_required
def search_sample(project_name, sample_name):
	"""
	Aplly a grew search inside a project and sample
	"""
	project = Project.query.filter_by(projectname=project_name).first()

	if not project:
		abort(404)
	if not request.json:
		abort(400)

	# TODO : test if sample exists

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

		# adding trees
		# {trees:{sent_id:{user:conll, user:conll}}, matches:{(sent_id, user_id):[{nodes: [], edges:[]}]}}
		trees.get(m["sent_id"],{})[user_id] = conll

		nodes = []
		for k in m['nodes'].values():
			nodes +=[k.split("_")[-1]]

		edges = []
		for k in m['edges'].values():
			edges +=[k.split("_")[-1]]

		matches[m["sent_id"]+'____'+user_id] = {"edges":edges,"nodes":nodes}


	js = json.dumps({"trees":trees,"matches":matches})
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
	sampleroles = project_service.get_samples_roles(project.id, sample_name)
	print(sampleroles)
	js = json.dumps(sampleroles)
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
	project = Project.query.filter_by(projectname=project_name).first()
	if not project: abort(404)
	if not request.json: abort(400)

	# TODO : check that sample exists
	# TODO? : check that user exists ?
	
	for u,r in request.json.items():
		if r: project_service.create_add_sample_role(u, sample_name, project.id, r)
		else:
			sr = SampleRole.query.filter_by(projectid=project.id, samplename=sample_name, userid=u).first()
			if sr:	project_service.delete_sample_role(sr)
	return sampleusers(project_name, sample_name)







@project.route('/<project_name>/sample/<sample_name>', methods=['DELETE'])
# @login_required
def delete_sample(project_name, sample_name):
	"""
	Delete a sample and everything in the db related to this sample
	"""
	project = Project.query.filter_by(projectname=project_name).first()
	if not project:
		abort(400)
	reply = json.loads(grew_request ('eraseSample', data={'project_id': project_name, 'sample_id': sample_name}))
	related_sample_roles = SampleRole.query.filter_by(projectid=project.id).delete()
	db.session.commit()
	return project_info(project_name)


@project.route('/<project_name>/sample/<sample_name>', methods=['POST'])
# @login_required
def update_sample(project_name, sample_name):
	"""
	TODO 
	"""
	pass

	

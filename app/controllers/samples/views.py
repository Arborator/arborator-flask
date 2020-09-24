from flask import render_template, flash, redirect, url_for, jsonify, request, Response, abort, current_app, make_response
from flask_login import login_required, current_user
import json, logging
from functools import wraps
import os
import re, base64
from ...utils.conll3 import conll3
from collections import OrderedDict
# from flask_cors import cross_origin
import io, zipfile, time

# local imports
from . import samples
from ...models.models import *
from ...utils.grew_utils import grew_request

from ...services import project_service, user_service, robot_service, github_service, samples_service
from ...repository import project_dao, samples_dao


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


@samples.route('/<project_name>/samples/fetch_all')
def project_samples(project_name):
	''' get project samples information'''
	print("KK project_name>/samples/fetch_all", project_name)
	project_samples = samples_service.get_project_samples(project_name)
	js = json.dumps(project_samples, default=str)
	resp = Response(js, status=200,  mimetype='application/json')
	return resp


@samples.route('/<project_name>/samples/<sample_name>/exercise-level/create-or-update', methods=['POST'])
@requires_access_level(2)
def create_or_update_sample_exercise_level(project_name, sample_name):
	if not request.json: abort(400)
	project_id = project_dao.find_by_name(project_name).id
	new_exercise_level = request.json['exerciseLevel']
	sample_exercise_level = samples_service.create_or_update_sample_exercise_level(sample_name, project_id, new_exercise_level)
	# if not sample_exercise_level:
	# 		sample_exercise_level = samples_service.add_sample_exercise_level(sample_name, project_id, )

	req = request.json
	
	
	# samples = {"samples":project_service.get_samples(req['projectname'])}
	# res = {}
	# if 'samplename' in req:
	# 	if not req['samplename'] in samples["samples"]: abort(404)
	# 	possible_roles = [x[0] for x in project_service.get_possible_roles()]
	# 	roleInt = [r[0] for r in project_service.get_possible_roles() if r[1] == role][0]
	# 	user = user_service.get_by_username(req['username'])
	# 	if not user: abort(400)
	# 	project_service.add_or_delete_sample_role(user, req['samplename'], req['projectname'], roleInt, True)
	# 	sample = project_service.get_sample(req['samplename'], req['projectname'])
	# 	res = sample
	js = json.dumps({"succeed": "ok"})
	resp = Response(js, status=200,  mimetype='application/json')
	return resp



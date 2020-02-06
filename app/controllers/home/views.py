from flask import render_template, jsonify, abort, flash, redirect, render_template, url_for, request, Response


from flask_login import current_user, login_required
from flask_cors import cross_origin
import os, re, json

from . import home
from ...models.models import *
from ... import db
from ...services import project_service, user_service

# from ...app.admin import views as adminviews


@cross_origin()
@home.route('/home/projects/', methods=['GET'])
def home_page():
	"""
	Home page

	Returns list of projects with:
	- is_private
	- roles (of the current user if logged in)
	"""
	# current_user.id = "rinema56@gmail.com"
	projects = Project.query.all()
	
	projects_info = list()
	if current_user.is_authenticated:
		for project in projects:
			# roles = sorted(set(SampleRole.query.filter_by(projectid=project.id, userid=current_user.id).all()))
			# TODO : choose to only obtain project roles (admin, guest, none) and not sample roles (annotator, etc)
			# roles = list(set(SampleRole.query.filter_by(projectid=project.id, userid=current_user.id).all()))
			# roles = [{'project':role.projectid, 'role':role.role.value}  for role in roles]
			infos = project_service.get_infos(project.projectname, current_user)
			# roles = [] # temp ignore
			# if not roles: roles = []
			if not infos: infos = {"admins":[], "guests":[]}
			projects_info.append(project.as_json(include={"admins":infos['admins'],"guests":infos['guests']}))
	else:
		for project in projects:
			projects_info.append(project.as_json(include={"admins":[],"guests":[]}))
	# print(666,projects_info)
	# print('projects', projects)

	js = json.dumps(projects_info)
	resp = Response(js, status=200,  mimetype='application/json')
	
	resp.headers['Access-Control-Allow-Origin'] = '*'
	resp.headers['Access-Control-Allow-Headers'] = '*'
	resp.headers['Access-Control-Allow-Methods'] = '*'
	return resp


@home.route('/q')
def q_test():
	"""
	Quickie Handler
	q.cgi convert
	"""
	return render_template('home/quickie.html')


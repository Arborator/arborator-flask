from flask import render_template, jsonify, abort, flash, redirect, render_template, url_for, request, Response


from flask_login import current_user, login_required
from flask_cors import cross_origin
import os, re, json

from . import home
from ..models import *
from .. import db

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
			roles = sorted(set(SampleRole.query.filter_by(projectid=project.id, userid=current_user.id).all()))
			if not roles:
				roles = []
			projects_info.append(project.as_json(include={"roles":roles}))
	else:
		for project in projects:
			projects_info.append(project.as_json())
	print(666,projects_info)
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


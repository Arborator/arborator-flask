from flask import render_template, jsonify, abort, flash, redirect, render_template, url_for, request, Response, current_app


from flask_login import current_user, login_required
# from flask_cors import cross_origin
import os, re, json

from . import home
from ...models.models import *
from ... import db
from ...services import project_service, user_service

# from ...app.admin import views as adminviews


# @cross_origin()
@home.route('/home/projects/', methods=['GET'])
def home_page():
	"""
	Home page

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


@home.route('/q')
def q_test():
	"""
	Quickie Handler
	q.cgi convert
	"""
	return render_template('home/quickie.html')


from flask import (
    render_template,
    jsonify,
    abort,
    flash,
    redirect,
    render_template,
    url_for,
    request,
    Response,
    current_app,
)
from flask_login import current_user, login_required
from werkzeug import secure_filename
import os, re, json
from functools import wraps
import requests


from . import admin

# from .forms import ProjectForm, UploadForm, UserAssignForm, ACCESS
from ... import db
from ...models.models import *

try:
    from ....config import Config  # dev
except:
    from config import Config  # prod
from ...utils.grew_utils import grew_request
from ..project.views import requires_access_level


def superadmin_required(func):
    """
    Decorator requiring to be a super_admin to see the view
    """

    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.super_admin:
            # flash("You do not have access to that page. Sorry!") # problem is with json you don't see the message :/
            resp = Response("", status=403, mimetype="application/json")
            return resp
            # return redirect(url_for('home.home_page'))
        # print("Congrats you're a super admin!")
        return func(*args, **kwargs)

    return decorated_view


## Dashboard View : list of projects and users
@admin.route("/", methods=["GET"])
# @login_required # ok
@superadmin_required
def superadmin_dashboard():
    """

    TODO: utile ?
    Returns a list of users and a list of projects
    """
    users = list_users().json
    projects = list_projects().json
    return jsonify({"Users": users, "Projects": projects})


# ### Projects Views
# @admin.route('/projects', methods=['GET'])
# # @login_required
# @superadmin_required
# def list_projects():
# 	"""
# 	List all projects
# 	"""
# 	projects = Project.query.all()

# 	for p in projects:


# 		if ProjectAccess.query.filter_by(project_id=p.id, user_id=current_user.id).first() is None:
# 			access = 0
# 		if p.is_private and access < 1: # private project and current_user is not a user of the project -> filtered
# 			projects.remove(p)

# 	js = json.dumps([p.as_json() for p in projects])
# 	resp = Response(js, status=200,  mimetype='application/json')
# 	# resp.headers['Access-Control-Allow-Origin'] = '*'
# 	return resp


def projectsongrew():
    reply = grew_request("getProjects", current_app)
    print("projectsongrew", reply)
    # reply = grew_request('getUsers')
    reply = json.loads(reply)
    if reply.get("status") == "OK":
        return reply.get("data", [])


def addprojectongrew(project_name):
    # if project_name in projectsongrew():
    # 	return "ERROR"
    reply = grew_request("newProject", current_app, data={"project_id": project_name})
    print("addprojectongrew", reply)
    reply = json.loads(reply)
    return reply.get("status", "grew error")


def addproject(project_name, visibility, image=b"", description=""):
    if Project.query.filter_by(project_name=project_name).first():
        return {"errormessage": "Project under the same name exists."}
    project = Project(
        project_name=project_name,
        description=description,
        visibility=int(visibility),
        image=image,
    )
    print("project visibility ", project.visibility, type(project.visibility))
    db.session.add(project)
    db.session.commit()
    grewanswer = addprojectongrew(project_name)
    if grewanswer != "OK":
        return {"errormessage": "Cannot create project on grew."}
    return {
        "message": "Project {project_name} created.".format(project_name=project_name)
    }


# marine : I don't think this is used currently
# @admin.route('/addproject', methods=['POST'])
# # @login_required
# # @superadmin_required
# def create_project():
# 	"""
# 	Create a project
# 	"""
# 	if not request.json:
# 		abort(404)
# 	imagefilename = request.json.get("imagefile",None)
# 	if imagefilename:

# 		with open(Config.UPLOAD_FOLDER + secure_filename(imagefilename), "w") as outf:
# 			outf.write(content)
# 		with open(os.path.join(Config.UPLOAD_FOLDER,secure_filename(imagefilename)), 'rb') as inf:
# 			imgblob = inf.read()
# 	else:
# 		imgblob=b""

# 	reply = addproject(request.json["project_name"], request.json["is_private"], description=request.json.get("description", ""), image=imgblob)
# 	print(reply)
# 	if 'errormessage' in reply:
# 		resp = Response(str(reply), status=409,  mimetype='application/json')
# 	else:
# 		resp = Response(str(reply), status=200,  mimetype='application/json')
# 	return resp


# project = Project(project_name=request.json["project_name"], description=request.json.get("description", ""), is_private=request.json["is_private"])
# print("project", project)
# # test whether the project already exists in the database
# if Project.query.filter_by(project_name=project.project_name).first() is None:
# 	db.session.add(project)
# 	# # create the project on grew
# 	print ('========== [newProject]')
# 	reply = grew_request ('newProject', data={'project_id': project.project_name})
# 	print (reply) # TODO: check if error, if error, remove project from db and send error message


# 	projects = Project.query.all()

# 	# return jsonify([p.as_json() for p in projects])
# 	resp = Response('{"message":"Project created."}', status=200,  mimetype='application/json')

# 	db.session.commit()

# else:
# 	print("project under the same name exists")
# 	resp = Response('{"errormessage":"Project under the same name exists."}', status=409,  mimetype='application/json')


# return resp


# @admin.route("/test")
# # @login_required
# def test():
# 	# print(current_user)
# 	# print(current_user.super_admin)
# 	## Projects management
# 	# list projects
# 	# res = requests.get("http://localhost:5000/admin")
# 	# print(current_user)
# 	# print(current_user.id)

# 	# delete a project
# 	# res = requests.delete("http://localhost:5000/admin/projects", json={"project_name":"aa"})

# 	# create a project
# 	filenames = ['/home/marine/Téléchargements/1_a.conllu', '/home/marine/Téléchargements/1_b.conllu']
# 	jason = {'files': filenames, "project_name":"first_project", "is_private":True, "import_user":"rinema56@gmail.com"}
# 	print("doing as requested")
# 	res = requests.post("http://localhost:5000/admin/projects/addproject", json=jason)

# 	# filenames = ['/home/marine/Téléchargements/1_b.conll']
# 	# for filename in filenames:
# 	# 	res = requests.post("http://localhost:5000/admin/projects", json={"project_name":"testy", "is_private":True}, files={'file':open(filename, 'rb')})
# 	# res = requests.delete("http://localhost:5000/admin/projects", json={"project_name":"aa"})

# 	# uploading files
# 	# filenames = ['/home/marine/Téléchargements/1_b.conll']
# 	# for filename in filenames:
# 	# 	res = requests.post("http://localhost:5000/admin/upload", files={'file':open(filename, 'rb')})
# 	# 	print('response from server:',res.text)
# 	return jsonify({"data":"ok"})


# @admin.route('/upload', methods=['POST'])
# # @login_required
# def upload():
# 	"""
# 	Upload a file in the data storage folder.
# 	"""
# 	f = request.files["file"]
# 	cwd = os.getcwd()
# 	f.save(Config.UPLOAD_FOLDER +secure_filename(f.filename)) #default is grew_server/data
# 	return jsonify({"status":"OK"})

# todo: remove here, see project views sample_upload
# def saveconll(request):
# 	"""
# 	save conll files inside a grew Project
# 	"""
# 	redoublenl = re.compile(r'\s*\n\s*\n+\s*')
# 	reextensions = re.compile(r'\.(conllu?|txt|tsv|csv)$')


# 	files = request.json.get("files", [])
# 	project_name = request.json["project_name"]
# 	import_user = request.json.get("import_user", "parser") # TODO : facultatif import_user
# 	print("project ", project_name)
# 	print("files to add ", files)

# 	print('========== [getSamples]')
# 	reply = grew_request(
# 			'getSamples',
# 			data = {'project_id': project_name}
# 				)
# 	print(json.loads(reply))
# 	samples = [sa['name'] for sa in json.loads(reply)['data']]

# 	for fichier in files:
# 		print("saving {}".format(fichier))
# 		content = open(fichier).read()
# 		sample_name = reextensions.sub("", os.path.basename(fichier))
# 		with open(Config.UPLOAD_FOLDER +secure_filename(sample_name), "w") as outf:
# 			outf.write(content)
# 		if sample_name not in samples:

# 		# create a new sample in the grew project
# 			print ('========== [newSample]')
# 			reply = grew_request ('newSample', data={'project_id': project_name, 'sample_id': sample_name })
# 			print (reply)


# 			print(project_name, sample_name, import_user)
# 			with open(os.path.join(Config.UPLOAD_FOLDER,sample_name), 'rb') as inf:
# 				print ('========== [saveConll]')
# 				reply = grew_request (
# 					'saveConll',
# 					data = {'project_id': project_name, 'sample_id': sample_name, "user_id": import_user},
# 					files={'conll_file': inf},
# 				)

# 	return jsonify({"status":"ok"})


# Users view : used to populate the annotators and validators for the project page
# status : ok
# full route = admin/users
@admin.route("/users", methods=["GET"])
def list_users():
    users = User.query.all()
    # default=str is used to serialize the date
    # https://stackoverflow.com/questions/11875770/how-to-overcome-datetime-datetime-not-json-serializable
    js = json.dumps(
        [u.as_json(exclude=["auth_provider", "created_dated"]) for u in users],
        default=str,
    )
    for user in users:
        print("KK users", user)
    resp = Response(js, status=200, mimetype="application/json")
    return resp


# status : no longer used
# @admin.route('/users', methods=["DELETE"])
# @login_required
# @superadmin_required
# def delete_user():
# 	"""
# 	Deletes a user and returns the list of remaining users
# 	"""
# 	if not request.json:
# 		abort(400)

# 	user = User.query.get_or_404(request.json["user_id"])
# 	if not user:
# 		abort(400)
# 	else:
# 		related_accesses = ProjectAccess.query.filter_by(user_id=user.id).delete()
# 		related_sample_roles = SampleRole.query.filter_by(user_id=user.id).delete()
# 		db.session.delete(user)
# 		db.session.commit()
# 	resp = list_users()
# 	return resp


# @admin.route('/users/manage_access', methods=['GET', 'POST'])
# # @login_required
# def manage_user_access_to_projects():
# 	"""
# 	Give a user an access to a project
# 	"""
# 	form = UserAssignForm()
# 	if request.method == "POST":
# 		project = form.project.data
# 		user_id = form.user.data.id
# 		project_access = ProjectAccess.query.filter_by(user_id=user_id, project_id=project.id).first()

# 		if project_access:
# 			project_access.access_level = form.access_level.data
# 		else:
# 			project_access = ProjectAccess(project_id=project.id, user_id=user_id, access_level=form.access_level.data)
# 			db.session.add(project_access)
# 		db.session.commit()
# 		flash('You have successfully assigned a project and role.')
# 		return redirect(url_for('admin.list_users'))

# 	return render_template('admin/users/user.html',
# 						   form=form,
# 						   title='Assign User')


@admin.route("/initdb/", methods=["GET"])
# @login_required
# @adminviews.superadmin_required
def init_database():
    """
    initdb
    """

    if os.path.isfile(str(db.engine.url)[len("sqlite:///") :]):
        resp = Response(
            '{"database":"was there already"}', status=401, mimetype="application/json"
        )
    else:

        print("current_user:", current_user)
        # , "super_admin:",current_user.super_admin)
        db.create_all()

        # all projects in grew are created in the database ===================
        projects = projectsongrew()
        print(projects)
        for project_name in projects:
            reply = grew_request(
                "eraseProject", current_app, data={"project_id": project_name}
            )
            print(reply)

            # print(6451,project_name,Project.query.filter_by(project_name=project_name).first())
            # if not Project.query.filter_by(project_name=project_name).first():
            # 	project = Project(project_name=project_name, description="copy from grew", is_private=False)
            # 	db.session.add(project)
            # 	db.session.commit()
            # 	print(6541321)
        projects = projectsongrew()
        print("maintenant on a ça sur grew", projects)

        # first testproject ==============
        # nomprojet = "French"
        # addproject(nomprojet, is_private=False, description="this is a test project to fill the database")

        # # first testproject add conll =================
        # filenames = ['initialization/peripitiesVoiture.conll', 'initialization/astuceCinema.conll']
        # jason = {'files': filenames, "import_user":"gold"}
        # res = requests.post("http://localhost:5000/api/projects/{nomprojet}/upload".format(nomprojet=nomprojet), json=jason)
        # print("grew said",res)

        # second testproject ==============
        nomprojet = "Naija"
        with open("initialization/naija.png", "rb") as inf:
            imgblob = inf.read()
        addproject(
            nomprojet,
            visibility=2,
            image=imgblob,
            description="this is a test project to fill the database",
        )
        filenames = [
            "initialization/P_WAZP_07_Imonirhuas.Life.Story_PRO.conll",
            "initialization/P_ABJ_GWA_10_Steven.lifestory_PRO.conll",
        ]
        jason = {"files": filenames, "import_user": "Bernard"}
        res = requests.post(
            "http://localhost:5000/api/projects/{nomprojet}/upload".format(
                nomprojet=nomprojet
            ),
            json=jason,
        )
        print("grew said", res)
        filenames = ["initialization/P_ABJ_GWA_10_Steven.lifestory_PRO.modif.conll"]
        jason = {
            "files": filenames,
            "import_user": "yuchen",
            "sample_names": ["P_ABJ_GWA_10_Steven.lifestory_PRO"],
        }
        res = requests.post(
            "http://localhost:5000/api/projects/{nomprojet}/upload".format(
                nomprojet=nomprojet
            ),
            json=jason,
        )
        print("grew said", res)

        print("database created", db.engine.url)
        resp = Response(
            '{"database":"created"}', status=200, mimetype="application/json"
        )

    return resp


@admin.route("/initdb/addstuff", methods=["GET"])
# @login_required
# @adminviews.superadmin_required
def addstuff():
    """
    Home Handler
    """
    # print (6546545)

    # print("current_user:",current_user)
    nomprojet = "azer_3"
    addproject(
        nomprojet,
        visibility=0,
        description="this is a test project to fill the database",
    )
    addprojectongrew(nomprojet)
    resp = Response(
        '{"database":"filled with stuff"}', status=200, mimetype="application/json"
    )
    return resp

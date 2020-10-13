from flask import render_template, flash, redirect, url_for, jsonify, request, Response, abort, current_app, make_response
from flask_login import login_required, current_user
import json
import logging
from functools import wraps
from ...utils.conll3 import conll3  # type: ignore
from collections import OrderedDict
# from flask_cors import cross_origin

# local imports
from . import samples
from ...models.models import *  # type: ignore
from ...utils.grew_utils import grew_request  # type: ignore

from ...services import project_service, user_service, robot_service, github_service, samples_service  # type: ignore
from ...repository import project_dao, samples_dao  # type: ignore


logging.getLogger('flask_cors').level = logging.DEBUG


def requires_access_level(access_level):
    """	decorator for access control. except for superadmins """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):

            # not authenticated -> login
            if not current_user.id:
                return redirect(url_for('auth.login'))

            if kwargs.get("project_name"):
                project_id = project_service.get_by_name(
                    kwargs["project_name"]).id
            elif kwargs.get("id"):
                project_id = kwargs["id"]
            else:
                abort(400)

            project_access = project_service.get_project_access(
                project_id, current_user.id)

            print("project_access for current user: {}".format(project_access))

            if not current_user.super_admin:  # super_admin are always admin even if it's not in the table
                if isinstance(project_access, int):
                    abort(403)
                if project_access is None or project_access.accesslevel.code < access_level:
                    abort(403)
                 # return redirect(url_for('home.home_page'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


@samples.route('/<project_name>/samples/fetch_all')
def project_samples(project_name):
    ''' get project samples information'''
    project_samples = samples_service.get_project_samples(project_name)
    js = json.dumps(project_samples, default=str)
    resp = Response(js, status=200,  mimetype='application/json')
    return resp


@samples.route('/<project_name>/samples/<sample_name>/exercise-level/create-or-update', methods=['POST'])
@requires_access_level(2)
def create_or_update_sample_exercise_level(project_name, sample_name):
    if not request.json:
        abort(400)
    project_id = project_dao.find_by_name(project_name).id
    new_exercise_level = request.json['exerciseLevel']
    sample_exercise_level = samples_service.create_or_update_sample_exercise_level(
        sample_name, project_id, new_exercise_level)
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

    # TODO (kirian) : return the sample
    js = json.dumps({"succeed": "ok"})
    resp = Response(js, status=200,  mimetype='application/json')
    return resp


@samples.route('/<project_name>/samples/<sample_name>/trees/fetch_all', methods=['GET'])
def get_sample_trees(project_name, sample_name) -> Response:
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
    print("KK request get_sample_trees")
    project = project_dao.find_by_name(project_name)
    exercise_mode = project.exercise_mode

    reply = json.loads(grew_request('getConll', current_app, data={
                       'project_id': project_name, 'sample_id': sample_name}))
    # reendswithnumbers = re.compile(r"_(\d+)$")

    if reply.get("status") != "OK":
        abort(409)

    samples = reply.get("data", {})
    if not project:
        abort(404)

    ##### exercise mode block #####
    project_access: int = 0
    exercise_level: int = 4
    if exercise_mode:
        exercise_level = samples_service.get_sample_exercise_level(
            sample_name, project.id)
        project_access = project_service.get_project_access(
            project.id, current_user.id)

        if project_access == 2:  # isAdmin (= isTeacher)
            sample_trees = samples_service.samples2trees(samples, sample_name)
        elif project_access == 1:  # isGuest (= isStudent)
            sample_trees = samples_service.samples2trees_exercise_mode(
                samples, sample_name, current_user, project_name)
        else:
            abort(409)  # is not authentificated
    ##### end block exercise mode #####

    else:
        if project.show_all_trees or project.visibility == 2:
            sample_trees = samples_service.samples2trees(samples, sample_name)
        else:
            validator = project_service.is_validator(
                project.id, sample_name, current_user.id)
            if validator:
                sample_trees = samples_service.samples2trees(
                    samples, sample_name)
            else:
                sample_trees = samples_service.samples2trees_with_restrictions(
                    samples, sample_name, current_user, project_name)

    data = {
        "sample_trees": sample_trees,
        "exercise_level":  exercise_level
    }
    js = json.dumps(data)
    resp = Response(js, status=200,  mimetype='application/json')
    print(resp)
    return resp

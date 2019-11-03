from ..models.models import *
from ...grew_server.test.test_server import send_request as grew_request
from ...config import Config
from ..utils.conll3 import conll3
from ..repository import project_dao

def get_project_access(project_id, user_id):
    ''' return the project access level given a project id and user id. returns 0 if the projject access is false '''
    project_access = project_dao.get_project_access(project_id, user_id)
    # if no access links this project and user, the user is a guest
    if not project_access: return 0
    return project_access.access_level

def get_by_name(project_name):
    ''' get project by name '''
    return project_dao.find_by_name(project_name)

def get_infos(project_name, current_user):
    ''' get project informations available for the current user '''
    project = project_dao.find_by_name(project_name)
    roles = project_dao.get_roles(project.id, current_user.id)

    if not roles and project.is_private: return 403

    admins = [a.userid for a in project_dao.get_admins(project.id)]
    guests = [g.userid for g in project_dao.get_guests(project.id)]

    reply = grew_request ( 'getSamples', data = {'project_id': project.projectname} )
    js = json.loads(reply)
    data = js.get("data")
    samples=[]
    nb_samples=0
    nb_sentences=0
    sum_nb_tokens=0
    average_tokens_per_sample=0
    if data:
        nb_samples = len(data)
        samples = []
        sample_lengths = []
        for sa in data:
            sample={'samplename':sa['name'], 'sentences':sa['size'], 'treesFrom':sa['users'], "roles":{}}
            lengths = []
            for r,label in project_dao.get_possible_roles():
                role = db.session.query(User, SampleRole).filter(
                    User.id == SampleRole.userid).filter(
                        SampleRole.projectid==project.id).filter(
                            SampleRole.samplename==sa['name']).filter(
                                SampleRole.role==r).all()
                sample["roles"][label] = [a.as_json() for a,b in role]

            reply = json.loads(grew_request('getConll', data={'project_id': project.projectname, 'sample_id':sa["name"]}))
            
            if reply.get("status") == "OK":
                truc = reply.get("data", {})
                for sent_id, dico in truc.items():
                    conll = list(dico.values())[0]
                    t = conll3.conll2tree(conll)
                    length = len(t)
                    lengths.append(length)

            sample["tokens"] = sum(lengths)
            if len(lengths) > 0 : sample["averageSentenceLength"] = sum(lengths)/len(lengths)

            sample["exo"] = "" # TODO : create the table in the db and update it
            samples.append(sample)
            sample_lengths += [sample["tokens"]]

        sum_nb_tokens = sum(sample_lengths)
        average_tokens_per_sample = sum(sample_lengths)/len(sample_lengths)
             
        reply = grew_request('getSentIds', data={'project_id': project_name})
        js = json.loads(reply)
        data = js.get("data")
        if data:
            nb_sentences = len(data)

    image = str(base64.b64encode(project.image))
    return { "name":project.projectname, "is_private":project.is_private, "description":project.description, "image":image, "samples":samples, "admins":admins,  "guests":guests, "number_samples":nb_samples, "number_sentences":nb_sentences, "number_tokens":sum_nb_tokens, "averageSentenceLength":average_tokens_per_sample}



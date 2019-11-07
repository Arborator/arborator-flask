import os, json, zipfile, time, io
from ..models.models import *
from ...grew_server.test.test_server import send_request as grew_request
from ...config import Config
from ..utils.conll3 import conll3
from ..repository import project_dao
from werkzeug import secure_filename

def get_project_access(project_id, user_id):
    ''' return the project access given a project id and user id. returns 0 if the project access is false '''
    project_access = project_dao.get_access(project_id, user_id)
    # if no access links this project and user, the user is a guest
    if not project_access: return 0
    return project_access

def add_project_access(project_access):
    ''' add a project access '''
    project_dao.add_access(project_access)

def create_add_project_access(user_id, project_id, access_level):
    ''' create and add a new project access given the args if there is an old access it is deleted '''
    pa = ProjectAccess(userid=user_id, projectid=project_id, accesslevel=access_level)
    project_dao.add_access(pa)

def delete_project_access(project_access):
    ''' deletes a project access '''
    project_dao.delete_project_access(project_access)

def get_all(json=False):
    ''' get all the projects. if json is true, returns the list of json'''
    if json: return project_dao.find_all()
    else: return [p.as_json() for p in project_dao.find_all()]

def get_by_name(project_name):
    ''' get project by name '''
    return project_dao.find_by_name(project_name)

def delete_by_name(project_name):
    ''' delete a project from db and grew given its name '''
    project = project_dao.find_by_name(project_name)
    project_dao.delete(project)
    grew_request('eraseProject', data={'project_id': p.projectname})

def delete(project):
    ''' delete the given project from db and grew '''
    project_dao.delete(project)
    grew_request('eraseProject', data={'project_id': project.projectname})

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

def add_sample_role(sample_role):
    ''' add a sample role '''
    project_dao.add_sample_role(sample_role)

def create_add_sample_role(user_id, sample_name, project_id, role):
    ''' create and add a new sample role, if there is an old role it is deleted'''
    existing_role = project_dao.get_user_role(project_id, sample_name, user_id)
    if existing_role:
        project_dao.delete_sample_role(existing_role)
    new_sr = SampleRole(userid=user_id, samplename=sample_name, projectid=project_id, role=role)
    project_dao.add_sample_role(new_sr)

def delete_sample(project_name, project_id, sample_name):
    ''' delete sample given the infos. delete it from grew and db '''
    grew_request('eraseSample', data={'project_id': project_name, 'sample_id': sample_name})
    related_sample_roles = project_dao.delete_sample_role_by_project(project_id)

def delete_sample_role(sample_role):
    ''' delete a sample role '''
    project_dao.delete_sample_role(sample_role)

def delete_sample_role_by_project(project_id):
    ''' delete a sample role by filtering a project id '''
    return project_dao.delete_sample_role_by_project(project_id)

def get_samples(project_name):
    ''' get existing samples for a project. from Grew.'''
    reply = grew_request ('getSamples',	data = {'project_id': project_name}	)
    js = json.loads(reply)
    data = js.get("data")
    if data: return [sa['name'] for sa in data]
    else: return []

def get_samples_roles(project_id, sample_name, json=False):
    ''' returns the samples roles for the given sample in the given project. can be returned in a json format '''
    sampleroles = SampleRole.query.filter_by(projectid=project_id, samplename=sample_name).all()
    if json: return {sr.userid:sr.role.value for sr in sampleroles}
    else: return sampleroles

def get_possible_roles():
    return project_dao.get_possible_roles()

def samples2trees(samples):
    ''' transforms a list of samples into a trees object '''
    trees={}
    for sentId, users in samples.items():	
        for userId, conll in users.items():
            tree = conll3.conll2tree(conll)
            if sentId not in trees: trees[sentId] = {"sentence":tree.sentence(), "conlls": {}}
            trees[sentId]["conlls"][userId] = conll
    return trees

def upload_project(fileobject, project_name, import_user, reextensions=None, existing_samples=[]):
    ''' 
    upload project into grew and filesystem (upload-folder, see Config). need a file object from request
    Will compile reextensions if no one is specified (better specify it before a loop)
    '''

    if reextensions == None : reextensions = re.compile(r'\.(conll(u|\d+)?|txt|tsv|csv)$')

    filename = secure_filename(fileobject.filename)
    sample_name = reextensions.sub("", filename)

    # writing file to upload folder
    fileobject.save(os.path.join(Config.UPLOAD_FOLDER, filename))

    if sample_name not in existing_samples:
        # create a new sample in the grew project
        print ('========== [newSample]')
        reply = grew_request ('newSample', data={'project_id': project_name, 'sample_id': sample_name })
        print (reply)

    else:
        print("/!\ sample already exists")

    with open(os.path.join(Config.UPLOAD_FOLDER, filename), 'rb') as inf:
        print ('========== [saveConll]')
        if import_user:
            reply = grew_request (
                'saveConll',
                data = {'project_id': project_name, 'sample_id': sample_name, "user_id": import_user},
                files={'conll_file': inf},
            )
        else: # if no import_user has been provided, it should be in the conll metadata
            reply = grew_request (
                'saveConll',
                data = {'project_id': project_name, 'sample_id': sample_name},
                files={'conll_file': inf},
            )
        print(reply)

def servSampleTrees(samples):
    ''' get samples in form of json trees '''
    trees={}
    for sentId, users in samples.items():	
        for userId, conll in users.items():
            # tree = conll3.conll2tree(conll)
            if sentId not in trees: trees[sentId] = { "conlls": {}}
            trees[sentId]["conlls"][userId] = conll
    js = json.dumps(trees)
    return js

def sampletree2contentfile(tree):
    if isinstance( tree, str ): tree = json.loads(tree)
    usertrees = dict()
    for sentId in tree.keys():
        for user, conll in tree[sentId]['conlls'].items():
            if user not in usertrees: usertrees[user] = list()
            usertrees[user].append(conll)
    for user, content in usertrees.items(): usertrees[user] = '\n'.join(usertrees[user])
    return usertrees

def contentfiles2zip( sampletrees):
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for sample in sampletrees:
            for fuser, filecontent in sample.items():
                data = zipfile.ZipInfo('{}.conll'.format( fuser) )
                data.date_time = time.localtime(time.time())[:6]
                data.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(data, filecontent)
    memory_file.seek(0)
    return memory_file

def servTreeToOutputs(tree):
    ''' ? TODO : ???? '''
    return None
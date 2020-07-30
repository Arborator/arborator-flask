import os, json, zipfile, time, io
from ..models.models import *
try: from ...config import Config # dev
except: from config import Config # prod
from ..utils.conll3 import conll3
from ..utils.grew_utils import grew_request
from ..repository import project_dao, user_dao, robot_dao
from ..services import robot_service
from werkzeug import secure_filename
from datetime import datetime
from flask import abort, current_app
from decimal import Decimal


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
    grew_request('eraseProject', current_app, data={'project_id': p.projectname})

def delete(project):
    ''' delete the given project from db and grew '''
    project_dao.delete(project)
    grew_request('eraseProject', current_app, data={'project_id': project.projectname})
    # TODO : grew_request to delete the configuration that goes with the project

def get_settings_infos(project_name, current_user):
    ''' get project informations without any samples '''
    project = project_dao.find_by_name(project_name)
    if not current_user.is_authenticated: # TODO : handle anonymous user
        roles = []
    else:
        roles = project_dao.get_roles(project.id, current_user.id)
    # if not roles and project.is_private: return 403 # removed for now -> the check is done in view and for each actions
    admins = [a.userid for a in project_dao.get_admins(project.id)]
    guests = [g.userid for g in project_dao.get_guests(project.id)]

    # config from arborator
    shown_features = project_dao.find_project_features(project)
    shown_metafeatures = project_dao.find_project_metafeatures(project)


    # config from grew
    reply = json.loads(grew_request("getProjectConfig", current_app, data={"project_id":project_name}))
    if reply["status"] != "OK":
        abort(400)
    annotationFeatures = reply["data"]
    if annotationFeatures is None:
        print("This project does not have a configuration stored on grew")

    config = {"shownfeatures":shown_features, "shownmeta":shown_metafeatures, "annotationFeatures":annotationFeatures}

    # cats = [c.value for c in project_dao.find_project_cats(project.id)]
    # stocks = project_dao.find_project_stocks(project.id)
    # labels = [ {'id':s.id,'labels':[ {"id":l.id, "stock_id":l.stock_id , "value":l.value} for l in project_dao.find_stock_labels(s.id) ]}  for s in stocks ]
    defaultUserTrees = [u.as_json() for u in project_dao.find_default_user_trees(project.id)]
    if project.image != None: image = str(base64.b64encode(project.image))
    else: image = ''
    settings_info = { 
        "name":project.projectname, 
        "visibility":project.visibility, 
        "description":project.description, 
        "image":image,
        "config":config,
        "admins":admins, 
        "guests":guests,
        "show_all_trees":project.show_all_trees, 
        "default_user_trees":defaultUserTrees}
    print("settingsinfo ", settings_info)
    return settings_info


#new from kirian
def get_project_config(project_name):
    reply = grew_request ( 'getProjectConfig', current_app, data = {'project_id': project_name} )
    data = json.loads(reply)
    print("KK get_project_config data", data)
    return data

def update_project_config(project_name, config):
    reply = grew_request ( 'updateProjectConfig', current_app, data = {
        'project_id': project_name,
        'config': json.dumps(config)
        } )
    print("KK reply", reply)
    data = json.loads(reply)
    print("KK update_project_config data", data)
    return data


# def add_cat_label(project_name, current_user, cat):
#     """ add a cat to a project """
#     return [c.value for c in project_dao.add_cat(project_name, cat)]

# def remove_cat_label(project_name, current_user, cat):
#     """ delete a cat from a project cats list """
#     return [c.value for c in project_dao.delete_cat(project_name, cat)]

# def parse_txtcats(project, cats):
#     """ parse and replace all the cats by these ones """
#     lines = cats.split('\n')
#     lines = [line for line in lines if not line.startswith('#')]
#     categories = lines[0].split(',')
#     return [c.value for c in project_dao.set_cats(project, categories)]

# def add_stock(project_name):
#     """ add a stock """
#     stocks = project_dao.add_stock(project_name)
#     labels = [ {'id':s.id,'labels':[ {"id":l.id, "stock_id":l.stock_id , "value":l.value} for l in project_dao.find_stock_labels(s.id) ]}  for s in stocks ]
#     return labels

# def remove_stock(project_name, stockid):
#     """ remove a stock """
#     stocks = project_dao.delete_stock(project_name, stockid)
#     labels = [ {'id':s.id,'labels':[ {"id":l.id, "stock_id":l.stock_id , "value":l.value} for l in project_dao.find_stock_labels(s.id) ]}  for s in stocks ]
#     return labels

# def add_label(project_name, stock_id, label):
#     """ add a label to a project stock """
#     stocks = project_dao.add_label(project_name, stock_id, label)
#     labels = [ {'id':s.id,'labels':[ {"id":l.id, "stock_id":l.stock_id , "value":l.value} for l in project_dao.find_stock_labels(s.id) ]}  for s in stocks ]
#     return labels

# def remove_label(project_name, label_id, stock_id, label ):
#     """ remove a label from its project stock """
#     # stocks = project_dao.delete_label(project_name, stock_id, label)
#     project_dao.delete_label_by_id(label_id)
#     project = project_dao.find_by_name(project_name)
#     stocks = project_dao.find_project_stocks(project.id)
#     labels = [ {'id':s.id,'labels':[ {"id":l.id, "stock_id":l.stock_id , "value":l.value} for l in project_dao.find_stock_labels(s.id) ]}  for s in stocks ]
#     return labels

# def parse_txtlabels(project, labels):
#     """ parse and replace all the labels by these ones. taking multiple columns (rows) """
#     lines = labels.split('\n')
#     lines = [line for line in lines if not line.startswith('#')]
#     labelstocks_with_labels =  [line.split(',') for line in lines]
#     stocks = project_dao.set_stock_and_labels(project, labelstocks_with_labels)
#     labels = [ {'id':s.id,'labels':[ {"id":l.id, "stock_id":l.stock_id , "value":l.value} for l in project_dao.find_stock_labels(s.id) ]}  for s in stocks ]
#     return labels

def change_show_all_trees(project_name, value):
    """ set show all trees and return the new project  """
    project = project_dao.set_show_all_trees(project_name, value)
    return project

def change_visibility(project_name, value):
    """ set a project to private and return the new project  """
    value = int(value)
    project = project_dao.set_visibility(project_name, value)
    return project

def change_description(project_name, value):
    """ set a project description and return the new project  """
    project = project_dao.set_description(project_name, value)
    return project

def change_image(project_name, value):
    """ set a project image (blob base64) and return the new project  """
    project = project_dao.set_image(project_name, value)
    return project

def add_default_user_tree(project, user_id, username, robot=False):
    """ add a default user tree """
    if robot:
        project_dao.add_defaultusertree_robot(project, username, True )
    else: 
        user = user_dao.find_by_id(user_id)
        print(user.as_json())
        project_dao.add_defaultusertree(project, user_id, user.username)

def remove_default_user_tree(dut_id):
    """ remove a default user tree """
    project_dao.delete_defaultusertree_by_id(dut_id)

def get_hub_summary():
    """ summary version for the hub. lighter. """
    projects_info = {'difference': False, 'projects': list()}
    projects = Project.query.all()
    reply = grew_request('getProjects', current_app)
    # print(123123,reply)
    if not reply: return projects_info
    data = json.loads(reply)['data']
    grewnames = set([project['name'] for project in data] )
    dbnames = set([project.projectname for project in projects] )
    common = grewnames & dbnames
    if len(grewnames ^ dbnames) > 0: projects_info['difference'] = True
    for project in projects:
        if project.projectname not in common: continue
        admins = [a.userid for a in project_dao.get_admins(project.id)]
        guests = [g.userid for g in project_dao.get_guests(project.id)]
        projectJson = project.as_json(include={"admins":admins,"guests":guests})
        
        for p in data: 
            if p['name'] == project.projectname: 
                projectJson['number_sentences'] = p['number_sentences']
                projectJson['number_samples'] = p['number_samples']
                projectJson['number_tokens'] = p['number_tokens']
                projectJson['number_trees'] = p['number_trees']
        projects_info['projects'].append(projectJson)
    return projects_info


def get_infos(project_name, current_user):
    ''' get project informations available for the current user '''
    project = project_dao.find_by_name(project_name)
    # current_user.id = "rinema56@gmail.com"
    if not current_user.is_authenticated: # TODO : handle anonymous user
        # print("Anonymous User ")
        roles = []
    else:
        roles = project_dao.get_roles(project.id, current_user.id)

    # if not roles and project.is_private: return 403 # removed for now -> the check is done in view and for each actions

    print(time.monotonic(), 'admins START')
    admins = [a.userid for a in project_dao.get_admins(project.id)]
    guests = [g.userid for g in project_dao.get_guests(project.id)]
    print(time.monotonic(), 'admins DONE')

    # config
    shown_features = project_dao.find_project_features(project)
    shown_metafeatures = project_dao.find_project_metafeatures(project)
    config = {"shownfeatures":shown_features, "shownmeta":shown_metafeatures}
    
    reply = grew_request ( 'getSamples', current_app, data = {'project_id': project.projectname} )
    js = json.loads(reply)
    data = js.get("data")
    samples=[]
    nb_samples=0
    nb_sentences=0
    sum_nb_tokens=0
    average_tokens_per_sample=0
    # print("type visibility", project.visibility)
    if data:
        nb_samples = len(data)
        samples = []
        sample_lengths = []
        print(time.monotonic(), 'big for START')
        for sa in data:
            sample={'samplename':sa['name'], 'sentences':sa['number_sentences'], 'number_trees':sa['number_trees'], 'tokens':sa['number_tokens'], 'treesFrom':sa['users'], "roles":{}}
            lengths = []
            for r,label in project_dao.get_possible_roles():
                role = db.session.query(User, SampleRole).filter(
                    User.id == SampleRole.userid).filter(
                        SampleRole.projectid==project.id).filter(
                            SampleRole.samplename==sa['name']).filter(
                                SampleRole.role==r).all()
                # sample["roles"][label] = [a.as_json() for a,b in role]
                sample["roles"][label] = [{'key':a.username,'value':a.username} for a,b in role]

            # gael : removed temporarily for request time (need to be done in grew)
            sample["exo"] = "" # dummy

            # reply = json.loads(grew_request('getConll', data={'project_id': project.projectname, 'sample_id':sa["name"]}))
            
            # if reply.get("status") == "OK":
            #     truc = reply.get("data", {})
            #     for sent_id, dico in truc.items():
            #         conll = list(dico.values())[0]
            #         t = conll3.conll2tree(conll)
            #         length = len(t)
            #         lengths.append(length)

            # sample["tokens"] = sum(lengths)
            # if len(lengths) > 0 : sample["averageSentenceLength"] = float( round( Decimal(sum(lengths)/len(lengths)) , 2) )

            # sample["exo"] = "" # TODO : create the table in the db and update it
            # # print('sample', sample)
            samples.append(sample)
            # sample_lengths += [sample["tokens"]]

        print(time.monotonic(), 'big for DONE')
        # gael : removed temporarily for request time (need to be done in grew)
        # sum_nb_tokens = sum(sample_lengths)
        # average_tokens_per_sample = sum(sample_lengths)/len(sample_lengths)

        print(time.monotonic(), 'average DONE')

        reply = grew_request('getSentIds', current_app, data={'project_id': project_name})
        js = json.loads(reply)
        data = js.get("data")
        if data: nb_sentences = len(data)

    if project.image != None: image = str(base64.b64encode(project.image))
    else: image = ''
    settings_info = { 
        "name":project.projectname, 
        "visibility":project.visibility,
        # "is_private":project.is_private, 
        # "is_open":project.is_open, 
        "description":project.description, 
        "image":image, 
        "config":config,
        "samples":samples, 
        "admins":admins,  
        "guests":guests, 
        "number_samples":nb_samples, 
        "number_sentences":nb_sentences, 
        "number_tokens":sum_nb_tokens, 
        "averageSentenceLength":average_tokens_per_sample}
    print("settings info 2", settings_info)
    return settings_info


def get_project_treesfrom(project_name):
    """ get users from treesFrom values """
    project = project_dao.find_by_name(project_name)
    reply = grew_request ( 'getSamples', current_app, data = {'project_id': project_name} )
    js = json.loads(reply)
    data = js.get("data")
    treesFrom = list()
    if data: treesFrom = [ sa['users'] for sa in data]
    treesFrom = list( set([item for sublist in treesFrom for item in sublist]) )
    if len(treesFrom) < 1: return []
    users = user_dao.find_by_usernames(treesFrom)
    d, a = {}, []
    for rowproxy in users: # rowproxy.items() returns an array like [(key0, value0), (key1, value1)]
        for column, value in rowproxy.items(): d = {**d, **{column: value}} # build up the dictionary
        a.append(d)
    r = robot_service.get_by_projectid_userlike(project.id)
    a.extend(r)
    return a

def add_sample_role(sample_role):
    ''' add a sample role '''
    project_dao.add_sample_role(sample_role)

def add_or_delete_sample_role(user, sample_name, project_name, role, delete):
    ''' create and add a new sample role, if there is an old role it is deleted'''
    p = project_dao.find_by_name(project_name)
    existing_role = project_dao.get_user_role(p.id, sample_name, user.id)
    print('existing role', existing_role)
    if existing_role: project_dao.delete_sample_role(existing_role)
    if delete: return True 
    #     print('delete')
    #     project_dao.delete_sample_role(existing_role)
    if not delete:
        new_sr = SampleRole(userid=user.id, samplename=sample_name, projectid=p.id, role=role)
        project_dao.add_sample_role(new_sr)
    return True

def create_add_sample_role(user_id, sample_name, project_id, role):
    ''' create and add a new sample role, if there is an old role it is deleted'''
    existing_role = project_dao.get_user_role(project_id, sample_name, user_id)
    if existing_role: project_dao.delete_sample_role(existing_role)
    new_sr = SampleRole(userid=user_id, samplename=sample_name, projectid=project_id, role=role)
    project_dao.add_sample_role(new_sr)

def create_empty_project(project_name, creator, project_description, project_visibility, project_showalltrees):
    ''' create an empty project '''
    new_project = grew_request('newProject', current_app, data={'project_id': project_name})
    print('new_project', new_project)
    # private = False
    # if project_private == 'true': private = True
    isopen = False
    # if project_open == 'true': isopen = True
    showalltrees = True
    if project_showalltrees == 'false': showalltrees = False
    project = Project(projectname=project_name, description=project_description, visibility=int(project_visibility), show_all_trees=showalltrees)
    print('projecttoooo', project)
    project_dao.add_project(project)
    p = project_dao.find_by_name(project_name)
    pa = ProjectAccess(userid=creator, projectid=p.id, accesslevel=2)
    project_dao.add_access(pa)
    default_features = ["FORM", "UPOS", "LEMMA", "MISC.Gloss"]
    default_metafeatures = ["text_en"]
    features = project_dao.add_features(p, default_features)
    metafeatures = project_dao.add_metafeatures(p, default_metafeatures)
    print("added the following features", features)
    print("added the following metafeatures", metafeatures)

    # what config should be sent to grew ?


def delete_sample(project_name, project_id, sample_name):
    ''' delete sample given the infos. delete it from grew and db '''
    grew_request('eraseSample', current_app, data={'project_id': project_name, 'sample_id': sample_name})
    related_sample_roles = project_dao.delete_sample_role_by_project(project_id)

def delete_sample_role(sample_role):
    ''' delete a sample role '''
    project_dao.delete_sample_role(sample_role)

def delete_sample_role_by_project(project_id):
    ''' delete a sample role by filtering a project id '''
    return project_dao.delete_sample_role_by_project(project_id)

def get_sample(sample_name, project_name, current_user):
    ''' retrieve a sample infos given the project name and sample name'''
    # p = get_infos(project_name, current_user)
    # sample = [s for s in p['samples'] if s['samplename'] == sample_name][0]
    return get_sample_roles(project_name, sample_name)
    # return sample


def get_sample_roles(project_name, sample_name):
    """ subfunc as getInfos but only to retrieve roles for a given sample (limit calculation) """
    project = project_dao.find_by_name(project_name)
    reply = json.loads( grew_request ( 'getSamples', current_app, data = {'project_id': project_name} ) )
    data = reply.get("data")
    sample={'samplename':sample_name, "roles":{}}
    if data:
        for sa in data:
            if sa['name'] == sample_name:
                for r,label in project_dao.get_possible_roles():
                    role = db.session.query(User, SampleRole).filter(
                        User.id == SampleRole.userid).filter(
                            SampleRole.projectid==project.id).filter(
                                SampleRole.samplename==sa['name']).filter(
                                    SampleRole.role==r).all()
                    sample["roles"][label] = [{'key':a.username,'value':a.username} for a,b in role]
    return sample


def get_samples(project_name):
    ''' get existing samples for a project. from Grew.'''
    reply = grew_request ('getSamples', current_app, data = {'project_id': project_name}	)
    js = json.loads(reply)
    data = js.get("data")
    if data: return [sa['name'] for sa in data]
    else: return []

def get_samples_roles(project_id, sample_name, json=False):
    ''' returns the samples roles for the given sample in the given project. can be returned in a json format '''
    sampleroles = SampleRole.query.filter_by(projectid=project_id, samplename=sample_name).all()
    if json: return {sr.userid:sr.role.value for sr in sampleroles}
    else: return sampleroles

def get_user_sample_role(project_id, sample_name, user_id):
    """ return the current user sample role """
    return project_dao.get_user_role(project_id, sample_name, user_id)

def is_annotator(project_id, sample_name, user_id):
    """ return true is the user is an annotatror for this project sample """
    sr = project_dao.get_user_role(project_id, sample_name, user_id)
    if sr == None: return False
    elif sr.role == 1: return True
    else : return False

def is_validator(project_id, sample_name, user_id):
    """ return true is the user is a validator for this project sample """
    sr = project_dao.get_user_role(project_id, sample_name, user_id)
    if sr == None: return False
    elif sr.role == 2: return True
    else : return False

def get_possible_roles():
    return project_dao.get_possible_roles()

def samples2trees(samples, sample_name):
    ''' transforms a list of samples into a trees object '''
    trees={}
    for sentId, users in samples.items():	
        for userId, conll in users.items():
            tree = conll3.conll2tree(conll)
            if sentId not in trees: trees[sentId] = {"samplename":sample_name ,"sentence":tree.sentence(), "conlls": {}, "matches":{}}
            trees[sentId]["conlls"][userId] = conll
    return trees

def samples2trees_with_restrictions(samples, sample_name, current_user, project_name):
    ''' transforms a list of samples into a trees object and restrict it to user trees and default tree(s) '''
    trees={}
    p = project_dao.find_by_name(project_name)
    default_user_trees_ids = [dut.username for dut in project_dao.find_default_user_trees(p.id)]

    default_usernames = list()
    default_usernames = default_user_trees_ids
    # if len(default_user_trees_ids) > 0: default_usernames = user_dao.find_username_by_ids(default_user_trees_ids)
    if current_user.username not in default_usernames: default_usernames.append(current_user.username)
    for sentId, users in samples.items():	
        filtered_users = { username: users[username] for username in default_usernames  if username in users}
        for userId, conll in filtered_users.items():
            tree = conll3.conll2tree(conll)
            if sentId not in trees: trees[sentId] = {"samplename":sample_name ,"sentence":tree.sentence(), "conlls": {}, "matches":{}}
            trees[sentId]["conlls"][userId] = conll
    return trees

def add_or_keep_timestamps(conll_file):
    ''' adds a timestamp on the tree if there is not one '''
    # TODO : do this more efficiently
    tmpfile = os.path.join(Config.UPLOAD_FOLDER, "tmp.conllu")
    trees = conll3.conllFile2trees(conll_file)
    for t in trees:
        if t.sentencefeatures.get("timestamp"):
            continue
        else:
            now = datetime.now()
            # int  millisecondes
            timestamp = datetime.timestamp(now) * 1000
            timestamp = round(timestamp)
            print(timestamp, type(timestamp))
            t.sentencefeatures["timestamp"] = str(timestamp)
        # TODO check format of the conll while we're at it ?

    conll3.trees2conllFile(trees, tmpfile)
    return tmpfile


def upload_sample(fileobject, project_name, import_user, reextensions=None, existing_samples=[]):
    ''' 
    upload sample into grew and filesystem (upload-folder, see Config). need a file object from request
    Will compile reextensions if no one is specified (better specify it before a loop)
    '''
    print('upload_sample service')

    if reextensions == None : reextensions = re.compile(r'\.(conll(u|\d+)?|txt|tsv|csv)$')

    filename = secure_filename(fileobject.filename)
    sample_name = reextensions.sub("", filename)
    # print("sampleName: ", sample_name)

    # writing file to upload folder
    fileobject.save(os.path.join(Config.UPLOAD_FOLDER, filename))

    if sample_name not in existing_samples:
        # create a new sample in the grew project
        print ('========== [newSample]')
        reply = grew_request ('newSample', current_app, data={'project_id': project_name, 'sample_id': sample_name })
        print ('reply = ', reply)

    else:
        print("/!\ sample already exists")

    # timestamping if needed
    tmpfile = add_or_keep_timestamps(os.path.join(Config.UPLOAD_FOLDER, filename))

    with open(tmpfile, 'rb') as inf:
        print ('========== [saveConll]')
        if import_user:
            reply = grew_request (
                'saveConll', current_app,
                data = {'project_id': project_name, 'sample_id': sample_name, "user_id": import_user},
                files={'conll_file': inf},
            )
        else: # if no import_user has been provided, it should be in the conll metadata
            reply = grew_request (
                'saveConll', current_app,
                data = {'project_id': project_name, 'sample_id': sample_name},
                files={'conll_file': inf},
            )
    print('REPLY S+TATIUUUSS', reply)
    reply = json.loads(reply)
    print('REPLY S+TATIUUUSS', reply)
    if reply.get("status") == "OK":
        return 200, sample_name+" saved successfully on Grew"
    else:
        mes = reply.get('data',{}).get('message','')
        if not mes: mes = 'unknown problem'
        li = reply.get('data',{}).get('line','')
        if li: li=' line '+str(li)
        else: li=''
        return 400, sample_name+" caused a problem: "+mes+li
        # abort(400)


def get_timestamp(conll):
    t = re.search("# timestamp = (\d+(?:\.\d+)?)\n", conll).groups()
    if t:
        return t[0]
    else:
        return False

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

def get_last_user(tree):
    timestamps = [(user, get_timestamp(conll)) for (user, conll) in tree.items()]
    if len(timestamps) == 1:
        last = timestamps[0][0]
    else:
        last = sorted([u for (u, t) in timestamps], key=lambda x: x[1])[-1]
    return last

def sampletree2contentfile(tree):
    if isinstance( tree, str ): tree = json.loads(tree)
    usertrees = dict()
    for sentId in tree.keys():
        for user, conll in tree[sentId]['conlls'].items():
            if user not in usertrees: usertrees[user] = list()
            usertrees[user].append(conll)
    for user, content in usertrees.items(): usertrees[user] = '\n'.join(usertrees[user])
    return usertrees

def contentfiles2zip(samplenames, sampletrees):
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for samplename, sample in zip(samplenames, sampletrees):
            for fuser, filecontent in sample.items():
                data = zipfile.ZipInfo('{}.{}.conllu'.format(samplename, fuser) )
                data.date_time = time.localtime(time.time())[:6]
                data.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(data, filecontent)
    memory_file.seek(0)
    return memory_file

# def formatTrees(m, trees, conll, user_id):
# 	'''
# 	m is the query result from grew
# 	list of trees
# 	'''
# 	nodes = []
# 	for k in m['nodes'].values():
# 		nodes +=[k.split("_")[-1]]

# 	edges = []
# 	for k in m['edges'].values():
# 		edges +=[k.split("_")[-1]]

# 	if m["sent_id"] not in trees:
# 		t = conll3.conll2tree(conll)
# 		s = t.sentence()
# 		trees[m["sent_id"]] = {"samplename":m['sample_id'] ,"sentence":s, "conlls":{user_id:conll},"matches":{user_id:{"edges":edges,"nodes":nodes}}}
# 	else:
# 		trees[m["sent_id"]]["conlls"][user_id]=conll
# 		trees[m["sent_id"]]["matches"][user_id]={"edges":edges,"nodes":nodes}
    
# 	return trees
        

# def formatTrees_user(m, trees, conll):
# 	'''
# 	m is the query result from grew
# 	list of trees
# 	'''
# 	nodes = m["nodes"]
# 	edges = m["edges"]
# 	user_id = m["user_id"]


# 	if m["sent_id"] not in trees:
# 		t = conll3.conll2tree(conll)
# 		s = t.sentence()
# 		trees[m["sent_id"]] = {"sentence":s, "conlls":{user_id:conll},"matches":{user_id:{"edges":edges,"nodes":nodes}}}
# 	else:
# 		trees[m["sent_id"]]["conlls"].update(user_id=conll)
# 		trees[m["sent_id"]]["matches"].update(user_id={"edges":edges,"nodes":nodes})
    
# 	return trees


def formatTrees_new(m, trees, conll):
    '''
    m is the query result from grew
    list of trees
    returns something like {'WAZL_15_MC-Abi_MG': {'WAZL_15_MC-Abi_MG__8': {'sentence': '# kalapotedly < you see < # ehn ...', 'conlls': {'kimgerdes': ...
    '''
    nodes = m["nodes"]
    edges = m["edges"]
    user_id = m["user_id"]
    sample_name = m["sample_id"]
    sent_id = m["sent_id"]

    if sample_name not in trees:
        trees[sample_name] = {}


    if sent_id not in trees[sample_name]:
        t = conll3.conll2tree(conll)
        s = t.sentence()
        trees[sample_name][sent_id] = {"sentence":s, "conlls":{user_id:conll},"matches":{user_id:[{"edges":edges,"nodes":nodes}]}}
    else:
        trees[sample_name][sent_id]["conlls"][user_id] = conll
        # /!\ there can be more than a single match for a same sample, sentence, user so it has to be a list
        # example [{'edges': {}, 'nodes': {'GOV': '1', 'DEP': '2'}}, {'edges': {}, 'nodes': {'GOV': '5', 'DEP': '7'}}]
        trees[sample_name][sent_id]["matches"][user_id] = trees[sample_name][sent_id]["matches"].get(user_id, [])+[{"edges":edges,"nodes":nodes}]
    # print(trees[sample_name][sent_id]["matches"])
    return trees
        

def servTreeToOutputs(tree):
    ''' ? TODO : ???? '''
    return None

def update_features(project, updated_features):
    shownfeatures = project_dao.find_project_features(project)
    # deleting old ones
    for f in shownfeatures:
        if f not in updated_features:
            project_dao.remove_feature(project, f)
    
    # adding missing ones
    for f in updated_features:
        to_add = []
        if not Feature.query.filter_by(project_id=project.id, value=f).first():
            to_add.append(f)
        project_dao.add_features(project, to_add)

    return project_dao.find_project_features(project)

def update_metafeatures(project, updated_features):
    shownmeta = project_dao.find_project_metafeatures(project)
    # deleting old ones
    for f in shownmeta:
        if f not in updated_features:
            print(f, "to remove")
            project_dao.remove_metafeature(project, f)
    
    # adding missing ones
    for f in updated_features:
        to_add = []
        if not MetaFeature.query.filter_by(project_id=project.id, value=f).first():
            to_add.append(f)
        project_dao.add_metafeatures(project, to_add)

    return project_dao.find_project_metafeatures(project)
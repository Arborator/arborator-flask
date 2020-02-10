import os, json, zipfile, time, io
from ..models.models import *
from ...config import Config
from ..utils.conll3 import conll3
from ..utils.grew_utils import grew_request, upload_project
from ..repository import project_dao, user_dao
from werkzeug import secure_filename
from datetime import datetime
from flask import abort
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
    grew_request('eraseProject', data={'project_id': p.projectname})

def delete(project):
    ''' delete the given project from db and grew '''
    project_dao.delete(project)
    grew_request('eraseProject', data={'project_id': project.projectname})

def get_settings_infos(project_name, current_user):
    ''' get project informations without any samples '''
    project = project_dao.find_by_name(project_name)
    if not current_user.is_authenticated: # TODO : handle anonymous user
        roles = []
    else: roles = project_dao.get_roles(project.id, current_user.id)
    # if not roles and project.is_private: return 403 # removed for now -> the check is done in view and for each actions
    admins = [a.userid for a in project_dao.get_admins(project.id)]
    guests = [g.userid for g in project_dao.get_guests(project.id)]
    cats = [c.value for c in project_dao.find_project_cats(project.id)]
    stocks = project_dao.find_project_stocks(project.id)
    labels = [ {'id':s.id,'labels':[ {"id":l.id, "stock_id":l.stock_id , "value":l.value} for l in project_dao.find_stock_labels(s.id) ]}  for s in stocks ]
    defaultUserTrees = [u.as_json() for u in project_dao.find_default_user_trees(project.id)]
    if project.image != None: image = str(base64.b64encode(project.image))
    else: image = ''
    return { "name":project.projectname, "is_private":project.is_private, "description":project.description, "image":image, "admins":admins, "guests":guests, "cats":cats, "labels":labels, "is_open":project.is_open, "show_all_trees":project.show_all_trees, "default_user_trees":defaultUserTrees}


def add_cat_label(project_name, current_user, cat):
    """ add a cat to a project """
    return [c.value for c in project_dao.add_cat(project_name, cat)]

def remove_cat_label(project_name, current_user, cat):
    """ delete a cat from a project cats list """
    return [c.value for c in project_dao.delete_cat(project_name, cat)]

def parse_txtcats(project, cats):
    """ parse and replace all the cats by these ones """
    lines = cats.split('\n')
    lines = [line for line in lines if not line.startswith('#')]
    categories = lines[0].split(',')
    return [c.value for c in project_dao.set_cats(project, categories)]

def add_stock(project_name):
    """ add a stock """
    stocks = project_dao.add_stock(project_name)
    labels = [ {'id':s.id,'labels':[ {"id":l.id, "stock_id":l.stock_id , "value":l.value} for l in project_dao.find_stock_labels(s.id) ]}  for s in stocks ]
    return labels

def remove_stock(project_name, stockid):
    """ remove a stock """
    stocks = project_dao.delete_stock(project_name, stockid)
    labels = [ {'id':s.id,'labels':[ {"id":l.id, "stock_id":l.stock_id , "value":l.value} for l in project_dao.find_stock_labels(s.id) ]}  for s in stocks ]
    return labels

def add_label(project_name, stock_id, label):
    """ add a label to a project stock """
    stocks = project_dao.add_label(project_name, stock_id, label)
    labels = [ {'id':s.id,'labels':[ {"id":l.id, "stock_id":l.stock_id , "value":l.value} for l in project_dao.find_stock_labels(s.id) ]}  for s in stocks ]
    return labels

def remove_label(project_name, label_id, stock_id, label ):
    """ remove a label from its project stock """
    # stocks = project_dao.delete_label(project_name, stock_id, label)
    project_dao.delete_label_by_id(label_id)
    project = project_dao.find_by_name(project_name)
    stocks = project_dao.find_project_stocks(project.id)
    labels = [ {'id':s.id,'labels':[ {"id":l.id, "stock_id":l.stock_id , "value":l.value} for l in project_dao.find_stock_labels(s.id) ]}  for s in stocks ]
    return labels

def parse_txtlabels(project, labels):
    """ parse and replace all the labels by these ones. taking multiple columns (rows) """
    lines = labels.split('\n')
    lines = [line for line in lines if not line.startswith('#')]
    labelstocks_with_labels =  [line.split(',') for line in lines]
    stocks = project_dao.set_stock_and_labels(project, labelstocks_with_labels)
    labels = [ {'id':s.id,'labels':[ {"id":l.id, "stock_id":l.stock_id , "value":l.value} for l in project_dao.find_stock_labels(s.id) ]}  for s in stocks ]
    return labels

def change_show_all_trees(project_name, value):
    """ set show all trees and return the new project  """
    project = project_dao.set_show_all_trees(project_name, value)
    return project

def change_is_open(project_name, value):
    """ set is open and return the new project  """
    project = project_dao.set_is_open(project_name, value)
    return project

def add_default_user_tree(project, user_id):
    """ add a default user tree """
    project_dao.add_defaultusertree(project, user_id)

def remove_default_user_tree(dut_id):
    """ remove a default user tree """
    project_dao.delete_defaultusertree_by_id(dut_id)

def get_hub_summary():
    """ summary version for the hub. lighter. """
    projects_info = list()
    projects = Project.query.all()
    for project in projects:
        admins = [a.userid for a in project_dao.get_admins(project.id)]
        guests = [g.userid for g in project_dao.get_guests(project.id)]
        projects_info.append(project.as_json(include={"admins":[],"guests":[]}))
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
        print(time.monotonic(), 'big for START')
        for sa in data:
            sample={'samplename':sa['name'], 'sentences':sa['size'], 'treesFrom':sa['users'], "roles":{}}
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
            sample["tokens"] = 0 # dummy

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

        reply = grew_request('getSentIds', data={'project_id': project_name})
        js = json.loads(reply)
        data = js.get("data")
        if data: nb_sentences = len(data)

    if project.image != None: image = str(base64.b64encode(project.image))
    else: image = ''
    return { "name":project.projectname, "is_private":project.is_private, "description":project.description, "image":image, "samples":samples, "admins":admins,  "guests":guests, "number_samples":nb_samples, "number_sentences":nb_sentences, "number_tokens":sum_nb_tokens, "averageSentenceLength":average_tokens_per_sample}


def get_project_treesfrom(project_name):
    """ get users from treesFrom values """
    project = project_dao.find_by_name(project_name)
    reply = grew_request ( 'getSamples', data = {'project_id': project_name} )
    js = json.loads(reply)
    data = js.get("data")
    treesFrom = list()
    if data: treesFrom = [ sa['users'] for sa in data]
    treesFrom = list( set([item for sublist in treesFrom for item in sublist]) )
    if len(treesFrom) < 1: return []
    users = user_dao.find_by_usernames(treesFrom)
    d, a = {}, []
    for rowproxy in users:
        # rowproxy.items() returns an array like [(key0, value0), (key1, value1)]
        for column, value in rowproxy.items():
            # build up the dictionary
            d = {**d, **{column: value}}
        a.append(d)
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

def create_empty_project(project_name, creator, project_description, project_private, project_open, project_showalltrees):
    ''' create an empty project '''
    new_project = grew_request('newProject', data={'project_id': project_name})
    print('new_project', new_project)
    private = False
    if project_private == 'true': private = True
    isopen = False
    if project_open == 'true': isopen = True
    showalltrees = True
    if project_showalltrees == 'false': showalltrees = False
    project = Project(projectname=project_name, description=project_description, is_private=private, is_open=isopen, show_all_trees=showalltrees)
    print('projecttoooo', project)
    project_dao.add_project(project)
    p = project_dao.find_by_name(project_name)
    pa = ProjectAccess(userid=creator, projectid=p.id, accesslevel=2)
    project_dao.add_access(pa)


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

def get_sample(sample_name, project_name, current_user):
    ''' retrieve a sample infos given the project name and sample name'''
    # p = get_infos(project_name, current_user)
    # sample = [s for s in p['samples'] if s['samplename'] == sample_name][0]
    return get_sample_roles(project_name, sample_name)
    # return sample


def get_sample_roles(project_name, sample_name):
    """ subfunc as getInfos but only to retrieve roles for a given sample (limit calculation) """
    project = project_dao.find_by_name(project_name)
    reply = json.loads( grew_request ( 'getSamples', data = {'project_id': project_name} ) )
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
    default_user_trees_ids = [dut.user_id for dut in project_dao.find_default_user_trees(p.id)]

    default_usernames = list()
    if len(default_user_trees_ids) > 0: default_usernames = user_dao.find_username_by_ids(default_user_trees_ids)
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
            timestamp = datetime.timestamp(now)
            t.sentencefeatures["timestamp"] = str(timestamp)
        # TODO check format of the conll while we're at it ?

    conll3.trees2conllFile(trees, tmpfile)
    return tmpfile


def upload_project(fileobject, project_name, import_user, reextensions=None, existing_samples=[]):
    ''' 
    upload project into grew and filesystem (upload-folder, see Config). need a file object from request
    Will compile reextensions if no one is specified (better specify it before a loop)
    '''
    print('upload_project service')

    if reextensions == None : reextensions = re.compile(r'\.(conll(u|\d+)?|txt|tsv|csv)$')

    filename = secure_filename(fileobject.filename)
    sample_name = reextensions.sub("", filename)
    # print("sampleName: ", sample_name)

    # writing file to upload folder
    fileobject.save(os.path.join(Config.UPLOAD_FOLDER, filename))

    if sample_name not in existing_samples:
        # create a new sample in the grew project
        print ('========== [newSample]')
        reply = grew_request ('newSample', data={'project_id': project_name, 'sample_id': sample_name })
        print ('reply = ', reply)

    else:
        print("/!\ sample already exists")

    # timestamping if needed
    tmpfile = add_or_keep_timestamps(os.path.join(Config.UPLOAD_FOLDER, filename))

    with open(tmpfile, 'rb') as inf:
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
    reply = json.loads(reply)
    if reply.get("status") != "OK":
        abort(400)

def get_timestamp(conll):
    t = re.search("# timestamp = (\d+\.\d+)\n", conll).groups()
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
                data = zipfile.ZipInfo('{}.{}.conll'.format(samplename, fuser) )
                data.date_time = time.localtime(time.time())[:6]
                data.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(data, filecontent)
    memory_file.seek(0)
    return memory_file

def formatTrees(m, trees, conll, user_id):
    '''
    m is the query result from grew
    list of trees
    '''
    nodes = []
    for k in m['nodes'].values():
        nodes +=[k.split("_")[-1]]

    edges = []
    for k in m['edges'].values():
        edges +=[k.split("_")[-1]]

    if m["sent_id"] not in trees:
        t = conll3.conll2tree(conll)
        s = t.sentence()
        trees[m["sent_id"]] = {"samplename":m['sample_id'] ,"sentence":s, "conlls":{user_id:conll},"matches":{user_id:{"edges":edges,"nodes":nodes}}}
    else:
        trees[m["sent_id"]]["conlls"][user_id]=conll
        trees[m["sent_id"]]["matches"][user_id]={"edges":edges,"nodes":nodes}
    
    return trees
		

def formatTrees_user(m, trees, conll):
    '''
    m is the query result from grew
    list of trees
    '''
    nodes = m["nodes"]
    edges = m["edges"]
    user_id = m["user_id"]


    if m["sent_id"] not in trees:
        t = conll3.conll2tree(conll)
        s = t.sentence()
        trees[m["sent_id"]] = {"sentence":s, "conlls":{user_id:conll},"matches":{user_id:{"edges":edges,"nodes":nodes}}}
    else:
        trees[m["sent_id"]]["conlls"].update(user_id=conll)
        trees[m["sent_id"]]["matches"].update(user_id={"edges":edges,"nodes":nodes})
    
    return trees
		

def servTreeToOutputs(tree):
    ''' ? TODO : ???? '''
    return None
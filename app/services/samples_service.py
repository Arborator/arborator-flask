import json

from flask import current_app

from ..models.models import SampleExerciseLevel
from ..repository import samples_dao, project_dao
from ..utils.grew_utils import grew_request




def get_project_samples(project_name):
    print("KK project_name", project_name)
    project = project_dao.find_by_name(project_name)
    reply = grew_request('getSamples', current_app, data = {'project_id': project_name} )
    js = json.loads(reply)
    data = js.get("data")
    samples=[]
    if data:
        for sa in data:
            sample={'samplename':sa['name'], 'sentences':sa['number_sentences'], 'number_trees':sa['number_trees'], 'tokens':sa['number_tokens'], 'treesFrom':sa['users'], "roles":{}}
            sample["roles"] = project_dao.get_sample_roles(project.id, sa['name'])
            sample["exerciseLevel"] = samples_dao.get_sample_exercise_level(sa['name'], project.id).exercise_level.code or 4
            samples.append(sample)
    return samples


def get_sample_exercise_level(sample_name, project_id):
    sample_exercise_level = samples_dao.get_sample_exercise_level(sample_name, project_id)
    return sample_exercise_level


def create_or_update_sample_exercise_level(sample_name, project_id, new_exercise_level):
    sample_exercise_level = samples_dao.get_sample_exercise_level(sample_name, project_id)
    if not sample_exercise_level:
        sample_exercise_level = samples_dao.create_sample_exercise_level(sample_name, project_id, new_exercise_level)
    else:
        sample_exercise_level = samples_dao.update_sample_exercise_level(sample_name, project_id, new_exercise_level)
    
    return sample_exercise_level
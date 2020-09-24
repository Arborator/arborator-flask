from ..models.models import SampleExerciseLevel, db
from ..repository import project_dao



def create_sample_exercise_level(sample_name, project_id, exercise_level):
    """ add a sample exercise level into db """
    sample_exercise_level = SampleExerciseLevel(sample_name = sample_name, project_id = project_id, exercise_level = exercise_level)
    db.session.add(sample_exercise_level)
    db.session.commit()
    return sample_exercise_level

def get_sample_exercise_level(sample_name, project_id):
    sample_exercise_level = SampleExerciseLevel.query.filter_by(sample_name=sample_name, project_id=project_id).first()
    return sample_exercise_level

def update_sample_exercise_level(sample_name, project_id, new_exercise_level):
    sample_exercise_level = get_sample_exercise_level(sample_name, project_id)
    sample_exercise_level.exercise_level = new_exercise_level
    db.session.commit()

    return sample_exercise_level

# def add_sample_exercise_level(sample_name, project_id, exercise_level):
#     sample_exercise_level = project_dao.add_sample_exercise_level(sample_name, project_id, exercise_level)
#     return sample_exercise_level

# def delete_sample_exercise_level(sample_name, project_id, exercise_level):
#     sample_exercise_level = project_dao.add_sample_exercise_level(sample_name, project_id, exercise_level)
#     return 1

# def update_sample_exercise_level(sample_name, project_id, exercise_level):
#     sample_exercise_level = project_dao.add_sample_exercise_level(sample_name, project_id, exercise_level)
#     return sample_exercise_level
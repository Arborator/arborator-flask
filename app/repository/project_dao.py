
def get_access(project_id, user_id):
    """ get the project access level, can be false if there is not project   """
    return ProjectAccess.query.filter_by(projectid=project_id, userid=user_id).first()
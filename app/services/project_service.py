# local imports
from ..models.models import *
from ...grew_server.test.test_server import send_request as grew_request
from ...config import Config
from ..repository import project_dao

def get_project_access(project_id, user_id):
    ''' return the project access level given a project id and user id. returns 0 if the projject access is false '''
    project_access = project_dao.get_project_access(project_id, user_id)
    # if no access links this project and user, the user is a guest
    if not project_access: return 0
    return project_access.access_level




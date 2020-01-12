from ..models.models import *
from ..utils.grew_utils import grew_request, upload_project
from ...config import Config
from ..utils.conll3 import conll3
from ..repository import user_dao

def get_by_id(user_id):
    return user_dao.find_by_id(user_id)

def get_by_username(user_name):
    return user_dao.find_by_name(user_name)
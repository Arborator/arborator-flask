from ..models.models import *
from ...grew_server.test.test_server import send_request as grew_request
from ...config import Config
from ..utils.conll3 import conll3
from ..repository import user_dao

def get_by_id(user_id):
    return user_dao.find_by_id(user_id)
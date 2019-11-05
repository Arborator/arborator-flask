from flask_login import login_required, current_user
from ..models.models import *

def find_by_id(user_id):
    ''' find a user by its id and return the first match '''
    return User.query.filter_by(id=user_id).first()
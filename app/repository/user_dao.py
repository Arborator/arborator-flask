from flask_login import login_required, current_user
from ..models.models import *
from ...app import db, login_manager #prod
from sqlalchemy import text

def find_by_id(user_id):
    ''' find a user by its id and return the first match '''
    return User.query.filter_by(id=user_id).first()

def find_by_ids(list_of_ids):
    ''' find multiple users at once given a list of user_id '''
    req = "SELECT * FROM users WHERE "
    where = ' OR '.join(["id = '{}'".format(i) for i in list_of_ids])
    sql = text(req+where)
    result = db.engine.execute(sql)
    return result

def find_username_by_ids(list_of_ids):
    ''' find multiple usernames at once given a list of user_id '''
    req = "SELECT username FROM users WHERE "
    where = ' OR '.join(["id = '{}'".format(i) for i in list_of_ids])
    print('ids', list_of_ids)
    print('req', req, 'where', where)
    print(req+where)
    sql = text(req+where)
    result = db.engine.execute(sql)
    return [ row.username for row in result ]

def find_by_usernames(list_of_usernames):
    ''' find by usernames '''
    req = "SELECT * FROM users WHERE "
    where = ' OR '.join(["username = '{}'".format(i) for i in list_of_usernames])
    sql = text(req+where)
    result = db.engine.execute(sql)
    return result

def find_by_name(user_name):
    ''' find a user by its username (supposed to be unique)and return the first match '''
    return User.query.filter_by(username=user_name).first()
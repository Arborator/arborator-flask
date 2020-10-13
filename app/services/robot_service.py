import os
import json
import zipfile
import time
import io
from ..models.models import *
from ..repository import project_dao, user_dao, robot_dao


def create_or_get_robot_for_project(name, projectid):
    ''' create or retireve robot for a given project '''
    r = robot_dao.find_by_name_and_projectid(name, projectid)
    if r:
        return r
    else:
        return robot_dao.add(name, projectid)


def get_by_name_and_projectid(name, projectid):
    ''' get a robot by its name and projectid '''
    return robot_dao.find_by_name_and_projectid(name, projectid)


def get_by_projectid(projectid):
    ''' get robots linked to a project '''
    return robot_dao.find_by_projectid(projectid)


def get_by_id(id):
    ''' get by id '''
    return robot_dao.find_by_id(id)


def get_by_projectid_userlike(projectid):
    ''' get robots linked to a project '''
    robots = robot_dao.find_by_projectid(projectid)
    robots = [r.as_json(include={'auth_provider': None, 'family_name': None, 'first_name': None,
                                 'last_seen': None, 'super_admin': False, 'robot': True}) for r in robots]
    # for r in robots: r['username'] = r['name']
    return robots

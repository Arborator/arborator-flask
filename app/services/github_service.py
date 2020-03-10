import os, json, zipfile, time, io
# from ..models.models import *
from ...config import Config #prod
# from ..utils.conll3 import conll3
# from ..utils.grew_utils import grew_request, upload_project
# from ..repository import project_dao, user_dao, robot_dao
# from ..services import robot_service
# from werkzeug import secure_filename
# from datetime import datetime
# from flask import abort
# from decimal import Decimal

# # tokens for github api
import time
import jwt
import json
import requests


def app_headers():
    """
    header for communication with github api
    """
    time_since_epoch_in_seconds = int(time.time())
    payload = {
      # issued at time
      'iat': time_since_epoch_in_seconds,
      # JWT expiration time (10 minute maximum)
      'exp': time_since_epoch_in_seconds + (10 * 60),
      # GitHub App's identifier
      'iss': Config.APP_ID #arborator-grew-id
    }

    actual_jwt = jwt.encode(payload, Config.PKEY, algorithm='RS256')

    headers = {"Authorization": "Bearer {}".format(actual_jwt.decode()),
               "Accept": "application/vnd.github.machine-man-preview+json"}
    return headers


def get_token():
    app_id = Config.APP_ID
    installation_id = Config.INSTALATION_ID
    resp = requests.post('https://api.github.com/installations/{}/access_tokens'.format(installation_id),
                     headers=app_headers())
    print('Code: ', resp.status_code)
    print('Content: ', resp.content.decode())
    token = json.loads(resp.content.decode()).get("token")
    return token
from flask import Blueprint

config = Blueprint('config', __name__)

from . import controller
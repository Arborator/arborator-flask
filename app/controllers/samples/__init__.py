from flask import Blueprint

samples = Blueprint('samples', __name__)

from . import views
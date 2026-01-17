from flask import Blueprint

bp = Blueprint('settings', __name__)

from blueprints.settings import routes
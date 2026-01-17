from flask import Blueprint

bp = Blueprint('users', __name__)

from blueprints.users import routes
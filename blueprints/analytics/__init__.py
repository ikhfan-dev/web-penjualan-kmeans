from flask import Blueprint

bp = Blueprint('analytics', __name__)

from blueprints.analytics import routes
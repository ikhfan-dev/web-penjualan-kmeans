from flask import Blueprint

bp = Blueprint('segments', __name__)

from blueprints.segments import routes
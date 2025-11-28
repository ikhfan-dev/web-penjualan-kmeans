from flask import Blueprint

bp = Blueprint('promotions', __name__)

from blueprints.promotions import routes
from flask import Blueprint

bp = Blueprint('sales', __name__)

from blueprints.sales import routes
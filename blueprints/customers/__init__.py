from flask import Blueprint

bp = Blueprint('customers', __name__)

from blueprints.customers import routes
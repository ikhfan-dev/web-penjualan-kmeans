from flask import Blueprint

bp = Blueprint('products', __name__)

from blueprints.products import routes
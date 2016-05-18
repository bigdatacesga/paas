from flask import Blueprint

api = Blueprint('api', __name__)

# Import the endpoints belonging to this blueprint
from . import user_endpoints
from . import errors


@api.before_request
def before_request():
    """All routes in this blueprint require authentication."""
    pass

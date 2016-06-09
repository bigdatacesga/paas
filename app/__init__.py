import os
from flask import Flask
from flask import Blueprint
#from .decorators import restricted

app = Flask(__name__)
# Read configuration to apply from environment
config_name = os.environ.get('FLASK_CONFIG', 'production')
#config_name = os.environ.get('FLASK_CONFIG', 'testing')
#config_name = os.environ.get('FLASK_CONFIG', 'development')

# apply configuration
cfg = os.path.join(os.getcwd(), 'config', config_name + '.py')
app.config.from_pyfile(cfg)

# Create a blueprint
api = Blueprint('api', __name__)
# Import the endpoints belonging to this blueprint
from . import user_endpoints
from . import errors
from . import decorators


@api.before_request
#@decorators.restricted(role='ROLE_USER')
def before_request():
    """All routes in this blueprint require authentication."""
    response = decorators.restricted_V2(role='ROLE_USER')
    if response != None:
        return response

# register blueprints
app.register_blueprint(api, url_prefix='/bigdata/api/v1')

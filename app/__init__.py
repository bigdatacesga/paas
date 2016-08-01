import os
from flask import Flask
from flask import Blueprint

app = Flask(__name__)
# Read configuration to apply from environment
config_name = os.environ.get('FLASK_CONFIG', 'development')

# apply configuration
cfg = os.path.join(os.getcwd(), 'config', config_name + '.py')
app.config.from_pyfile(cfg)

# Create a blueprint
api = Blueprint('api', __name__)
# Import the endpoints belonging to this blueprint
from . import endpoints
from . import errors

# register blueprints
app.register_blueprint(api, url_prefix='/bigdata/api/v1')

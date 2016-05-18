import os
from flask import Flask, jsonify, g



def create_app(config_name):
    """Create an application instance."""
    app = Flask(__name__)

    # apply configuration
    cfg = os.path.join(os.getcwd(), 'config', config_name + '.py')
    app.config.from_pyfile(cfg)

    # register blueprints
    from .v1 import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/bigdata/api/v1')

    return app
from flask import jsonify
from . import api, app
import kvstore as kv
import registry


class ValidationError(ValueError):
    pass


class AuthenticationError(Exception):
    status_code = 401

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@api.errorhandler(AuthenticationError)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@api.errorhandler(ValidationError)
def bad_request(e):
    response = jsonify({'status': 400, 'error': 'bad request',
                        'message': e.args[0]})
    response.status_code = 400
    return response


@api.errorhandler(registry.InvalidOptionsError)
def invalid_instantiation_options(e):
    response = jsonify({'status': 400, 'error': 'invalid options',
                        'message': e.args[0]})
    response.status_code = 400
    return response


@api.errorhandler(kv.KeyDoesNotExist)
def key_does_not_exist(e):
    app.logger.warn('404 Error ' + e.message)
    response = jsonify({'status': 404, 'error': 'Key not found',
                        'message': e.message})
    response.status_code = 404
    return response


@api.app_errorhandler(404)  # this has to be an app-wide handler
def not_found(e):
    response = jsonify({'status': 404, 'error': 'not found',
                        'message': 'invalid resource URI'})
    response.status_code = 404
    return response


@api.errorhandler(405)
def method_not_supported(e):
    response = jsonify({'status': 405, 'error': 'method not supported',
                        'message': 'the method is not supported'})
    response.status_code = 405
    return response


@api.app_errorhandler(500)  # this has to be an app-wide handler
def internal_server_error(e):
    response = jsonify({'status': 500, 'error': 'internal server error',
                        'message': e.args[0]})
    response.status_code = 500
    return response

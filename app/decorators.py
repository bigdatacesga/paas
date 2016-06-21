import base64
import functools
import hashlib
import time
import uuid
import threading

from flask import request, make_response, g, jsonify, url_for, \
                  copy_current_request_context
from keyczar.keyczar import Crypter

from . import app

import kvstore

KEYS = app.config.get('SECRET_KEYS')
IGNORE_AUTH = app.config.get('IGNORE_AUTH')


def restricted(role='ROLE_USER'):
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('x-auth-token')

            if token is None:
                return _no_token()

            if _is_token_signature_valid(token):
                fields = token.split(':')

                username = base64.b64decode(fields[0])
                g.user = username

                passwd_encrypted = fields[1]
                crypter = Crypter.Read(KEYS)
                passwd = crypter.Decrypt(passwd_encrypted)
                g.passwd = passwd

                token_role = base64.b64decode(fields[2])
                g.role = token_role

                #expires = time.localtime(int(fields[3])/1000)
                expires = int(fields[3])/1000
            else:
                return _unauthorized()

            if token_role != role:
                return _invalid_role()

            now = time.time()
            if now > expires:
                return _expired_token()

            results = f(*args, **kwargs)
            response = make_response(results)
            return response
        return decorated
    return decorator


def _is_token_signature_valid(token):
    fields = token.split(':')
    if len(fields) != 5:
        _unauthorized()
    subject = ':'.join(fields[:4])
    secret = KEYS
    subject = subject + ':' + secret
    token_signature = fields[4]
    computed_signature = hashlib.md5(subject).hexdigest()
    return computed_signature == token_signature


def _unauthorized():
    response = jsonify({'status': 401, 'error': 'unauthorized',
                        'message': 'please provide a valid authentication token'})
    response.status_code = 401
    return response


def _invalid_role():
    response = jsonify({'status': 401, 'error': 'unauthorized',
                        'message': 'invalid role'})
    response.status_code = 401
    return response


def _expired_token():
    response = jsonify({'status': 401, 'error': 'unauthorized',
                        'message': 'token has expired'})
    response.status_code = 401
    return response


def _no_token():
    response = jsonify({'status': 401, 'error': 'unauthorized',
                        'message': 'no token has been provided'})
    response.status_code = 401
    return response

# In case authentication should be ignored we simply overwrite the decorator
if IGNORE_AUTH:
    def no_auth(role):
        def decorator(f):
            @functools.wraps(f)
            def decorated(*args, **kwargs):
                g.user = 'test'
                g.role = 'ROLE_USER'
                results = f(*args, **kwargs)
                response = make_response(results)
                return response
            return decorated
        return decorator
    restricted = no_auth


CONSUL_ENDPOINT = app.config.get('CONSUL_ENDPOINT')
kv = kvstore.Client(CONSUL_ENDPOINT)

def asynchronous(f):
    """Run the request asyncronously

    Inital response:
        - Status code 202 Accepted
        - Location header with the URL of a job resource.

    Job running:
        - A GET request to the job returns 202

    Job finished:
        - Status code 303 See Other
        - Location header points to the newly created resource

    The client then needs to send a DELETE request to the task resource to
    remove it from the system.
    """
    @functools.wraps(f)
    def decorator(*args, **kwargs):
        id = uuid.uuid4().hex
        kv.set('queue/{}/status'.format(id), 'pending')

        @copy_current_request_context
        def job():
            response = make_response(f(*args, **kwargs))
            status_code = response.status_code
            if status_code == 201:
                kv.set('queue/{}/status'.format(id), 'registered')
            else:
                kv.set('queue/{}/status'.format(id), 'error')
            kv.set('queue/{}/status_code'.format(id), status_code)
            kv.set('queue/{}/url'.format(id), response.headers['Location'])

        job = threading.Thread(target=job)
        job.start()
        return jsonify({}), 202, {
            'Location': url_for('api.get_async_job_status', id=id)}

    return decorator

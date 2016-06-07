import os

basedir = os.path.abspath(os.path.dirname(__file__))

# Secret passphrase
# FIXME: Temporarily SECRET must have the same value as SECRET_KEYS
#        due to the current spring boot implementation
SECRET = '/etc/keyczar/keys'
# Secret keyczar keys
SECRET_KEYS = '/etc/keyczar/keys'
# Fill as needed
DEBUG = False
# IGNORE_AUTH = True
# SECRET_KEY = 'admin'

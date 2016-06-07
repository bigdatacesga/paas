import os

basedir = os.path.abspath(os.path.dirname(__file__))

# Secret passphrase
# FIXME: Temporarily SECRET must have the same value as SECRET_KEYS
#        due to the current spring boot implementation
#SECRET = '/home/jonatan/Desktop/TFM/portal_keys' #'/etc/keyczar/keys'
# Secret keyczar keys
#SECRET_KEYS = '/home/jonatan/Desktop/TFM/portal_keys' #'/etc/keyczar/keys'
# Fill as needed
DEBUG = True
IGNORE_AUTH = True
# SECRET_KEY = 'admin'


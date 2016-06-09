import os

basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True
IGNORE_AUTH = True
MESOS_FRAMEWORK_ENDPOINT = 'http://127.0.0.1:5001/bigdata/mesos_framework/v1/instance'
CONSUL_ENDPOINT = 'http://consul:8500/v1/kv'

SECRET = '/etc/keyczar/keys'
SECRET_KEYS = '/etc/keyczar/keys'
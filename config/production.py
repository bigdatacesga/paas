# Secret passphrase
# FIXME: Temporarily SECRET must have the same value as SECRET_KEYS
#        due to the current spring boot implementation
SECRET = '/etc/keyczar/keys'
# Secret keyczar keys
SECRET_KEYS = '/etc/keyczar/keys'
# Fill as needed
DEBUG = False
IGNORE_AUTH = False
MESOS_FRAMEWORK_ENDPOINT = 'http://mesos_framework:5000/bigdata/mesos_framework/v1/clusters'
ORQUESTRATOR_ENDPOINT = 'http://orquestrator:5005/orquestrator/v1/clusters'
CONSUL_ENDPOINT = 'http://consul:8500/v1/kv'


# Secret passphrase
# FIXME: Temporarily SECRET must have the same value as SECRET_KEYS
#        due to the current spring boot implementation
SECRET = '/etc/keyczar/keys'
# Secret keyczar keys
SECRET_KEYS = '/etc/keyczar/keys'
# Fill as needed
DEBUG = True
IGNORE_AUTH = True
MESOS_FRAMEWORK_ENDPOINT = 'http://framework:6001/bigdata/mesos_framework/v1/clusters'
ORCHESTRATOR_ENDPOINT = 'http://orchestrator:6002/v1/clusters'
CONSUL_ENDPOINT = 'http://consul:8500/v1/kv'

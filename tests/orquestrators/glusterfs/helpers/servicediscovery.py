"""Consul Service Discovery API


Examples:
    import servicediscovery
    service = servicediscovery.Client('http://localhost:8500/v1/agent/service/register')
    service.register(id='flexlm1', name='flexlm',
                address='10.112.0.211', port=28518,
                tags=('light', 'v1'))
    service.deregister(id='flexlm1')
    service.list()
    service.info(name='flexlm')

The registration/deregistration is done using the consul agent API:
    http://localhost:8500
    PUT /v1/agent/service/register
    DELETE /v1/agent/service/deregister/<serviceId>

To query the information we use the catalog API:
    http://localhost:8500 or http://consul.service.int.cesga.es:8500
    GET /v1/catalog/services
    GET /v1/catalog/service/bigdata
    GET /v1/catalog/nodes
    GET /v1/catalog/node/c13-9

The payload for the registration request has the following format:
{
  "ID": "flexlm1",
  "Name": "flexlm",
  "Tags": ["flexlm1", "light", "v1"],
  "Address": "10.112.0.211",
  "Port": 28518,
  "Check": {
    "id": "flexlm",
    "name": "flexlm on port 28518",
    "tcp": "10.112.0.211:28518",
    "Interval": "30s",
    "timeout": "2s"
  }
}

"""

import requests

# Location of the consul service
# ENDPOINT = 'http://localhost:8500/v1/agent/service/register'


class Client(object):
    """Service Discovery Client to perform basic operations

    Examples:
        import servicediscovery
        service = servicediscovery.Client('http://localhost:8500')
        service.register(id='flexlm1', name='flexlm',
                    address='10.112.0.211', port=28518,
                    tags=('light', 'v1'))
        service.deregister(id='flexlm1')
        service.list()
        service.info(name='flexlm')

    The registration/deregistration is done using the consul agent API:
        PUT /v1/agent/service/register
        DELETE /v1/agent/service/deregister/<serviceId>
    """

    def __init__(self, endpoint='http://localhost:8500'):
        self.endpoint = endpoint
        self.url_register = '{}/{}'.format(self.endpoint, 'v1/agent/service/register')
        self.url_deregister = '{}/{}'.format(self.endpoint, 'v1/agent/service/deregister')
        self.url_services = '{}/{}'.format(self.endpoint, '/v1/catalog/services')
        self.url_service = '{}/{}'.format(self.endpoint, '/v1/catalog/service')
        self.url_nodes = '{}/{}'.format(self.endpoint, '/v1/catalog/nodes')
        self.url_node = '{}/{}'.format(self.endpoint, '/v1/catalog/node')

    def register(self, id, name, address, port=None, tags=None, check=None):
        """Register a new service with the local consul agent"""
        service = {}
        service['ID'] = id
        service['Name'] = name
        service['Address'] = address
        if port:
            service['Port'] = port
        if tags:
            service['Tags'] = tags
        if check:
            service['Check'] = check
        r = requests.put(self.url_register, json=service)
        if r.status_code != 200:
            raise ServiceDiscoveryRegistrationError(
                'PUT returned {}'.format(r.status_code))
        return r

    def deregister(self, id):
        """Deregister a service with the local consul agent"""
        r = requests.delete('{}/{}'.format(self.url_deregister, id))
        if r.status_code != 200:
            raise ServiceDiscoveryDeregistrationError(
                'DELETE returned {}'.format(r.status_code))
        return r

    def list(self):
        """List all services that have been registered"""
        r = requests.get(self.url_services)
        return r.json()

    def info(self, name):
        """Info about a given service"""
        r = requests.get('{}/{}'.format(self.url_service, name))
        return r.json()


class ServiceDiscoveryRegistrationError(Exception):
    pass


class ServiceDiscoveryDeregistrationError(Exception):
    pass

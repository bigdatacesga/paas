"""K/V Store API"""

import base64
import requests

# Location of the consul service
# Option 1: Use the local agent for better performance
#ENDPOINT = 'http://localhost:8500/v1/kv'
# Option 2: Use the address of one of the three consul servers
#ENDPOINT = 'http://10.112.0.101:8500/v1/kv'


class Client(object):
    """K/V Store Client to perform basic operations

    Examples:
        import kvstore
        kv = kvstore.Client('http://localhost:8500/v1/kv')
        kv.set(key, value)
        kv.get(key)
        kv.recurse(key)
        kv.delete(key)
        kv.delete(key, recursive=True)
        kv.index(key, recursive=True)
        kv.get(key, wait=True, index=index, wait='10m')
        kv.recurse(key, wait=True, index=index, wait='10m')
    """

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def set(self, k, v):
        """Add or update a key, value pair to the database"""
        k = k.lstrip('/')
        url = '{}/{}'.format(self.endpoint, k)
        r = requests.put(url, data=str(v))
        if r.status_code != 200 or r.json() is not True:
            raise KVStoreError('PUT returned {}'.format(r.status_code))

    def get(self, k, wait=False, wait_index=False, timeout='5m'):
        """Get the value of a given key"""
        k = k.lstrip('/')
        url = '{}/{}'.format(self.endpoint, k)
        params = {}
        if wait:
            params['index'] = wait_index
            params['wait'] = timeout
        r = requests.get(url, params=params)
        if r.status_code == 404:
            raise KeyDoesNotExist("Key " + k + " does not exist")
        if r.status_code != 200:
            raise KVStoreError('GET returned {}'.format(r.status_code))
        return base64.b64decode(r.json()[0]['Value'])

    def recurse(self, k, wait=False, wait_index=None, timeout='5m'):
        """Recursively get the tree below the given key"""
        k = k.lstrip('/')
        url = '{}/{}'.format(self.endpoint, k)
        params = {}
        params['recurse'] = 'true'
        if wait:
            params['wait'] = timeout
            if not wait_index:
                params['index'] = self.index(k, recursive=True)
            else:
                params['index'] = wait_index
        r = requests.get(url, params=params)
        if r.status_code == 404:
            raise KeyDoesNotExist("Key " + k + " does not exist")
        if r.status_code != 200:
            raise KVStoreError('GET returned {}'.format(r.status_code))
        entries = {} 
        for e in r.json():
            if e['Value']:
                entries[e['Key']] = base64.b64decode(e['Value'])
            else:
                entries[e['Key']] = ''
        return entries

    def index(self, k, recursive=False):
        """Get the current index of the key or the subtree. 
        This is needed for later creating long polling requests
        """
        k = k.lstrip('/')
        url = '{}/{}'.format(self.endpoint, k)
        params = {}
        if recursive:
            params['recurse'] = ''
        r = requests.get(url, params=params)
        return r.headers['X-Consul-Index']

    def delete(self, k, recursive=False):
        """Delete a given key or recursively delete the tree below it"""
        k = k.lstrip('/')
        url = '{}/{}'.format(self.endpoint, k)
        params = {}
        if recursive:
            params['recurse'] = ''
        r = requests.delete(url, params=params)
        if r.status_code != 200:
            raise KVStoreError('DELETE returned {}'.format(r.status_code))


class KVStoreError(Exception):
    pass


class KeyDoesNotExist(Exception):
    pass

"""Functions to simplify working with containers"""
from __future__ import print_function
import socket
import kvstore

kv = kvstore.Client('http://10.112.0.101:8500/v1/kv')

MAPPINGS = {'c13-9': 'gluster1',
            'c13-10': 'gluster2',
            'c14-9': 'gluster3',
            'c14-10': 'gluster4',
            }


def get_container_name_for(host, service, domain):
    """Generate the associated container name for the given service"""
    #return "{}-{}.{}".format(host, service, domain)
    return MAPPINGS[host]


def get_networks_for(node):
    """Get the addresses associated with a given container"""
    networks = {}
    #storage_address = socket.gethostbyname(container_name)
    storage_address = kv.get('frameworks/jlopez/gluster/3.7.11/HOME/nodes/{}/address'.format(node))
    networks['storage'] = {}
    networks['storage']['address'] = storage_address
    networks['storage']['netmask'] = 16
    networks['private'] = {}
    networks['private']['address'] = storage_address.replace('117', '112')
    networks['private']['netmask'] = 16
    networks['gateway'] = '10.112.0.1'
    return networks

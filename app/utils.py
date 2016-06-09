#import registry
from .configuration_registry import registry

def validate(data, required_fields):
    """Validate if all required_fields are in the given data dictionary"""
    if all(field in data for field in required_fields):
        return True
    return False


def trim_dn(username, version, framework, dn):
    dn = dn.replace("instances", "")
    if username is not None:
        dn = dn.replace("/{}".format(username), "")
    if version is not None:
        dn = dn.replace("/{}".format(version), "")
    if framework is not None:
        dn= dn.replace("/{}".format(framework), "")
    return dn

def print_full_instance(instance):
    """ Try to get all the info from an instance or if error, return the dn"""
    try:
        return {
            "result": "success",
            "uri": str(instance),
            "data": instance.to_dict()
        }
    except registry.KeyDoesNotExist as e:
        return {
            "result": "failure",
            "uri": str(instance),
            "message": e.message
        }


def print_instance(instance, filters):
    """ Try to get the basic info from the instance or if error, return the dn"""
    (username, service, version) = filters
    try:
        d = instance.to_dict()
        return {
            "result": "success",
            "uri": str(instance),
            "data": d
        }
    except registry.KeyDoesNotExist as e:
        return {
            "result": "failure",
            "uri": str(instance),
            "message": e.message
        }


#### TEMPRARY FIX ###
import requests
CONSUL_ENDPOINT = 'http://consul.service.int.cesga.es:8500/v1/kv'
NETWORKS_ENDPOINT = 'http://networks.service.int.cesga.es:5000/resources/networks/v1/networks'
def reserve_network_address(network, clustername, node):
    r = requests.get(NETWORKS_ENDPOINT + "/{}/addresses?{}".format(network, "free"))
    addresses = r.json()
    if addresses["number"] >= 1:
        address = addresses["addresses"][0]
    else:
        raise Exception("Can't get networks")

    r = requests.get(NETWORKS_ENDPOINT + "/{}".format(network))
    network_info = r.json()
    network_info["address"] = address

    payload = {'status': 'used', 'clustername': clustername, 'node': node}
    r = requests.put(NETWORKS_ENDPOINT + "/{}/addresses/{}".format(network, address), data=payload)
    if r.status_code != 204:
        raise Exception("Can't get network")

    return network_info


def initialize_networks(instance):
    networks_list = list()
    nodes = instance.nodes

    for node in nodes:
        networks = node.networks
        for network in networks:
            rest_network_data = reserve_network_address(network.networkname, node.clustername,
                                                        node.name)
            network_dict = dict()
            for k in rest_network_data:
                network_dict[k] = rest_network_data[k]
            network_dict['name'] = network.device
            networks_list.append(network_dict)

        # FIXME
        node.set_networks(networks_list)
        # node.networks = networks_list
import requests

CONSUL_ENDPOINT = 'http://consul.service.int.cesga.es:8500/v1/kv'
NETWORKS_ENDPOINT = 'http://networks.service.int.cesga.es:5000/resources/networks/v1/networks'


def validate(data, required_fields):
    """Validate if all required_fields are in the given data dictionary"""
    if all(field in data for field in required_fields):
        return True
    return False


def set_node_info(node, node_name=None, instance_name=None):
    node_id = instance_name + "_" + node_name
    node.node_id = node_id
    node.clustername = instance_name


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
            network_dict['name'] = network.name
            networks_list.append(network_dict)

        # FIXME
        node.set_networks(networks_list)
        # node.networks = networks_list

from .errors import ValidationError
import registry
import requests

CONSUL_ENDPOINT = 'http://consul.service.int.cesga.es:8500/v1/kv'
NETWORKS_ENDPOINT = 'http://networks.service.int.cesga.es:5000/resources/networks/v1/networks'


###########################################
# SERVICE ATTRIBUTES PARSING AND HANDLING #
###########################################

def validate(data, required_fields):
    """Validate if all required_fields are in the given data dictionary"""
    if all(field in data for field in required_fields):
        return True
    return False


def parse_post_template_data(request):
    json_dict = request.get_json()
    data = dict()
    try:
        #name, version
        data["name"] = json_dict['name'].lower()
        data["version"] = json_dict['version'].lower()

    except KeyError:
        raise ValidationError('Invalid data, values are missing.')

    return data


def set_node_info(node, node_name=None, instance_name=None):
    node_id = instance_name + "_" + node_name
    node.node_id = node_id
    node.clustername = instance_name


def set_node_dn(node_dn):
    # Initialize the registry module
    registry.connect(CONSUL_ENDPOINT)

    node = registry.Node(node_dn)
    node.node_dn = node_dn


############################
# NODE NETWORKS MANAGEMENT #
############################

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


def get_network_info(network):
    r = requests.get(NETWORKS_ENDPOINT + "/{}".format(network))
    network_info = r.json()
    network_info["address"] = ""
    return network_info


def get_network_names():
    r = requests.get(NETWORKS_ENDPOINT)
    network_names = r.json()["networks"]
    return network_names


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

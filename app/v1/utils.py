import json
from .errors import ValidationError
import registry
import kvstore as kv
import requests

# Create a global kvstore client
ENDPOINT = 'http://consul:8500/v1/kv'
client = kv.Client(ENDPOINT)

NETWORKS_ENDPOINT = 'http://networks.service.int.cesga.es:5000/resources/networks/v1/networks'
#NETWORKS_ENDPOINT = 'http://10.112.13.1:5001/resources/networks/v1/networks'

#############################################
# SERVICE CHECKING AND VALIDATION FUNCTIONS #
#############################################
def check_user(user):
    try:
        if client.get("users/{}/status".format(user)) == "active":
            return True
        else:
            return False
    except kv.KeyDoesNotExist:
        return False


def check_service(service):
    try:
        client.recurse("frameworks/{}".format(service))
    except kv.KeyDoesNotExist:
        return False
    return True


def check_flavour(service, flavour):
    try:
        client.recurse("frameworks/{}/{}".format(service, flavour))
    except kv.KeyDoesNotExist:
        return False
    return True


###########################################
# SERVICE ATTRIBUTES PARSING AND HANDLING #
###########################################
def parse_string_as_json(returned_string):
    return json.loads(returned_string)


def parse_post_data(request):
    json_dict = request.get_json()
    data = dict()
    try:
        data["service_type"] = json_dict['service_type'].lower()
        data["service_name"] = json_dict['service_name'].lower()
        data["cpu"] = json_dict['cpu']
        data["mem"] = json_dict['mem']
        data["number_of_disks"] = json_dict['num_disks']
        data["num_nodes"] = json_dict['num_nodes']
        data["clustername"] = json_dict['clustername']

    except KeyError:
            raise ValidationError('Invalid data, values are missing.')

    return data


def parse_request_parameters(request):
    # THE ORDER MATTERS, DO NOT CHANGE
    service_type = request.args.get('type', None)
    if service_type is None or service_type == "":
        return None, None, None

    service_name = request.args.get('name', None)
    if service_name is None or service_name == "":
        return service_type.lower(), None, None

    instance_id = request.args.get('id', None)
    if instance_id is None or instance_id == "":
        return service_type.lower(), service_name.lower(), None

    return service_type.lower(), service_name.lower(), instance_id.lower()


def create_url(username, service_type, service_name, instance_id):
    # THE ORDER MATTERS, DO NOT CHANGE
    recurse_bool = True
    url = "/instances/" + username
    if service_type is not None:
        url = url + "/" + service_type

    if service_name is not None:
        url = url + "/" + service_name

    if instance_id is not None:
        url = url + "/" + instance_id
        recurse_bool = False

    return recurse_bool, url


############################
# KEY/VALUE STORE HANDLING #
############################
def _get_key_first_element(key):
    return key.rstrip('/').split('/')[0]


def _get_key_last_element(key):
    return key.rstrip('/').split('/')[-1]


def _remove_key_first_element(key):
    x = ""
    for e in key.rstrip('/').split('/')[1:]:
        x += e + "/"
    return x


def treeify(d, key, value):
    first_element = _get_key_first_element(key)
    last_element = _get_key_last_element(key)
    if first_element == last_element:
        d[first_element] = value
    else:
        try:
            new_data = d[first_element]
        except KeyError:
            d[first_element] = dict()
            new_data = d[first_element]
        treeify(new_data, _remove_key_first_element(key), value)


#####################
# TEMPLATE HANDLING #
#####################
def get_instance_attributes(data):
    d = dict()
    for key in data.keys():
        v = data[key]
        if not isinstance(v, dict):
            d[key] = v
    return d


def get_framework_template(path):
    attributes = client.recurse(path)
    d = dict()
    d["node"] = dict()
    d["node"]["disk"] = dict()
    d["node"]["network"] = dict()
    d["node"]["services"] = dict()
    d["service"] = dict()
    d["service"]["node"] = dict()

    for key in attributes.keys():
        new_key = key.replace(path, "")

        # Key is from instance
        if len(new_key.split('/')) == 1 and new_key != "":
            d[new_key] = attributes[key]

        # Key is under node tree (just copy, deflate will come later)
        # Paths are checked longest-match first, greedy behaviour, beware
        elif new_key.startswith("node/network/"):
            d["node"]["network"][_get_key_last_element(new_key)] = attributes[key]
        elif new_key.startswith("node/disk/"):
            d["node"]["disk"][_get_key_last_element(new_key)] = attributes[key]
        elif new_key.startswith("node/services/"):
            d["node"]["services"][_get_key_last_element(new_key)] = attributes[key]
        elif new_key.startswith("node/"):
            d["node"][_get_key_last_element(new_key)] = attributes[key]

        # elif new_key.startswith("services/node/"):
        #    d["service"]["node"][_get_key_last_element(new_key)] = vars[key]

        # Key is under services tree (copy tree as is)
        elif new_key.startswith("services"):
            # d["service"][_get_key_last_element(new_key)] = vars[key]
            treeify(d, new_key, attributes[key])

    return d


#########################
# INSTANCE REGISTRATION #
#########################
def register_instance(data, instance_data, nodes_dict, services_dict):
    # Initialize the registry module
    registry.connect(ENDPOINT)

    # Save the instance in the key/value storage
    instance_dn = registry.register(user=data["service_username"], framework=data["service_type"],
                                    flavour=data["service_name"], nodes=nodes_dict, services=services_dict)

    # After registering the instance, an instance id will have been assigned, we can now get it
    service_full_name = \
        data["service_username"] + '-' + \
        data["service_type"] + '-' + \
        data["service_name"] + '-' + \
        instance_dn.split("/")[-1]
    instance_data["service_full_name"] = service_full_name

    # Get the recently created instance and set the attributes
    instance = registry.get_cluster_instance(dn=instance_dn)
    instance.set_attributes(instance_data)

    # Return the full path to the instance
    return instance_dn, instance_data


def set_node_info(node_dn=None, node_name=None, instance_name=None):
    # Initialize the registry module
    registry.connect(ENDPOINT)

    node_id = instance_name + "_" + node_name
    node = registry.Node(node_dn)
    node.node_id = node_id
    node.clustername = instance_name
    # node.node_dn = node_dn # Remove this line if not necessary in the future anymore


def set_node_dn(node_dn):
    # Initialize the registry module
    registry.connect(ENDPOINT)

    node = registry.Node(node_dn)
    node.node_dn = node_dn


#########################
# NODE DISKS MANAGEMENT #
#########################
def deflate_node_disks(number_of_disks, disk_data):
    disks = list()
    for i in range(int(number_of_disks)):
        disk = disk_data.copy()
        disk['name'] = "disk" + str(i + 1)
        disks.append(disk)
    return disks


def initialize_node_disks(node_dn, number_of_disks, disk_data):
    # Initialize the registry module
    registry.connect(ENDPOINT)

    node = registry.Node(node_dn)
    mesos_disks = list()
    for i in range(int(number_of_disks)):
        mesos_disk = disk_data.copy()
        mesos_disk['name'] = "disk" + str(i + 1)
        mesos_disks.append(mesos_disk)

    # FIXME
    node.set_disks(mesos_disks)
    # node.disks = mesos_disks


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


def deflate_node_networks(network_data):
    # network_names = get_network_names()
    # ips_per_net = 1
    # num_of_nets = len(network_names)
    networks = list()

    # code to be used in the future when networks are specified for every service
    # with a single call we get all the networks that are to be deployed and for each one
    # an address is added to the service nodes
    # for k in range(num_of_nets):
    #     rest_network_data = get_network_info(network_names[k])
    #     for j in range(ips_per_net):
    #         network = network_data.copy()
    #         for key in network_data:
    #             network[key] = rest_network_data[key]
    #         device_num = k * ips_per_net + j
    #         network['name'] = "eth"+str(device_num)
    #         network['device'] = "eth"+str(device_num)
    #         networks.append(network)
    #

    # Code to be removed in the future
    # ADMIN
    rest_network_data = reserve_network_address("admin", "not_supported", "not_supported")
    network = network_data.copy()
    for k in network_data:
        network[k] = rest_network_data[k]
    network['name'] = "eth0"
    network['device'] = "eth0"
    networks.append(network)

    # STORAGE
    rest_network_data = reserve_network_address("storage", "not_supported", "not_supported")
    network = network_data.copy()
    for k in network_data:
        network[k] = rest_network_data[k]
    network['name'] = "eth1"
    network['device'] = "eth1"
    networks.append(network)

    return networks

# To be removed if not needed in the near future
# def initialize_node_networks(node_dn, network_data):
#     # Initialize the registry module
#     registry.connect(ENDPOINT)
#
#     node = registry.Node(node_dn)
#
#     networks = list()
#
#     # ADMIN
#     rest_network_data = reserve_network_address("admin", node.clustername, node.name)
#     network = network_data.copy()
#     for k in network_data:
#         network[k] = rest_network_data[k]
#     network['name'] = "eth0"
#     network['device'] = "eth0"
#     networks.append(network)
#
#     # STORAGE
#     rest_network_data = reserve_network_address("storage", node.clustername, node.name)
#     network = network_data.copy()
#     for k in network_data:
#         network[k] = rest_network_data[k]
#     network['name'] = "eth1"
#     network['device'] = "eth1"
#     networks.append(network)
#
#     # FIXME
#     node.set_networks(networks)
#     # node.disks = mesos_disks




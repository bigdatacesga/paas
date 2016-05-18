import json
import registry
import kvstore as kv
import requests

from flask import Flask, abort
from flask import jsonify, request

from . import api
from . import utils as ut
from .errors import ValidationError


ENDPOINT = 'http://consul:8500/v1/kv'
MESOS_FRAMEWORK_ENDPOINT = 'http://mesos_framework.service.int.cesga.es:5000/bigdata/mesos_framework/v1/instance'
TEMPLATE_ENDPOINT = 'frameworks'
service_endp = kv.Client(ENDPOINT)
app = Flask(__name__)


@api.route('/services', methods=['GET'])
@api.route('/services/', methods=['GET'])
def get_instances_by_params():
    username = "jenes"

    (service_type, service_name, instance_id) = ut.parse_request_parameters(request)
    (recurse_bool, url) = ut.create_url(username, service_type, service_name, instance_id)
    app.logger.info('Request for service info from ' + username + " to url: " + str(url))

    try:
        instances = service_endp.recurse(url)
        return jsonify({'services': instances})
            
    except kv.KeyDoesNotExist as error:
        app.logger.info('404 Error ' + error.message)
        abort(404)


@api.route('/services/nodes/', methods=['GET'])
def get_cluster_nodes():
    username = "jenes"
    (service_type, service_name, instance_id) = ut.parse_request_parameters(request)

    if any([x is None for x in [service_type, service_name, instance_id]]):
        raise ValidationError('Params are missing')

    # In this case recurse_bool will always be false
    (recurse_bool, base_url) = ut.create_url(username, service_type, service_name, instance_id)

    registry.connect(ENDPOINT)
    instance = registry.get_cluster_instance(dn=base_url)
    nodes = instance.nodes
    node_names_list = list()
    for node in nodes:
        node_names_list.append(node.name)
    return jsonify({'nodes': node_names_list})


@api.route('/services/', methods=['DELETE'])
@api.route('/services', methods=['DELETE'])
def delete_service():
    abort(501) # Not implemented
    #
    # # username = "jenes"
    # (service_type, service_name, instance_id) = ut.parse_request_parameters(request)
    #
    # if any([x is None for x in [service_type, service_name, instance_id]]):
    #     raise ValidationError('Params are missing')
    #
    # # In this case recurse_bool will always be false
    # # recurse_bool, url = ut.create_url(username, service_type, service_name, instance_id)
    #
    # # service_endp.delete(url, recursive=True)
    #
    # return jsonify({'result': "fail", 'message': "method not implemented"})


@api.route('/services/', methods=['POST'])
def launch_service():
    username = "jenes"

    # Get data from user parameters
    data = ut.parse_post_data(request)

    # Log request
    app.logger.info("User {} wants to launch new cluster with params {}".format(username, str(data)))

    # Check that the user, service and flavour are available
    if not (ut.check_user(username) and ut.check_service(data["service_type"]) and
            ut.check_flavour(data["service_type"], data["service_name"])):
        app.logger.info("Can't launch cluster because service doesn't exist or the user is not valid")
        abort(404)

    # default node attributes data from template
    instance_template = ut.get_framework_template(
        TEMPLATE_ENDPOINT + "/{}/{}/v1/instance/".format(data["service_type"], data["service_name"]))

    instance_data = ut.get_instance_attributes(instance_template)
    node_data = instance_template["node"]
    services_dict = instance_template["services"]

    # Fill service username
    data["service_username"] = username

    # Instance info
    instance_data["cpu"] = data["num_nodes"] * data["cpu"]
    instance_data["mem"] = data["num_nodes"] * data["mem"]
    instance_data["number_of_disks"] = data["num_nodes"] * data["number_of_disks"]
    instance_data["number_of_nodes"] = data["num_nodes"]
    instance_data["instance_name"] = data["clustername"]
    instance_data["instance_state"] = "registered"

    # Node info
    node_data["cpu"] = str(data["cpu"])  # You can remove str in the future when registry is fixed
    node_data["mem"] = str(data["mem"])  # You can remove str in the future when registry is fixed
    node_data["number_of_disks"] = str(data["number_of_disks"])
    node_data["status"] = "registered"

    # nodes
    nodes_dict = dict()
    name_pattern = node_data["name"]
    for i in range(int(instance_data["number_of_nodes"])):
        copied_data = node_data.copy()
        copied_data["name"] = name_pattern+str(i)
        copied_data["node_id"] = str(i)
        copied_data["disks"] = ut.deflate_node_disks(node_data["number_of_disks"], node_data["disk"])
        copied_data.pop("disk", None)
        copied_data["networks"] = ut.deflate_node_networks(node_data["network"])
        copied_data.pop("network", None)
        nodes_dict[copied_data["name"]] = copied_data

    instance_dn, instance_data = ut.register_instance(data, instance_data, nodes_dict, services_dict)
    app.logger.info("Cluster {} was successfully registered".format(instance_data["service_full_name"]))

    for node in nodes_dict:
        node_dn = instance_dn + "/nodes/" + nodes_dict[node]["name"]
        ut.set_node_info(node_dn=node_dn, node_name=nodes_dict[node]["name"],
                         instance_name=instance_data["service_full_name"])

    data = {"instance_dn": instance_dn}
    data_json = json.dumps(data)
    headers = {'Content-type': 'application/json'}
    response = requests.post(MESOS_FRAMEWORK_ENDPOINT, data=data_json, headers=headers)
    app.logger.info(
        "Cluster {} was successfully forwarded to the mesos framework".format(instance_data["service_full_name"]))
    app.logger.info(
        "Mesos framework response was {} ".format(response))
    return jsonify({'result': 'success'})

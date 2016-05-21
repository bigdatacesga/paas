import json
import kvstore as kv
import requests

from flask import Flask, abort
from flask import jsonify, request

from . import api
from . import utils as ut
from .errors import ValidationError

#import registry
from .configuration_registry import registry

ENDPOINT = 'http://consul:8500/v1/kv'
MESOS_FRAMEWORK_ENDPOINT = 'http://mesos_framework.service.int.cesga.es:5000/bigdata/mesos_framework/v1/instance'
TEMPLATE_ENDPOINT = 'frameworks'
service_endp = kv.Client(ENDPOINT)
app = Flask(__name__)



@api.route('/services', methods=['GET'])
@api.route('/services/', methods=['GET'])
def get_sevices():
    app.logger.info('Request for all services')
    try:
        services = [] # service_endp.recurse("/services")
        return jsonify({'services': services})

    except kv.KeyDoesNotExist as error:
        app.logger.info('404 Error ' + error.message)
        abort(404)


@api.route('/services/<service>/<version>', methods=['GET'])
def get_sevice(service, version):
    app.logger.info('Request for all services')
    try:
        registry.connect(ENDPOINT)
        service = registry.get_service_template(service, version)
        # FIXME Create a toString method of a Service Object
        service_string = service.name
        return jsonify({'services': service_string})

    except kv.KeyDoesNotExist as error:
        app.logger.info('404 Error ' + error.message)
        abort(404)


@api.route('/instances', methods=['GET'])
@api.route('/instances/', methods=['GET'])
def get_all_instances():
    app.logger.info('Request for all instances')
    try:
        #instances = [] # service_endp.recurse("/instances")
        registry.connect(ENDPOINT)
        instances = registry.get_cluster_instances()
        return jsonify({'services': instances})

    except kv.KeyDoesNotExist as error:
        app.logger.info('404 Error ' + error.message)
        abort(404)


@api.route('/instances/<username>', methods=['GET'])
@api.route('/instances/<username>/', methods=['GET'])
def get_user_instances(username):
    app.logger.info('Request for instances of user {} '.format(username))
    try:
        #instances = [] # service_endp.recurse("/instances/{}".format(username))
        registry.connect(ENDPOINT)
        instances = registry.get_cluster_instances(username)
        return jsonify({'services': instances})

    except kv.KeyDoesNotExist as error:
        app.logger.info('404 Error ' + error.message)
        abort(404)

@api.route('/instances/<username>/<service>', methods=['GET'])
def get_user_service_instances(username, service):
    app.logger.info('Request for instances of user {} and service {}'.format(username, service))
    try:
        #instances = [] # service_endp.recurse("/instances/{}/{}".format(username, service))
        registry.connect(ENDPOINT)
        instances = registry.get_cluster_instances(username, service)
        return jsonify({'services': instances})

    except kv.KeyDoesNotExist as error:
        app.logger.info('404 Error ' + error.message)
        abort(404)

@api.route('/instances/<username>/<service>/<version>', methods=['GET'])
def get_user_service_version_instances(username, service, version):
    app.logger.info('Request for instances of user {} and service {} with version {}'.format(username, service, version))
    try:
        #instances = [] # service_endp.recurse("/instances/{}/{}/{}".format(username, service, version))
        registry.connect(ENDPOINT)
        instances = registry.get_cluster_instances(username, service, version)
        return jsonify({'services': instances})

    except kv.KeyDoesNotExist as error:
        app.logger.info('404 Error ' + error.message)
        abort(404)


@api.route('/instances/<username>/<service>/<version>/<instanceid>', methods=['GET'])
def get_instance(username, service, version, instanceid):
    app.logger.info('Request for instance nodes of user {} and service {} with version {}'.format(username, service, version))
    try:
        registry.connect(ENDPOINT)
        instance = registry.get_cluster_instance(dn="/instances/{}/{}/{}/{}".format(username, service, version, instanceid))
        # FIXME Implement a 'toString' method to describe an Instance object from the endpoint
        return jsonify({'instance': instance.service_full_name})

    except kv.KeyDoesNotExist as error:
        app.logger.info('404 Error ' + error.message)
        abort(404)

@api.route('/instances/<username>/<service>/<version>/<instanceid>/nodes', methods=['GET'])
def get_instance_nodes(username, service, version, instanceid):
    app.logger.info('Request for instance nodes of user {} and service {} with version {}'.format(username, service, version))
    try:
        registry.connect(ENDPOINT)
        instance = registry.get_cluster_instance(dn="/instances/{}/{}/{}/{}".format(username, service, version, instanceid))
        nodes = instance.nodes
        node_names_list = list()
        for node in nodes:
            # FIXME Implement a 'toString' methos to describe a node object from the endpoint
            node_names_list.append(node.name)
        return jsonify({'nodes': node_names_list})

    except kv.KeyDoesNotExist as error:
        app.logger.info('404 Error ' + error.message)
        abort(404)

@api.route('/instances/<username>/<service>/<version>/<instanceid>/services', methods=['GET'])
def get_instance_services(username, service, version, instanceid):
    app.logger.info('Request for instance nodes of user {} and service {} with version {}'.format(username, service, version))
    try:
        registry.connect(ENDPOINT)
        instance = registry.get_cluster_instance(dn="/instances/{}/{}/{}/{}".format(username, service, version, instanceid))
        services = instance.services
        service_names_list = list()
        for service in services:
            # FIXME Implement a 'toString' methos to describe a service object from the endpoint
            service_names_list.append(service.name)
        return jsonify({'services': service_names_list})

    except kv.KeyDoesNotExist as error:
        app.logger.info('404 Error ' + error.message)
        abort(404)

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

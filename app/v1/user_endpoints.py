import json
import kvstore as kv
import requests

from flask import Flask, abort
from flask import jsonify, request

from . import api
from . import utils as ut
from .errors import ValidationError

import registry
#from .configuration_registry import registry

ENDPOINT = 'http://consul:8500/v1/kv'
MESOS_FRAMEWORK_ENDPOINT = 'http://mesos_framework.service.int.cesga.es:5000/bigdata/mesos_framework/v1/instance'
#MESOS_FRAMEWORK_ENDPOINT = 'http://127.0.0.1:5002/bigdata/mesos_framework/v1/instance'
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
@api.route('/instances/<username>/<service>/', methods=['GET'])
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
@api.route('/instances/<username>/<service>/<version>/', methods=['GET'])
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
@api.route('/instances/<username>/<service>/<version>/<instanceid>/', methods=['GET'])
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
@api.route('/instances/<username>/<service>/<version>/<instanceid>/nodes/', methods=['GET'])
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
@api.route('/instances/<username>/<service>/<version>/<instanceid>/services/', methods=['GET'])
def get_instance_services(username, service, version, instanceid):
    app.logger.info('Request for instance nodes of user {} and service {} with version {}'.format(username, service, version))
    try:
        registry.connect(ENDPOINT)
        instance = registry.get_cluster_instance(dn="/instances/{}/{}/{}/{}".format(username, service, version, instanceid))
        services = instance.services
        service_names_list = list()
        for service in services:
            # FIXME Implement a 'toString' method to describe a service object from the endpoint
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

@api.route('/services', methods=['POST'])
@api.route('/services/', methods=['POST'])
def create_service():

    # Get data from user parameters
    template_data = ut.parse_post_template_data(request)

    registry.connect(ENDPOINT)
    template = registry.register(name=template_data["name"], version=template_data["version"], templatetype='json+jinja2')
    return str(template), 200


@api.route('/services/<service>/<version>/<attribute>', methods=['PUT'])
@api.route('/services/<service>/<version>/<attribute>/', methods=['PUT'])
def fill_service_by_param(service, version, attribute):
    if attribute in ("description", "template", "options"):
        data = request.get_data()
        registry.connect(ENDPOINT)
        template = registry.get_service_template(service, version)
        if attribute == "description":
            template.description = data
        elif attribute == "template":
            template.template = data
        elif attribute == "options":
            template.options = data
    return str(template), 200


@api.route('/services/<service>/<version>', methods=['POST'])
@api.route('/services/<service>/<version>/', methods=['POST'])
def launch_service(service, version):
    username = "jenes"
    options = request.get_json()
    registry.connect(ENDPOINT)
    instance = registry.instantiate(username, service, version, options)
    ut.initialize_networks(instance)

    for node in instance.nodes:
        ut.set_node_info(node, node.name, instance.instance_full_name)

    data = {"instance_dn": str(instance)}
    data_json = json.dumps(data)
    headers = {'Content-type': 'application/json'}
    response = requests.post(MESOS_FRAMEWORK_ENDPOINT, data=data_json, headers=headers)
    if response.status_code != 200:
        abort(500)

    app.logger.info(
        "Cluster was successfully forwarded to the mesos framework")
    app.logger.info(
        "Mesos framework response was {} ".format(response))

    return str(instance), 200
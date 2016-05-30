from flask import abort, jsonify, request
from . import api, app
from . import utils
import json
import requests
import registry

ENDPOINT = 'http://consul:8500/v1/kv'
MESOS_FRAMEWORK_ENDPOINT = 'http://mesos_framework:5000/bigdata/mesos_framework/v1/instance'

registry.connect(ENDPOINT)


@api.route('/services', methods=['GET'])
def get_services():
    app.logger.info('Request for all services')
    services = registry.get_services()
    print services
    return jsonify({'services': services})


@api.route('/services', methods=['POST'])
def create_service():
    if request.is_json:
        data = request.get_json()
        if utils.validate(data, required_fields=('name', 'version', 'description')):
            template = registry.register(name=data["name"], version=data["version"],
                                         description=data["description"])
            return str(template), 200
    abort(400)


@api.route('/services/<service>', methods=['GET'])
def get_service_versions(service):
    versions = registry.get_service_versions(service)
    return jsonify({'versions': versions})


@api.route('/services/<service>/<version>', methods=['GET'])
def get_service(service, version):
    service = registry.get_service_template(service, version)
    return jsonify(service.to_JSON())


@api.route('/services/<service>/<version>/template', methods=['PUT'])
def set_service_template(service, version):
    if request.headers['Content-Type'] == 'application/json':
        templatetype = 'json+jinja2'
    elif request.headers['Content-Type'] == 'application/yaml':
        templatetype = 'yaml+jinja2'
    data = request.get_data()
    template = registry.get_service_template(service, version)
    template.template = data
    template.templatetype = templatetype
    return '', 204


@api.route('/services/<service>/<version>/options', methods=['PUT'])
def set_service_options(service, version):
    data = request.get_data()
    template = registry.get_service_template(service, version)
    template.options = data
    return '', 204


@api.route('/services/<service>/<version>/orquestrator', methods=['PUT'])
def set_service_orquestrator(service, version):
    data = request.get_data()
    template = registry.get_service_template(service, version)
    template.orquestrator = data
    return '', 204


@api.route('/services/<service>/<version>', methods=['POST'])
def launch_service(service, version):
    username = "jenes"
    options = request.get_json()
    registry.connect(ENDPOINT)
    instance = registry.instantiate(username, service, version, options)
    utils.initialize_networks(instance)

    for node in instance.nodes:
        utils.set_node_info(node, node.name, instance.instance_full_name)

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


@api.route('/instances', methods=['GET'])
def get_all_instances():
    app.logger.info('Request for all instances')
    instances = registry.get_cluster_instances()
    return jsonify({'instances': instances})


@api.route('/instances/<username>', methods=['GET'])
def get_user_instances(username):
    app.logger.info('Request for instances of user {} '.format(username))
    instances = registry.get_cluster_instances(username)
    return jsonify({'services': instances})


@api.route('/instances/<username>/<service>', methods=['GET'])
def get_user_service_instances(username, service):
    app.logger.info('Request for instances of user {} and service {}'.format(username, service))
    instances = registry.get_cluster_instances(username, service)
    return jsonify({'services': instances})


@api.route('/instances/<username>/<service>/<version>', methods=['GET'])
def get_user_service_version_instances(username, service, version):
    app.logger.info('Request for instances of user {} and service {} with version {}'
                    .format(username, service, version))
    instances = registry.get_cluster_instances(username, service, version)
    return jsonify({'services': instances})


@api.route('/instances/<username>/<service>/<version>/<instanceid>', methods=['GET'])
def get_instance(username, service, version, instanceid):
    instance = registry.get_cluster_instance(dn='/instances/{}/{}/{}/{}'
                                             .format(username, service, version, instanceid))
    return jsonify(instance.to_JSON())


@api.route('/instances/<username>/<service>/<version>/<instanceid>/nodes', methods=['GET'])
def get_instance_nodes(username, service, version, instanceid):
    app.logger.info('Request for instance nodes of user {} and service {} with '
                    'version {}'.format(username, service, version))
    instance = registry.get_cluster_instance(
        dn="/instances/{}/{}/{}/{}".format(username, service, version, instanceid))
    return jsonify({'nodes': [node.to_JSON() for node in instance.nodes]})


@api.route('/instances/<username>/<service>/<version>/<instanceid>/services', methods=['GET'])
def get_instance_services(username, service, version, instanceid):
    instance = registry.get_cluster_instance(
        dn="/instances/{}/{}/{}/{}".format(username, service, version, instanceid))
    return jsonify({'services': [s.to_JSON() for s in instance.services]})

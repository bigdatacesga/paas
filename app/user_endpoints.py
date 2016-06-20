from flask import abort, jsonify, request, g
from . import api, app
from . import utils
import json
import requests
import registry
from .decorators import restricted

#from .configuration_registry import registry

CONSUL_ENDPOINT = app.config.get('CONSUL_ENDPOINT')
MESOS_FRAMEWORK_ENDPOINT = app.config.get('MESOS_FRAMEWORK_ENDPOINT')


registry.connect(CONSUL_ENDPOINT)


@api.route('/services', methods=['POST'])
@restricted(role='ROLE_USER')
def register_service():
    """Register a new service"""
    if request.is_json:
        data = request.get_json()
        if utils.validate(data, required_fields=('name', 'version', 'description')):
            template = registry.register(name=data["name"], version=data["version"],
                                         description=data["description"])
            return str(template), 200
    abort(400)


@api.route('/services', methods=['GET'])
@restricted(role='ROLE_USER')
def get_services():
    """Get the current list of registered services"""
    services = registry.get_services()
    return jsonify({'services': services})


@api.route('/services/<service>', methods=['GET'])
def get_service_versions(service):
    """Get the available versions of a service"""
    versions = registry.get_service_versions(service)
    return jsonify({'versions': versions})


@api.route('/services/<service>/<version>', methods=['GET'])
@restricted(role='ROLE_USER')
def get_service(service, version):
    """Get info about a specific version of a service"""
    service = registry.get_service_template(service, version)
    return jsonify(service.to_dict())


@api.route('/services/<service>/<version>/template', methods=['GET'])
@restricted(role='ROLE_USER')
def get_service_template(service, version):
    """Get the template used to generate the resources needed by a service"""
    service = registry.get_service_template(service, version)
    template = service.template
    return jsonify(template)


@api.route('/services/<service>/<version>/template', methods=['PUT'])
@restricted(role='ROLE_USER')
def set_service_template(service, version):
    """Set the template needed to generate the required service resources"""
    if request.headers['Content-Type'] == 'application/json':
        templatetype = 'json+jinja2'
    elif request.headers['Content-Type'] == 'application/yaml':
        templatetype = 'yaml+jinja2'
    data = request.get_data().decode('utf-8')
    template = registry.get_service_template(service, version)
    template.template = data
    template.templatetype = templatetype
    return '', 204


@api.route('/services/<service>/<version>/options', methods=['GET'])
@restricted(role='ROLE_USER')
def get_service_options(service, version):
    """Get the options needed by the service template"""
    service = registry.get_service_template(service, version)
    options = service.options
    return jsonify(options)


@api.route('/services/<service>/<version>/options', methods=['PUT'])
@restricted(role='ROLE_USER')
def set_service_options(service, version):
    """Set the options needed by the service template"""
    data = request.get_data().decode('utf-8')
    template = registry.get_service_template(service, version)
    template.options = data
    return '', 204


@api.route('/services/<service>/<version>/orquestrator', methods=['GET'])
@restricted(role='ROLE_USER')
def get_service_orquestrator(service, version):
    """Get the orquestrator needed to start the service once instantiated"""
    service = registry.get_service_template(service, version)
    orquestrator = service.orquestrator
    return jsonify(orquestrator)


@api.route('/services/<service>/<version>/orquestrator', methods=['PUT'])
@restricted(role='ROLE_USER')
def set_service_orquestrator(service, version):
    """Set the orquestrator needed to start the service once instantiated"""
    data = request.get_data().decode('utf-8')
    template = registry.get_service_template(service, version)
    template.orquestrator = data
    return '', 204


@api.route('/services/<service>/<version>', methods=['POST'])
@restricted(role='ROLE_USER')
def launch_service(service, version):
    """Launch a new service instance"""
    app.logger.info('Request to launch a new service instance from user {}'
                    .format(g.user))
    username = g.user
    options = request.get_json()
    instance = registry.instantiate(username, service, version, options)

    for node in instance.nodes:
        node.status = "submitted"

    data = {"instance_dn": str(instance)}
    data_json = json.dumps(data)
    headers = {'Content-type': 'application/json'}
    response = requests.post(MESOS_FRAMEWORK_ENDPOINT, data=data_json,
                             headers=headers)
    if response.status_code != 200:
        app.logger.error('Mesos framework error: {}'.format(response))
        abort(500)

    return str(instance), 200


@api.route('/instances', methods=['GET'])
@restricted(role='ROLE_USER')
def get_all_instances():
    app.logger.info('Request for all instances')
    instances = registry.get_cluster_instances()
    return jsonify({'instances': [utils.print_instance(instance, (None, None, None)) for instance in instances]})


@api.route('/instances/<username>', methods=['GET'])
@restricted(role='ROLE_USER')
def get_user_instances(username):
    app.logger.info('Request for instances of user {} '.format(username))

    instances = registry.get_cluster_instances(user=username)
    return jsonify({'instances': [utils.print_instance(instance, (username, None, None)) for instance in instances]})


@api.route('/instances/<username>/<service>', methods=['GET'])
@restricted(role='ROLE_USER')
def get_user_service_instances(username, service):
    app.logger.info('Request for instances of user {} and service {}'.format(username, service))
    instances = registry.get_cluster_instances(username, service)
    return jsonify({'instances': [utils.print_instance(instance, (username, service, None)) for instance in instances]})


@api.route('/instances/<username>/<service>/<version>', methods=['GET'])
@restricted(role='ROLE_USER')
def get_user_service_version_instances(username, service, version):
    app.logger.info('Request for instances of user {} and service {} with version {}'
                    .format(username, service, version))
    instances = registry.get_cluster_instances(username, service, version)
    return jsonify({'instances': [utils.print_instance(instance, (username, service, version)) for instance in instances]})


@api.route('/instances/<username>/<service>/<version>/<instanceid>', methods=['GET'])
@restricted(role='ROLE_USER')
def get_instance(username, service, version, instanceid):
    instance = registry.get_cluster_instance(dn='/instances/{}/{}/{}/{}'
                                             .format(username, service, version, instanceid))
    return jsonify(utils.print_full_instance(instance))


@api.route('/instances/<username>/<service>/<version>/<instanceid>/nodes', methods=['GET'])
@restricted(role='ROLE_USER')
def get_instance_nodes(username, service, version, instanceid):
    app.logger.info('Request for instance nodes of user {} and service {} with '
                    'version {}'.format(username, service, version))
    instance = registry.get_cluster_instance(
        dn="/instances/{}/{}/{}/{}".format(username, service, version, instanceid))
    return jsonify({'nodes': [node.to_JSON() for node in instance.nodes]})


@api.route('/instances/<username>/<service>/<version>/<instanceid>/services', methods=['GET'])
@restricted(role='ROLE_USER')
def get_instance_services(username, service, version, instanceid):
    instance = registry.get_cluster_instance(
        dn="/instances/{}/{}/{}/{}".format(username, service, version, instanceid))
    return jsonify({'services': [s.to_JSON() for s in instance.services]})


@api.route('/instances/<username>/<service>/<version>/<instanceid>', methods=['DELETE'])
@restricted(role='ROLE_USER')
def destroy_instance(username, service, version, instanceid):
    # Remove from the mesos system
    instance = registry.get_cluster_instance(username, service, version, instanceid)
    data = {"instance_dn": str(instance)}
    data_json = json.dumps(data)
    headers = {'Content-type': 'application/json'}
    response = requests.delete(MESOS_FRAMEWORK_ENDPOINT, data=data_json,
                             headers=headers)
    if response.status_code != 200:
        app.logger.error('Mesos framework error: {}'.format(response))
        abort(500)

    # Remove from the kvstore
    # registry.deinstantiate(username, service, version, instanceid)
    return jsonify({"message": "success"}), 200

@api.route('/instances/<username>/<service>/<version>/<instanceid>/orquestrate', methods=['GET'])
@restricted(role='ROLE_USER')
def run_orquestrator(username, service, version, instanceid):
    instance = registry.get_cluster_instance(
        dn="/instances/{}/{}/{}/{}".format(username, service, version, instanceid))
    service = registry.get_service_template(service, version)
    orquestrator = service.orquestrator

    import os

    os.environ['INSTANCE'] = str(instance)
    os.environ['REGISTRY'] = app.config.get('CONSUL_ENDPOINT')

    os.environ['OP'] = "start"
    exec orquestrator

    # os.environ['OP'] = "stop"
    # exec orquestrator
    #
    # os.environ['OP'] = "status"
    # exec orquestrator
    #
    # os.environ['OP'] = "restart"
    # exec orquestrator

    return jsonify({'code': orquestrator})

@api.route('/test', methods=['GET'])
@restricted(role='ROLE_USER')
def echo_hello():
    return jsonify({'message': 'Hello {}'.format(g.user)})

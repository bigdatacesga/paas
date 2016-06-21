from flask import abort, jsonify, request, g
from . import api, app
from . import utils
import json
import requests
import registry
from .decorators import restricted

CONSUL_ENDPOINT = app.config.get('CONSUL_ENDPOINT')
MESOS_FRAMEWORK_ENDPOINT = app.config.get('MESOS_FRAMEWORK_ENDPOINT')


registry.connect(CONSUL_ENDPOINT)


@api.route('/products', methods=['POST'])
@restricted(role='ROLE_USER')
def register_product():
    """Register a new product"""
    if request.is_json:
        data = request.get_json()
        if utils.validate(data, required_fields=('name', 'version', 'description')):
            template = registry.register(name=data["name"], version=data["version"],
                                         description=data["description"])
            return str(template), 200
    abort(400)


@api.route('/products', methods=['GET'])
@restricted(role='ROLE_USER')
def get_products():
    """Get the current list of registered products"""
    products = registry.get_products()
    return jsonify({'products': products})


@api.route('/products/<product>', methods=['GET'])
def get_product_versions(product):
    """Get the available versions of a produt"""
    versions = registry.get_product_versions(product)
    return jsonify({'versions': versions})


@api.route('/products/<product>/<version>', methods=['GET'])
@restricted(role='ROLE_USER')
def get_product(product, version):
    """Get info about a specific version of a product"""
    product = registry.get_product(product, version)
    return jsonify(product.to_dict())


@api.route('/products/<product>/<version>/template', methods=['GET'])
@restricted(role='ROLE_USER')
def get_product_template(product, version):
    """Get the template used to generate the resources needed by a product"""
    product = registry.get_product(product, version)
    template = product.template
    return jsonify(template)


@api.route('/products/<product>/<version>/template', methods=['PUT'])
@restricted(role='ROLE_USER')
def set_product_template(product, version):
    """Set the template needed to generate the required product resources"""
    if request.headers['Content-Type'] == 'application/json':
        templatetype = 'json+jinja2'
    elif request.headers['Content-Type'] == 'application/yaml':
        templatetype = 'yaml+jinja2'
    data = request.get_data().decode('utf-8')
    template = registry.get_product(product, version)
    template.template = data
    template.templatetype = templatetype
    return '', 204


@api.route('/products/<product>/<version>/options', methods=['GET'])
@restricted(role='ROLE_USER')
def get_product_options(product, version):
    """Get the options needed by the product template"""
    product = registry.get_product(product, version)
    options = product.options
    return jsonify(options)


@api.route('/products/<product>/<version>/options', methods=['PUT'])
@restricted(role='ROLE_USER')
def set_product_options(product, version):
    """Set the options needed by the product template"""
    data = request.get_data().decode('utf-8')
    template = registry.get_product_template(product, version)
    template.options = data
    return '', 204


@api.route('/products/<product>/<version>/orquestrator', methods=['GET'])
@restricted(role='ROLE_USER')
def get_product_orquestrator(product, version):
    """Get the orquestrator needed to start the product once instantiated"""
    product = registry.get_product_template(product, version)
    orquestrator = product.orquestrator
    return jsonify(orquestrator)


@api.route('/products/<product>/<version>/orquestrator', methods=['PUT'])
@restricted(role='ROLE_USER')
def set_product_orquestrator(product, version):
    """Set the orquestrator needed to start the product once instantiated"""
    data = request.get_data().decode('utf-8')
    template = registry.get_product_template(product, version)
    template.orquestrator = data
    return '', 204


@api.route('/products/<product>/<version>', methods=['POST'])
@restricted(role='ROLE_USER')
def launch_product(product, version):
    """Launch a new cluster instance"""
    app.logger.info('Request to launch a new cluster instance from user {}'
                    .format(g.user))
    username = g.user
    options = request.get_json()
    cluster = registry.instantiate(username, product, version, options)
    clusterdn = str(cluster)

    for node in cluster.nodes:
        node.status = "submitted"

    app.logger.info('Submitting cluster instance to Mesos')
    data = {"clusterdn": clusterdn}
    response = requests.post(MESOS_FRAMEWORK_ENDPOINT, json=data)
    if response.status_code != 200:
        app.logger.error('Mesos framework returned {}'.format(response.status_code))
        app.logger.error('{}'.format(response.json()))
        abort(500)

    app.logger.info('Launching orquestrator thread')
    utils.launch_orquestrator_when_ready(clusterdn)

    return clusterdn, 200


@api.route('/clusters', methods=['GET'])
@restricted(role='ROLE_USER')
def get_all_clusters():
    app.logger.info('Request for all clusters')
    clusters = registry.get_cluster_instances()
    return jsonify({
        'clusters': [utils.print_instance(instance, (None, None, None))
                     for instance in clusters]})


@api.route('/clusters/<username>', methods=['GET'])
@restricted(role='ROLE_USER')
def get_user_clusters(username):
    app.logger.info('Request for clusters of user {} '.format(username))

    clusters = registry.get_cluster_instances(user=username)
    return jsonify({
        'clusters': [utils.print_instance(instance, (username, None, None))
                      for instance in clusters]})


@api.route('/clusters/<username>/<service>', methods=['GET'])
@restricted(role='ROLE_USER')
def get_user_service_clusters(username, service):
    app.logger.info('Request for clusters of user {} and service {}'.format(username, service))
    clusters = registry.get_cluster_instances(username, service)
    return jsonify({
        'clusters': [utils.print_instance(instance, (username, service, None))
                      for instance in clusters]})


@api.route('/clusters/<username>/<service>/<version>', methods=['GET'])
@restricted(role='ROLE_USER')
def get_user_service_version_clusters(username, service, version):
    app.logger.info('Request for clusters of user {} and service {} with version {}'
                    .format(username, service, version))
    clusters = registry.get_cluster_instances(username, service, version)
    return jsonify({
        'clusters': [utils.print_instance(instance, (username, service, version))
                      for instance in clusters]})


@api.route('/clusters/<username>/<service>/<version>/<instanceid>', methods=['GET'])
@restricted(role='ROLE_USER')
def get_instance(username, service, version, instanceid):
    instance = registry.get_cluster_instance(dn='/clusters/{}/{}/{}/{}'
                                             .format(username, service, version, instanceid))
    return jsonify(utils.print_full_instance(instance))


@api.route('/clusters/<username>/<service>/<version>/<instanceid>/nodes', methods=['GET'])
@restricted(role='ROLE_USER')
def get_instance_nodes(username, service, version, instanceid):
    app.logger.info('Request for instance nodes of user {} and service {} with '
                    'version {}'.format(username, service, version))
    instance = registry.get_cluster_instance(
        dn="/clusters/{}/{}/{}/{}".format(username, service, version, instanceid))
    return jsonify({'nodes': [node.to_JSON() for node in instance.nodes]})


@api.route('/clusters/<username>/<service>/<version>/<instanceid>/services', methods=['GET'])
@restricted(role='ROLE_USER')
def get_instance_services(username, service, version, instanceid):
    instance = registry.get_cluster_instance(
        dn="/clusters/{}/{}/{}/{}".format(username, service, version, instanceid))
    return jsonify({'services': [s.to_JSON() for s in instance.services]})


@api.route('/clusters/<username>/<service>/<version>/<instanceid>', methods=['DELETE'])
@restricted(role='ROLE_USER')
def destroy_instance(username, service, version, instanceid):
    # Remove from the mesos system
    instance = registry.get_cluster_instance(username, service, version, instanceid)
    data = {"clusterdn": str(instance)}
    data_json = json.dumps(data)
    headers = {'Content-type': 'application/json'}
    response = requests.delete(MESOS_FRAMEWORK_ENDPOINT, data=data_json,
                               headers=headers)
    if response.status_code != 200:
        app.logger.error('Mesos framework error: {}'.format(response.error))
        abort(500)

    # Remove from the kvstore
    # registry.deinstantiate(username, service, version, instanceid)
    return jsonify({"message": "success"}), 200

from flask import abort, jsonify, request, g, url_for
from . import api, app
from . import utils
import json
import requests
import registry
import kvstore
from .decorators import restricted, asynchronous

CONSUL_ENDPOINT = app.config.get('CONSUL_ENDPOINT')
MESOS_FRAMEWORK_ENDPOINT = app.config.get('MESOS_FRAMEWORK_ENDPOINT')

registry.connect(CONSUL_ENDPOINT)
kv = kvstore.Client(CONSUL_ENDPOINT)


@api.route('/products', methods=['POST'])
@restricted(role='ROLE_USER')
def register_product():
    """Register a new product"""
    if request.is_json:
        data = request.get_json()
        if utils.validate(data, required_fields=('name', 'version', 'description')):
            name = data['name']
            version = data['version']
            description = data['description']
            product = registry.register(name, version, description)
            location = url_for('api.get_product', product=name, version=version,
                               _external=True)
            return '', 201, {'Location': location}
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
# @asynchronous
def launch_cluster(product, version):
    """Launch a new cluster instance"""
    app.logger.info('Request to launch a new cluster instance from user {}'
                    .format(g.user))
    username = g.user
    options = request.get_json()
    cluster = registry.instantiate(username, product, version, options)
    clusterdn = cluster.dn
    id = cluster.name

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

    return '', 201, {
        'Location': url_for('api.get_cluster', username=username, product=product,
                            version=version, id=id, _external=True)}


@api.route('/clusters', methods=['GET'])
@restricted(role='ROLE_USER')
def get_all_clusters():
    app.logger.info('Request for all clusters')
    clusters = registry.query_clusters()
    return jsonify({
        'clusters': [utils.print_instance(instance, (None, None, None))
                     for instance in clusters]})


@api.route('/clusters/<username>', methods=['GET'])
@restricted(role='ROLE_USER')
def get_user_clusters(username):
    app.logger.info('Request for clusters of user {} '.format(username))

    clusters = registry.query_clusters(user=username)
    return jsonify({
        'clusters': [utils.print_instance(instance, (username, None, None))
                      for instance in clusters]})


@api.route('/clusters/<username>/<product>', methods=['GET'])
@restricted(role='ROLE_USER')
def get_user_product_clusters(username, product):
    app.logger.info('Request for clusters of user {} and service {}'.format(username, product))
    clusters = registry.query_clusters(username, product)
    return jsonify({
        'clusters': [utils.print_instance(instance, (username, product, None))
                      for instance in clusters]})


@api.route('/clusters/<username>/<product>/<version>', methods=['GET'])
@restricted(role='ROLE_USER')
def get_user_product_version_clusters(username, product, version):
    app.logger.info('Request for clusters of user {} and service {} with version {}'
                    .format(username, product, version))
    clusters = registry.query_clusters(username, product, version)
    return jsonify({
        'clusters': [utils.print_instance(instance, (username, product, version))
                      for instance in clusters]})


@api.route('/clusters/<username>/<product>/<version>/<id>', methods=['GET'])
@restricted(role='ROLE_USER')
def get_cluster(username, product, version, id):
    cluster = registry.get_cluster(dn='/clusters/{}/{}/{}/{}'
                                             .format(username, product, version, id))
    return jsonify(utils.print_full_instance(cluster))


@api.route('/clusters/<username>/<product>/<version>/<id>/nodes', methods=['GET'])
@restricted(role='ROLE_USER')
def get_cluster_nodes(username, product, version, id):
    app.logger.info('Request for instance nodes of user {} and service {} with '
                    'version {}'.format(username, product, version))
    cluster = registry.get_cluster(
        dn="/clusters/{}/{}/{}/{}".format(username, product, version, id))
    return jsonify({'nodes': [node.to_JSON() for node in cluster.nodes]})


@api.route('/clusters/<username>/<product>/<version>/<id>/services', methods=['GET'])
@restricted(role='ROLE_USER')
def get_cluster_services(username, product, version, id):
    cluster = registry.get_cluster(
        dn="/clusters/{}/{}/{}/{}".format(username, product, version, id))
    return jsonify({'services': [s.to_JSON() for s in cluster.services]})


@api.route('/clusters/<username>/<product>/<version>/<id>', methods=['DELETE'])
@restricted(role='ROLE_USER')
def destroy_cluster(username, product, version, id):
    # Remove from the mesos system
    cluster = registry.get_cluster(username, product, version, id)
    response = requests.delete('{}/{}'.format(MESOS_FRAMEWORK_ENDPOINT, registry.id_from(cluster.dn)))
    if response.status_code != 204:
        app.logger.error('Mesos framework error. Response: {}'.format(response))
        abort(500)

    # Remove from the kvstore
    # registry.deinstantiate(username, service, version, id)
    return jsonify({"message": "success"}), 200


@api.route('/queue/<id>', methods=['GET'])
def get_async_job_status(id):
    """Get the status of an async request"""
    status = kv.get('queue/{}/status'.format(id))
    if status != 'pending':
        url = kv.get('queue/{}/url'.format(id))
        status = kv.get('queue/{}/status'.format(id))
        return (jsonify({'status': status, 'url': url}), 303,
                {'Location': url})
    return jsonify({'status': 'pending'}), 200

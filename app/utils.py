import registry
import threading
import time
import requests
from . import app

ORQUESTRATOR_ENDPOINT = app.config.get('ORQUESTRATOR_ENDPOINT')

def validate(data, required_fields):
    """Validate if all required_fields are in the given data dictionary"""
    if all(field in data for field in required_fields):
        return True
    return False


def trim_dn(username, version, framework, dn):
    dn = dn.replace("instances", "")
    if username is not None:
        dn = dn.replace("/{}".format(username), "")
    if version is not None:
        dn = dn.replace("/{}".format(version), "")
    if framework is not None:
        dn = dn.replace("/{}".format(framework), "")
    return dn


def print_full_instance(instance):
    """ Try to get all the info from an instance or if error, return the dn"""
    try:
        return {
            "result": "success",
            "uri": str(instance),
            "data": instance.to_dict()
        }
    except registry.KeyDoesNotExist as e:
        return {
            "result": "failure",
            "uri": str(instance),
            "message": e.message
        }


def print_instance(instance, filters):
    """ Try to get the basic info from the instance or if error, return the dn"""
    (username, service, version) = filters
    try:
        return {
            "result": "success",
            "uri": str(instance),
            "data": instance.to_dict()
        }
    except registry.KeyDoesNotExist as e:
        return {
            "result": "failure",
            "uri": trim_dn(username, service, version, str(instance)),
            "message": e.message
        }


def launch_orquestrator_when_ready(clusterdn):
    """Launch the orquestrator process"""
    cluster = registry.get_cluster_instance(dn=clusterdn)
    clusterid = registry.id_from(clusterdn)

    def orquestrate_when_cluster_is_ready():
        while cluster.status != 'executing':
            time.sleep(5)
        app.logger.info('Cluster ready: launching orquestrator')
        requests.post('{}/{}'.format(ORQUESTRATOR_ENDPOINT, clusterid))

    t = threading.Thread(target=orquestrate_when_cluster_is_ready)
    t.daemon = True
    t.start()

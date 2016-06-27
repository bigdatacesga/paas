#!/usr/bin/env python
# encoding: utf-8
from __future__ import print_function
from fabric.api import *
from fabric.colors import red, green, yellow
from fabric.contrib.files import exists
from datetime import datetime
from helpers.decorators import rpc
import helpers.servicediscovery as servicediscovery
import os
import time


env.user = 'root'
# Docker engines
env.hosts = ['c13-1', 'c13-2', 'c13-3', 'c13-4']
# Network Address Range
IP_RANGE_START = 1
IP_RANGE_END = 4

SERVICE = 'gluster'
DOMAIN = 'node.int.cesga.es'
TAG = '3.7.11'
#TAG = '20151006-snapshot'
IMAGE = 'docker-registry.cesga.es:5000/{0}:{1} '.format(SERVICE, TAG)

NODES = {
    'gluster{}.node.int.cesga.es'.format(i): {
        'storage': '10.117.123.{}'.format(i),
        'admin': '10.112.123.{}'.format(i)
    } for i in range(IP_RANGE_START, IP_RANGE_END + 1)
}
NETMASK = '16'
GW = '10.112.0.1'

# MAPPINGS: docker engine host -> container
MAPPINGS = {}
containers = sorted(NODES.keys(), reverse=True)
for host in sorted(env.hosts):
    MAPPINGS[host] = containers.pop()

#MAPPINGS = {
    #'c14-1': 'gluster1.node.int.cesga.es',
    #'c14-2': 'gluster2.node.int.cesga.es',
    #'c14-3': 'gluster3.node.int.cesga.es',
    #'c14-4': 'gluster4.node.int.cesga.es',
#}

env.user = 'root'
env.hosts = MAPPINGS.keys()

IPS = [NODES[n]['admin'] for n in sorted(NODES.keys())]
env.roledefs['docker_engines'] = env.hosts
env.roledefs['nodes'] = IPS
env.roledefs['initiator'] = [IPS[0]]
env.roledefs['peerback'] = [IPS[1]]
env.roledefs['responders'] = IPS[1:]

# Debugging mode
# To enable it use: export FABRIC_DEBUG=1
if os.environ.get('NOOP'):

    print(yellow('\n\n== Running in NOOP mode ==\n\n'))

    def run(name):
        print('[{0}] run: {1}'.format(env.host, name))

    def put(source, destination):
        print('[{0}] put: {1} {2}'.format(env.host, source, destination))

    @task
    @parallel
    def hostname():
        """Print the hostnames: mainly used for testing purposes"""
        run('/bin/hostname')


def get_container_name_for(host):
    """Return the associated container name for the given host"""
    return MAPPINGS[host]


@task
@runs_once
def start():
    """Start the GlusterFS service and all the containers that provide it"""
    execute(run_containers)
    DELAY = 10
    print(green('All containers have been started succesfully'))
    print(yellow('Waiting {} seconds for services to start'.format(DELAY)))
    time.sleep(DELAY)
    execute(initialize)
    # TODO: Containers take some time to respond by SSH so the next steps must be delayed
    #execute(configure_service)
    #execute(peer_probe)
    #execute(peer_probe_against_initiator)
    #execute(create_volumes)


@task
@runs_once
def initialize():
    """Initialize the GlusterFS cluster and create the volumes"""
    execute(configure_service)
    execute(peer_probe)
    execute(peer_probe_against_initiator)
    execute(create_volumes)
    execute(start_volumes)


@task
@roles('nodes')
def configure_service():
    """Configure the GlusterFS filesystems"""
    # Generate /etc/hosts
    for nodename in NODES:
        run('echo "{} {} {}" >> /etc/hosts'.format(
            NODES[nodename]['storage'], nodename,
            shortname(nodename)))


def shortname(nodename):
    """Shortten the node name taking only the hostname part of it"""
    return nodename.replace('.{}'.format(DOMAIN), '')


@task
@roles('initiator')
def peer_probe():
    """Probe for peers step 1"""
    for peer in env.roledefs['responders']:
        run('gluster peer probe {}'.format(resolv(peer)))


def resolv(ip):
    """Resolve the shortname for the given IP"""
    for nodename in NODES:
        if NODES[nodename]['admin'] == ip:
            return shortname(nodename)


@task
@roles('peerback')
def peer_probe_against_initiator():
    """Probe for peers step 2"""
    run('gluster peer probe {}'.format(resolv(env.roledefs['initiator'][0])))


@task
@roles('initiator')
def create_volumes():
    """Create GlusterFS volumes"""
    nodes = [shortname(node) for node in NODES.keys()]
    layout = ''
    for (node1, node2) in pairwise(nodes):
        for brick in range(1, 12):
            layout += '{node1}:/data/{brick}/drv0 {node2}:/data/{brick}/drv0 '.format(
                node1=node1, node2=node2, brick='brick{}'.format(brick))
    run('gluster volume create distributed-replicated-volume-0 '
        'replica 2 transport tcp {}'.format(layout))


@task
@roles('initiator')
def start_volumes():
    """Start GlusterFS volumes"""
    run('gluster volume start distributed-replicated-volume-0')


def pairwise(nodes):
    """Create pairs of nodes: 1->2, 3->4, ..."""
    group1 = nodes[::2]
    group2 = nodes[1::2]
    return zip(group1, group2)


@task
@parallel
def start_service():
    """Start the GlusterFS service"""
    #run('service rpcbind start')
    #run('service glusterd start')
    raise NotImplementedError


@task
@parallel
def stop_service():
    """Stop the GlusterFS service without stopping the containers"""
    # TODO: Check what we really need to stop
    #run('service glusterd stop')
    #run('service rpcbind stop')
    pass


@task
@parallel
def status():
    """Check the status of the GlusterFS service"""
    print(yellow("== SERVICE STATUS =="))
    run('service rpcbind status')
    run('service glusterd status')
    print(yellow('== PEER STATUS =='))
    run(yellow('gluster peer status'))
    print('== VOLUME INFO ==')
    run(yellow('gluster volume info'))


def run_containers():
    """Run all containers that provide this service

    This command starts from a fresh image instead of
    starting a previously stopped container
    """
    container_name = get_container_name_for(env.host)
    # Do not assign a local IP to the node
    OPTS = '--net="none" '
    # Privileged option is needed by gluster to create volumes
    # in other case you get the following error:
    # "Setting extended attributes failed, reason: Operation not permitted."
    OPTS += '--privileged '
    for n in range(1, 12):
        if not exists('/data/{}/{}'.format(n, SERVICE)):
            run('mkdir -p /data/{}/{}'.format(n, SERVICE))
        OPTS += '-v /data/{0}/{1}:/data/brick{0} '.format(n, SERVICE)
    OPTS += '-v /dev/log:/dev/log '
    OPTS += '-v /sys/fs/cgroup:/sys/fs/cgroup:ro '
    OPTS += '-v /root/.ssh/authorized_keys:/root/.ssh/authorized_keys '
    OPTS += '-d '
    OPTS += '-ti '
    # DOCKER_FIX trick to avoid this issue:
    # https://github.com/docker/docker/issues/14203
    OPTS += "-e DOCKER_FIX='' "
    run('docker run {opts} -h {name} --name {name} {image}'.format(
        name=container_name, opts=OPTS, image=IMAGE))
    time.sleep(2)
    add_network_connectivity(container_name)
    #register_in_consul(id=container_name, name=SERVICE,
    #                   address=networks['private']['address'], check='SSH')


def add_network_connectivity(container_name):
    """Adds the public networks interfaces to the given container"""
    node = NODES[container_name]
    put('files/bin/pipework', '/tmp/pipework')
    run('chmod u+x /tmp/pipework')
    run('/tmp/pipework virbrSTORAGE -i eth0 {name} {ip}/{mask}'
        .format(name=container_name,
                ip=node['storage'],
                mask=NETMASK))
    run('/tmp/pipework virbrPRIVATE -i eth1 {name} {ip}/{mask}@{gateway}'
        .format(name=container_name,
                ip=node['admin'],
                mask=NETMASK,
                gateway=GW))


@rpc
def register_in_consul(id, name, address, check=None):
    """Register the docker container in consul"""
    sd = servicediscovery.Client()
    if check == 'SSH':
        check = {'id': id, 'name': 'SSH', 'tcp': '{}:{}'.format(address, 22),
                 'Interval': '30s', 'timeout': '4s'}
    sd.register(id, name, address, check=check)


@task
@runs_once
def stop():
    """Stop the GlusterFS service and all the containers that provide it"""
    with settings(warn_only=True):
        execute(stop_service)
        execute(stop_containers)


@task
@runs_once
def destroy():
    """Destroy the GlusterFS cluster stopping and removing the containers"""
    with settings(warn_only=True):
        execute(stop_service)
        execute(stop_containers)
        execute(rm_containers)


def rm_containers():
    """Delete previously stopped containers"""
    container_name = get_container_name_for(env.host)
    run("docker rm {}".format(container_name))


@task
@parallel
def save():
    """Save the state of all the containers that provide this service"""
    container_name = get_container_name_for(env.host)
    image = {
        'name': '{0}/{1}-{0}'.format(SERVICE, env.host),
        'tag': '{:%Y%m%d}-snapshot'.format(datetime.now()),
        'source': container_name,
        'comment': 'Snapshot generated using fab',
        'author': 'Fabric'
    }
    run("docker commit -m='{comment}' -a='{author}' {source} {name}:{tag}"
        .format(**image))
    run("docker tag -f {name}:{tag} docker-registry.cesga.es:5000/{name}:{tag}"
        .format(**image))
    run("docker push docker-registry.cesga.es:5000/{name}:{tag}"
        .format(**image))


def start_containers():
    """Start all containers that provide this service"""
    container_name = get_container_name_for(env.host)
    run("docker start {}".format(container_name))
    add_network_connectivity(container_name)


def stop_containers():
    """Stop all containers that provide this service"""
    container_name = get_container_name_for(env.host)
    run("docker stop {}".format(container_name))


@task
def test():
    """Print hostname"""
    run('/bin/hostname')
    test_remote_function(SERVICE)

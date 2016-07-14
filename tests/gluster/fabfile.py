#!/usr/bin/env python
# encoding: utf-8
"""Orchestration template

The following tasks must be implemented:
    - start
    - stop
    - restart
    - status

An instance endpoint has to be provided using the CLUSTERDN environment variable.
For example:

    CLUSTERDN="instances/test/reference/1.0.0/1"

A fabric roledef  is created for each service defined in the registry.
It can be used with the decorator: @roles('servicename1')

WARN: The hosts are accesed using the IP address of the first network device,
usually eth0.

The properties of a given service can be accessed through:

    SERVICES['servicename'].propertyname

for example:

    SERVICES['namenode'].heap
    # If the property has dots we can use
    SERVICES['datanode'].get('dfs.blocksize')
    # Or even define a default value in case it does not exist
    SERVICES['datanode'].get('dfs.blocksize', '134217728')

Details about a given node can be obtained through each Node object returned by service.nodes

The fabfile can be tested running it in NOOP mode (testing mode) exporting a NOOP env variable.

Required roles: initiator, responders, peerback

"""
from __future__ import print_function
import os
import sys
from fabric.api import *
from fabric.colors import red, green, yellow
from fabric.contrib.files import exists
# FIXME: Installing configuration-registry with pip and importing registry directly does not work
#  inside the fabfile. Temporarily it is copied manually in the utils directory
#from utils import registry
# In the big data nodes configuration-registry is installed globally
import registry
import time
from pprint import pprint


# Maximum number of retries to wait for a node to change to status running
MAX_RETRIES = 100
# Seconds between retries
DELAY = 5


def eprint(*args, **kwargs):
    """Print to stderr"""
    print(*args, file=sys.stderr, **kwargs)


if os.environ.get('CLUSTERDN'):
    CLUSTERDN = os.environ.get('CLUSTERDN')
else:
    eprint(red('An instance endpoint has to be provided using the CLUSTERDN environment variable'))
    sys.exit(2)

if os.environ.get('REGISTRY'):
    REGISTRY = os.environ.get('REGISTRY')
else:
    REGISTRY = 'http://consul.service.int.cesga.es:8500/v1/kv'

# Retrieve info from the registry
registry.connect(REGISTRY)
cluster = registry.Cluster(CLUSTERDN)
nodes = cluster.nodes
services = cluster.services


def wait_until_node_is_running(node):
    """Wait until node is in status running: i.e. docker-executor finished"""
    name = node.name
    retry = 0
    while not node.status == 'running':
        retry += 1
        if retry > max_retries: sys.exit(3)
        print('Waiting for node {}: {}/{}'.format(name, retry, MAX_RETRIES))
        time.sleep(DELAY)


def get_node_address_for_fabric(node):
    """Return the network address to be used by fabric to connect to the node

    By convention the address used is the address of its first network interface
    """
    return node.networks[0].address


# Expose the relevant information
NODES = {node.name: node for node in nodes}
SERVICES = {service.name: service for service in services}
NODE = {}
for node in nodes:
    wait_until_node_is_running(node)
    properties = {'hostname': node.name}
    for dev in node.networks:
        properties[dev.name] = dev.address
    for disk in node.disks:
        properties[disk.name] = disk.destination
    # The node is labeled with the network address that will be used by fabric
    # to connect to the node, this allows to retrieve the node using NODE[env.host]
    label = get_node_address_for_fabric(node)
    NODE[label] = properties

# Show cluster information
pprint(NODE)

env.user = 'root'
env.hosts = NODE.keys()
# Allow known hosts with changed keys
env.disable_known_hosts = True
# Retry 30 times each 10 seconds -> (30-1)*10 = 290 seconds
env.connection_attempts = 30
env.timeout = 10
# Enable ssh client keep alive messages
env.keepalive = 15

# Define the fabric roles according to the cluster services
for service in services:
    env.roledefs[service.name] = [n.networks[0].address for n in service.nodes]

#
# Debugging mode
#
# To enable it use: export NOOP=1
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


@task
@runs_once
def start():
    """Initialize the GlusterFS cluster and create the volumes"""
    execute(configure_service)
    execute(peer_probe)
    execute(peer_probe_against_initiator)
    execute(create_volumes)
    execute(start_volumes)
    cluster.status = 'running'
    print(green("All services started"))


@task
def configure_service():
    """Configure the GlusterFS filesystems"""
    generate_etc_hosts()


def generate_etc_hosts():
    # Generate /etc/hosts
    for n in NODE.values():
        run('echo "{} {}" >> /etc/hosts'.format(n['eth1'], n['hostname']))


@task
@roles('initiator')
def peer_probe():
    """Probe for peers step 1"""
    for peer in env.roledefs['responders']:
        run('gluster peer probe {}'.format(NODE[peer]['hostname']))


@task
@roles('peerback')
def peer_probe_against_initiator():
    """Probe for peers step 2"""
    initiator = env.roledefs['initiator'][0]
    run('gluster peer probe {}'
        .format(NODE[initiator]['hostname']))


@task
@roles('initiator')
def create_volumes():
    """Create GlusterFS volumes"""
    run('gluster peer status')
    # Use eth1 to reference the nodes
    #nodes = [n['eth1'] for n in NODE.values()]
    # Use the hostnames to reference the nodes
    nodes = [n['hostname'] for n in NODE.values()]
    bricks = [NODE[env.host][b] for b in NODE[env.host] if 'brick' in b]
    layout = ''
    for (node1, node2) in pairwise(nodes):
        #for brick in range(1, 12):
        for brick in bricks:
            layout += '{node1}:{brick}/drv0 {node2}:{brick}/drv0 '.format(
                node1=node1, node2=node2, brick=brick)
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
def status():
    """Check the status of the GlusterFS service"""
    print(yellow("== SERVICE STATUS =="))
    run('systemctl status rpcbind')
    run('systemctl status glusterd')
    print(yellow('== PEER STATUS =='))
    run('gluster peer status')
    print('== VOLUME INFO ==')
    run('gluster volume info')


@task
@runs_once
def stop():
    """Stop the GlusterFS service and all the containers that provide it"""
    with settings(warn_only=True):
        execute(stop_service)


@task
def stop_service():
    """Stop the GlusterFS service without stopping the containers"""
    # TODO: Check what we really need to stop
    run('systemctl stop glusterd')
    run('systemctl stop rpcbind')


@task
@runs_once
def restart():
    """Restart all the services of the cluster"""
    execute(stop)
    execute(start)


@task
@roles('initiator')
def test():
    """Just run some test command"""
    run('uname -a')

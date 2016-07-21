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
from fabric.contrib.files import exists, append, sed, comment, uncomment
# FIXME: Installing configuration-registry with pip and importing registry directly does not work
#  inside the fabfile. Temporarily it is copied manually in the utils directory
#from utils import registry
# In the big data nodes configuration-registry is installed globally
import registry
import time
from pprint import pprint
from StringIO import StringIO


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
        if retry > MAX_RETRIES: sys.exit(3)
        print('Waiting for node {}: {}/{}'.format(name, retry, MAX_RETRIES))
        time.sleep(DELAY)


def get_node_address_for_fabric(node):
    """Return the network address to be used by fabric to connect to the node

    By convention the address used is the address of its **second** network interface
    """
    return node.networks[1].address


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


SYSTEMD_SERVICE_CONTENTS = """
[Unit]
Description=Cassandra
After=network.target

[Service]
PIDFile=/var/lib/cassandra/cassandra.pid
User=cassandra
Group=cassandra
Environment=JAVA_HOME=/usr/java/jdk1.8.0_101
ExecStart=/usr/sbin/cassandra -f -p /var/lib/cassandra/cassandra.pid
StandardOutput=journal
StandardError=journal
LimitNOFILE=infinity
LimitMEMLOCK=infinity
Restart=always

[Install]
WantedBy=multi-user.target
"""


@task
@runs_once
def start():
    """Initialize the GlusterFS cluster and create the volumes"""
    execute(configure_service)
    execute(start_seeds)
    execute(start_others)
    cluster.status = 'running'
    print(green("All services started"))


@task
def configure_service():
    """Configure the GlusterFS filesystems"""
    generate_etc_hosts()
    modify_cassandra_yaml()
    modify_jvm_options()
    create_dirs()
    add_cassandra_to_systemd()
    #start_service()


def generate_etc_hosts():
    # Generate /etc/hosts
    for n in NODE.values():
        append('/etc/hosts', '{} {}'.format(n['eth0'], n['hostname']))


def modify_cassandra_yaml():
    """Modify cassandra.yaml configuration file"""
    CFG = '/etc/cassandra/conf/cassandra.yaml'
    #sed(CFG, "cluster_name: 'Test Cluster'", "cluster_name: 'BD Cassandra Cluster'")
    sed(CFG, 'Test Cluster', 'BD Cassandra Cluster')
    sed(CFG, '/var/lib/cassandra/commitlog', '/data/0/cassandra/commitlog')
    sed(CFG, '- /var/lib/cassandra/data', '- /data/1/cassandra/data')
    sed(CFG, '- seeds: "127.0.0.1"', '- seeds: "cassandranode0"')
    sed(CFG, 'endpoint_snitch: SimpleSnitch', 'endpoint_snitch: GossipingPropertyFileSnitch')
    # External network
    comment(CFG, r'^rpc_address: localhost$')
    uncomment(CFG, 'rpc_interface: eth1')
    # Inter-node network
    comment(CFG, r'^listen_address: localhost$')
    uncomment(CFG, 'listen_interface: eth0')


def create_dirs():
    """Create required dirs"""
    disks = [NODE[env.host][b] for b in NODE[env.host] if 'disk' in b]
    # commitlog goes into disk0
    run('mkdir -p /data/0/cassandra/commitlog')
    for disk in disks:
        run('mkdir -p {}/cassandra/data'.format(disk))
    run('chown -R cassandra /data/*/cassandra')
    if not exists('/var/run/cassandra'):
        run('mkdir /var/run/cassandra')
        run('chown cassandra /var/run/cassandra')


def modify_jvm_options():
    """Modify jvm.options configuration file"""
    CFG = '/etc/cassandra/conf/jvm.options'
    uncomment(CFG, r'-Xmx4G')
    uncomment(CFG, r'-Xms4G')
    sed(CFG, r'#-Xmn800M', '-Xmn200M')


def add_cassandra_to_systemd():
    """Add cassandra to systemd"""
    put(StringIO(SYSTEMD_SERVICE_CONTENTS), '/usr/lib/systemd/system/cassandra.service')
    if exists('/etc/rc.d/init.d/cassandra'):
        run('rm /etc/rc.d/init.d/cassandra')
    run('systemctl daemon-reload')
    run('systemctl enable cassandra')


@task
@roles('seeds')
def start_seeds():
    """Start the nodes that will act as the seeds"""
    #run('su cassandra -c "/usr/sbin/cassandra -p /var/run/cassandra/cassandra.pid"')
    run('systemctl start cassandra')


@task
@roles('others')
def start_others():
    """Start the rest of nodes (the ones that are not seeds)"""
    run('systemctl start cassandra')


@task
def status():
    """Check the status of the GlusterFS service"""
    print(yellow("== SERVICE STATUS =="))
    run('systemctl status cassandra')


@task
@runs_once
def stop():
    """Stop the GlusterFS service and all the containers that provide it"""
    with settings(warn_only=True):
        execute(stop_service)


@task
def stop_service():
    """Stop the GlusterFS service without stopping the containers"""
    run('systemctl stop cassandra')


@task
@runs_once
def restart():
    """Restart all the services of the cluster"""
    execute(stop)
    execute(start)


@task
@parallel
@roles('initiator')
def test():
    """Just run some test command"""
    run('uname -a')

#!/usr/bin/env python
# encoding: utf-8
"""Orquestration template

The following tasks must be implemented:
    - start
    - stop
    - restart
    - status

An instance endpoint has to be provided using the INSTANCE environment variable.
For example:

    INSTANCE="instances/test/reference/1.0.0/1"

A fabric roledef  is created for each service defined in the registry.
It can be used with the decorator: @roles('servicename1')

WARN: The hosts are accesed using the IP address of the first network device,
usually eth0.

The properties of a given service can be accessed through:

    SERVICES['servicename'].propertyname

for example:

    SERVICES['namenode'].heap

Details about a given node can be obtained through each Node object returned by service.nodes

The fabfile can be tested running it in NOOP mode (testing mode) exporting a NOOP env variable.
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

if os.environ.get('INSTANCE'):
    INSTANCE = os.environ.get('INSTANCE')
else:
    eprint(red('An instance endpoint has to be provided using the INSTANCE environment variable'))
    sys.exit(2)

if os.environ.get('REGISTRY'):
    REGISTRY = os.environ.get('REGISTRY')
else:
    REGISTRY = 'http://consul.service.int.cesga.es:8500/v1/kv'

# Retrieve info from the registry
registry.connect(REGISTRY)
cluster = registry.Cluster(INSTANCE)
nodes = cluster.nodes
services = cluster.services

# Expose the relevant information
NODES = {node.name: node for node in nodes}
SERVICES = {service.name: service for service in services}

env.user = 'root'
env.hosts = [n.networks[0].address for n in nodes]

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
    """Configure and start all the services required in the cluster"""
    execute(configure_service1)
    SERVICES['service1'].status = 'running'
    print(green("All services started"))


@task
@runs_once
def stop():
    """Stop all the services of the cluster"""
    with settings(warn_only=True):
        execute(stop_service1)
        SERVICES['service1'].status = 'stopped'


@task
@runs_once
def restart():
    """Restart all the services of the cluster"""
    run('/bin/hostname')


@task
@runs_once
def status():
    """Return the status of all the services of the cluster"""
    run('/bin/hostname')


@task
@roles('service1')
def configure_service1():
    """Configure service1"""
    run('/bin/hostname')


@task
@roles('service1')
def stop_service1():
    """Stop service1"""
    run('/bin/hostname')


@task
def test():
    """Print hostname"""
    run('/bin/hostname')


def eprint(*args, **kwargs):
    """Print to stderr"""
    print(*args, file=sys.stderr, **kwargs)

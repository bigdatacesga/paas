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

    INSTANCE="instances/user/cdh/5.7.0/1"

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
import json
from fabric.api import *
from fabric.colors import red, green, yellow
from fabric.contrib.files import exists
# FIXME: Installing configuration-registry with pip and importing registry directly does not work
#  inside the fabfile. Temporarily it is copied manually in the utils directory
import registry
#from utils import registry

if os.environ.get('INSTANCE'):
    INSTANCE = os.environ.get('INSTANCE')
else:
    #eprint(red('An instance endpoint has to be provided using the INSTANCE environment variable'))
    print(red('An instance endpoint has to be provided using the INSTANCE environment variable'))
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
OP = os.environ.get('OP')

print("OS is: " + OP)

def start():
    print("start")

def stop():
    print("stop")

def status():
    print("status")

def restart():
    print("restart")

if __name__ == "__main__":
    if OP is "start":
        start()
    elif OP is "stop":
        stop()
    elif OP is "status":
        status()
    elif OP is "restart":
        restart()
    else:
        print("Error")

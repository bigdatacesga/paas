CESGA Big Data Infrastructure
=======================

Big Data Services REST API
=======================

This repository contains a REST API built using Flask.

It is based on layout recommended by Miguel Grinberg on the 
[git repo](https://github.com/miguelgrinberg/oreilly-flask-apis-video.git)
of the [Building Web APIs with Flask](http://bit.ly/flaskapi) course.


-- To create virtual environment and instal dependencies
virtualenv venv
. venv/bin/activate
pip install -r requirements.txt

-- To run
cd rest
python run.py


This API will act as middleware between the user graphical interface, the cesga-big-data-services-webui project and the set of scripts and other software that will take care of the provisioning, registering, launching, managing and stopping of the various services provided.

Test with:

curl -X POST http://127.0.0.1:5000/bigdata/api/v1/services/ -d '{"service_type": "mpi", "service_name": "1.7.0", "cpu": 2, "mem": 2048, "num_nodes": 2, "num_disks": 2, "custom_disks": "False", "clustername": "testingPost"}' -H "Content-type: application/json"



Registering services
--------------------
POST /services

  {
    "name": "cdh",
    "version": "5.7.0",
    "description": "Hadoop cluster based on Cloudera CDH 5.7.0",
  }

ex:
curl -X POST http://127.0.0.1:5000/bigdata/api/v1/services/ -d '{"name":"cdh", "version":"1.0"}' -H "Content-type: application/json"


PUT /services/<name>/<version>/template

  data -> jinja2 json template: eg. service-template.json
  {% set comma = joiner(",") %}
    {
    "nodes": {
        "master0": {
            "name": "master0", "clustername": "X",
            "docker_image": "X", "docker_opts": "X",
            "port": "X", "check_ports": [22, 80, 443], "tags": ["yarn", "master"],
            "cpu": 1, "mem": 1024,
            "host": "X", "id": "X", "status": "X",
            "disks": {
                "disk1": {
                    "name": "disk1", "type": "ssd",
                    "origin": "/data/1/{{ instancename }}",
                    "destination": "/data/1", "mode": "rw"
                }
            },
            "networks": {
                "eth0": {
                    "networkname": "admin", "device": "X", "bridge": "X",
                    "address": "X", "gateway": "X", "netmask": "X"
                },
                "eth1": {
                    "networkname": "storage", "device": "X", "bridge": "X",
                    "address": "X", "gateway": "X", "netmask": "X"
                }
            },
            "services": ["yarn", "snamenode"]
        },
        "master1": {
            "name": "master1", "clustername": "X",
            "docker_image": "X", "docker_opts": "X",
            "port": "X", "check_ports": [22, 80, 443], "tags": ["namenode", "master"],
            "cpu": 1, "mem": 1024,
            "host": "X", "id": "X", "status": "X",
            "disks": {
                "disk1": {
                    "name": "disk1", "type": "ssd",
                    "origin": "/data/1/{{ instancename }}",
                    "destination": "/data/1", "mode": "rw"
                }
            },
            "networks": {
                "eth0": {
                    "networkname": "admin", "device": "X", "bridge": "X",
                    "address": "X", "gateway": "X", "netmask": "X"
                },
                "eth1": {
                    "networkname": "storage", "device": "X", "bridge": "X",
                    "address": "X", "gateway": "X", "netmask": "X"
                }
            },
            "services": ["namenode"]
        },
    {% for n in range(0, opts['slaves.number']) %}
        {{ comma() }} "slave{{ n }}": {
            "name": "slave{{ n }}", "clustername": "X",
            "docker_image": "X", "docker_opts": "X",
            "port": "X", "check_ports": [22, 4444], "tags": ["datanode", "slave"],
            "cpu": 1, "mem": 1024,
            "host": "X", "id": "X", "status": "X",
            "disks": { {% set comma = joiner(",") %}{% for k in range(0, opts['slaves.disks']) %}
                {{ comma() }} "disk{{ k }}": {
                    "name": "disk{{ k }}", "type": "sata",
                    "origin": "/data/{{ k }}/{{ instancename }}",
                    "destination": "/data/{{ k }}", "mode": "rw"
                } {% endfor %}
            },
            "networks": {
                "eth0": {
                    "networkname": "admin", "device": "X", "bridge": "X",
                    "address": "X", "gateway": "X", "netmask": "X"
                },
                "eth1": {
                    "networkname": "storage", "device": "X", "bridge": "X",
                    "address": "X", "gateway": "X", "netmask": "X"
                }
            },
            "services": ["datanode"]
        }
    {% endfor %}
    },
    "services": {
        "yarn": {
            "name": "yarn",
            "status": "running",
            "yarn.scheduler.minimum-allocation-vcores": 1,
            "nodes": ["master0"]
        },
        "datanode": {
            "name": "datanode",
            "status": "pending",
            "dfs.blocksize": {{ opts['dfs.blocksize'] }},
            "nodes": [{% set comma = joiner(",") %}{% for n in range(0, opts['slaves.number']) %}{{ comma() }}"slave{{ n }}"{% endfor %}]
        }
    }
    }

ex:
curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/services/cdh/1.0/template/ -d @template.txt -H "Content-type: application/text"

>>>>>>> 8f13b4ef6685658f4ddf77958fc11ebcf00a877b

PUT /services/<name>/<version>/options

  {
    "required": {
        "slaves.number": 4,
    },
    "optional": {
        "slaves.cpu": 2,
        "slaves.mem": 2048,
        "slaves.disks": 11
    },
    "advanced": {
        "datanode.heap": 1024
    },
    "descriptions": {
        "slaves.number": "Number of slave nodes",
        "slaves.cpu": "Number of cores per slave node",
        "slaves.mem": "Memory per slave node (MB)",
        "slaves.disks": "Number of disks per slave node",
        "datanode.heap": "Max heap memory for the datanode service"
    }
  }
ex:
curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/services/cdh/1.0/options/ -d @options.txt -H "Content-type: application/text"

PUT /services/<name>/<version>/options

  "Just a simple description of the service"
ex:
curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/services/cdh/1.0/description/ -d @description.txt -H "Content-type: application/text"


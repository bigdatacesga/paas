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
### POST /services

  {
    "name": "cdh",
    "version": "5.7.0",
    "description": "Hadoop cluster based on Cloudera CDH 5.7.0",
  }

curl -X POST http://127.0.0.1:5000/bigdata/api/v1/services -d '{"name":"gluster", "version":"3.7.11", "description": "GlusterFS parallel filesystem cluster"}' -H "Content-type: application/json"

### PUT /services/<name>/<version>/template

  jinja2 json template: eg. see service-template.json in configuration-registry module

curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/services/gluster/3.7.11/template --data-binary @service-template.json -H "Content-type: application/json"

### PUT /services/<name>/<version>/options

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

curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/services/gluster/3.7.11/options --data-binary @options.json -H "Content-type: application/json"

### PUT /services/<name>/<version>/orquestrator

    data -> orquestrator script to call to start the service

curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/services/gluster/3.7.11/orquestrator --data-binary @orquestrator.py -H "Content-type: application/json"

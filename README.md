Big Data PaaS REST API
======================

Installation
------------

    virtualenv venv
    . venv/bin/activate
    pip install -r requirements.txt
    python wsgi.py


The Big Data PaaS API has been designed using a microservices architecture which simplifies its deployment and allows for better scalability.
Different services are involved for registration, provisioning, scheduling and configuration.

Test with:

```
curl -H "Content-type: application/json" -X POST -d '{"size": 2, "disks": 2}' http://127.0.0.1:5000/bigdata/api/v1/services/gluster/3.7.11
```

Tracking instance status
------------------------
The status of a given instance can be tracked using instance.status:

    prepared
    submitted
    queued
    scheduled
    running


Launching instances
--------------------

curl -X POST http://127.0.0.1:5000/bigdata/api/v1/services/cdh/5.7.2 -d '{"slaves.number": 3}' -H "Content-type: application/json"



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

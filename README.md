Big Data PaaS REST API
======================

Introduction
------------
The Big Data PaaS API has been designed using a microservices architecture which simplifies its deployment and allows for better scalability.

Different services take care of registration, provisioning, scheduling and configuration.

Terminology
-----------
The following terms are used through the platform:

- Solutions: reserved for future use in a SaaS platform,
             eg. machine learning, data analysis dashboard

- Products: PaaS offers products,
            eg. CDH, mongodb, slurm

- Clusters: A given product is instantiated in a cluster which contains:

    - Nodes: each docker container of a cluster

    - Services: configuration specific for a service that will be applied
                to a given group of nodes that run the service


Installation
------------

    virtualenv venv
    . venv/bin/activate
    pip install -r requirements.txt
    python wsgi.py


Test with:

```
curl -H "Content-type: application/json" -X POST -d '{"size": 2}' http://127.0.0.1:5000/bigdata/api/v1/products/reference/1.0.0
----
http POST http://127.0.0.1:5000/bigdata/api/v1/products/reference/1.0.0 size:=2
```

Tracking cluster status
-----------------------
The status of a given cluster can be tracked using cluster.status:


    registered: the cluster instance has been registered in the registry
    scheduling: the scheduler (Mesos) is trying to allocate resources for the cluster
    scheduled: the scheduler has finished allocating resources and the executors have started
    configuring: the orchestrator is configuring the cluster
    configured: the orchestrator has finished configuring the cluster
    ready: the cluster is ready
    destroyed: the cluster has been destroyed

Each microservice manages its own set of status:

    registry:     ----------  -> registered
    framework:    scheduling  -> scheduled
    orchestrator: configuring -> configured

Launching clusters
------------------

### POST /products/<name>/<version>
  {
    "size": "2"
  }

```
curl -H "Content-type: application/json" -X POST -d '{"size": 2}' http://127.0.0.1:5000/bigdata/api/v1/products/reference/1.0.0
----
http POST http://127.0.0.1:5000/bigdata/api/v1/products/reference/1.0.0 size:=2
```

The required options are defined in the corresponding product options:

    curl http://127.0.0.1:5000/bigdata/api/v1/products/reference/1.0.0/options

Registering products
--------------------
### POST /products

  {
    "name": "cdh",
    "version": "5.7.0",
    "description": "Hadoop cluster based on Cloudera CDH 5.7.0",
  }

```
http POST http://127.0.0.1:5000/bigdata/api/v1/products name=reference version=1.0.0 description='Reference product: minimal'
curl -X POST http://127.0.0.1:5000/bigdata/api/v1/products -d '{"name":"gluster", "version":"3.7.11", "description": "GlusterFS parallel filesystem cluster"}' -H "Content-type: application/json"
```


### PUT /products/<name>/<version>/template

  jinja2 json template: eg. see service-template.json in configuration-registry module

curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/products/reference/1.0.0/template --data-binary @minimal.json -H "Content-type: application/json"

### PUT /products/<name>/<version>/options

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

curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/products/gluster/3.7.11/options --data-binary @options.json -H "Content-type: application/json"
curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/products/reference/1.0.0/options --data-binary @options/size.json -H "Content-type: application/json"

### PUT /products/<name>/<version>/orquestrator

    data -> orquestrator script to call to start the service

curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/products/gluster/3.7.11/orquestrator --data-binary @orquestrator.py -H "Content-type: application/json"
curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/products/reference/1.0.0/orquestrator --data-binary @orquestrators/minimal/fabfile.py -H "Content-type: application/json"

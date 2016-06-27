Orquestration template
======================

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

How to run
----------
In NOOP mode (no changes applied in the nodes):

    INSTANCE="instances/jlopez/cdh/5.7.0/1" NOOP=1 fab start
    INSTANCE="instances/jlopez/cdh/5.7.0/1" NOOP=1 fab stop

WARN: In NOOP mode the status of the services will still be changed in the registry.

In normal mode:

    INSTANCE="instances/jlopez/cdh/5.7.0/1" fab start


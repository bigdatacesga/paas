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

WARN: The hosts are accesed using the IP address of the second network device,
usually eth1.

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
from fabric.colors import red, green, yellow, blue
from fabric.contrib.files import exists, append, sed, comment, uncomment
# FIXME: Installing configuration-registry with pip and importing registry directly does not work
#  inside the fabfile. Temporarily it is copied manually in the utils directory
#from utils import registry
# In the big data nodes configuration-registry is installed globally
import registry
import time
from pprint import pprint
from StringIO import StringIO
import jinja2


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


def external_address(node):
    """Return the network address to be used by fabric to connect to the node

    By convention the address used is the address of its **second** network interface
    """
    return node.networks[1].address


def internal_address(node):
    """Return the network address to be used internally by the cluster

    By convention the address used is the address of its **first** network interface
    """
    return node.networks[0].address


def put_template(tmpl_string, dest, **kwargs):
    """Upload a template contained in tmpl_string to the dest path
       The kwargs are passed as context to the template
    """
    t = jinja2.Template(tmpl_string)
    rendered = t.render(**kwargs)
    put(StringIO(rendered), dest)


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
    properties['address_int'] = internal_address(node)
    properties['address_ext'] = external_address(node)
    # The node is labeled with the network address that will be used by fabric
    # to connect to the node, this allows to retrieve the node using NODE[env.host]
    label = external_address(node)
    NODE[label] = properties


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
    env.roledefs[service.name] = [external_address(n) for n in service.nodes]

# Define also a global var ROLE to be used for internal cluster configuration
ROLE = {}
for service in services:
    ROLE[service.name] = [internal_address(n) for n in service.nodes]

print(blue('= Summary of cluster information ='))
print('== NODE ==')
pprint(NODE)
print('== Fabric roles ==')
pprint(env.roledefs)
print('== ROLE ==')
pprint(ROLE)
print(blue('= End of summary ='))

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


#
# CONFIGURATION FILE TEMPLATES
#
# /usr/lib/systemd/system/cassandra.service
CASSANDRA_SERVICE = """# /usr/lib/systemd/system/cassandra.service

[Unit]
Description=Cassandra
After=network.target

[Service]
#Type=forking
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
# /etc/cassandra/conf/cassandra.yaml
CASSANDRA_YAML = """# Cassandra storage config YAML
#   See http://wiki.apache.org/cassandra/StorageConfiguration for
#   full explanations of configuration directives
cluster_name: '{{ p['cluster_name'] }}'
num_tokens: 256
hinted_handoff_enabled: true
max_hint_window_in_ms: 10800000 # 3 hours
hinted_handoff_throttle_in_kb: 1024
max_hints_delivery_threads: 2
hints_directory: /var/lib/cassandra/hints
hints_flush_period_in_ms: 10000
max_hints_file_size_in_mb: 128
batchlog_replay_throttle_in_kb: 1024
authenticator: AllowAllAuthenticator
authorizer: AllowAllAuthorizer
role_manager: CassandraRoleManager
roles_validity_in_ms: 2000
permissions_validity_in_ms: 2000
partitioner: org.apache.cassandra.dht.Murmur3Partitioner
data_file_directories:
{% for data_dir in p['data_file_directories'] %}
- {{ data_dir }}
{% endfor %}
commitlog_directory: {{ p['commitlog_directory'] }}
disk_failure_policy: stop
commit_failure_policy: stop
key_cache_size_in_mb:
key_cache_save_period: 14400
row_cache_size_in_mb: 0
row_cache_save_period: 0
counter_cache_size_in_mb:
counter_cache_save_period: 7200
saved_caches_directory: /var/lib/cassandra/saved_caches
commitlog_sync: periodic
commitlog_sync_period_in_ms: 10000
commitlog_segment_size_in_mb: 32
seed_provider:
    - class_name: org.apache.cassandra.locator.SimpleSeedProvider
      parameters:
          - seeds: "{{ p['seeds']|join(',') }}"
concurrent_reads: 32
concurrent_writes: 32
concurrent_counter_writes: 32
concurrent_materialized_view_writes: 32
memtable_allocation_type: heap_buffers
index_summary_capacity_in_mb:
index_summary_resize_interval_in_minutes: 60
trickle_fsync: false
trickle_fsync_interval_in_kb: 10240
storage_port: 7000
ssl_storage_port: 7001
listen_interface: {{ p['listen_interface'] }}
start_native_transport: true
native_transport_port: 9042
start_rpc: false
rpc_interface: {{ p['rpc_interface'] }}
rpc_port: 9160
rpc_keepalive: true
rpc_server_type: sync
thrift_framed_transport_size_in_mb: 15
incremental_backups: false
snapshot_before_compaction: false
auto_snapshot: true
tombstone_warn_threshold: 1000
tombstone_failure_threshold: 100000
column_index_size_in_kb: 64
batch_size_warn_threshold_in_kb: 5
batch_size_fail_threshold_in_kb: 50
unlogged_batch_across_partitions_warn_threshold: 10
compaction_throughput_mb_per_sec: 16
compaction_large_partition_warning_threshold_mb: 100
sstable_preemptive_open_interval_in_mb: 50
read_request_timeout_in_ms: 5000
range_request_timeout_in_ms: 10000
write_request_timeout_in_ms: 2000
counter_write_request_timeout_in_ms: 5000
cas_contention_timeout_in_ms: 1000
truncate_request_timeout_in_ms: 60000
request_timeout_in_ms: 10000
cross_node_timeout: false
endpoint_snitch: GossipingPropertyFileSnitch
dynamic_snitch_update_interval_in_ms: 100 
dynamic_snitch_reset_interval_in_ms: 600000
dynamic_snitch_badness_threshold: 0.1
request_scheduler: org.apache.cassandra.scheduler.NoScheduler
server_encryption_options:
    internode_encryption: none
    keystore: conf/.keystore
    keystore_password: cassandra
    truststore: conf/.truststore
    truststore_password: cassandra
client_encryption_options:
    enabled: false
    optional: false
    keystore: conf/.keystore
    keystore_password: cassandra
internode_compression: all
inter_dc_tcp_nodelay: false
tracetype_query_ttl: 86400
tracetype_repair_ttl: 604800
gc_warn_threshold_in_ms: 1000
enable_user_defined_functions: false
enable_scripted_user_defined_functions: false
windows_timer_interval: 1
"""
# /etc/cassandra/conf/jvm.options
JVM_OPTIONS = """###########################################################################
#                             jvm.options                                 #
#                                                                         #
# - all flags defined here will be used by cassandra to startup the JVM   #
# - one flag should be specified per line                                 #
# - lines that do not start with '-' will be ignored                      #
# - only static flags are accepted (no variables or parameters)           #
# - dynamic flags will be appended to these on cassandra-env              #
###########################################################################

#################
# HEAP SETTINGS #
#################

# Heap size is automatically calculated by cassandra-env based on this
# formula: max(min(1/2 ram, 1024MB), min(1/4 ram, 8GB))
# That is:
# - calculate 1/2 ram and cap to 1024MB
# - calculate 1/4 ram and cap to 8192MB
# - pick the max
#
# For production use you may wish to adjust this for your environment.
# If that's the case, uncomment the -Xmx and Xms options below to override the
# automatic calculation of JVM heap memory.
#
# It is recommended to set min (-Xms) and max (-Xmx) heap sizes to
# the same value to avoid stop-the-world GC pauses during resize, and
# so that we can lock the heap in memory on startup to prevent any
# of it from being swapped out.
-Xms{{ max_heap_size }}
-Xmx{{ initial_heap_size }}

# Young generation size is automatically calculated by cassandra-env
# based on this formula: min(100 * num_cores, 1/4 * heap size)
#
# The main trade-off for the young generation is that the larger it
# is, the longer GC pause times will be. The shorter it is, the more
# expensive GC will be (usually).
#
# It is not recommended to set the young generation size if using the
# G1 GC, since that will override the target pause-time goal.
# More info: http://www.oracle.com/technetwork/articles/java/g1gc-1984535.html
#
# The example below assumes a modern 8-core+ machine for decent
# times. If in doubt, and if you do not particularly want to tweak, go
# 100 MB per physical CPU core.
-Xmn{{ young_generation_size }}

#################
#  GC SETTINGS  #
#################

### CMS Settings

-XX:+UseParNewGC
-XX:+UseConcMarkSweepGC
-XX:+CMSParallelRemarkEnabled
-XX:SurvivorRatio=8
-XX:MaxTenuringThreshold=1
-XX:CMSInitiatingOccupancyFraction=75
-XX:+UseCMSInitiatingOccupancyOnly
-XX:CMSWaitDuration=10000
-XX:+CMSParallelInitialMarkEnabled
-XX:+CMSEdenChunksRecordAlways
# some JVMs will fill up their heap when accessed via JMX, see CASSANDRA-6541
-XX:+CMSClassUnloadingEnabled

### G1 Settings (experimental, comment previous section and uncomment section below to enable)

## Use the Hotspot garbage-first collector.
#-XX:+UseG1GC
#
## Have the JVM do less remembered set work during STW, instead
## preferring concurrent GC. Reduces p99.9 latency.
#-XX:G1RSetUpdatingPauseTimePercent=5
#
## Main G1GC tunable: lowering the pause target will lower throughput and vise versa.
## 200ms is the JVM default and lowest viable setting
## 1000ms increases throughput. Keep it smaller than the timeouts in cassandra.yaml.
#-XX:MaxGCPauseMillis=500

## Optional G1 Settings

# Save CPU time on large (>= 16GB) heaps by delaying region scanning
# until the heap is 70% full. The default in Hotspot 8u40 is 40%.
#-XX:InitiatingHeapOccupancyPercent=70

# For systems with > 8 cores, the default ParallelGCThreads is 5/8 the number of logical cores.
# Otherwise equal to the number of cores when 8 or less.
# Machines with > 10 cores should try setting these to <= full cores.
#-XX:ParallelGCThreads=16
# By default, ConcGCThreads is 1/4 of ParallelGCThreads.
# Setting both to the same value can reduce STW durations.
#-XX:ConcGCThreads=16

### GC logging options -- uncomment to enable

-XX:+PrintGCDetails
-XX:+PrintGCDateStamps
-XX:+PrintHeapAtGC
-XX:+PrintTenuringDistribution
-XX:+PrintGCApplicationStoppedTime
-XX:+PrintPromotionFailure
#-XX:PrintFLSStatistics=1
#-Xloggc:/var/log/cassandra/gc.log
-XX:+UseGCLogFileRotation
-XX:NumberOfGCLogFiles=10
-XX:GCLogFileSize=10M
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


def generate_etc_hosts():
    """Generate the /etc/hosts file using internal cluster addresses"""
    for n in NODE.values():
        append('/etc/hosts', '{} {}'.format(n['address_int'], n['hostname']))


def modify_cassandra_yaml():
    """Modify cassandra.yaml configuration file"""
    node = NODE[env.host]
    disk_paths = sorted([node[p] for p in node if 'disk' in p])

    p = {}
    p['cluster_name'] = cluster.name
    # By convention we place commitlog into the first disk path and the rest
    # are used as data file directories
    p['data_file_directories'] = ['{}/cassandra/data'.format(d) for d in disk_paths[1:]]
    p['commitlog_directory'] = '{}/cassandra/commitlog'.format(disk_paths[0])
    p['seeds'] = ROLE['seeds']
    p['listen_interface'] = 'eth0'
    p['rpc_interface'] = 'eth1'

    put_template(CASSANDRA_YAML, '/etc/cassandra/conf/cassandra.yaml', p=p)


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
    cassandra = SERVICES['cassandra']
    max_heap_size = cassandra.get('max_heap_size', '4G')
    initial_heap_size = cassandra.get('initial_heap_size', '4G')
    young_generation_size = cassandra.get('young_generation_size' ,'200M')
    put_template(JVM_OPTIONS, '/etc/cassandra/conf/jvm.options',
                 max_heap_size=max_heap_size,
                 initial_heap_size=initial_heap_size,
                 young_generation_size=young_generation_size)


def add_cassandra_to_systemd():
    """Add cassandra to systemd"""
    put(StringIO(CASSANDRA_SERVICE), '/usr/lib/systemd/system/cassandra.service')
    if exists('/etc/rc.d/init.d/cassandra'):
        run('rm /etc/rc.d/init.d/cassandra')
    run('systemctl daemon-reload')
    run('systemctl enable cassandra')


@task
@roles('seeds')
def start_seeds():
    """Start the nodes that will act as the seeds"""
    run('systemctl start cassandra')


@task
@roles('others')
def start_others():
    """Start the rest of nodes (the ones that are not seeds)"""
    run('systemctl start cassandra')


@task
def status():
    """Check the status of the GlusterFS service"""
    run('nodetool status')


@task
@runs_once
def stop():
    """Stop the GlusterFS service and all the containers that provide it"""
    with settings(warn_only=True):
        execute(stop_service)


@task
def stop_service():
    """Stop the Cassandra service"""
    run('systemctl stop cassandra')


@task
@runs_once
def restart():
    """Restart all the services of the cluster"""
    execute(stop)
    execute(start)

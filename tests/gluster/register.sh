# First get a TOKEN
# export TOKEN='<TOKEN>'
# export AUTH="x-auth-token: $TOKEN"
http POST http://paas:5000/bigdata/api/v1/products name=gluster version=3.7.11 description='GlusterFS cluster with a default distributed-replicated file system' x-auth-token:$TOKEN
curl -X PUT http://paas:5000/bigdata/api/v1/products/gluster/3.7.11/template --data-binary @template.json -H "Content-type: application/json" -H "$AUTH"
curl -X PUT http://paas:5000/bigdata/api/v1/products/gluster/3.7.11/options --data-binary @options.json -H "$AUTH"
curl -X PUT http://paas:5000/bigdata/api/v1/products/gluster/3.7.11/orchestrator --data-binary @fabfile.py -H "$AUTH"

# Launching
# http POST http://paas:5000/bigdata/api/v1/products/gluster/3.7.11 size:=2 x-auth-token:$TOKEN

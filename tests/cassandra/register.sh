# First get a TOKEN
# export TOKEN='<TOKEN>'
# export AUTH="x-auth-token: $TOKEN"
http POST http://paas:6000/bigdata/api/v1/products name=cassandra version=3.0.8 description='The Cassandra database is the right choice when you need scalability and high availability without compromising performance.' x-auth-token:$TOKEN
curl -X PUT http://paas:6000/bigdata/api/v1/products/cassandra/3.0.8/template --data-binary @template.json -H "Content-type: application/json" -H "$AUTH"
curl -X PUT http://paas:6000/bigdata/api/v1/products/cassandra/3.0.8/options --data-binary @options.json -H "$AUTH"
curl -X PUT http://paas:6000/bigdata/api/v1/products/cassandra/3.0.8/orchestrator --data-binary @fabfile.py -H "$AUTH"

# Launching
# http POST http://paas:6000/bigdata/api/v1/products/cassandra/3.0.8 size:=2 x-auth-token:$TOKEN

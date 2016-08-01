# First get a TOKEN
# export TOKEN='<TOKEN>'
# export AUTH="x-auth-token: $TOKEN"
http POST http://paas:6000/bigdata/api/v1/products name=mongodb version=3.2.8 description='MongoDB is a free and open-source cross-platform document-oriented database.' logo_url='http://hadoop.cesga.es/img/mongodb-for-giant-ideas-bbab5c3cf8.png' x-auth-token:$TOKEN
curl -X PUT http://paas:6000/bigdata/api/v1/products/mongodb/3.2.8/template --data-binary @template.json -H "Content-type: application/json" -H "$AUTH"
curl -X PUT http://paas:6000/bigdata/api/v1/products/mongodb/3.2.8/options --data-binary @options.json -H "$AUTH"
curl -X PUT http://paas:6000/bigdata/api/v1/products/mongodb/3.2.8/orchestrator --data-binary @fabfile.py -H "$AUTH"

# Launching
# http POST http://paas:6000/bigdata/api/v1/products/mongodb/3.2.8 size:=2 x-auth-token:$TOKEN

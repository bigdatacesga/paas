# Minimal: JSON
http POST http://127.0.0.1:5000/bigdata/api/v1/products name=reference version=1.0.0 description='Reference product: minimal'
curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/products/reference/1.0.0/template --data-binary @templates/minimal.json -H "Content-type: application/json"
curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/products/reference/1.0.0/options --data-binary @options/size.json
curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/products/reference/1.0.0/orquestrator --data-binary @orquestrators/minimal/fabfile.py
# Minimal: YAML
http POST http://127.0.0.1:5000/bigdata/api/v1/products name=reference version=1.0.0-yaml description='Reference product: minimal (yaml version)'
curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/products/reference/1.0.0-yaml/template --data-binary @templates/minimal.yaml -H "Content-type: application/yaml"
curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/products/reference/1.0.0-yaml/options --data-binary @options/size.json
curl -X PUT http://127.0.0.1:5000/bigdata/api/v1/products/reference/1.0.0-yaml/orquestrator --data-binary @orquestrators/minimal/fabfile.py

"""Tests for the paas service REST API"""
import unittest
import registry
import test_client as tc
from app.v1 import user_endpoints

ENDPOINT = 'http://consul:8500/v1/kv'

class paas_TestCase(unittest.TestCase):

    def setUp(self):
        self.client = tc.TestClient(self.app, "jenes", "bogus")
        #self.registry = registry.connect(ENDPOINT)

    def tearDown(self):
        pass

    def test_post_service(self):
        self.client.post()

    def test_get_service(self):
        rv, json = self.client.get('/services')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['services'])
from django.test import TestCase
from django.test.client import Client
from xformmanager.tests.util import create_xsd_and_populate
from xformmanager.models import *
from hq.models import ExtUser

class APITestCase(TestCase):
    def setUp(self):
        # we cannot load this using django built-in fixtures
        # because django filters are model dependent
        # (and we have a whack of dynamically generated non-model db tables)
        domain = Domain(name='mockdomain')
        domain.save()
        user = ExtUser()
        user.domain = domain
        user.username = 'jewelstaite'
        user.password = 'sha1$245de$137d06d752eee1885a6bbd1e40cbe9150043dd5e'
        user.save()
        create_xsd_and_populate("data/brac_chw.xsd", "data/brac_chw_1.xml", domain)
        response = self.client.post('/accounts/login/', \
                         {'username': 'jewelstaite', 'password': 'test'})
        # the login screen always gives a 302 - temporarily relocated response
        self.assertStatus(response, 302)
        pass

    def test_api_calls(self):
        # test the actual URL plus the non APPEND_SLASH url
        # (django should return 301 - permanently moved)
        response = self.client.get('/api')
        self.assertStatus(response, 301)
        response = self.client.get('/api/')
        self.assertStatus(response, 200)
        response = self.client.get('/api/xforms')
        self.assertStatus(response, 301)
        response = self.client.get('/api/xforms/')
        self.assertStatus(response, 200)
        response = self.client.get('/api/xforms/1')
        self.assertStatus(response, 301)
        response = self.client.get('/api/xforms/1/')
        self.assertStatus(response, 200)
        response = self.client.get('/api/xforms/1/1')
        self.assertStatus(response, 301)
        response = self.client.get('/api/xforms/1/1/')
        self.assertStatus(response, 200)
        
        # because the URLs do not end in '$', then both 
        # of these URL pairs are caught by the same expression
        response = self.client.get('/api/xforms/1/schema')
        self.assertStatus(response, 200)
        response = self.client.get('/api/xforms/1/schema/')
        self.assertStatus(response, 200)
        response = self.client.get('/api/xforms/1/metadata')
        self.assertStatus(response, 200)
        response = self.client.get('/api/xforms/1/metadata/')
        self.assertStatus(response, 200)
        response = self.client.get('/api/xforms/1/1/metadata')
        self.assertStatus(response, 200)
        response = self.client.get('/api/xforms/1/1/metadata/')
        self.assertStatus(response, 200)

    def assertStatus(self, response, status):
        if response.status_code != status:
            print "ERROR :" + response.content    
        self.failUnlessEqual(response.status_code, status)

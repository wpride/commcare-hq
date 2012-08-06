#from django.conf.urls.defaults import patterns, url
from django.conf.urls.defaults import *

urlpatterns = patterns('corehq.apps.sms.views',
    url(r'^post/?$', 'post', name='sms_post'),
    url(r'^send_to_recipients/$', 'send_to_recipients'),
    url(r'^compose/$', 'compose_message', name='sms_compose_message'),
    url(r'^message_test/(?P<phone_number>\d+)/$', 'message_test', name='message_test'),
    url(r'^api/send_sms/$', 'api_send_sms', name='api_send_sms'),
    url(r'^$', 'messaging', name='messaging'),
)

global_urls = patterns('corehq.apps.sms.views',
    url(r'^add/?$', 'add_backend', name='add_sms_backend'),
    url(r'^(?P<backend_id>[\w-]+)/remove?$', 'remove_backend', name='remove_sms_backend'),
    url(r'^$', 'sms_backends', name='sms_backends'),
)

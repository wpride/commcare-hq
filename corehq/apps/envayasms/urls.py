from django.conf.urls.defaults import *

urlpatterns = patterns('corehq.apps.envayasms.views',
    url(r'^$', 'receive_action', name='receive_envayasms_action'),
)

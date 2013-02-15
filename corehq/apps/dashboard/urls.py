from django.conf.urls.defaults import *
from corehq.apps.dashboard.views import HQDomainDashboardView

urlpatterns = patterns('corehq.apps.dashboard.views',
)

domain_specific = patterns('corehq.apps.dashboard.views',
    url(r'^$', HQDomainDashboardView.as_view(), name='domain_dashboard'),
)

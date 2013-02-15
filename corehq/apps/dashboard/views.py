from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from corehq.apps.domain.decorators import login_and_domain_required
from dimagi.utils.decorators.memoized import memoized


class HQDomainDashboardView(TemplateView):
    template_name = "dashboard/dashboard_base.html"

    @property
    @memoized
    def domain(self):
        return self.request_args[0]

    @method_decorator(login_and_domain_required)
    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.request_args = args
        self.context = {
            "domain": self.domain,
            "project": self.domain,
        }

        return render(request, self.template_name, self.context)


from django.template.defaultfilters import slugify
from corehq.apps.reports.api import ReportApiSource, ConfigItemMeta, CONFIG_TYPE_DATE, IndicatorMeta
from corehq.apps.reports.dispatcher import datespan_default
from corehq.apps.reports.fields import ReportField, DatespanField
from corehq.apps.reports.sqlreport import SqlDataApi
from dimagi.utils.decorators.memoized import memoized
from tastypie import fields
from tastypie.bundle import Bundle
from corehq.apps.api.resources import JsonResource
from corehq.apps.api.resources.v0_1 import CustomResourceMeta
from corehq.apps.reports.datatables import DataTablesColumnGroup
from corehq.apps.reports.filters.base import BaseReportFilter, BaseSingleOptionFilter


class DetailURIResource(object):
    def detail_uri_kwargs(self, bundle_or_obj):
        """
        Given a ``Bundle`` or an object (typically a ``Model`` instance),
        it returns the extra kwargs needed to generate a detail URI.
        """
        kwargs = {}

        try:
            if isinstance(bundle_or_obj, Bundle):
                kwargs[self._meta.detail_uri_name] = getattr(bundle_or_obj.obj, self._meta.detail_uri_name)
            else:
                kwargs[self._meta.detail_uri_name] = getattr(bundle_or_obj, self._meta.detail_uri_name)
        except AttributeError:
            pass

        return kwargs


class ReportResource(DetailURIResource, JsonResource):
    meta_fields = {
        'config': 'config_meta',
        'indicators': 'indicators_meta',
        'indicator_groups': 'indicator_groups_meta'
    }
    type = "report"
    slug = fields.CharField(attribute='slug', readonly=True, unique=True)
    name = fields.CharField(attribute='name', readonly=True)
    config = fields.ListField(attribute='config_meta', readonly=True)
    indicators = fields.ListField(attribute='indicators_meta', readonly=True)
    indicator_groups = fields.ListField(attribute='indicator_groups_meta', readonly=True, null=True)
    results = fields.ListField(attribute='results', readonly=True, null=True)

    def dehydrate(self, bundle):
        full = bundle.request.GET.get('full')
        has_results = bool(bundle.obj.results)
        if full or not has_results:
            for field, attribute in self.meta_fields.items():
                v = getattr(bundle.obj, attribute, None) or []
                bundle.data[field] = [a.to_json() for a in v]

        if not full and has_results:
            for f in self.meta_fields:
                del bundle.data[f]

        if not has_results:
            del bundle.data['results']

        return bundle

    def obj_get(self, bundle, **kwargs):
        domain = kwargs['domain']
        slug = kwargs['slug']
        request = self._get_request(bundle.request)
        return TestReport(request=request, domain=domain)

    @datespan_default
    def _get_request(self, request):
        return request

    def obj_get_list(self, bundle, **kwargs):
        from benin.reports import MEGeneral
        domain = kwargs['domain']
        return [TestReport(request=bundle.request, domain=domain)]

    class Meta(CustomResourceMeta):
        object_class = ReportApiSource
        resource_name = 'report'
        detail_uri_name = 'slug'
        allowed_methods = ['get']
        collection_name = 'reports'

#
# class GenericTabularReportAPIMixin(BaseReportResourceModel):
#     value_excludes = ['---', '--', '']
#     _groups = []
#
#     @property
#     @memoized
#     def config(self):
#         configs = []
#         for f in self.filter_classes:
#             if isinstance(f, BaseSingleOptionFilter):
#                 configs.append(ConfigItem(f.slug, f.label, 'select',
#                                           options=f.options,
#                                           default=f.selected,
#                                           description=f.help_text))
#             elif isinstance(f, BaseReportFilter):
#                 configs.append(ConfigItem(f.slug, f.label, 'unknown',
#                                           description=f.help_text))
#             elif isinstance(f, DatespanField):
#                 configs.append(ConfigItem('startdate', 'Date range start', 'date'))
#                 configs.append(ConfigItem('enddate', 'Date range end', 'date'))
#             elif isinstance(f, ReportField):
#                 configs.append(ConfigItem(f.slug, f.name, 'unknown'))
#
#         return configs
#
#     @property
#     @memoized
#     def indicators(self):
#         indicators = []
#         self._add_indicators(indicators, self.headers)
#         return indicators
#
#     def _add_indicators(self, indicators, headers, group=None):
#         for h in headers:
#             if isinstance(h, DataTablesColumnGroup):
#                 group = slugify(h.html)
#                 if group not in self._groups:
#                     self._groups.append(Group(group, h.html))
#
#                 self._add_indicators(indicators, h, group=group)
#             else:
#                 indicators.append(Indicator(slugify(h.html), h.html, group=group, description=h.help_text))
#
#     @property
#     def indicator_groups(self):
#         self.indicators
#         return self._groups
#
#     @property
#     @memoized
#     def results(self):
#         if self.needs_filters:
#             return None
#
#         results = []
#         rows = self.rows
#         for r in rows:
#             row = dict()
#             for i, ind in enumerate(self.indicators):
#                 value = r[i].get('sort_key') if isinstance(r[i], dict) else r[i]
#                 if value not in self.value_excludes:
#                     row[ind.slug] = value
#
#             results.append(row)
#
#         return results


class TestReport(ReportApiSource):
    slug = 'test'
    name = 'Test'

    @property
    def config_meta(self):
        return [ConfigItemMeta('date', 'Date', CONFIG_TYPE_DATE)]

    @property
    def indicators_meta(self):
        return [IndicatorMeta('test', 'Test')]

    @property
    def results(self):
        return None


class TestSqlReport(SqlDataApi):
    sqldata_class = ChildProtectionData

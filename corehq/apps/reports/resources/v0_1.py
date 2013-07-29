from django.template.defaultfilters import slugify
from corehq.apps.reports.dispatcher import datespan_default
from corehq.apps.reports.fields import ReportField, DatespanField
from dimagi.utils.decorators.memoized import memoized
from tastypie import fields
from tastypie.bundle import Bundle
from corehq.apps.api.resources import JsonResource
from corehq.apps.api.resources.v0_1 import CustomResourceMeta
from corehq.apps.reports.datatables import DataTablesColumnGroup
from corehq.apps.reports.filters.base import BaseReportFilter, BaseSingleOptionFilter


class BaseModel(object):
    """
    Assumes class will be instantiated with ``fields`` as 'args' and
    ``optional_fields`` as 'kwargs'.

    Ordering of args must be correct.
    """
    fields = []
    optional_fields = []

    def __init__(self, *args, **kwargs):
        if not len(args) == len(self.fields):
            raise Exception("Unexpected fields. Expected '%s', got '%s'" % (self.fields, args))

        self._attrs = dict(zip(self.fields, args))
        for f in self.optional_fields:
            v = kwargs.get(f, None)
            if v:
                self._attrs[f] = v

        self.validate()

    def validate(self):
        pass

    def to_json(self):
        return self._attrs


class BaseReportResourceModel(object):
    slug = ''
    name = ''

    def __init__(self, request=None, domain=None):
        self.request = request
        self.domain = domain

    @property
    def config(self):
        """
        Return a list of ReportResourceConfig instances.
        """
        return []

    @property
    def indicators(self):
        """
        Return a list of Indicator instances.
        """
        return []

    @property
    def indicator_groups(self):
        """
        Return a list of Group instances.
        """
        return []


class ConfigItem(BaseModel):
    fields = ['slug', 'name', 'data_type']
    optional_fields = ['options', 'default', 'description']

    def validate(self):
        if self._attrs['data_type'] not in ['string', 'integer', 'date', 'datetime', 'select']:
            return False


class Indicator(BaseModel):
    fields = ['slug', 'name']
    optional_fields = ['group', 'description']


class Group(BaseModel):
    fields = ['slug', 'name']
    optional_fields = ['description']


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
    meta_fields = ['config', 'indicators', 'indicator_groups']
    type = "report"
    slug = fields.CharField(attribute='slug', readonly=True, unique=True)
    name = fields.CharField(attribute='name', readonly=True)
    config = fields.ListField(attribute='config', readonly=True)
    indicators = fields.ListField(attribute='indicators', readonly=True)
    groups = fields.ListField(attribute='indicator_groups', readonly=True, null=True)
    results = fields.ListField(attribute='results', readonly=True, null=True)

    def dehydrate(self, bundle):
        full = bundle.request.GET.get('full')
        if full or not bundle.obj.results:
            for f in self.meta_fields:
                v = getattr(bundle.obj, f) or []
                bundle.data[f] = [a.to_json() for a in v]

        if not full and bundle.obj.results:
            for f in self.meta_fields:
                del bundle.data[f]

        return bundle

    def obj_get(self, bundle, **kwargs):
        from benin.reports import MEGeneral
        domain = kwargs['domain']
        slug = kwargs['slug']
        request = self._get_request(bundle.request)
        return MEGeneral(request, domain=domain)

    @datespan_default
    def _get_request(self, request):
        return request

    def obj_get_list(self, bundle, **kwargs):
        from benin.reports import MEGeneral
        domain = kwargs['domain']
        return [MEGeneral(bundle.request, domain=domain), TestReport(bundle.request, domain=domain)]

    class Meta(CustomResourceMeta):
        object_class = BaseReportResourceModel
        resource_name = 'report'
        detail_uri_name = 'slug'


class GenericTabularReportAPIMixin(BaseReportResourceModel):
    value_excludes = ['---', '--', '']
    _groups = []

    @property
    @memoized
    def config(self):
        configs = []
        for f in self.filter_classes:
            if isinstance(f, BaseSingleOptionFilter):
                configs.append(ConfigItem(f.slug, f.label, 'select',
                                          options=f.options,
                                          default=f.selected,
                                          description=f.help_text))
            elif isinstance(f, BaseReportFilter):
                configs.append(ConfigItem(f.slug, f.label, 'unknown',
                                          description=f.help_text))
            elif isinstance(f, DatespanField):
                configs.append(ConfigItem('startdate', 'Date range start', 'date'))
                configs.append(ConfigItem('enddate', 'Date range end', 'date'))
            elif isinstance(f, ReportField):
                configs.append(ConfigItem(f.slug, f.name, 'unknown'))

        return configs

    @property
    @memoized
    def indicators(self):
        indicators = []
        self._add_indicators(indicators, self.headers)
        return indicators

    def _add_indicators(self, indicators, headers, group=None):
        for h in headers:
            if isinstance(h, DataTablesColumnGroup):
                group = slugify(h.html)
                if group not in self._groups:
                    self._groups.append(Group(group, h.html))

                self._add_indicators(indicators, h, group=group)
            else:
                indicators.append(Indicator(slugify(h.html), h.html, group=group, description=h.help_text))

    @property
    def indicator_groups(self):
        self.indicators
        return self._groups

    @property
    @memoized
    def results(self):
        if self.needs_filters:
            return None

        results = []
        rows = self.rows
        for r in rows:
            row = dict()
            for i, ind in enumerate(self.indicators):
                value = r[i].get('sort_key') if isinstance(r[i], dict) else r[i]
                if value not in self.value_excludes:
                    row[ind._attrs['slug']] = value

            results.append(row)

        return results


class TestReport(BaseReportResourceModel):
    slug = 'test'
    name = 'Test'
    config = [ConfigItem('date', 'Date', 'date')]
    indicators = [Indicator('a', 'A'), Indicator('a', 'A')]

    @property
    def results(self):
        return None

CONFIG_TYPE_BOOLEAN = 'boolean'
CONFIG_TYPE_STRING = 'string'
CONFIG_TYPE_INTEGER = 'integer'
CONFIG_TYPE_DATE = 'date'
CONFIG_TYPE_DATETIME = 'datetime'

CONFIG_DATA_TYPES = [CONFIG_TYPE_BOOLEAN, CONFIG_TYPE_STRING, CONFIG_TYPE_INTEGER,
                     CONFIG_TYPE_DATE, CONFIG_TYPE_DATETIME]


class BaseModel(object):
    """
    Assumes class will be instantiated with ``fields`` as 'args' and
    ``optional_fields`` as 'kwargs'.

    Ordering of args must match ordering in ``fields`` attribute.
    """
    fields = []
    optional_fields = []

    def __init__(self, *args, **kwargs):
        if not len(args) == len(self.fields):
            raise Exception("Unexpected fields. Expected '%s', got '%s'" % (self.fields, args))

        for field, value in dict(zip(self.fields, args)).items():
            setattr(self, field, value)

        for field in self.optional_fields:
            value = kwargs.get(field, None)
            if value:
                setattr(self, field, value)

        self.validate()

    def validate(self):
        pass

    def to_json(self):
        d = dict()
        for f in self.fields:
            d[f] = getattr(self, f)

        for f in self.optional_fields:
            val = getattr(self, f, None)
            if val:
                d[f] = val

        return d


class ConfigItemMeta(BaseModel):
    fields = ['slug', 'name', 'data_type']
    optional_fields = ['group_by', 'options', 'default', 'help_text']

    def validate(self):
        if self.data_type not in CONFIG_DATA_TYPES:
            raise ValueError('Unexpected value for data_type: %s' % self.data_type)


class IndicatorMeta(BaseModel):
    fields = ['slug', 'name']
    optional_fields = ['group', 'help_text']


class IndicatorGroupMeta(BaseModel):
    fields = ['slug', 'name']
    optional_fields = ['help_text']


class ReportApiSource(object):
    _meta_fields = ['config', 'indicators', 'indicator_groups']
    slug = ''
    name = ''

    def __init__(self, domain=None, request=None, config=None):
        self.domain = domain
        self.config = config
        self.request = request

        if self.request:
            self._build_config_from_request()

        self.post_init()

    def post_init(self):
        pass

    @property
    def config_meta(self):
        """
        Return a list of ConfigItemMeta instances or dict with appropriate keys.
        """
        raise NotImplementedError()

    @property
    def indicators_meta(self):
        """
        Return a list of IndicatorMeta instances.
        """
        raise NotImplementedError()

    @property
    def indicator_groups_meta(self):
        """
        Return a list of IndicatorGroupMeta instances.
        """
        raise NotImplementedError()

    def get_results(self, indicator_slugs=None):
        """
        Return a list of dicts mapping indicator slugs to values.

        e.g.
        [{
            'user': 'a',
            'indicator1': 10,
            'indicator2': 4
        },
        {
            'user': 'b,
            'indicator1': 8,
            'indicator2': 5
        }]

        """
        pass

    def api_meta(self, full=False):
        meta = dict(slug=self.slug, name=self.name)

        if full:
            for field in self._meta_fields:
                value = getattr(self, '%s_meta' % field) or []
                meta[field] = [item.to_json() if isinstance(item, BaseModel) else item for item in value]

        return meta

    def _build_config_from_request(self):
        conf = [(item.slug, self.request.GET.get(item.slug, item.default)) for item in self.config_meta]
        self.config = dict(conf)


def get_report_results(klass, domain, config, indicator_slugs=None, include_meta=False, meta_full=False):
    report = klass(domain=domain, config=config)
    data = report.get_results(indicator_slugs)

    ret = dict(results=data)
    if include_meta:
        ret.update(report.api_meta(full=meta_full))

    return ret

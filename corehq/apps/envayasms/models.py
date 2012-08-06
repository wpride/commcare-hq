from couchdbkit.ext.django.schema import *
from django.conf import settings
import time

# Create your models here.

class EnqueuedMessage(Document):
    sent_at = DateTimeProperty(auto_now=True)
    message = StringProperty()
    phone_number = StringProperty() # not using contacts so we can query the field
    backend_id = StringProperty()

    @classmethod
    def recent_messages(cls):
        return cls.view('envayasms/by_time', descending=True, include_docs=True, startkey=(time.time() - settings.ENVAYASMS_CONFIG.get('max_delay', 60))*1000).all()

    @classmethod
    def by_backend(cls, backend):
        if not isinstance(backend, basestring):
            backend = backend._id
        return cls.view('envayasms/by_mobilebackend', key=backend, include_docs=True).all()

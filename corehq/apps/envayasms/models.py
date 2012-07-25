from couchdbkit.ext.django.schema import *
from django.conf import settings
import time

# Create your models here.

class EnqueuedMessage(Document):
    sent_at = DateTimeProperty(auto_now=True)
    message = StringProperty()
    phone_number = StringProperty() # not using contacts so we can query the field

    @classmethod
    def recent_messages(cls):
        return cls.view('envayasms/by_time', descending=True, include_docs=True, startkey=(time.time() - settings.ENVAYASMS_CONFIG.get('max_delay', 60))*1000).all()

    @classmethod
    def by_country_code(cls, country_code):
        return cls.view('envayasms/by_phone_number', startkey=country_code, endkey="%s%c" % (country_code, unichr(0xfff8)), include_docs=True)

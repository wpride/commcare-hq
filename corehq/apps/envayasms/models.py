from couchdbkit.ext.django.schema import *
from django.conf import settings
from datetime import datetime, timedelta

# Create your models here.

class EnqueuedMessage(Document):
    sent_at = DateTimeProperty(auto_now=True)
    message = StringProperty()
    phone_number = StringProperty() # not using contacts so we can query the field

    @classmethod
    def recent_messages(cls):
        return cls.view('sms/by_time', include_docs=True, startkey=(datetime.now() - timedelta(seconds=settings.ENVAYASMS_CONFIG.get('max_delay', 60))))

    @classmethod
    def messages_for(cls, country_code):
        return cls.view('sms/by_phone_number', startkey=country_code, endkey="%s%c" % (country_code, unichr(0xfff8)), include_docs=True)

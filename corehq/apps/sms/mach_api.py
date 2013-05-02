from corehq.apps.sms.util import clean_outgoing_sms_text
import urllib
from django.conf import settings
import urllib2
import forms

"""
To implement the API you must have:
API_ID: a unique identifier
API_DESCRIPTION: a human-readable identifier
API_ARGUMENTS: a list of the parameters sent to the send function
send(msg, url='', params=''): a function that sends a message by that API
API_FORM(): a function or class that returns a Django form instance to take parameters for

{
   "_id": "MOBILE_BACKEND_TROPO_US",
   "description": "Tropo - US Number",
   "outbound_module": "corehq.apps.tropo.api",
   "outbound_params": {
       "messaging_token": "xxx"
   },
   "doc_type": "MobileBackend"
}
"""

API_ID = "MACH"
API_DESCRIPTION = "MACH"
API_PARAMETERS = ['url', 'params'] # must match both send
API_DIRTY_PARAMS = []

def API_HELP_MESSAGE(request, backend):
    return ""

def send(msg, url='', params=''):
    """
    Sends a message via mach's API
    """
    outgoing_sms_text = clean_outgoing_sms_text(msg.text)
    context = {
        'message': outgoing_sms_text,
        'phone_number': urllib.quote(msg.phone_number),
    }
    url = "%s?%s" % (url, params % context)
    # just opening the url is enough to send the message
    # TODO, check response
    resp = urllib2.urlopen(url)

class MachSMSForm(forms.SMSForm):
    url = forms.URLField(label="URL", required=True)
    params = forms.CharField(label="URL params", required=True)

API_FORM = MachSMSForm
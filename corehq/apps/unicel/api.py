from datetime import datetime
from corehq.apps.sms.models import SMSLog, INCOMING
from corehq.apps.sms.util import domains_for_phone, users_for_phone,\
    clean_phone_number, clean_outgoing_sms_text
from urllib2 import urlopen
from urllib import urlencode
from corehq.apps.sms import forms

API_ID = "UNICEL"
API_DESCRIPTION = "Unicel"
API_PARAMETERS = ['username', 'password', 'sender']

OUTBOUND_URLBASE = "http://www.unicel.in/SendSMS/sendmsg.php"

class InboundParams(object):
    """
    A constant-defining class for incoming sms params
    """
    SENDER = "sender"
    MESSAGE = "msg"
    TIMESTAMP = "stime"
    UDHI = "udhi"
    DCS = "dcs"
    
class OutboundParams(object):    
    """
    A constant-defining class for outbound sms params
    """
    SENDER = "sender"
    MESSAGE = "msg"
    USERNAME = "uname"
    PASSWORD = "pass"
    DESTINATION = "dest"

# constant additional parameters when sending a unicode message
UNICODE_PARAMS = [("udhi", 0),
                  ("dcs", 8)]

DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"

def create_from_request(request):
    """
    From an inbound request (representing an incoming message), 
    create a message (log) object with the right fields populated.
    """
    sender = request.REQUEST.get(InboundParams.SENDER, "")
    message = request.REQUEST.get(InboundParams.MESSAGE, "")
    timestamp = request.REQUEST.get(InboundParams.TIMESTAMP, "")
    # parse date or default to current utc time
    actual_timestamp = datetime.strptime(timestamp, DATE_FORMAT) \
                            if timestamp else datetime.utcnow()
    
    # not sure yet if this check is valid
    is_unicode = request.REQUEST.get(InboundParams.UDHI, "") == "1"
    if is_unicode:
        message = message.decode("hex").decode("utf_16_be")
    # if you don't have an exact match for either of these fields, save nothing
    domains = domains_for_phone(sender)
    domain = domains[0] if len(domains) == 1 else "" 
    recipients = users_for_phone(sender)
    recipient = recipients[0].get_id if len(recipients) == 1 else "" 
    
    log = SMSLog(couch_recipient=recipient,
                        couch_recipient_doc_type="CouchUser",
                        phone_number=sender,
                        direction=INCOMING,
                        date=actual_timestamp,
                        text=message,
                        domain=domain,
                        backend_api=API_ID)
    log.save()
    
    return log
    

def send(message, username='', password='', sender=''):
    """
    Send an outbound message using the Unicel API
    """
    
    phone_number = clean_phone_number(message.phone_number).replace("+", "")
    # these are shared regardless of API
    params = [(OutboundParams.DESTINATION, phone_number),
              (OutboundParams.USERNAME, username),
              (OutboundParams.PASSWORD, password),
              (OutboundParams.SENDER, sender)]
    try:
        text = str(message.text)
        # it's ascii
        params.append((OutboundParams.MESSAGE, text))
    except UnicodeEncodeError:
        params.extend(UNICODE_PARAMS)
        encoded = message.text.encode("utf_16_be").encode("hex").upper()
        params.append((OutboundParams.MESSAGE, encoded))
    data = urlopen('%s?%s' % (OUTBOUND_URLBASE, urlencode(params))).read()
    
class EnvayaSMSForm(forms.SMSForm):
    username = forms.CharField(label='Username')
    password = forms.CharField(widget=forms.PasswordInput, label='Password')
    sender = forms.CharField('Phone number')

API_FORM = EnvayaSMSForm

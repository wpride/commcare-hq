from urllib import urlencode
from urllib2 import urlopen
from corehq.apps.sms import forms

API_ID = "TROPO"
API_DESCRIPTION = "Tropo"
API_PARAMETERS = ['username', 'password', 'sender']
API_DIRTY_PARAMS = ['password']

def API_HELP_MESSAGE(request, backend):
    return ""

def send(msg, *args, **kwargs):
    """
    Expected kwargs:
        messaging_token
    """
    phone_number = msg.phone_number
    if phone_number[0] != "+":
        phone_number = "+" + phone_number
    params = urlencode({
        "action" : "create"
       ,"token" : kwargs["messaging_token"]
       ,"numberToDial" : phone_number
       ,"msg" : msg.text
       ,"_send_sms" : "true"
    })
    url = "https://api.tropo.com/1.0/sessions?%s" % params
    response = urlopen(url).read()
    print response

class TropoForm(forms.SMSForm):
    username = forms.CharField(label='Username')
    password = forms.CharField(widget=forms.PasswordInput, label='Password')
    sender = forms.CharField('Phone number')

API_FORM = TropoForm
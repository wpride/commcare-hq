from models import EnqueuedMessage
from corehq.apps.sms import forms
from django.core.urlresolvers import reverse

API_ID = "ANDROID"
API_DESCRIPTION = "EnvayaSMS Android Gateway"
API_PARAMETERS = ['password', 'gateway_number']
API_DIRTY_PARAMS = ['password']

def API_HELP_MESSAGE(request, backend):
    domain = backend.domain
    if domain[0] is None:
        domain = []
    return "Enter the following URL into EnvayaSMS: %s" % request.build_absolute_uri(reverse('receive_envayasms_action', args=domain))

def send(msg, password, gateway_number):
    phone_number = msg.phone_number
    if phone_number[0] != "+":
        phone_number = "+" + phone_number
    m = EnqueuedMessage(phone_number=phone_number, message=msg.text, password=password, gateway_number=gateway_number)
    m.save()

class EnvayaSMSForm(forms.SMSForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Password')
    gateway_number = forms.CharField('Gateway phone number')

API_FORM = EnvayaSMSForm
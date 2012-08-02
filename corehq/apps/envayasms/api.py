from models import EnqueuedMessage
from django import forms

API_ID = "ANDROID"
API_DESCRIPTION = "EnvayaSMS Android Gateway"
API_PARAMETERS = ['password', 'gateway_number']

def send(msg, gateway_number):
    phone_number = msg.phone_number
    if phone_number[0] != "+":
        phone_number = "+" + phone_number
    m = EnqueuedMessage(phone_number=phone_number, message=msg.text, gateway_number=gateway_number)
    m.save()

class EnvayaSMSForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, label='Password')
    gateway_number = forms.CharField('Gateway phone number')

API_FORM = EnvayaSMSForm
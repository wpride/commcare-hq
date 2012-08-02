from urllib import urlencode
from urllib2 import urlopen
from corehq.apps.sms import forms

API_ID = "HTTP"
API_DESCRIPTION = "Generic HTTP Gateway"
API_ARGUMENTS = ['url', 'message_param', 'number_param', 'include_plus', 'method', 'additional_params']

def send(msg, *args, **kwargs):
    """
    Expected kwargs:
        url                 the url to send to
        message_param       the parameter which the gateway expects to represent the sms message
        number_param        the parameter which the gateway expects to represent the phone number to send to
        include_plus        True to include the plus sign in front of the number, false not to (optional, defaults to false)
        method              "GET" or "POST" (optional, defaults to "GET")
        additional_params   a dictionary of additional parameters that will be sent in the request (optional, defaults to {})
    """
    url = kwargs.get("url")
    include_plus = kwargs.get("include_plus", False)
    method = kwargs.get("method", "GET")
    params = {}
    #
    phone_number = msg.phone_number
    if include_plus:
        if phone_number[0] != "+":
            phone_number = "+" + phone_number
    else:
        if phone_number[0] == "+":
            phone_number = phone_number[1:]
    #
    params[kwargs["message_param"]] = msg.text
    params[kwargs["number_param"]] = phone_number
    #
    url_params = urlencode(params)
    additional_params = kwargs.get("additional_params", False)
    if additional_params:
        url_params = "%s&%s" % (url_params, additional_params)
    if method == "GET":
        response = urlopen(url + "?" + url_params).read()
    else:
        response = urlopen(url, url_params).read()

class HTTPSMSForm(forms.SMSForm):
    url = forms.URLField(label="URL", required=True)
    message_param = forms.CharField(label="Message parameter", required=True, help_text="The parameter which the gateway expects to represent the sms message")
    number_param = forms.CharField(label="Number parameter", required=True, help_text="The parameter which the gateway expects to represent the phone number to send to")
    include_plus = forms.BooleanField(label="Include plus?", help_text="Include plus sign in front of number when sending to gateway")
    method = forms.ChoiceField(label="HTTP method", choices=(("GET", "GET"), ("POST", "POST")))
    additional_params = forms.CharField(label="Additional params", required=False, help_text="URL-encoded params for the gateway")

API_FORM = HTTPSMSForm
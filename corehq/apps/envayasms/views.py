import json
from .api import API_ID as BACKEND_API_ID
from corehq.apps.ivr.api import incoming as incoming_call
from corehq.apps.sms.api import incoming as incoming_sms
from corehq.apps.sms import api
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
import json, time, sha, base64
from models import EnqueuedMessage
from django.conf import settings
import phonenumbers
from corehq.apps.sms.mixin import MobileBackend
from django.core.urlresolvers import reverse

@csrf_exempt
def receive_action(request, domain=None):
    data = request.POST

    number_raw = request.POST.get('phone_number', '')
    if number_raw == '':
        return HttpResponseBadRequest(json.dumps({'error': {'message': 'Missing arguments'}}))
    if not number_raw.startswith('+'):
        number_raw = "+%s" % number_raw
    phone_number = phonenumbers.parse(number_raw)
    country_code = phone_number.country_code
    backend = MobileBackend.find(domain, country_code)

    if backend.outbound_params.get('password', '') is not '':
        params = ','.join('%s=%s' % (k, request.POST[k]) for k in sorted(request.POST.keys()))
        domain = backend.domain
        if domain[0] is None:
            domain = []
        server_url = request.build_absolute_uri(reverse('receive_envayasms_action', args=domain))
        print server_url, params, backend.outbound_params['password']
        secure_key = sha.new(','.join((server_url, params, backend.outbound_params['password']))).digest()
        if base64.b64decode(request.META.get('HTTP_X_REQUEST_SIGNATURE', '')) != secure_key:
            return HttpResponseForbidden(json.dumps({'error': {'message': 'Bad password'}}))
            
    action = data.get('action', '')
    if action == 'incoming':
        # receive message
        if data.get('message_type') == 'call':
            incoming_call(data.get('from', ''), backend._id)
        else:
            incoming_sms(data.get('from', ''), data.get('message', ''), backend._id)

    elif action == 'outgoing':
        # send back outgoing
        messages = EnqueuedMessage.by_country_code(country_code)
        events = [{'event': 'send', 'messages': [{'to': data.phone_number, 'message': data.message} for data in messages]}]
        for message in messages:
            message.delete()

        return HttpResponse(json.dumps({'events': events}), content_type='application/json')
    elif action == 'send_status':
        pass # I guess we don't care if we get the message back
    elif action == 'device_status':
        pass
    elif action == 'forward_sent':
        pass # message sent from the phone's internal android sms app forwarded to HQ
    elif action == 'amqp_started':
        pass
    return HttpResponse('{"events": []}', content_type='application/json')

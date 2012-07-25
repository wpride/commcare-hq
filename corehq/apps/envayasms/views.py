import json
from .api import API_ID as BACKEND_API_ID
from corehq.apps.ivr.api import incoming as incoming_call
from corehq.apps.sms.api import incoming as incoming_sms
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
import json, time, sha, base64
#import phonenumbers
from django.conf import settings

@csrf_exempt
def receive_action(request):
    data = request.POST

    params = ','.join('%s=%s' % (k, request.POST[k]) for k in sorted(request.POST.keys()))

    if settings.ENVAYASMS_CONFIG.get('password', None) is not None:
        secure_key = sha.new(','.join((settings.ENVAYASMS_CONFIG.get('url', ''), params, settings.ENVAYASMS_CONFIG.get('password')))).digest()
        if base64.b64decode(request.META.get('HTTP_X_REQUEST_SIGNATURE', '')) != secure_key:
            return HttpResponseForbidden(json.dumps({'error': {'message': 'Bad password'}}))
            
    action = data.get('action', '')
    if action == 'incoming':
        if data.get('message_type') == 'call':
        	incoming_call(data.get('from', ''), BACKEND_API_ID)
        else:
            incoming_sms(data.get('from', ''), data.get('message', ''), BACKEND_API_ID)
    elif action == 'outgoing':
        # send back outgoing
        phone_number = request.POST.get('phone_number', '')
        if not phone_number.startswith('+'):
            phone_number = '+%s' % phone_number
        messages = EnqueuedMessage.recent_messages()#EnqueuedMessage.messages_for(phone_number.country_code)
        events = [{'event': 'send', 'messages': [{'to': data.recipient, 'message': data.message} for data in messages]}]
        messages.delete()

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


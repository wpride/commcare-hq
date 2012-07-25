from models import EnqueuedMessage
API_ID = "ENVAYASMS"

def send(msg, *args, **kwargs):
    """
    Expected kwargs:
        messaging_token
    """
    phone_number = msg.phone_number
    if phone_number[0] != "+":
        phone_number = "+" + phone_number
    m = EnqueuedMessage(phone_number=phone_number, message=msg.text)
    m.save()


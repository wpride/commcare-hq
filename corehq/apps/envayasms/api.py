from models import EnqueuedMessage
API_ID = "ANDROID"

def send(message):
    phone_number = msg.phone_number
    if phone_number[0] != "+":
        phone_number = "+" + phone_number
    m = EnqueuedMessage(phone_number=phone_number, message=msg.text)
    m.save()

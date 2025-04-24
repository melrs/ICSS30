import pika, json
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from datetime import datetime

conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
ch = conn.channel()
ch.queue_declare(queue='reservation-created')
ch.queue_declare(queue='payment-approved')
ch.queue_declare(queue='payment-declined')
ch.queue_declare(queue='ticket-issued')

with open("payment_public.pem", "rb") as f:
    payment_key = serialization.load_pem_public_key(f.read())

itineraries = [
    {"destination": "Bahamas", "departure": "2025-07-01", "ship": "OceanX", "price": 1000},
    {"destination": "Caribbean", "departure": "2025-08-10", "ship": "SeaCruiser", "price": 1500}
]

def search_itineraries(destination):
    return [i for i in itineraries if i["destination"] == destination]

def reserve(destination, passengers):
    itinerary = search_itineraries(destination)[0]
    reservation = {
        "destination": destination,
        "ship": itinerary["ship"],
        "price": itinerary["price"],
        "date": itinerary["departure"],
        "passengers": passengers,
        "timestamp": datetime.now().isoformat()
    }
    ch.basic_publish(exchange='', routing_key='reservation-created', body=json.dumps(reservation))
    print("[Reservation] Created and sent to Payment MS.")

def verify_signature(message, signature):
    try:
        payment_key.verify(
            signature,
            message,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except:
        return False

def callback_approved(ch, method, properties, body):
    msg = json.loads(body)
    if verify_signature(msg["message"].encode(), bytes.fromhex(msg["signature"])):
        print("[Reservation] Payment approved:", msg["message"])

def callback_declined(ch, method, properties, body):
    msg = json.loads(body)
    if verify_signature(msg["message"].encode(), bytes.fromhex(msg["signature"])):
        print("[Reservation] Payment declined. Reservation canceled.")

ch.basic_consume(queue='payment-approved', on_message_callback=callback_approved, auto_ack=True)
ch.basic_consume(queue='payment-declined', on_message_callback=callback_declined, auto_ack=True)

reserve("Bahamas", 2)
print("[Reservation] Waiting for payment status...")
ch.start_consuming()

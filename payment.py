import random
import pika, json
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from config import PAYMENT_APPROVED_QUEUE, PAYMENT_DECLINED_QUEUE, RESERVATION_CREATED_QUEUE, PAYMENT_MESSAGE_FORMAT, ITINERARIES_FILE

private_key = serialization.load_pem_private_key(open("payment_private.pem", "rb").read(), password=None)

with open(ITINERARIES_FILE, "r") as f:
    itineraries = {itinerary["id"]: itinerary for itinerary in json.load(f)}

def sign(message):
    return private_key.sign(
        message.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    ).hex()

conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
ch = conn.channel()

for queue in [RESERVATION_CREATED_QUEUE, PAYMENT_APPROVED_QUEUE, PAYMENT_DECLINED_QUEUE]:
    ch.queue_declare(queue=queue)

def callback(ch, method, properties, body):
    data = json.loads(body)
    itinerary = itineraries[int(data["destination_id"])]
    message = f"Reservation confirmed for {itinerary['destination']} on ship {itinerary['ship']}."

    approved = random.choice([True, False])

    msg = {
        "message": message,
        "signature": sign(message)
    }

    queue = PAYMENT_APPROVED_QUEUE if approved else PAYMENT_DECLINED_QUEUE
    ch.basic_publish(exchange='', routing_key=queue, body=json.dumps(msg))
    print(f"[Payment] {'Approved' if approved else 'Denied'} - Message sent.")

ch.basic_consume(queue=RESERVATION_CREATED_QUEUE, on_message_callback=callback, auto_ack=True)
print("[Payment] Waiting for reservations...")
ch.start_consuming()

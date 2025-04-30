import random
import pika, json
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from config import PAYMENT_APPROVED_EXCHANGE, PAYMENT_APPROVED_RESERVE_QUEUE, PAYMENT_APPROVED_TICKED_QUEUE, PAYMENT_DECLINED_QUEUE, RESERVATION_CREATED_QUEUE, PAYMENT_MESSAGE_FORMAT, ITINERARIES_FILE, PAYMENT_PRIVATE_KEY_FILE
from utils import load_itineraries, create_channel, sign_message
from datetime import datetime


itineraries = load_itineraries(ITINERARIES_FILE)
ch = create_channel()

ch.exchange_declare(exchange=PAYMENT_APPROVED_EXCHANGE, exchange_type='fanout')

for queue in [RESERVATION_CREATED_QUEUE, PAYMENT_APPROVED_RESERVE_QUEUE, PAYMENT_APPROVED_TICKED_QUEUE, PAYMENT_DECLINED_QUEUE]:
    ch.queue_declare(queue=queue)

ch.queue_bind(exchange=PAYMENT_APPROVED_EXCHANGE, queue=PAYMENT_APPROVED_RESERVE_QUEUE)
ch.queue_bind(exchange=PAYMENT_APPROVED_EXCHANGE, queue=PAYMENT_APPROVED_TICKED_QUEUE)

def handle_reservation(ch, method, properties, body):
    data = json.loads(body)
    itinerary = itineraries[int(data["itinerary_id"])]
    status = 'denied'
    routing_key = PAYMENT_DECLINED_QUEUE
    exchange = ''
    if random.choice([True, False]):
        status = 'approved'
        routing_key = ''
        exchange = PAYMENT_APPROVED_EXCHANGE

    message = f'Payment {status} for {itinerary["destination"]} on ship {itinerary["ship"]}.'
    ch.basic_publish(exchange=exchange, routing_key=routing_key, body=json.dumps(create_signed_message(message)))
    print(f"[Payment] [{datetime.now().isoformat()}] {message}")

def create_signed_message(message):
    return {
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "signature": sign_message(message, PAYMENT_PRIVATE_KEY_FILE)
    }

ch.basic_consume(queue=RESERVATION_CREATED_QUEUE, on_message_callback=handle_reservation, auto_ack=True)
print("[Payment] Waiting for reservations...")
ch.start_consuming()

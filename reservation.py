import pika, json
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from datetime import datetime
from utils import verify_signature, create_channel, load_itineraries
from config import PAYMENT_PUBLIC_KEY_FILE, PAYMENT_APPROVED_RESERVE_QUEUE, PAYMENT_DECLINED_QUEUE, RESERVATION_CREATED_QUEUE, TICKET_ISSUED_QUEUE, ITINERARIES_FILE

ch = create_channel()

for queue in [RESERVATION_CREATED_QUEUE, PAYMENT_APPROVED_RESERVE_QUEUE, PAYMENT_DECLINED_QUEUE, TICKET_ISSUED_QUEUE]:
    ch.queue_declare(queue=queue)

itineraries = load_itineraries(ITINERARIES_FILE)

def search_itineraries(destination):
    if destination in itineraries:
        return itineraries[destination]
    print("[Reservation] No itinerary found.")
    return None


def reserve(destination, passengers):
    itinerary = search_itineraries(destination)
    reservation = {
        "itinerary_id": itinerary["id"],
        "destination": destination,
        "ship": itinerary["ship"],
        "date": itinerary["departure"],
        "total_price": itinerary["price"] * passengers,
        "passengers": passengers,
        "timestamp": datetime.now().isoformat()
    }
    ch.basic_publish(exchange='', routing_key=RESERVATION_CREATED_QUEUE, body=json.dumps(reservation))
    print("[Reservation] Created.")

def handle_payment_approved(ch, method, properties, body):
    msg = json.loads(body)
    print("[Reservation] Payment approved:", msg["message"].encode())
    if verify_signature(msg["message"].encode(), bytes.fromhex(msg["signature"]), PAYMENT_PUBLIC_KEY_FILE):
        print("[Reservation] Payment approved:", msg["message"])

def handle_payment_declined(ch, method, properties, body):
    msg = json.loads(body)
    print("[Reservation] Payment declined:", msg["message"].encode())
    if verify_signature(msg["message"].encode(), bytes.fromhex(msg["signature"]), PAYMENT_PUBLIC_KEY_FILE):
        print("[Reservation] Payment declined. Reservation canceled.")

def handle_ticket_issued(ch, method, properties, body):
    msg = json.loads(body)
    print("[Reservation]", msg["message"])

ch.basic_consume(queue=PAYMENT_APPROVED_RESERVE_QUEUE, on_message_callback=handle_payment_approved, auto_ack=True)
ch.basic_consume(queue=PAYMENT_DECLINED_QUEUE, on_message_callback=handle_payment_declined, auto_ack=True)
ch.basic_consume(queue=TICKET_ISSUED_QUEUE, on_message_callback=handle_ticket_issued, auto_ack=True)

reserve(1, 2)
print("[Reservation] Waiting for payment status...")
ch.start_consuming()

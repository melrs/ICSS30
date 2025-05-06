import time
import pika
import threading
from config import ITINERARIES_FILE, MARKETING_EXCHANGE
from utils import load_itineraries

itineraries = load_itineraries(ITINERARIES_FILE)

print("Available itineraries:")
for itinerary in itineraries.values():
    print(f"    {itinerary['id']}. {itinerary['destination']} - {itinerary['ship']} - {itinerary['departure']} - {itinerary['price']} - {itinerary['departurePort']}")

def subscribe_to_promotion(destination):
    conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    ch = conn.channel()
    ch.exchange_declare(exchange=MARKETING_EXCHANGE, exchange_type='direct')
    result = ch.queue_declare(queue='', exclusive=True)
    queue = result.method.queue
    ch.queue_bind(exchange=MARKETING_EXCHANGE, queue=queue, routing_key=f'promotions-{destination.lower()}')
    ch.basic_consume(queue=queue, on_message_callback=lambda ch, method, props, body: print(f"[Promotion] {body.decode()}"), auto_ack=True)
    print(f"[Subscriber] Subscribed to promotions for {destination}. Waiting for messages...")
    ch.start_consuming()

past_choices = []
while True:
    choice = input("Enter the id of the itinerary you want to receive promotions for (or type 'done' to exit): ")
    if choice.lower() == 'done':
        print("Exiting...")
        break
    try:
        choice = int(choice)
        if choice not in itineraries:
            print("Invalid choice. Please try again.")
            continue
        if choice in past_choices:
            print("You have already subscribed to this itinerary.")
            continue
        past_choices.append(choice)
        destination = itineraries[choice]['destination']
        threading.Thread(target=subscribe_to_promotion, args=(destination,), daemon=True).start()
        time.sleep(5)
    except ValueError:
        print("Invalid input. Please enter a valid itinerary id or 'done'.")

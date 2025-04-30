import pika
import json
import random
from config import ITINERARIES_FILE
import time

conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
ch = conn.channel()

with open(ITINERARIES_FILE, 'r') as file:
    itineraries = json.load(file)
    destinations = [itinerary['destination'] for itinerary in itineraries]

for destination in destinations:
    ch.queue_declare(queue=f'promotions-{destination.lower()}')

def publish_promotion(destination, msg):
    queue = f'promotions-{destination.lower()}'
    ch.basic_publish(exchange='', routing_key=queue, body=msg)
    print(f"[Marketing] Promotion for {destination} published.")

try:
    while True:
        random_itinerary = random.choice(itineraries)
        random_destination = random_itinerary['destination']
        current_time = time.strftime("%d/%m/%Y %H:%M:%S")
        random_promotion = f"{random_destination} - {random_itinerary.get('promotion', 'Special offer!')} - {current_time}"

        publish_promotion(random_destination, random_promotion)
        print(f"[Marketing] Promotion for {random_destination} sent: {random_promotion}")
        
        time.sleep(random.randint(7, 15))
except KeyboardInterrupt:
    print("\n[Marketing] Promotion publishing stopped.")
    conn.close()

import pika

conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
ch = conn.channel()

destinations = ['Bahamas', 'Caribbean']
for destination in destinations:
    ch.queue_declare(queue=f'promotions-{destination.lower()}')

def publish_promotion(destination, msg):
    queue = f'promotions-{destination.lower()}'
    ch.basic_publish(exchange='', routing_key=queue, body=msg)
    print(f"[Marketing] Promotion for {destination} published.")

publish_promotion("Bahamas", "Bahamas 20% OFF today only!")

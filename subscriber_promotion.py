import pika

destinations = ['Bahamas']

conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
ch = conn.channel()

for destination in destinations:
    queue = f'promotions-{destination.lower()}'
    ch.queue_declare(queue=queue)
    ch.basic_consume(queue=queue, on_message_callback=lambda ch, method, props, body: print(f"[Promotion] {body.decode()}"), auto_ack=True)

print("[Subscriber] Waiting for promotions...")
ch.start_consuming()

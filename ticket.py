import pika, json
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from config import PAYMENT_APPROVED_QUEUE, TICKET_ISSUED_QUEUE

with open("payment_public.pem", "rb") as f:
    pub_key = serialization.load_pem_public_key(f.read())

def verify_signature(message, signature):
    try:
        pub_key.verify(
            bytes.fromhex(signature),
            message.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except:
        return False

conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
ch = conn.channel()

for queue in [PAYMENT_APPROVED_QUEUE, TICKET_ISSUED_QUEUE]:
    ch.queue_declare(queue=queue)

def callback(ch, method, properties, body):
    data = json.loads(body)
    if verify_signature(data["message"], data["signature"]):
        ticket = f"TICKET | {data['message']}"
        ch.basic_publish(exchange='', routing_key=TICKET_ISSUED_QUEUE, body=ticket)
        print("[Ticket] Generated and published.")

ch.basic_consume(queue=PAYMENT_APPROVED_QUEUE, on_message_callback=callback, auto_ack=True)
print("[Ticket] Waiting for payment confirmations...")
ch.start_consuming()

from datetime import datetime
import pika, json
from config import PAYMENT_APPROVED_TICKED_QUEUE, TICKET_ISSUED_QUEUE, PAYMENT_PUBLIC_KEY_FILE
from utils import verify_signature

conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
ch = conn.channel()

for queue in [PAYMENT_APPROVED_TICKED_QUEUE, TICKET_ISSUED_QUEUE]:
    ch.queue_declare(queue=queue)

def createTicket(ch, method, properties, body):
    data = json.loads(body)
    if verify_signature(data["message"], data["signature"], PAYMENT_PUBLIC_KEY_FILE):
        message = f"Ticket Issued for {data['message']}"
        ch.basic_publish(exchange='', routing_key=TICKET_ISSUED_QUEUE, body=json.dumps(create_message(message)))
        print(f"[Ticket] [{datetime.now().isoformat()}] " + message)

def create_message(message):
    return {
        "timestamp": datetime.now().isoformat(),
        "message": message,
    }

ch.basic_consume(queue=PAYMENT_APPROVED_TICKED_QUEUE, on_message_callback=createTicket, auto_ack=True)
print("[Ticket] Waiting for payment confirmations...")
ch.start_consuming()

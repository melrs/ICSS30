from datetime import datetime
import pika, json
from config import PAYMENT_APPROVED_QUEUE, TICKET_ISSUED_QUEUE, PAYMENT_PUBLIC_KEY_FILE, PAYMENT_EXCHANGE, TICKET_EXCHANGE
from utils import verify_signature

conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
ch = conn.channel()
ch.exchange_declare(exchange=TICKET_EXCHANGE, exchange_type='direct')

def createTicket(ch, method, properties, body):
    data = json.loads(body)
    print(method.routing_key)
    if verify_signature(data["message"], data["signature"], PAYMENT_PUBLIC_KEY_FILE):
        message = f"Ticket Issued for {data['message']}"
        ch.basic_publish(exchange=TICKET_EXCHANGE, routing_key=TICKET_ISSUED_QUEUE, body=json.dumps(create_message(message)))
        print(f"[Ticket] [{datetime.now().isoformat()}] " + message)

def create_message(message):
    return {
        "timestamp": datetime.now().isoformat(),
        "message": message,
    }

ch.queue_declare(queue=PAYMENT_APPROVED_QUEUE)
ch.queue_bind(exchange=PAYMENT_EXCHANGE, queue=PAYMENT_APPROVED_QUEUE, routing_key=PAYMENT_APPROVED_QUEUE)
ch.basic_consume(queue=PAYMENT_APPROVED_QUEUE, on_message_callback=createTicket, auto_ack=True)
print("[Ticket] Waiting for payment confirmations...")
ch.start_consuming()

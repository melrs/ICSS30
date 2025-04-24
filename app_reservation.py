import tkinter as tk
from tkinter import ttk, messagebox
import json
from datetime import datetime
import threading
import pika
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from config import RESERVATION_QUEUES, ITINERARIES_FILE, ITINERARY_TEMPLATE, RESERVATION_CREATED_QUEUE, PAYMENT_PUBLIC_KEY_FILE, PAYMENT_APPROVED_QUEUE, PAYMENT_DECLINED_QUEUE, TICKET_ISSUED_QUEUE
from utils import is_valid_date
from config import ITINERARY_TEMPLATE

with open(PAYMENT_PUBLIC_KEY_FILE, "rb") as f:
    payment_key = serialization.load_pem_public_key(f.read())

conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
ch = conn.channel()

for queue in RESERVATION_QUEUES:
    ch.queue_declare(queue=queue)

with open(ITINERARIES_FILE, "r") as f:
    itineraries = json.load(f)

def search_itineraries():
    results = get_filtered_itineraries(itineraries)
    result_text.delete(1.0, tk.END)
    if not results:
        result_text.insert(tk.END, "No itinerary found.")
        return

    for i in results:
        result_text.insert(tk.END, ITINERARY_TEMPLATE.format(
            id=i["id"],
            destination=i["destination"],
            ship=i["ship"],
            departure=i["departure"],
            arrival=i["arrival"],
            stops=", ".join(i["stops"]),
            nights=i["nights"],
            price=i["price"],
            departurePort=i["departurePort"]
        ))        
    result_text.insert(tk.END, "\n\n")

def get_filtered_itineraries(results):
    destination = destination_var.get().strip()
    boarding_date = boarding_date_var.get().strip()
    boarding_port = port_var.get().strip()

    if destination:
        results = [i for i in results if i["destination"].lower() == destination.lower()]
    if boarding_date:
        results = [i for i in results if datetime.strptime(i["departure"], "%Y-%m-%d").date() == datetime.strptime(boarding_date, "%d/%m/%Y").date()]
    if boarding_port:
        results = [i for i in results if i["departurePort"].lower() == boarding_port.lower()]
    
    return results

def make_reservation(id, passengers):
    reservation = {
        "destination_id": id,
        "passengers": passengers,
        "timestamp": datetime.now().isoformat()
    }

    ch.basic_publish(exchange='', routing_key=RESERVATION_CREATED_QUEUE, body=json.dumps(reservation))
    status_var.set("Reservation created. Awaiting payment...")

def verify_signature(message, signature):
    try:
        payment_key.verify(
            signature,
            message,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        return False

def consume_queues():
    conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    ch = conn.channel()

    for queue in RESERVATION_QUEUES:
        ch.queue_declare(queue=queue)

    def callback_approved(ch, method, properties, body):
        msg = json.loads(body)
        if verify_signature(msg["message"].encode(), bytes.fromhex(msg["signature"])):
            result_text.delete(1.0, tk.END)
            status_var.set("✅ Payment approved!")
            result_text.insert(tk.END, f"{msg['message']}\n\n")

    def callback_declined(ch, method, properties, body):
        msg = json.loads(body)
        if verify_signature(msg["message"].encode(), bytes.fromhex(msg["signature"])):
            result_text.delete(1.0, tk.END)
            status_var.set("❌ Payment declined.")
            result_text.insert(tk.END, "Reservation cancelled.\n\n")

    def callback_ticket(ch, method, properties, body):
        ticket_var.set(f"🎫 {body.decode()}")

    ch.basic_consume(queue=PAYMENT_APPROVED_QUEUE, on_message_callback=callback_approved, auto_ack=True)
    ch.basic_consume(queue=PAYMENT_DECLINED_QUEUE, on_message_callback=callback_declined, auto_ack=True)
    ch.basic_consume(queue=TICKET_ISSUED_QUEUE, on_message_callback=callback_ticket, auto_ack=True)

    ch.start_consuming()


threading.Thread(target=consume_queues, daemon=True).start()

root = tk.Tk()
root.title("Cruise Reservation")

ttk.Label(root, text="Destination:").grid(row=0, column=0, sticky="e")
destination_var = tk.StringVar()
ttk.Entry(root, textvariable=destination_var, width=20).grid(row=0, column=1)

ttk.Label(root, text="Boarding Date:").grid(row=1, column=0, sticky="e")
boarding_date_var = tk.StringVar()
date_entry = ttk.Entry(root, textvariable=boarding_date_var, width=20)
date_entry.grid(row=1, column=1)
boarding_date_var.trace_add("write", lambda *args: date_entry.config(foreground=("red" if not is_valid_date(boarding_date_var.get()) else "white")))
 
ttk.Label(root, text="Boarding Port:").grid(row=2, column=0, sticky="e")
port_var = tk.StringVar()
ttk.Entry(root, textvariable=port_var, width=20).grid(row=2, column=1)


ttk.Button(root, text="Search Itineraries", command=search_itineraries).grid(row=3, column=0, columnspan=2, pady=5)

result_text = tk.Text(root, height=10, width=60)
result_text.grid(row=4, column=0, columnspan=2, padx=10, pady=5)

status_var = tk.StringVar(value="Waiting for user action.")
frame = ttk.Frame(root)
frame.grid(row=5, column=0, columnspan=3, padx=10, pady=5)
ttk.Label(frame, text="ID:").grid(row=1, column=0, sticky="e")
id_var = tk.StringVar()
ttk.Entry(frame, textvariable=id_var, width=10).grid(row=1, column=1, padx=5, pady=5)

ttk.Label(frame, text="Passengers:").grid(row=0, column=0, sticky="e")
passengers_var = tk.StringVar()
ttk.Entry(frame, textvariable=passengers_var, width=10).grid(row=0, column=1, padx=5, pady=5)

ttk.Button(frame, text="Make Reservation", command=lambda: make_reservation(id_var.get(), passengers_var.get())).grid(row=2, column=0, columnspan=2)

ticket_var = tk.StringVar(value="")
ttk.Label(root, textvariable=ticket_var, font=("Courier", 10, "bold"), foreground="green").grid(row=7, column=0, columnspan=2, pady=10)

root.mainloop()

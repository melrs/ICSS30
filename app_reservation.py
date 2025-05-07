import tkinter as tk
from tkinter import ttk, messagebox
import json
from datetime import datetime
import threading
import pika
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from config import RESERVATION_QUEUES, ITINERARIES_FILE, ITINERARY_TEMPLATE, RESERVATION_CREATED_QUEUE, PAYMENT_PUBLIC_KEY_FILE, PAYMENT_APPROVED_QUEUE, PAYMENT_DECLINED_QUEUE, TICKET_ISSUED_QUEUE, PAYMENT_EXCHANGE, TICKET_EXCHANGE
from utils import is_valid_date, load_itineraries, create_channel, verify_signature

ch = create_channel()
ch.queue_declare(queue=RESERVATION_CREATED_QUEUE)

def populate_itinerary_results(destination, boarding_date, boarding_port):
    results = get_filtered_itineraries(destination, boarding_date, boarding_port)
    result_text.grid(row=4, column=0, columnspan=2, padx=10, pady=5)
    result_text.delete(1.0, tk.END)
    if not results:
        result_text.insert(tk.END, "No itinerary found.")
        return

    for result in results:
        result_text.insert(tk.END, ITINERARY_TEMPLATE.format(
            id=result["id"],
            destination=result["destination"],
            ship=result["ship"],
            departure=result["departure"],
            arrival=result["arrival"],
            stops=", ".join(result["stops"]),
            nights=result["nights"],
            price=result["price"],
            departurePort=result["departurePort"]
        ))        
    result_text.insert(tk.END, "\n\n")
    create_reservation_ui(root)

def get_filtered_itineraries(destination, boarding_date, boarding_port):
    results = load_itineraries(ITINERARIES_FILE).values()
    if destination:
        results = [result for result in results if result["destination"].lower() == destination.lower()]
    if boarding_date:
        results = [result for result in results if datetime.strptime(result["departure"], "%Y-%m-%d").date() == datetime.strptime(boarding_date, "%d/%m/%Y").date()]
    if boarding_port:
        results = [result for result in results if result["departurePort"].lower() == boarding_port.lower()]
    
    return results

def consume_queues(root):
    ch = create_channel()

    for queue in RESERVATION_QUEUES:
        ch.queue_declare(queue=queue)

    def callback_approved(ch, method, properties, body):
        print("[Reservation] Payment approved.")
        msg = json.loads(body)
        if verify_signature(msg["message"], msg["signature"], PAYMENT_PUBLIC_KEY_FILE):
            print("[Reservation] Payment approved:", msg["message"])
            messagebox.showinfo("Success", "Payment approved. Proceeding to issue ticket.")

    def callback_declined(ch, method, properties, body):
        print("[Reservation] Payment declined.")
        msg = json.loads(body)
        if verify_signature(msg["message"], msg["signature"], PAYMENT_PUBLIC_KEY_FILE):
            print("[Reservation] Payment declined:", msg["message"])
            messagebox.showerror("Error", "Payment declined. Reservation canceled.")

    def callback_ticket(ch, method, properties, body):
        print("[Reservation] Ticket issued.")
        print(method.routing_key)
        messagebox.showinfo("Success", "Ticket issued successfully.")
   
    queue_approved = ch.queue_declare(queue='', exclusive=True).method.queue
    ch.queue_bind(exchange=PAYMENT_EXCHANGE, queue=queue_approved, routing_key=PAYMENT_APPROVED_QUEUE)
    ch.basic_consume(queue=queue_approved, on_message_callback=callback_approved, auto_ack=True)
    
    queue_denclined = ch.queue_declare(queue='', exclusive=True).method.queue
    ch.queue_bind(exchange=PAYMENT_EXCHANGE, queue=queue_denclined, routing_key=PAYMENT_DECLINED_QUEUE)
    ch.basic_consume(queue=queue_denclined, on_message_callback=callback_declined, auto_ack=True)
    
    queue_ticket = ch.queue_declare(queue='', exclusive=True).method.queue
    ch.queue_bind(exchange=TICKET_EXCHANGE, queue=queue_ticket, routing_key=TICKET_ISSUED_QUEUE)
    ch.basic_consume(queue=queue_ticket, on_message_callback=callback_ticket, auto_ack=True)

    ch.start_consuming()


root = tk.Tk()
root.title("Cruise Reservation")
result_text = tk.Text(root, height=10, width=60)

threading.Thread(target=lambda: consume_queues(root), daemon=True).start()

def initialize_booking_interface(root):
    frame = ttk.Frame(root)
    frame.grid(row=0, column=0, columnspan=3, padx=10, pady=5)
    
    ttk.Label(frame, text="Destination:").grid(row=0, column=0, sticky="e")
    destination_var = tk.StringVar()
    ttk.Entry(frame, textvariable=destination_var, width=20).grid(row=0, column=1, padx=0)

    ttk.Label(frame, text="Boarding Date:").grid(row=1, column=0, sticky="e")
    boarding_date_var = tk.StringVar()
    date_entry = ttk.Entry(frame, textvariable=boarding_date_var, width=20)
    date_entry.grid(row=1, column=1)
    boarding_date_var.trace_add("write", lambda *args: date_entry.config(foreground=("red" if not is_valid_date(boarding_date_var.get()) else "white")))
 
    ttk.Label(frame, text="Boarding Port:").grid(row=2, column=0, sticky="e")
    port_var = tk.StringVar()
    ttk.Entry(frame, textvariable=port_var, width=20).grid(row=2, column=1)

    ttk.Button(
        frame, 
        text="Search Itineraries", 
        command=lambda: populate_itinerary_results(destination_var.get().strip(), boarding_date_var.get().strip(), port_var.get().strip())
    ).grid(row=3, column=0, columnspan=2, pady=5)

def make_reservation(id, passengers):
    reservation = {
        "itinerary_id": id,
        "passengers": passengers,
        "timestamp": datetime.now().isoformat()
    }

    ch.basic_publish(exchange='', routing_key=RESERVATION_CREATED_QUEUE, body=json.dumps(reservation))

def create_reservation_ui(root):
    frame = ttk.Frame(root)
    frame.grid(row=5, column=0, columnspan=3, padx=10, pady=5)
    
    ttk.Label(frame, text="ID:").grid(row=1, column=0, sticky="e")
    id_var = tk.StringVar()
    ttk.Entry(frame, textvariable=id_var, width=20).grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(frame, text="Passengers:").grid(row=0, column=0, sticky="e")
    passengers_var = tk.StringVar()
    ttk.Entry(frame, textvariable=passengers_var, width=20).grid(row=0, column=1, padx=5, pady=5)

    ttk.Button(
        frame, 
        text="Make Reservation",
        command=lambda: handle_reservation(id_var.get(), passengers_var.get(), root)
    ).grid(row=2, column=0, columnspan=2)

def handle_reservation(id, passengers, root):
    for widget in root.winfo_children():
        widget.destroy()
    
    try:
        passengers = int(passengers)
        if passengers <= 0:
            raise ValueError("Number of passengers must be greater than 0.")
        result_text = tk.Text(root, height=10, width=60)
        result_text.grid(row=4, column=0, columnspan=2, padx=10, pady=5)
        result_text.tag_configure("green", foreground="green")
        result_text.insert(tk.END, f'✅ Creating reservation for itinerary #{id} with {passengers} passengers.\n', "green")
        make_reservation(id, passengers)
    except ValueError as e:
        messagebox.showerror("Error", str(e))

initialize_booking_interface(root)
root.mainloop()

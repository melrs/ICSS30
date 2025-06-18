import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from config import (
    ITINERARIES_FILE,
    RESERVATION_CREATED_QUEUE,
    RESERVATION_CANCELLED_QUEUE
)
from utils import load_itineraries, create_channel
from request_dto import Itinerary

class ItineraryService:
    def __init__(self):
        self.app = Flask(__name__)
        self._register_routes()
        self. all_itineraries = load_itineraries(ITINERARIES_FILE)
        consumer_thread = threading.Thread(target=self._start_rabbitmq_consumers, daemon=True)
        consumer_thread.start()
        self.reservations = {}

    def _register_routes(self):
        self.app.add_url_rule('/itineraries', view_func=self.get_itineraries, methods=['GET'])

    def get_itineraries(self):
        itinerary_request = Itinerary.from_dict(request.args)
        if itinerary_request.id: return self._get_itinerary_id_from_request(itinerary_request.id)
        filtered_itineraries = []

        for id, itinerary_details in self.all_itineraries.items():
            if self._filter_itineraries(itinerary_request, itinerary_details):
                filtered_itineraries.append(itinerary_details)

        if not filtered_itineraries:
            return jsonify({"message": "No itineraries found matching criteria or no availability."}), 404

        return jsonify(filtered_itineraries), 200
    
    def _start_rabbitmq_consumers(self):
        ch = create_channel()
        ch.queue_declare(queue=RESERVATION_CREATED_QUEUE)
        ch.queue_declare(queue=RESERVATION_CANCELLED_QUEUE)
        ch.basic_consume(queue=RESERVATION_CREATED_QUEUE, on_message_callback=self._consume_reservation_created, auto_ack=False)
        ch.basic_consume(queue=RESERVATION_CANCELLED_QUEUE, on_message_callback=self._consume_reservation_cancelled_or_declined, auto_ack=False)
        ch.start_consuming()  

    def _consume_reservation_created(self, ch, method, properties, body):
        data = json.loads(body)
        itinerary_id = int(data.get("itinerary_id"))
        passengers = int(data.get("passengers", 1))
        id = int(data.get("id"))
        self.reservations[id] = {
            "itinerary_id": itinerary_id,
            "passengers": passengers,
            "timestamp": datetime.now().isoformat()
        }

        if self.all_itineraries[itinerary_id].get("available_cabins", 0) >= passengers:
            self.all_itineraries[itinerary_id]["available_cabins"] -= passengers
            print(f"[Itinerary MS] Reservation created: {passengers} cabins booked for itinerary {itinerary_id}. Remaining: {self.all_itineraries[itinerary_id]['available_cabins']}.")

        ch.basic_ack(method.delivery_tag)

    def _consume_reservation_cancelled_or_declined(self, ch, method, properties, body):
        data = json.loads(body)
        print(self.reservations)
        id = int(data.get("reservation_id"))
        print(f"[Itinerary MS] Processing cancellation/decline for reservation ID: {id}")
        print(self.reservations.get(id))
        itinerary_id = self.reservations.get(id, {}).get("itinerary_id")
        passengers = self.reservations.get(id, {}).get("passengers", 1)


        if itinerary_id in self.all_itineraries:
            self.all_itineraries[itinerary_id]["available_cabins"] = min(
                self.all_itineraries[itinerary_id]["available_cabins"] + passengers,
                self.all_itineraries[itinerary_id]["total_cabins"]
            )
            print(f"[Itinerary MS] Updated availability for itinerary {itinerary_id}: {self.all_itineraries[itinerary_id]['available_cabins']} available cabins.")
        else:
            print(f"[Itinerary MS] Itinerary {itinerary_id} not found for cancellation/declined.")
        ch.basic_ack(method.delivery_tag)

    def _get_itinerary_id_from_request(self, id):
        return jsonify(self.all_itineraries.get(int(id), {"message": "Itinerary not found."})), 200

    def _filter_itineraries(self, itinerary_request, itinerary_details):
        print(itinerary_details)
        match_destination = not itinerary_request.destination or itinerary_details["destination"].lower() == itinerary_request.destination.lower()
        match_port = not itinerary_request.boarding_port or itinerary_details["departurePort"].lower() == itinerary_request.boarding_port.lower()
        match_date = not itinerary_request.date or datetime.strptime(itinerary_details["departure"], "%Y-%m-%d").date() == itinerary_request.date
        should_filter = itinerary_details["available_cabins"] > 0 or not any([itinerary_request.destination, itinerary_request.date, itinerary_request.boarding_port])
        return  match_destination and match_port and match_date and should_filter
    
    def run(self):
        print("[Itinerary MS] Starting Flask application on port 5003...")
        self.app.run(host='0.0.0.0', port=5003, debug=True, use_reloader=False)
        print("[Itinerary MS] Flask application started.")

if __name__ == '__main__':
    service = ItineraryService()
    print("[Itinerary MS] Initializing RabbitMQ consumers...")
    service.run()
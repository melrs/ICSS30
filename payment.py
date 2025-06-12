import random
import json
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
from request_dto import PaymentRequest, PaymentPayload, PaymentResponse

load_dotenv()
from config import (
    PAYMENT_EXCHANGE, PAYMENT_APPROVED_QUEUE, PAYMENT_DECLINED_QUEUE,
    ITINERARIES_FILE, PAYMENT_PRIVATE_KEY_FILE, EXTERNAL_PAYMENT_SYSTEM_URL
)
from utils import load_itineraries, create_channel, sign_message

class PaymentService:
    def __init__(self):
        self.app = Flask(__name__)
        self.itineraries = load_itineraries(ITINERARIES_FILE)
        self.channel = create_channel()
        self.channel.exchange_declare(exchange=PAYMENT_EXCHANGE, exchange_type='direct')
        self._register_routes()
    
    def request_payment_link(self):
        print("[Payment API] Received payment request")
        try:
            data = self._load_data_or_cry()
            print(data)
            transaction_id = f"PAY-{random.randint(100000, 999999)}"
            print(f"[Payment API] Sending payment request to external system: {EXTERNAL_PAYMENT_SYSTEM_URL}")
            payload = self._create_payload(PaymentRequest.from_dict(data), transaction_id)
            response = requests.post(EXTERNAL_PAYMENT_SYSTEM_URL, json=payload)
            response.raise_for_status()
            
            return self._create_response(response, transaction_id), 200
        except Exception as e:
            print(f"[Payment API ERROR] Unexpected error: {e}")
            return jsonify({"error": "Unexpected error occurred"}), 500

    def receive_payment_webhook(self):
        try:
            data = self._load_data_or_cry()
            print(f"[Payment Webhook] Received data: {data}")
            payload = PaymentPayload.from_dict(data)
            print(f"[Payment Webhook] Received payment notification: {payload}")
            message_content = f"Transaction {payload.transaction_id} for {payload.amount} {payload.currency} from {payload.buyer_info} for itinerary {payload.itinerary_id} was {payload.status}."
            signed_message = self._create_signed_message(message_content, payload)
            self.channel.basic_publish(
                exchange=PAYMENT_EXCHANGE,
                routing_key=self._get_routing_key(payload.status),
                body=json.dumps(signed_message)
            )
            print(f"[Payment] Message published")
        except Exception as e:
            print(f"[Payment Error] Failed to publish message to RabbitMQ: {e}")
            return jsonify({"error": "Internal server error during message publishing"}), 500

        return jsonify({"message": f"Payment notification received and processed: {payload.status}"}), 200

    def _register_routes(self):
        self.app.add_url_rule('/payments/request-link', view_func=self.request_payment_link, methods=['POST'])
        self.app.add_url_rule('/payments/webhook', view_func=self.receive_payment_webhook, methods=['POST'])

    def _load_data_or_cry(self):
        data = request.get_json()
        if not data:
            raise ValueError("Invalid JSON data received")
        return data
    
    def _create_response(self, response, transaction_id):
        return jsonify(PaymentResponse.from_dict(
            response.json(),
            transaction_id, 
            "Payment link generated successfully by external system.",
            "pending_external_confirmation"
        ).to_dict())
    
    def _create_payload(self, request, transaction_id):
        return PaymentPayload.from_request(request, transaction_id).to_dict()

    def _get_routing_key(self, status):
        routing_map = {
            'approved': PAYMENT_APPROVED_QUEUE,
            'declined': PAYMENT_DECLINED_QUEUE
        }
        routing_key = routing_map.get(status)
        if not routing_key:
            raise ValueError(f"Invalid payment status: {status}")
        
        return routing_key
    
    def _create_signed_message(self, message, payload: PaymentPayload):
        return {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "signature": sign_message(message, PAYMENT_PRIVATE_KEY_FILE),
            "data": payload.to_dict()
        }

    def run(self):
        print("[Payment MS] Starting Flask application...")
        self.app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
        try:
            # self.channel.close()
            print("[Payment MS] RabbitMQ connection closed.")
        except Exception as e:
            print(f"[Payment MS] Error closing RabbitMQ connection: {e}")

if __name__ == '__main__':
    service = PaymentService()
    service.run()

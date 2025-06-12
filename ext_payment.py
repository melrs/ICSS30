from flask import Flask, request, jsonify
import random
import requests
import threading
from config import PAYMENT_WEBHOOK_URL
from request_dto import PaymentPayload, PaymentResponse

class ExternalPaymentSystem:
    def __init__(self):
        self.app = Flask(__name__)
        self._register_routes()
    
    def _register_routes(self):
        self.app.add_url_rule('/ext/process', view_func=self.process_payment, methods=['POST'])

    def process_payment(self):
        data = self._load_data_or_cry()
        payload = PaymentPayload.from_dict(data)
        payload.status = random.choice(['approved', 'declined'])
        threading.Thread(target=self.send_webhook_notification, args=(payload.to_dict(),)).start()

        return self._create_response(payload), 200

    def _create_response(self, payload):
       return jsonify(PaymentResponse(
            message=f"Payment processing initiated for transaction {payload.transaction_id}.",
            payment_link=f"http://localhost:5002/w/{payload.transaction_id}",
            transaction_id=payload.transaction_id,
            external_transaction_id=payload.transaction_id,
            status=payload.status
        ).to_dict())
    
    def _load_data_or_cry(self):
        data = request.get_json()
        if not data:
            raise ValueError("Invalid JSON data received")
        return data
    
    def send_webhook_notification(self, payload):
        try:
            print(f"[External Payment System] Sending webhook to {PAYMENT_WEBHOOK_URL} with status: {payload['status']} for transaction {payload['transaction_id']}")
            response = requests.post(PAYMENT_WEBHOOK_URL, json=payload)
            response.raise_for_status()
            print(f"[External Payment System] Webhook sent successfully for transaction {payload['transaction_id']}. Response: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[External Payment System ERROR] Failed to send webhook for transaction {payload['transaction_id']}: {e}")

    def run(self):
        print("[External Payment System] Starting Flask application on port 5002...")
        self.app.run(host='0.0.0.0', port=5002, debug=True, use_reloader=False)

if __name__ == '__main__':
    payment_system = ExternalPaymentSystem()
    payment_system.run()
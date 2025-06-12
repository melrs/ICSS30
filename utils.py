from collections import namedtuple
from datetime import datetime
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import json, pika
from config import RABBITMQ_HOST

PaymentRequest = namedtuple('PaymentRequest', ['itinerary_id', 'passengers', 'total_price', 'buyer_info', 'currency'])

def create_channel():
    conn = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    ch = conn.channel()
    return ch

def is_valid_date(date_var):
    try:
        datetime.strptime(date_var, "%d/%m/%Y")
        return True
    except ValueError:
        return False

def load_itineraries(file_name):
    with open(file_name, "r") as f:
        itineraries = {itinerary["id"]: itinerary for itinerary in json.load(f)}
    return itineraries

def sign_message(message, file_name):
    private_key = serialization.load_pem_private_key(open(file_name, "rb").read(), password=None)
    return private_key.sign(
        message.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    ).hex()

def verify_signature(message, signature, pub_key_path):
    with open(pub_key_path, "rb") as f:
        pub_key = serialization.load_pem_public_key(f.read())

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
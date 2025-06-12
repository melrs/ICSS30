# Constants for queue names

RESERVATION_CREATED_QUEUE = "reservation-created"
RESERVATION_CANCELLED_QUEUE = "reservation-cancelled"
PAYMENT_APPROVED_TICKED_QUEUE = "payment-approved-ticket"
PAYMENT_APPROVED_QUEUE = "payment-approved"
PAYMENT_DECLINED_QUEUE = "payment-declined"
TICKET_ISSUED_QUEUE = "ticket-issued"
PAYMENT_EXCHANGE = "payment-exchange"
TICKET_EXCHANGE = "ticket-exchange"
RESERVATION_CANCELLED_QUEUE = "reservation-cancelled"
MARKETING_EXCHANGE = "marketing-exchange"
RESERVATION_QUEUES = [
    RESERVATION_CREATED_QUEUE,
    PAYMENT_APPROVED_QUEUE,
    PAYMENT_DECLINED_QUEUE,
    TICKET_ISSUED_QUEUE
]

# Constants for file paths
ITINERARIES_FILE = "itineraries.json"
PAYMENT_PUBLIC_KEY_FILE = "payment_public.pem"
PAYMENT_PRIVATE_KEY_FILE = "payment_private.pem"

# Constants for RabbitMQ connection parameters
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 15672

# Constants for cryptographic parameters
HASH_ALGORITHM = "SHA256"
SIGNATURE_PADDING = "PKCS1v15"

# Constants for message formats
RESERVATION_MESSAGE_FORMAT = {
    "destination": str,
    "ship": str,
    "price": float,
    "date": str,
    "passengers": int,
    "timestamp": str
}

PAYMENT_MESSAGE_FORMAT = {
    "message": str,
    "signature": str
}

# Constants for GUI elements
WINDOW_TITLE = "Cruise Reservation System"
WINDOW_SIZE = "800x600"

ITINERARY_TEMPLATE = """
----------------------------------------
ID: {id}
Destination: {destination}
Ship: {ship}
Departure: {departure}
Arrival: {arrival}
Stops: {stops}
Nights: {nights}
Price: {price}
Boarding Port: {departurePort}
----------------------------------------
"""

ITINERARY_TEMPLATES = (
    "Destination: {destination}\n"
    "Ship: {ship}\n"
    "Departure: {departure}\n"
    "Price: {price}\n"
    "Boarding Port: {boarding_port}\n"
)
# Constants for GUI messages
SEARCH_SUCCESS_MESSAGE = "Search completed successfully."
SEARCH_FAILURE_MESSAGE = "No itineraries found."

EXTERNAL_PAYMENT_SYSTEM_URL = "http://localhost:5002/ext/process"
PAYMENT_WEBHOOK_URL = "http://localhost:5001/payments/webhook"

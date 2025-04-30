# Constants for queue names

RESERVATION_CREATED_QUEUE = "reservation-created"
PAYMENT_APPROVED_TICKED_QUEUE = "payment-approved-ticket"
PAYMENT_APPROVED_RESERVE_QUEUE = "payment-approved-reserve"
PAYMENT_DECLINED_QUEUE = "payment-declined"
TICKET_ISSUED_QUEUE = "ticket-issued"
PAYMENT_APPROVED_EXCHANGE = "payment-approved-exchange"
RESERVATION_QUEUES = [
    RESERVATION_CREATED_QUEUE,
    PAYMENT_APPROVED_RESERVE_QUEUE,
    PAYMENT_DECLINED_QUEUE,
    TICKET_ISSUED_QUEUE
]

# Constants for file paths
ITINERARIES_FILE = "itineraries.json"
PAYMENT_PUBLIC_KEY_FILE = "payment_public.pem"
PAYMENT_PRIVATE_KEY_FILE = "payment_private.pem"

# Constants for RabbitMQ connection parameters
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672

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

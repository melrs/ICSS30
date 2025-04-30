
# 🚢 Cruise Reservation System with Microservices, RabbitMQ, and Asymmetric Keys

This project was developed as part of the **Distributed Systems** course (UTFPR - 2023/2) to apply concepts of **microservices**, **asynchronous messaging (RabbitMQ)**, and **asymmetric key cryptography**.

## 📦 General Architecture

The system consists of 4 main microservices and 1 promotions subscriber:

- **Reservation MS**: Manages itineraries, reservations, and process status.
- **Payment MS**: Simulates payment validation and digitally signs messages.
- **Ticket MS**: Generates tickets after payment confirmation.
- **Marketing MS**: Publishes promotions for specific destinations.
- **Subscriber**: Consumes promotions for desired destinations.

Communication between microservices is handled via **RabbitMQ**, using **fanout exchange and specific queues** to ensure multiple services receive the same message when necessary.

## 🔐 Security with Digital Signatures

- The **Payment MS** generates a key pair (private/public).
- It **digitally signs** payment approval/rejection messages.
- Other microservices verify the signature using the **public key**.

## ⚙️ Prerequisites

- Python 3.8+
- RabbitMQ running locally (`localhost:5672`)
- Python dependencies 

## ▶️ How to Run the Project

### 1. Start RabbitMQ
Ensure RabbitMQ is installed and running locally.

### 2. Generate the key pair (if not already generated)

```bash
openssl genrsa -out keys/payment_private.pem 2048
openssl rsa -in keys/payment_private.pem -pubout -out keys/payment_public.pem
```

### 3. Run the microservices in separate terminals

```bash
# Terminal 1 - Reservation MS
python app_reservation.py

# Terminal 2 - Payment MS
python payment.py

# Terminal 3 - Ticket MS
python ticket.py

# Terminal 4 - Marketing MS
python marketing.py

# Terminal 5 - Promotions Subscriber
python subscriber_promotion.py
```

## 🧪 Testing and Verification

- Test reservations with approved and rejected payments.
- Verify that the digital signature is correctly validated by the consuming microservices.
- Payment approval messages should be received by both **Reservation MS** and **Ticket MS**.

---

UTFPR - Curitiba | 2025/1


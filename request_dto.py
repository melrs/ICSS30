from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
from datetime import date, datetime

@dataclass
class PaymentRequest:
    itinerary_id: int
    passengers: int
    total_price: Decimal
    client_id: int
    currency: str = "USD"

    def from_dict(data: dict) -> "PaymentRequest":
        instance = PaymentRequest(
            itinerary_id=data.get("itinerary_id", 0), 
            passengers=data.get("passengers", 1),
            total_price=Decimal(data.get("total_price", 0)),
            client_id=data.get("client_id", 0),
            currency=data.get("currency", "USD")
        )
        instance._validate_data(data)
        return instance

    def _validate_data(self, data: dict):
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary.")
        if not all(key in data for key in ["itinerary_id", "passengers", "total_price", "client_id"]):
            raise ValueError("Missing required fields: itinerary_id, passengers, total_price, client_id.")
        if not isinstance(data["itinerary_id"], int) or data["itinerary_id"] <= 0:
            raise ValueError("itinerary_id must be a positive integer.")
        if not isinstance(data["passengers"], int) or data["passengers"] <= 0:
            raise ValueError("passengers must be a positive integer.")
        if not isinstance(data["total_price"], (int, float, Decimal)):
            raise ValueError("total_price must be a number.")
        if not isinstance(data["client_id"], int):
            raise ValueError("client_id must be a number.")
        if "currency" in data and not isinstance(data["currency"], str):
            raise ValueError("currency must be a string.")

@dataclass
class PaymentPayload:
    transaction_id: str
    amount: Decimal
    currency: str
    client_id: int
    itinerary_id: int
    status: str

    def from_request(request: PaymentRequest, transaction_id):
        return PaymentPayload(
            transaction_id=transaction_id,
            amount=request.total_price,
            currency=request.currency,
            client_id=request.client_id,
            itinerary_id=request.itinerary_id,
            status="pending_external_confirmation"
        )

    def from_dict(data: dict) -> "PaymentPayload":
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary.")
        if not all(key in data for key in ["transaction_id", "amount", "currency", "client_id", "itinerary_id", "status"]):
            raise ValueError("Missing required fields: transaction_id, amount, currency, client_id, itinerary_id, status.")
        
        return PaymentPayload(
            transaction_id=data["transaction_id"],
            amount=Decimal(data["amount"]),
            currency=data["currency"],
            client_id=data["client_id"],
            itinerary_id=data["itinerary_id"],
            status=data["status"]
        )

    def to_dict(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "amount": str(self.amount),  # Convert Decimal to string for JSON serialization
            "currency": self.currency,
            "client_id": self.client_id,
            "itinerary_id": self.itinerary_id,
            "status": self.status
        }

@dataclass
class PaymentResponse:
    message: str
    payment_link: Optional[str] = None
    transaction_id: Optional[str] = None
    external_transaction_id: Optional[str] = None
    status: str = "pending_external_confirmation"

    def from_dict(data: dict, transaction_id: Optional[str] = None, message: Optional[str] = None, status: Optional[str] = None) -> "PaymentResponse":
        instance = PaymentResponse(
            message=message,
            payment_link=data.get("payment_link"),
            transaction_id=transaction_id,
            external_transaction_id=data.get("external_transaction_id", None),
            status=status
        )

        if not isinstance(status, str):
            raise ValueError("status must be a string.")
        
        if not instance.payment_link:
            print("[Payment API ERROR] External system did not return a payment link.")
            raise ValueError("External payment system response missing payment link.")
        return instance

    def to_dict(self) -> dict:
        response = {
            "message": self.message,
            "status": self.status
        }
        if self.payment_link:
            response["payment_link"] = self.payment_link
        if self.transaction_id:
            response["transaction_id"] = self.transaction_id
        if self.external_transaction_id:
            response["external_transaction_id"] = self.external_transaction_id
        return response

@dataclass
class Itinerary:
    destination: Optional[str] = ""
    date: Optional["date"] = None
    boarding_port: Optional[str] = ""
    id: Optional[int] = None

    def from_dict(data: dict) -> "Itinerary":
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary.")
        
        return Itinerary(
            destination=data.get("destination", None),
            date=datetime.strptime(data["departure"], "%Y-%m-%d").date() if "departure" in data else None,
            boarding_port=data.get("boarding_port", None),
            id=data.get("id", None)
        )
    
    def to_dict(self) -> dict:
        return {
            "destination": self.destination,
            "date": self.date.isoformat() if self.date else None,
            "boarding_port": self.boarding_port,
            "id": self.id
        }


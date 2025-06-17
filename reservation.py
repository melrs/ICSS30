import json
import threading
import time
import random
from datetime import datetime
from flask import Flask, request, jsonify, url_for
import pika
import requests
from flask_sse import sse
from flask_cors import CORS 

from config import (
    RABBITMQ_HOST, RESERVATION_CREATED_QUEUE,
    PAYMENT_APPROVED_QUEUE, PAYMENT_DECLINED_QUEUE, TICKET_ISSUED_QUEUE,
    PAYMENT_EXCHANGE, TICKET_EXCHANGE, MARKETING_EXCHANGE,
    PAYMENT_PUBLIC_KEY_FILE, RESERVATION_CANCELLED_QUEUE, ITINERARIES_FILE
)
from utils import create_channel, verify_signature, load_itineraries # load_itineraries ainda é usado para carregar destinos para promoções

app = Flask(__name__)
app.config["REDIS_URL"] = "redis://localhost"
app.config['SERVER_NAME'] = 'localhost:5000'
app.config['PREFERRED_URL_SCHEME'] = 'http'
app.register_blueprint(sse, url_prefix='/sse')
MS_ITINERARIES_URL = "http://localhost:5003"
MS_PAYMENT_URL = "http://localhost:5001"
CORS(app)

publish_channel = create_channel()
publish_channel.exchange_declare(exchange=PAYMENT_EXCHANGE, exchange_type='direct')
publish_channel.exchange_declare(exchange=TICKET_EXCHANGE, exchange_type='direct')
publish_channel.exchange_declare(exchange=MARKETING_EXCHANGE, exchange_type='direct')
publish_channel.queue_declare(queue=RESERVATION_CREATED_QUEUE)
publish_channel.queue_declare(queue=RESERVATION_CANCELLED_QUEUE)

promotion_subscribers = []

def _publish_sse_event(channel_name, event_type, message_data):
    try:
        with app.app_context():
            sse.publish(message_data, type=event_type, channel=channel_name)
            print(f"[Reservation MS - SSE] Publicado '{event_type}' no canal '{channel_name}': {message_data.get('message', '')[:50]}...")
    except Exception as e:
        print(f"[Reservation MS - SSE Error] Falha ao publicar SSE no canal '{channel_name}': {e}")

def _get_client_status_channel(client_id):
    return f"reservation-status-{client_id}"

def _get_promo_channel(client_id):
    return f"promotions-{client_id}"

def _handle_payment_approved(ch, method, properties, body):
    data = json.loads(body)
    message_to_verify = f"{data['timestamp']}|{data['message']}"
    if verify_signature(message_to_verify, data["signature"], PAYMENT_PUBLIC_KEY_FILE):
        print(f"[Reservation MS - Consumer] Pagamento Aprovado: {data['message']}")
        client_id = None
        try: 
            client_id_part = data['message'].split("from Client ")[1].split(" for itinerary")[0].strip()
            if client_id_part: client_id = client_id_part
        except (IndexError, ValueError): pass
        
        target_channel = _get_client_status_channel(client_id) if client_id else "general_reservation_status"
        _publish_sse_event(target_channel, 'payment_approved', data)
    else:
        print("[Reservation MS - Consumer] Assinatura inválida para pagamento aprovado. Ignorando.")
    ch.basic_ack(method.delivery_tag)

def _handle_payment_declined(ch, method, properties, body):
    data = json.loads(body)
    message_to_verify = f"{data['timestamp']}|{data['message']}"
    if verify_signature(message_to_verify, data["signature"], PAYMENT_PUBLIC_KEY_FILE):
        print(f"[Reservation MS - Consumer] Pagamento Recusado: {data['message']}")
        client_id = None
        try:
            client_id_part = data['message'].split("from Client ")[1].split(" for itinerary")[0].strip()
            if client_id_part: client_id = client_id_part
        except (IndexError, ValueError): pass

        target_channel = _get_client_status_channel(client_id) if client_id else "general_reservation_status"
        _publish_sse_event(target_channel, 'payment_declined', data)
    else:
        print("[Reservation MS - Consumer] Assinatura inválida para pagamento recusado. Ignorando.")
    ch.basic_ack(method.delivery_tag)

def _handle_ticket_issued(ch, method, properties, body):
    data = json.loads(body)
    print(f"[Reservation MS - Consumer] Bilhete Emitido: {data['message']}")
    client_id = None
    try:
        client_id_part = data['message'].split("from Client ")[1].split(" for itinerary")[0].strip()
        if client_id_part: client_id = client_id_part
    except (IndexError, ValueError): pass

    target_channel = _get_client_status_channel(client_id) if client_id else "general_reservation_status"
    _publish_sse_event(target_channel, 'ticket_issued', data)
    ch.basic_ack(method.delivery_tag)

def _handle_promotion(ch, method, properties, body):
    message = body.decode()
    print(f"[Reservation MS - Consumer] Promoção Recebida: {message}")

    for client_id in promotion_subscribers:
        print(f"[Reservation MS - Consumer] Enviando promoção para cliente {client_id}...")
        _publish_sse_event(_get_promo_channel(client_id), 'promotion', {"message": message})

    ch.basic_ack(method.delivery_tag)

def start_rabbitmq_consumers():
    consumer_channel = create_channel()
    
    consumer_channel.queue_declare(queue=PAYMENT_APPROVED_QUEUE)
    consumer_channel.queue_declare(queue=PAYMENT_DECLINED_QUEUE)
    consumer_channel.queue_declare(queue=TICKET_ISSUED_QUEUE)
    consumer_channel.queue_declare(queue=RESERVATION_CANCELLED_QUEUE)
    consumer_channel.queue_declare(queue=RESERVATION_CREATED_QUEUE)
    consumer_channel.queue_bind(exchange=PAYMENT_EXCHANGE, queue=PAYMENT_APPROVED_QUEUE, routing_key=PAYMENT_APPROVED_QUEUE)
    consumer_channel.queue_bind(exchange=PAYMENT_EXCHANGE, queue=PAYMENT_DECLINED_QUEUE, routing_key=PAYMENT_DECLINED_QUEUE)
    consumer_channel.queue_bind(exchange=TICKET_EXCHANGE, queue=TICKET_ISSUED_QUEUE, routing_key=TICKET_ISSUED_QUEUE)


    consumer_channel.basic_consume(queue=PAYMENT_APPROVED_QUEUE, on_message_callback=_handle_payment_approved, auto_ack=False)
    consumer_channel.basic_consume(queue=PAYMENT_DECLINED_QUEUE, on_message_callback=_handle_payment_declined, auto_ack=False)
    consumer_channel.basic_consume(queue=TICKET_ISSUED_QUEUE, on_message_callback=_handle_ticket_issued, auto_ack=False)
    
    promo_queue_name = consumer_channel.queue_declare(queue='', exclusive=True).method.queue
    consumer_channel.queue_bind(exchange=MARKETING_EXCHANGE, queue=promo_queue_name, routing_key=f'promotions')
    consumer_channel.basic_consume(queue=promo_queue_name, on_message_callback=_handle_promotion, auto_ack=False)

    print("[Reservation MS] Aguardando atualizações de status e promoções do RabbitMQ...")
    consumer_channel.start_consuming()

consumer_thread = threading.Thread(target=start_rabbitmq_consumers, daemon=True)
consumer_thread.start()


@app.route('/api/reserve/itineraries', methods=['GET'])
def get_itineraries():
    destination = request.args.get('destination')
    boarding_date = request.args.get('boarding_date')
    boarding_port = request.args.get('boarding_port')

    params = {k: v for k, v in locals().items() if v is not None and k in ['destination', 'boarding_date', 'boarding_port']}
    
    try:
        response = requests.get(f"{MS_ITINERARIES_URL}/itineraries", params=params)
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Não foi possível conectar ao MS Itinerários. Ele está rodando?"}), 503
    except requests.exceptions.RequestException as e:
        print(f"[Reservation MS ERROR] Erro ao buscar itinerários: {e}")
        return jsonify({"error": "Falha ao recuperar itinerários."}), 500

@app.route('/api/reserve/new', methods=['POST'])
def make_reservation():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON inválido"}), 400

    itinerary_id = data.get('itinerary_id')
    passengers = data.get('passengers')
    client_id = data.get('client_id')

    if not all([itinerary_id, passengers, client_id]):
        return jsonify({"error": "Dados ausentes: itinerary_id, passengers e client_id são obrigatórios"}), 400
    
    print(f"[Reservation MS] Recebida solicitação de reserva: Itinerário ID: {itinerary_id}, Passageiros: {passengers}, Cliente ID: {client_id}")
    try:
        itinerary_response = requests.get(f"{MS_ITINERARIES_URL}/itineraries?id={itinerary_id}")
        itinerary_response.raise_for_status()
        itinerary_details = itinerary_response.json()
        if not itinerary_details:
            return jsonify({"error": "Itinerário não encontrado ou sem cabines disponíveis no MS Itinerários."}), 404

        if itinerary_details.get("available_cabins", 0) <= 0:
            return jsonify({"error": "Itinerário sem cabines disponíveis."}), 409

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Não foi possível conectar ao MS Itinerários para obter detalhes. Ele está rodando?"}), 503
    except requests.exceptions.RequestException as e:
        print(f"[Reservation MS ERROR] Erro ao obter detalhes do itinerário do MS Itinerários: {e}")
        return jsonify({"error": "Falha ao validar itinerário."}), 500
    except Exception as e:
        print(f"[Reservation MS ERROR] Ocorreu um erro inesperado ao obter detalhes do itinerário: {e}")
        return jsonify({"error": "Ocorreu um erro inesperado."}), 500

    total_price = itinerary_details['price'] * passengers
    buyer_info = {"name": f"Client {client_id}", "email": f"client{client_id}@example.com"}

    reservation_data = {
        "id": int(time.time()) + random.randint(1000, 9999),
        "itinerary_id": itinerary_id,
        "passengers": passengers,
        "total_price": total_price,
        "client_id": client_id,
        "timestamp": datetime.now().isoformat()
    }

    print(f"[Reservation MS] Criando reserva: {reservation_data}")

    try:
        publish_channel.basic_publish(
            exchange='', routing_key=RESERVATION_CREATED_QUEUE,
            body=json.dumps(reservation_data)
        )
        print(f"[Reservation MS] Mensagem de reserva criada publicada para o itinerário {itinerary_id}.")

        payment_request_payload = {
            "itinerary_id": itinerary_id, 
            "passengers": passengers,
            "total_price": total_price, 
            "buyer_info": buyer_info,
            "client_id": client_id,
            "currency": "BRL",
        }
        print(f"[Reservation MS] Solicitando link de pagamento ao MS Pagamento para o itinerário {itinerary_id}.")
        payment_response = requests.post(f"{MS_PAYMENT_URL}/payments/request-link", json=payment_request_payload)
        payment_response.raise_for_status()

        payment_data = payment_response.json()
        payment_link = payment_data.get('payment_link')
        transaction_id = payment_data.get('transaction_id')

        if not payment_link:
            return jsonify({"error": "O MS Pagamento não retornou um link de pagamento."}), 500

        return jsonify({
            "message": "Reserva criada e link de pagamento solicitado.",
            "reservation_id": reservation_data['id'],
            "payment_link": payment_link,
            "transaction_id": transaction_id,
            "sse_channel_for_status": _get_client_status_channel(client_id)
        }), 201

    except pika.exceptions.AMQPConnectionError as e:
        print(f"[Reservation MS ERROR] Erro de conexão com RabbitMQ: {e}")
        return jsonify({"error": "Erro interno do servidor: Problema de conexão com RabbitMQ."}), 500
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Não foi possível conectar ao MS Pagamento. Ele está rodando?"}), 503
    except requests.exceptions.RequestException as e:
        print(f"[Reservation MS ERROR] Erro durante a solicitação de link de pagamento: {e}")
        return jsonify({"error": f"Falha ao obter link de pagamento: {e}"}), 500
    except Exception as e:
        print(f"[Reservation MS ERROR] Ocorreu um erro inesperado: {e}")
        return jsonify({"error": "Ocorreu um erro inesperado."}), 500

@app.route('/api/reserve/cancel/<reservation_id>', methods=['DELETE'])
def cancel_reservation(reservation_id):
    cancel_data = {
        "reservation_id": int(reservation_id),
        "timestamp": datetime.now().isoformat(),
        "status": "cancelled",
    }
    print(f"[Reservation MS] Recebida solicitação de cancelamento da reserva: {reservation_id}")
    try:
        publish_channel.basic_publish(
            exchange='', routing_key=RESERVATION_CANCELLED_QUEUE,
            body=json.dumps(cancel_data)
        )
        print(f"[Reservation MS] Mensagem de cancelamento da reserva {reservation_id} publicada.")
        return jsonify({"message": f"Solicitação de cancelamento da reserva {reservation_id} iniciada."}), 200
    except pika.exceptions.AMQPConnectionError as e:
        print(f"[Reservation MS ERROR] Erro de conexão com RabbitMQ: {e}")
        return jsonify({"error": "Erro interno do servidor: Problema de conexão com RabbitMQ."}), 500
    except Exception as e:
        print(f"[Reservation MS ERROR] Ocorreu um erro inesperado durante o cancelamento: {e}")
        return jsonify({"error": "Ocorreu um erro inesperado."}), 500

@app.route('/api/reserve/promotions/subscribe', methods=['POST'])
def subscribe_to_promotions():
    data = request.get_json()
    if not data or 'client_id' not in data:
        return jsonify({"error": "client_id ausente"}), 400
    
    client_id = int(data['client_id'])

    if client_id not in promotion_subscribers:
        promotion_subscribers.append(client_id)
        print(f"[Reservation MS] Cliente {client_id} inscrito em promoções.")

    return jsonify({"message": "Inscrito com sucesso em promoções.", "client_id": client_id}), 200

@app.route('/api/reserve/promotions/unsubscribe', methods=['POST'])
def unsubscribe_from_promotions():
    data = request.get_json()
    print(f"[Reservation MS] Recebida solicitação de cancelamento de inscrição em promoções: {data}")
    if not data or 'client_id' not in data:
        return jsonify({"error": "client_id ausente"}), 400
    
    client_id = int(data['client_id'])
    if client_id in promotion_subscribers:
        promotion_subscribers.remove(client_id)
        print(f"[Reservation MS] Cliente {client_id} cancelou a inscrição em promoções.")
        return jsonify({"message": "Cancelamento de inscrição em promoções bem-sucedido."}), 200
    else:
        print(f"[Reservation MS] Cliente {client_id} não estava inscrito em promoções.")
        return jsonify({"error": "Cliente não estava inscrito em promoções."}), 404

# --- Inicialização da Aplicação Flask ---

if __name__ == '__main__':
    print("[Reservation MS] Iniciando aplicação Flask na porta 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

    try:
        # if publish_channel and publish_channel.is_open:
        #     publish_channel.close()
        print("[Reservation MS] Canal de publicação RabbitMQ fechado.")
    except Exception as e:
        print(f"[Reservation MS] Erro ao fechar canal de publicação RabbitMQ: {e}")
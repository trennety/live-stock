import pika
import pymongo
import json
import os

# Konfigurationen aus Umgebungsvariablen laden
rabbitmq_host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
rabbitmq_port = int(os.getenv('RABBITMQ_PORT', 5672))
queue_name = os.getenv('QUEUE_NAME', 'default_queue')
mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://mongo1:27017,mongo2:27018,mongo3:27019/?replicaSet=rs0')
mongodb_db = 'stockmarket'
mongodb_collection = 'stocks'

# Glättungsfaktor für den EMA
alpha = 0.1

# Verbindung zu RabbitMQ herstellen
try:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port))
    channel = connection.channel()
    print(f"Connecting to RabbitMQ at {rabbitmq_host}:{rabbitmq_port}")
except pika.exceptions.AMQPConnectionError as e:
    print(f"Failed to connect to RabbitMQ at {rabbitmq_host}:{rabbitmq_port} - {str(e)}")
    exit(1)

# Verbindung zu MongoDB herstellen
try:
    client = pymongo.MongoClient(mongodb_uri)
    db = client[mongodb_db]
    collection = db[mongodb_collection]
    print(f"Connecting to MongoDB at {mongodb_uri}")
except pymongo.errors.ServerSelectionTimeoutError as e:
    print(f"Failed to connect to MongoDB at {mongodb_uri} - {str(e)}")
    exit(1)

# Hole den aktuellen Durchschnittspreis aus der MongoDB
current_data = collection.find_one({'type': 'average_price'})
if current_data:
    avg_price = current_data['avgPrice']
else:
    avg_price = 0.0

def callback(ch, method, properties, body):
    global avg_price
    
    try:
        # Daten laden und Preis extrahieren
        data = json.loads(body)
        price = float(data['price'])

        # Berechne den exponentiellen gleitenden Durchschnitt
        avg_price = round(alpha * price + (1 - alpha) * avg_price, 2)
        print(f"Neuer Durchschnittspreis: {avg_price}")

        # Durchschnittspreis in die MongoDB speichern
        collection.update_one(
            {'type': 'average_price'},
            {'$set': {'avgPrice': avg_price}},
            upsert=True
        )

        # Nachricht nach erfolgreicher Verarbeitung bestätigen
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except (json.JSONDecodeError, ValueError) as e:
        print(f"Fehler bei der Verarbeitung der Nachricht: {e}")
        # Nachricht wird nicht bestätigt und bleibt in der Warteschlange, um erneut verarbeitet zu werden

    except Exception as e:
        print(f"Unerwarteter Fehler: {e}")
        # Nachricht wird nicht bestätigt und bleibt in der Warteschlange, um erneut verarbeitet zu werden

# RabbitMQ Queue konsumieren
channel.basic_consume(queue=queue_name, on_message_callback=callback)

print(f" [*] Waiting for messages in {queue_name}. To exit press CTRL+C")
channel.start_consuming()

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

# Liste zum Zwischenspeichern der letzten 1000 Preise
price_buffer = []
batch_size = 1000  # Anzahl der Datenpakete, die gesammelt werden sollen

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

def calculate_and_store_average():
    """Berechnet den Durchschnitt der gesammelten Preise und speichert ihn in MongoDB."""
    global price_buffer
    
    if price_buffer:
        avg_price = round(sum(price_buffer) / len(price_buffer), 2)
        print(f"Berechneter Durchschnittspreis für {queue_name}: {avg_price}")
        
        # Durchschnittspreis in die MongoDB für die spezifische Warteschlange speichern
        collection.update_one(
            {'queue': queue_name},
            {'$set': {'avgPrice': avg_price}},
            upsert=True
        )
        
        # Liste zurücksetzen
        price_buffer = []

def callback(ch, method, properties, body):
    global price_buffer

    try:
        # Daten laden und Preis extrahieren
        data = json.loads(body)
        price = float(data['price'])

        # Preis zum Zwischenspeicher hinzufügen
        price_buffer.append(price)
        print(f"Preis für {queue_name} hinzugefügt: {price}")

        # Wenn 1000 Datenpakete gesammelt wurden, berechne den Durchschnitt und speichere ihn
        if len(price_buffer) >= batch_size:
            calculate_and_store_average()

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
